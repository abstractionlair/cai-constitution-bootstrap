#!/usr/bin/env python3
"""
Expand Evaluation Set

Generate additional test instructions to reach 300+ examples with zero train/test leakage.

Usage:
    python scripts/expand_eval_set.py
"""

import json
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set

# Import utilities
import sys
sys.path.append(str(Path(__file__).parent.parent))

from scripts.utils.clean_model_loader import CleanModelLoader
from scripts.utils.completion_prompts import CompletionStylePrompts

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def load_training_instructions(path: Path) -> Set[str]:
    """Load all training instructions to check for leakage."""
    instructions = set()
    with open(path, 'r') as f:
        for line in f:
            ex = json.loads(line)
            instructions.add(ex['instruction'].strip().lower())
    return instructions


def load_existing_test_instructions(path: Path) -> List[Dict[str, Any]]:
    """Load existing test instructions."""
    instructions = []
    with open(path, 'r') as f:
        for line in f:
            instructions.append(json.loads(line))
    return instructions


def generate_test_instructions(
    model,
    tokenizer,
    prompts: CompletionStylePrompts,
    num_to_generate: int,
    excluded: Set[str],
    seed: int = 200
) -> List[Dict[str, Any]]:
    """
    Generate new test instructions ensuring no overlap with training.

    Args:
        model: Loaded model instance
        tokenizer: Loaded tokenizer instance
        prompts: CompletionStylePrompts instance
        num_to_generate: Number of instructions to generate
        excluded: Set of instructions to exclude (training set)
        seed: Random seed

    Returns:
        List of generated test instructions
    """
    random.seed(seed)

    # Instruction types
    instruction_types = [
        'factual',
        'explanation',
        'list_generation',
        'creative',
        'instruction_following'
    ]

    generated = []
    attempts = 0
    max_attempts = num_to_generate * 3

    logger.info(f"Generating {num_to_generate} test instructions (seed={seed})")
    logger.info(f"  Excluding {len(excluded)} training instructions")

    while len(generated) < num_to_generate and attempts < max_attempts:
        attempts += 1

        # Round-robin through types
        inst_type = instruction_types[len(generated) % len(instruction_types)]

        # Generate instruction using loader's generation method
        prompt = prompts.create_instruction_generation_prompt()

        # Use model and tokenizer passed in
        import torch

        inputs = tokenizer(
            prompt,
            add_special_tokens=False,
            return_tensors="pt"
        ).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.8,  # Higher temperature for diversity
                top_p=0.95,
                repetition_penalty=1.15,  # Stronger penalty for diversity
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id
            )

        # Decode and parse
        full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
        completion = full_output[len(prompt):].strip()

        # Parse numbered lines
        lines = [l.strip() for l in completion.split('\n') if l.strip()]

        for line in lines[:3]:  # Take up to 3 instructions per generation
            # Parse instruction number
            if not line[0].isdigit():
                continue

            # Remove number prefix
            parts = line.split('.', 1)
            if len(parts) < 2:
                parts = line.split(')', 1)
            if len(parts) < 2:
                continue

            instruction = parts[1].strip()

            # Skip empty or meta instructions
            if not instruction or len(instruction) < 10:
                continue
            if any(word in instruction.lower() for word in ['instruction', 'example', 'list', 'generate']):
                continue

            # Check for leakage
            if instruction.strip().lower() in excluded:
                logger.debug(f"  Skipping duplicate: {instruction[:60]}...")
                continue

            # Add to generated
            generated.append({
                'instruction': instruction,
                'type': inst_type,
                'seed': seed + len(generated),
                'generated_at': datetime.now().isoformat()
            })

            # Add to excluded to avoid duplicates within this run
            excluded.add(instruction.strip().lower())

            if len(generated) >= num_to_generate:
                break

        if len(generated) % 10 == 0 and len(generated) > 0:
            logger.info(f"  Generated {len(generated)}/{num_to_generate}...")

    logger.info(f"✅ Generated {len(generated)} unique test instructions")
    return generated


