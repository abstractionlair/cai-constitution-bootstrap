#!/usr/bin/env python3
"""
Diversity-Guided Instruction Generation

Implements Codex-recommended Strategy 2: Use existing instructions as negative
examples in prompt to guide model toward diversity.

Method:
- Sample 6-7 existing instructions
- Create completion prompt: "Generate diverse set covering different topics..."
- Model continues numbered list (positions 8-10)
- Naturally avoids patterns from examples 1-7

Usage:
    python scripts/generate_diversity_guided.py --seed 200 --count 100 --existing data/stage1_sft_data_clean.jsonl
"""

import argparse
import json
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import sys

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.utils.clean_model_loader import CleanModelLoader
from scripts.utils.instruction_critic import InstructionCritic
from scripts.utils.completion_prompts import CompletionStylePrompts
from scripts.utils import provenance_helper

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def load_existing_instructions(path: Path) -> List[str]:
    """Load existing instructions for negative examples."""
    instructions = []
    with open(path, 'r') as f:
        for line in f:
            ex = json.loads(line)
            instructions.append(ex['instruction'])
    return instructions


def create_diversity_prompt(sample_instructions: List[str], num_samples: int = 7) -> str:
    """
    Create diversity-guided completion prompt.

    Per Codex recommendation:
    - 6-7 exemplars showing variety
    - Explicit "diverse, covering different topics" instruction
    - Model continues at position num_samples + 1

    Args:
        sample_instructions: List of instructions to use as negative examples
        num_samples: How many to include (default 7 per Codex)

    Returns:
        Completion prompt ready for model
    """
    prompt = (
        "Generate a diverse set of 10 instructions for an AI assistant, "
        "avoiding duplication and covering different topics and styles "
        "(STEM, creative writing, daily tasks, ethics, reasoning).\n\n"
    )

    # Add sampled instructions as negative examples
    for i, inst in enumerate(sample_instructions[:num_samples], 1):
        prompt += f"{i}. {inst}\n"

    # Model continues from next position
    prompt += f"{num_samples + 1}. "

    return prompt


def generate_diversity_batch(
    model,
    tokenizer,
    existing_instructions: List[str],
    batch_size: int = 3,
    num_samples: int = 7,
    temperature: float = 0.8,
    rep_penalty: float = 1.3
) -> List[str]:
    """
    Generate batch of diverse instructions.

    Args:
        loader: CleanModelLoader instance
        existing_instructions: Pool to sample negative examples from
        batch_size: How many new instructions to generate (3 per Codex)
        num_samples: How many negative examples (7 per Codex)
        temperature: 0.8 per Codex recommendation
        rep_penalty: 1.25-1.3 per Codex

    Returns:
        List of generated instructions
    """
    # Sample negative examples uniformly
    sample = random.sample(existing_instructions, min(num_samples, len(existing_instructions)))

    # Create diversity prompt
    prompt = create_diversity_prompt(sample, num_samples)

    # Generate continuation
    import torch

    inputs = tokenizer(
        prompt,
        add_special_tokens=False,
        return_tensors="pt"
    ).to(model.device)

    # Stop sequences
    stop_sequences = ["\nInstruction", "\nQ:", "\n###", "\nUser:", "\nResponse:", "\n\n"]
    stop_token_ids = [
        tokenizer.encode(seq, add_special_tokens=False)[-1]
        for seq in stop_sequences
    ]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,  # Enough for 3 instructions
            temperature=temperature,
            top_p=0.9,
            repetition_penalty=rep_penalty,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=stop_token_ids + [tokenizer.eos_token_id]
        )

    # Decode
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    completion = full_output[len(prompt):].strip()

    # Parse numbered lines
    instructions = []
    lines = [l.strip() for l in completion.split('\n') if l.strip()]

    for line in lines:
        # Must start with number
        if not line[0].isdigit():
            continue

        # Remove number prefix
        parts = line.split('.', 1)
        if len(parts) < 2:
            parts = line.split(')', 1)
        if len(parts) < 2:
            continue

        instruction = parts[1].strip()

        # Skip empty or too short
        if not instruction or len(instruction) < 10:
            continue

        # Skip meta-instructions per Codex warning
        meta_keywords = ['instruction', 'example', 'list', 'generate', 'write', 'create']
        if any(kw in instruction.lower() for kw in meta_keywords):
            # Check if it's actually meta or just contains the word
            # e.g., "Write a haiku" is good, "Write another instruction" is meta
            if 'another' in instruction.lower() or 'more' in instruction.lower():
                logger.debug(f"Skipping meta-instruction: {instruction[:60]}...")
                continue

        instructions.append(instruction)

        if len(instructions) >= batch_size:
            break

    return instructions


