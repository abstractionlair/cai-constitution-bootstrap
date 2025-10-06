#!/usr/bin/env python3
"""
Generate sample SFT training data for manual inspection (V2 - Model-Generated Instructions).

Version 2 Changes:
- Uses model completion to generate diverse instructions (not templates)
- Adds logprob-based quality filtering at two stages:
  1. Instruction quality (filter bad instructions)
  2. Instruction+response pair quality (filter bad pairs)
- Higher quality, more diverse data

Purpose: Create 50-100 examples with full provenance metadata for quality review
         before committing to expensive full data generation.

Cost: ~$1-2 (15-30 minutes on H100 @ $2.69/hr)
Output: artifacts/sample_sft_data_v2_<timestamp>.jsonl

Usage:
    python3 scripts/generate_sample_data_v2.py --count 50
    python3 scripts/generate_sample_data_v2.py --count 100 --seed 42
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
import random

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.clean_model_loader import CleanModelLoader
from utils.data_formatter import CompletionStylePrompts
from utils.provenance_helper import create_artifact_metadata
from utils.instruction_generator import InstructionGenerator
from utils.instruction_critic import (
    critique_instruction_quality,
    critique_instruction_response_pair
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_dataset_v2(count: int = 50, seed: int = 42, confidence_threshold: float = 1.0):
    """
    Generate sample SFT training data with model-generated instructions and quality filtering.

    Args:
        count: Number of examples to generate (default 50)
        seed: Random seed for reproducibility (default 42)
        confidence_threshold: Minimum logprob margin for confident judgments (default 1.0)
    """
    logger.info("==" * 35)
    logger.info("Sample SFT Data Generation V2 (Model-Generated + Quality Filtered)")
    logger.info("==" * 35)
    logger.info(f"Target count: {count}")
    logger.info(f"Seed: {seed}")
    logger.info(f"Confidence threshold: {confidence_threshold}")
    logger.info("")

    # Initialize model loader
    import os
    model_path = os.environ.get('MODEL_PATH', 'Qwen/Qwen2.5-32B')
    if model_path != 'Qwen/Qwen2.5-32B':
        logger.info(f"Using MODEL_PATH environment variable: {model_path}")

    logger.info("Loading model (this may take a few minutes)...")
    loader = CleanModelLoader(model_path, load_in_4bit=True)
    model, tokenizer, provenance = loader.load()

    logger.info(f"✅ Model loaded")
    logger.info(f"   Provenance: {provenance}")
    logger.info("")

    # Initialize generators
    instruction_gen = InstructionGenerator(seed=seed)
    prompt_formatter = CompletionStylePrompts()

    # Track QC metrics
    qc_metrics = {
        # Instruction generation
        'instructions_generated': 0,
        'instructions_good': 0,
        'instructions_bad': 0,
        'instructions_low_confidence': 0,

        # Response generation
        'responses_generated': 0,
        'delimiter_found': 0,
        'delimiter_missing': 0,
        'heuristic_cutoff': 0,
        'hit_token_limit': 0,
        'token_counts': [],

        # Pair quality
        'pairs_evaluated': 0,
        'pairs_good': 0,
        'pairs_bad': 0,
        'pairs_low_confidence': 0,

        # Final
        'examples_kept': 0,
    }

    # Step 1: Generate instructions via model completion
    logger.info("=" * 70)
    logger.info("Step 1: Generate Instructions via Model Completion")
    logger.info("=" * 70)

    # Generate more than we need (will filter)
    generation_target = int(count * 1.5)  # 50% buffer for filtering
    logger.info(f"Generating {generation_target} instructions (target {count} after filtering)...")

    instruction_dicts = instruction_gen.generate_instructions_in_batches(
        model, tokenizer,
        count=generation_target,
        batch_size=20,
        max_new_tokens=1000,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1
    )

    qc_metrics['instructions_generated'] = len(instruction_dicts)
    logger.info(f"✅ Generated {len(instruction_dicts)} raw instructions")
    logger.info("")

    # Step 2: Filter instructions by quality
    logger.info("=" * 70)
    logger.info("Step 2: Filter Instructions by Quality (Logprob)")
    logger.info("=" * 70)

    good_instructions = []
    for i, inst_dict in enumerate(instruction_dicts):
        instruction = inst_dict['instruction']

        # Critique instruction quality
        critique = critique_instruction_quality(
            model, tokenizer, instruction,
            confidence_threshold=confidence_threshold
        )

        if critique['is_good'] and critique['confident']:
            good_instructions.append({
                **inst_dict,
                'instruction_critique': critique
            })
            qc_metrics['instructions_good'] += 1
        elif not critique['confident']:
            qc_metrics['instructions_low_confidence'] += 1
        else:
            qc_metrics['instructions_bad'] += 1

        # Log progress
        if (i + 1) % 10 == 0:
            logger.info(f"  Evaluated {i+1}/{len(instruction_dicts)} instructions...")

    logger.info(f"✅ Quality filtered: {len(good_instructions)} good instructions (from {len(instruction_dicts)} generated)")
    logger.info(f"   Good: {qc_metrics['instructions_good']}")
    logger.info(f"   Bad: {qc_metrics['instructions_bad']}")
    logger.info(f"   Low confidence: {qc_metrics['instructions_low_confidence']}")
    logger.info("")

    # Check if we have enough
    if len(good_instructions) < count:
        logger.warning(f"⚠️  Only {len(good_instructions)} good instructions, need {count}")
        logger.warning(f"   Proceeding with what we have...")

    # Step 3: Generate responses for good instructions
    logger.info("=" * 70)
    logger.info("Step 3: Generate Responses for Good Instructions")
    logger.info("=" * 70)

    instruction_response_pairs = []
    for i, inst_dict in enumerate(good_instructions[:count * 2]):  # Generate extra for filtering
        instruction = inst_dict['instruction']

        # Create completion prompt
        prompt = prompt_formatter.create_response_generation_prompt(instruction)

        # Generate response
        response = loader.generate(
            model, tokenizer, prompt,
            max_new_tokens=80,
            temperature=0.4,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=True
        )

        qc_metrics['responses_generated'] += 1
        raw_token_count = len(tokenizer.encode(response))

        # Clean up response with layered guards
        # 1. Stop at ###END### delimiter
        delimiter_found = '###END###' in response
        if delimiter_found:
            response = response.split('###END###')[0]
            qc_metrics['delimiter_found'] += 1
        else:
            qc_metrics['delimiter_missing'] += 1

        # 2. Heuristic cutoff at continuation markers
        import re
        heuristic_cutoff_applied = False
        continuation_patterns = [
            r'\n\n(?:Instruction|Q:|A:|Response:)',
            r'\n(?:What |How |Why |When |Where |Who |Can |Should )',
        ]
        for pattern in continuation_patterns:
            match = re.search(pattern, response)
            if match:
                response = response[:match.start()]
                heuristic_cutoff_applied = True
                break

        if heuristic_cutoff_applied:
            qc_metrics['heuristic_cutoff'] += 1

        # 3. Remove trailing whitespace
        response = response.strip()

        clean_token_count = len(tokenizer.encode(response))
        qc_metrics['token_counts'].append(clean_token_count)

        if raw_token_count >= 75:
            qc_metrics['hit_token_limit'] += 1

        instruction_response_pairs.append({
            **inst_dict,
            'response': response,
            'raw_token_count': raw_token_count,
            'clean_token_count': clean_token_count
        })

        # Log progress
        if (i + 1) % 10 == 0:
            logger.info(f"  Generated {i+1} responses...")

    logger.info(f"✅ Generated {len(instruction_response_pairs)} instruction-response pairs")
    logger.info("")

    # Step 4: Filter instruction+response pairs by quality
    logger.info("=" * 70)
    logger.info("Step 4: Filter Instruction+Response Pairs by Quality (Logprob)")
    logger.info("=" * 70)

    final_examples = []
    for i, pair in enumerate(instruction_response_pairs):
        instruction = pair['instruction']
        response = pair['response']

        # Critique pair quality
        critique = critique_instruction_response_pair(
            model, tokenizer, instruction, response,
            confidence_threshold=confidence_threshold
        )

        qc_metrics['pairs_evaluated'] += 1

        if critique['is_good'] and critique['confident']:
            qc_metrics['pairs_good'] += 1
            qc_metrics['examples_kept'] += 1

            # Create training format
            formatted_text = f"Instruction: {instruction}\nResponse: {response}"

            # Create final example with metadata
            example = {
                'instruction': instruction,
                'response': response,
                'formatted_text': formatted_text,
                'metadata': create_artifact_metadata(
                    provenance=provenance,
                    script_name=Path(__file__).name,
                    artifact_type='sample_training_data_v2',
                    seed=pair['generation_seed'],
                    temperature=0.4,
                    max_new_tokens=80,
                    do_sample=True,
                    example_index=len(final_examples),
                    sample_size=count,
                    confidence_threshold=confidence_threshold,
                    instruction_critique=pair.get('instruction_critique'),
                    pair_critique=critique
                )
            }

            final_examples.append(example)

            # Stop if we have enough
            if len(final_examples) >= count:
                break
        elif not critique['confident']:
            qc_metrics['pairs_low_confidence'] += 1
        else:
            qc_metrics['pairs_bad'] += 1

        # Log progress
        if (i + 1) % 10 == 0:
            kept = len(final_examples)
            logger.info(f"  Evaluated {i+1}/{len(instruction_response_pairs)} pairs... (kept {kept})")

    logger.info(f"✅ Quality filtered: {len(final_examples)} high-quality examples")
    logger.info(f"   Good pairs: {qc_metrics['pairs_good']}")
    logger.info(f"   Bad pairs: {qc_metrics['pairs_bad']}")
    logger.info(f"   Low confidence: {qc_metrics['pairs_low_confidence']}")
    logger.info("")

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path('artifacts') / f'sample_sft_data_v2_{timestamp}.jsonl'
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        for example in final_examples:
            f.write(json.dumps(example) + '\n')

    logger.info(f"✅ Saved to: {output_path}")
    logger.info("")

    # Compute and display QC metrics
    import statistics
    token_counts = qc_metrics['token_counts']
    median_tokens = statistics.median(token_counts) if token_counts else 0
    mean_tokens = statistics.mean(token_counts) if token_counts else 0

    inst_gen = qc_metrics['instructions_generated']
    inst_good_pct = (qc_metrics['instructions_good'] / inst_gen * 100) if inst_gen > 0 else 0
    inst_bad_pct = (qc_metrics['instructions_bad'] / inst_gen * 100) if inst_gen > 0 else 0

    resp_gen = qc_metrics['responses_generated']
    delimiter_pct = (qc_metrics['delimiter_found'] / resp_gen * 100) if resp_gen > 0 else 0
    limit_pct = (qc_metrics['hit_token_limit'] / resp_gen * 100) if resp_gen > 0 else 0

    pairs_eval = qc_metrics['pairs_evaluated']
    pairs_good_pct = (qc_metrics['pairs_good'] / pairs_eval * 100) if pairs_eval > 0 else 0
    pairs_bad_pct = (qc_metrics['pairs_bad'] / pairs_eval * 100) if pairs_eval > 0 else 0

    logger.info("==" * 35)
    logger.info("Quality Control Metrics (V2 - Multi-Stage Filtering)")
    logger.info("==" * 35)
    logger.info(f"Final examples: {len(final_examples)} (target: {count})")
    logger.info("")
    logger.info("Stage 1 - Instruction Generation:")
    logger.info(f"  Generated: {inst_gen}")
    logger.info(f"  Good: {qc_metrics['instructions_good']} ({inst_good_pct:.1f}%)")
    logger.info(f"  Bad: {qc_metrics['instructions_bad']} ({inst_bad_pct:.1f}%)")
    logger.info(f"  Low confidence: {qc_metrics['instructions_low_confidence']}")
    logger.info("")
    logger.info("Stage 2 - Response Generation:")
    logger.info(f"  Generated: {resp_gen}")
    logger.info(f"  Delimiter found: {qc_metrics['delimiter_found']} ({delimiter_pct:.1f}%)")
    logger.info(f"  Median tokens: {median_tokens:.0f}")
    logger.info(f"  Mean tokens: {mean_tokens:.1f}")
    logger.info(f"  Hit token limit: {qc_metrics['hit_token_limit']} ({limit_pct:.1f}%)")
    logger.info("")
    logger.info("Stage 3 - Pair Quality Filtering:")
    logger.info(f"  Evaluated: {pairs_eval}")
    logger.info(f"  Good: {qc_metrics['pairs_good']} ({pairs_good_pct:.1f}%)")
    logger.info(f"  Bad: {qc_metrics['pairs_bad']} ({pairs_bad_pct:.1f}%)")
    logger.info(f"  Low confidence: {qc_metrics['pairs_low_confidence']}")
    logger.info("")
    logger.info(f"Overall yield: {len(final_examples)}/{inst_gen} = {len(final_examples)/inst_gen*100:.1f}%")
    logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description='Generate sample SFT training data V2 (model-generated + filtered)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=50,
        help='Number of examples to generate (default: 50)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--confidence-threshold',
        type=float,
        default=1.0,
        help='Minimum logprob margin for confident judgments (default: 1.0)'
    )

    args = parser.parse_args()

    # Validate
    if args.count < 10:
        logger.error("Count must be at least 10")
        return 1

    if args.count > 200:
        logger.warning(f"Count {args.count} is quite large for a sample. Consider 50-100.")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Cancelled")
            return 0

    # Generate
    try:
        generate_sample_dataset_v2(
            count=args.count,
            seed=args.seed,
            confidence_threshold=args.confidence_threshold
        )
        return 0
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