def main():
    """Main evaluation set expansion workflow."""
    logger.info("=" * 60)
    logger.info("EXPAND EVALUATION SET")
    logger.info("=" * 60)

    # Paths
    train_path = Path('data/stage1_sft_data_clean.jsonl')
    test_path = Path('data/test_instructions.jsonl')
    output_path = Path('data/test_instructions_expanded.jsonl')

    # Step 1: Load training instructions
    logger.info(f"\n📥 Loading training instructions from {train_path}")
    train_instructions = load_training_instructions(train_path)
    logger.info(f"   Training set: {len(train_instructions)} unique instructions")

    # Step 2: Load existing test instructions
    logger.info(f"\n📥 Loading existing test instructions from {test_path}")
    existing_test = load_existing_test_instructions(test_path)
    logger.info(f"   Existing test set: {len(existing_test)} instructions")

    # Step 3: Remove overlaps from existing test set
    logger.info(f"\n🔍 Checking for train/test overlap")
    clean_test = []
    removed_overlap = 0

    for inst in existing_test:
        if inst['instruction'].strip().lower() in train_instructions:
            logger.info(f"   Removing overlap: {inst['instruction'][:60]}...")
            removed_overlap += 1
        else:
            clean_test.append(inst)

    logger.info(f"   Removed {removed_overlap} overlapping instructions")
    logger.info(f"   Clean test set: {len(clean_test)} instructions")

    # Step 4: Calculate how many new instructions needed
    target_size = 350  # Aim for 350 to be safe above 300 minimum
    needed = target_size - len(clean_test)

    if needed <= 0:
        logger.info(f"\n✅ Already have {len(clean_test)} instructions (target: {target_size})")
        logger.info("   No expansion needed")
        return 0

    logger.info(f"\n📝 Need to generate {needed} additional instructions")

    # Step 5: Load model
    logger.info(f"\n🔧 Loading model...")
    loader = CleanModelLoader(
        model_name="Qwen/Qwen2.5-32B",
        load_in_4bit=True
    )
    model, tokenizer, provenance = loader.load()
    prompts = CompletionStylePrompts()

    # Step 6: Generate new instructions
    logger.info(f"\n🎲 Generating new test instructions")

    # Create excluded set (training + clean test)
    excluded = train_instructions.copy()
    for inst in clean_test:
        excluded.add(inst['instruction'].strip().lower())

    new_instructions = generate_test_instructions(
        model=model,
        tokenizer=tokenizer,
        prompts=prompts,
        num_to_generate=needed,
        excluded=excluded,
        seed=200
    )

    # Step 7: Combine and save
    logger.info(f"\n💾 Saving expanded evaluation set")
    expanded_test = clean_test + new_instructions

    with open(output_path, 'w') as f:
        for inst in expanded_test:
            f.write(json.dumps(inst) + '\n')

    logger.info(f"   ✅ Saved {len(expanded_test)} instructions to {output_path}")

    # Step 8: Verify no leakage
    logger.info(f"\n🔍 Final verification")
    final_check = set()
    for inst in expanded_test:
        final_check.add(inst['instruction'].strip().lower())

    overlap = final_check & train_instructions
    if overlap:
        logger.error(f"   ❌ Found {len(overlap)} overlapping instructions!")
        for inst in list(overlap)[:3]:
            logger.error(f"      {inst[:60]}...")
        return 1
    else:
        logger.info(f"   ✅ Zero train/test leakage confirmed")

    logger.info("\n" + "=" * 60)
    logger.info("✅ EVALUATION SET EXPANSION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"   Original: {len(existing_test)} instructions")
    logger.info(f"   Removed overlaps: {removed_overlap}")
    logger.info(f"   Generated new: {len(new_instructions)}")
    logger.info(f"   Final: {len(expanded_test)} instructions")
    logger.info(f"   Target: {target_size}+ (spec minimum: 300)")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