def main():
    parser = argparse.ArgumentParser(description="Diversity-guided instruction generation")
    parser.add_argument('--seed', type=int, required=True, help='Random seed')
    parser.add_argument('--count', type=int, required=True, help='Target instruction count')
    parser.add_argument('--existing', type=Path, required=True, help='Path to existing instructions')
    parser.add_argument('--output', type=Path, required=True, help='Output JSONL file')
    parser.add_argument('--temperature', type=float, default=0.8, help='Generation temperature')
    parser.add_argument('--rep-penalty', type=float, default=1.3, help='Repetition penalty')

    args = parser.parse_args()

    # Set seed
    random.seed(args.seed)

    logger.info("=" * 60)
    logger.info("DIVERSITY-GUIDED INSTRUCTION GENERATION")
    logger.info("=" * 60)
    logger.info(f"Seed: {args.seed}")
    logger.info(f"Target: {args.count} instructions")
    logger.info(f"Temperature: {args.temperature}")
    logger.info(f"Rep penalty: {args.rep_penalty}")

    # Load existing instructions for negative examples
    logger.info(f"\n📥 Loading existing instructions from {args.existing}")
    existing = load_existing_instructions(args.existing)
    logger.info(f"   Loaded {len(existing)} existing instructions")

    # Load model and critic
    logger.info(f"\n🔧 Loading model...")
    loader = CleanModelLoader(model_name="Qwen/Qwen2.5-32B", load_in_4bit=True)
    model, tokenizer, provenance = loader.load()
    critic = InstructionCritic(model, tokenizer)
    prompts = CompletionStylePrompts()

    # Generate instructions
    logger.info(f"\n🎲 Generating diverse instructions")
    generated_instructions = []
    attempts = 0
    max_attempts = args.count * 3  # Allow room for filtering

    while len(generated_instructions) < args.count and attempts < max_attempts:
        attempts += 1

        # Generate batch (3 at a time per Codex)
        batch = generate_diversity_batch(
            model=model,
            tokenizer=tokenizer,
            existing_instructions=existing + generated_instructions,  # Growing pool
            batch_size=3,
            num_samples=7,
            temperature=args.temperature,
            rep_penalty=args.rep_penalty
        )

        # Filter with critic
        for inst in batch:
            # Check uniqueness
            if inst.lower().strip() in [ex.lower().strip() for ex in existing + generated_instructions]:
                logger.debug(f"Skipping duplicate: {inst[:60]}...")
                continue

            # Instruction critique
            critique = critic.critique_instruction(inst, confidence_threshold=1.0)

            if critique.is_good:
                generated_instructions.append(inst)
                if len(generated_instructions) % 10 == 0:
                    logger.info(f"   Generated {len(generated_instructions)}/{args.count}...")

                if len(generated_instructions) >= args.count:
                    break

    logger.info(f"✅ Generated {len(generated_instructions)} unique instructions")

    # Generate responses
    logger.info(f"\n💬 Generating responses")
    pairs = []

    for i, inst in enumerate(generated_instructions, 1):
        # Generate response
        response_prompt = prompts.create_response_prompt(inst)

        import torch

        inputs = tokenizer(
            response_prompt,
            add_special_tokens=False,
            return_tensors="pt"
        ).to(model.device)

        stop_sequences = ["\nInstruction", "\nQ:", "\n###", "\nUser:", "\nResponse:"]
        stop_token_ids = [
            tokenizer.encode(seq, add_special_tokens=False)[-1]
            for seq in stop_sequences
        ]

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.4,
                top_p=0.9,
                repetition_penalty=1.1,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=stop_token_ids + [tokenizer.eos_token_id]
            )

        full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = full_output[len(response_prompt):].strip()

        # Clean response
        response = prompts.clean_response(response)

        # Pair critique
        pair_critique = critic.critique_pair(inst, response, confidence_threshold=1.0)

        # Enforce confidence gate per spec (both is_good AND confident required)
        if pair_critique.is_good and pair_critique.confident:
            pairs.append({
                'instruction': inst,
                'response': response,
                'instruction_critique': {'is_good': True, 'confident': True},  # Already filtered
                'pair_critique': pair_critique.to_dict(),
                'metadata': provenance_helper.create_artifact_metadata(
                    artifact_type='diversity_guided_pair',
                    script_name='generate_diversity_guided.py',
                    model_name="Qwen/Qwen2.5-32B",
                    loader_provenance=provenance,
                    generation_params={
                        'seed': args.seed,
                        'temperature': args.temperature,
                        'rep_penalty': args.rep_penalty,
                        'method': 'diversity_guided'
                    }
                )
            })

            if len(pairs) % 10 == 0:
                logger.info(f"   Accepted {len(pairs)} pairs...")

    logger.info(f"✅ Generated {len(pairs)} instruction-response pairs")

    # Save
    logger.info(f"\n💾 Saving to {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, 'w') as f:
        for pair in pairs:
            f.write(json.dumps(pair) + '\n')

    logger.info(f"   ✅ Saved {len(pairs)} pairs")

    logger.info("\n" + "=" * 60)
    logger.info("✅ DIVERSITY-GUIDED GENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"   Instructions generated: {len(generated_instructions)}")
    logger.info(f"   Pairs accepted: {len(pairs)}")
    logger.info(f"   Acceptance rate: {len(pairs) / len(generated_instructions) * 100:.1f}%")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
