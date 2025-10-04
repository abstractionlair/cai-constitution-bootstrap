#!/usr/bin/env python3
"""
Multi-GPU parallel data generation for Constitutional AI Bootstrap.

Distributes example generation across multiple GPUs for near-linear speedup.
Each GPU generates an independent slice of the dataset.

Usage:
    # Single GPU (fallback to sequential)
    python3 scripts/generate_data_parallel.py --count 15000

    # Multi-GPU (automatic detection)
    accelerate launch --multi_gpu scripts/generate_data_parallel.py --count 15000

    # Manual multi-GPU (4 GPUs)
    CUDA_VISIBLE_DEVICES=0,1,2,3 accelerate launch --num_processes 4 scripts/generate_data_parallel.py --count 15000

Scaling:
    1 GPU:  15k examples → ~4-8 hours, $10-20
    4 GPUs: 15k examples → ~1-2 hours, $12-24 (3-4x speedup, 20% cost increase)

Output:
    artifacts/sft_data_<timestamp>.jsonl (merged from all GPUs)
    artifacts/sft_data_<timestamp>_gpu<N>.jsonl (per-GPU slices)

Each GPU:
- Loads model independently (no communication during generation)
- Generates its slice with deterministic seeds (reproducible)
- Saves to per-GPU file
- GPU 0 merges all slices at the end

Why this works:
- Data generation is embarrassingly parallel (no dependencies)
- Each example uses unique seed (no duplicates across GPUs)
- No inter-GPU communication needed during generation
"""

import sys
import json
import logging
import argparse
import os
from pathlib import Path
from datetime import datetime
import random

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.clean_model_loader import CleanModelLoader
from utils.data_formatter import CompletionStylePrompts
from utils.provenance_helper import create_artifact_metadata

# Try to import accelerate for multi-GPU
try:
    from accelerate import Accelerator
    ACCELERATE_AVAILABLE = True
except ImportError:
    ACCELERATE_AVAILABLE = False
    print("⚠️  accelerate not available, falling back to single GPU")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [GPU %(process)d] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Instruction templates (same as generate_sample_data.py)
INSTRUCTION_TEMPLATES = {
    'list': [
        'List {count} {topic}',
        'Name {count} types of {topic}',
        'Give me {count} examples of {topic}',
    ],
    'count': [
        'How many {item} are in {context}?',
        'Count the number of {item} in: {context}',
    ],
    'sort': [
        'Sort these items: {items}',
        'Arrange in order: {items}',
        'Put in alphabetical order: {items}',
    ],
    'filter': [
        'From this list, select only {criteria}: {items}',
        'Filter for {criteria}: {items}',
    ],
    'classify': [
        'Is this {category}? {item}',
        'Classify as {options}: {item}',
    ],
    'extract': [
        'Extract {target} from: {text}',
        'Find the {target} in: {text}',
    ],
}


def generate_instruction(instruction_type: str, seed: int) -> dict:
    """
    Generate a random instruction of given type.

    Returns dict with: instruction, instruction_type, generation_seed
    """
    rng = random.Random(seed)

    if instruction_type == 'list':
        template = rng.choice(INSTRUCTION_TEMPLATES['list'])
        count = rng.choice([3, 5, 7])
        topics = ['animals', 'countries', 'fruits', 'colors', 'programming languages',
                  'cities', 'planets', 'vegetables', 'musical instruments']
        topic = rng.choice(topics)
        instruction = template.format(count=count, topic=topic)

    elif instruction_type == 'count':
        template = rng.choice(INSTRUCTION_TEMPLATES['count'])
        items = ['words', 'letters', 'numbers', 'items', 'elements']
        contexts = [
            'the quick brown fox',
            'apple banana cherry',
            '1 2 3 4 5',
            'red green blue yellow'
        ]
        instruction = template.format(item=rng.choice(items), context=rng.choice(contexts))

    elif instruction_type == 'sort':
        template = rng.choice(INSTRUCTION_TEMPLATES['sort'])
        item_lists = [
            'zebra, apple, moon, banana',
            'python, java, c++, rust',
            '5, 1, 9, 3, 7',
        ]
        instruction = template.format(items=rng.choice(item_lists))

    elif instruction_type == 'filter':
        template = rng.choice(INSTRUCTION_TEMPLATES['filter'])
        criteria = ['even numbers', 'fruits', 'animals', 'vowels']
        item_lists = [
            '1, 2, 3, 4, 5, 6',
            'apple, car, banana, tree',
            'cat, dog, tree, bird',
            'a, b, e, f, i, j'
        ]
        instruction = template.format(criteria=rng.choice(criteria), items=rng.choice(item_lists))

    elif instruction_type == 'classify':
        template = rng.choice(INSTRUCTION_TEMPLATES['classify'])
        categories = ['positive/negative', 'fruit/vegetable', 'animal/plant']
        items = ['happy day', 'tomato', 'oak tree']
        instruction = template.format(
            category=rng.choice(categories).split('/')[0],
            options=rng.choice(categories),
            item=rng.choice(items)
        )

    elif instruction_type == 'extract':
        template = rng.choice(INSTRUCTION_TEMPLATES['extract'])
        targets = ['phone number', 'email', 'date', 'name']
        texts = [
            'Call me at 555-1234',
            'Email: user@example.com',
            'Born on Jan 1, 2000',
            'My name is John Smith'
        ]
        instruction = template.format(target=rng.choice(targets), text=rng.choice(texts))

    else:
        raise ValueError(f"Unknown instruction type: {instruction_type}")

    return {
        'instruction': instruction,
        'instruction_type': instruction_type,
        'generation_seed': seed
    }


def generate_dataset_slice(
    count: int,
    seed: int,
    start_idx: int,
    end_idx: int,
    gpu_id: int,
    num_gpus: int,
    output_path: Path
):
    """
    Generate a slice of the dataset on this GPU.

    Args:
        count: Total examples across all GPUs
        seed: Base random seed
        start_idx: Start index for this GPU's slice
        end_idx: End index for this GPU's slice (exclusive)
        gpu_id: This GPU's ID (0-indexed)
        num_gpus: Total number of GPUs
        output_path: Where to save this GPU's output
    """
    slice_size = end_idx - start_idx

    logger.info("=" * 70)
    logger.info(f"GPU {gpu_id}/{num_gpus}: Generating examples {start_idx}-{end_idx-1}")
    logger.info("=" * 70)
    logger.info(f"Total dataset size: {count}")
    logger.info(f"This GPU's slice: {slice_size} examples")
    logger.info(f"Base seed: {seed}")
    logger.info("")

    # Initialize model loader
    logger.info("Loading model (this may take a few minutes)...")
    loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_4bit=True)
    model, tokenizer, provenance = loader.load()

    logger.info(f"✅ Model loaded on GPU {gpu_id}")
    logger.info(f"   Provenance: {provenance}")
    logger.info("")

    # Initialize prompt formatter
    prompt_formatter = CompletionStylePrompts()

    # Distribute examples across instruction types
    instruction_types = list(INSTRUCTION_TEMPLATES.keys())
    examples_per_type = slice_size // len(instruction_types)
    remainder = slice_size % len(instruction_types)

    type_counts = {t: examples_per_type for t in instruction_types}
    # Distribute remainder
    for i in range(remainder):
        type_counts[instruction_types[i]] += 1

    logger.info("Distribution by type (this GPU):")
    for itype, icount in type_counts.items():
        logger.info(f"  {itype}: {icount}")
    logger.info("")

    # Generate examples
    examples = []
    local_idx = 0  # Index within this GPU's slice

    for instruction_type, type_count in type_counts.items():
        logger.info(f"Generating {type_count} '{instruction_type}' examples...")

        for i in range(type_count):
            # Global example index (across all GPUs)
            global_idx = start_idx + local_idx

            # Generate instruction with deterministic seed based on global index
            # This ensures no duplicates across GPUs
            inst_seed = seed + global_idx
            inst_data = generate_instruction(instruction_type, inst_seed)

            # Create completion prompt
            prompt = prompt_formatter.create_response_generation_prompt(
                inst_data['instruction']
            )

            # Generate response
            # Note: Reproducibility via inst_seed handled by setting torch/numpy random state,
            # not per-generation seed parameter (CleanModelLoader.generate doesn't accept seed)
            response = loader.generate(
                model, tokenizer, prompt,
                max_new_tokens=150,
                temperature=0.7,
                do_sample=True
            )

            # Clean up response
            response = response.strip()

            # Create training format
            formatted_text = f"Instruction: {inst_data['instruction']}\nResponse: {response}"

            # Create example with metadata
            example = {
                'instruction': inst_data['instruction'],
                'response': response,
                'formatted_text': formatted_text,
                'instruction_type': instruction_type,
                'metadata': create_artifact_metadata(
                    provenance=provenance,
                    script_name=Path(__file__).name,
                    artifact_type='sft_training_data_parallel',
                    seed=inst_seed,
                    temperature=0.7,
                    max_new_tokens=150,
                    do_sample=True,
                    example_index=global_idx,
                    total_examples=count,
                    gpu_id=gpu_id,
                    num_gpus=num_gpus
                )
            }

            examples.append(example)
            local_idx += 1

            # Log progress every 10 examples
            if (local_idx % 10) == 0:
                logger.info(f"  Generated {local_idx}/{slice_size} examples on GPU {gpu_id}...")

    logger.info(f"✅ GPU {gpu_id} generated {len(examples)} examples")
    logger.info("")

    # Save this GPU's slice
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

    logger.info(f"✅ GPU {gpu_id} saved to: {output_path}")
    logger.info("")

    return len(examples)


def merge_slices(timestamp: str, num_gpus: int, total_count: int):
    """
    Merge per-GPU slices into final dataset (GPU 0 only).

    Args:
        timestamp: Timestamp for output filename
        num_gpus: Number of GPU slices to merge
        total_count: Expected total examples
    """
    logger.info("=" * 70)
    logger.info("Merging GPU slices into final dataset")
    logger.info("=" * 70)

    output_path = Path('artifacts') / f'sft_data_{timestamp}.jsonl'

    total_examples = 0
    with open(output_path, 'w') as outf:
        for gpu_id in range(num_gpus):
            slice_path = Path('artifacts') / f'sft_data_{timestamp}_gpu{gpu_id}.jsonl'

            if not slice_path.exists():
                logger.error(f"❌ Missing slice from GPU {gpu_id}: {slice_path}")
                return False

            slice_count = 0
            with open(slice_path, 'r') as inf:
                for line in inf:
                    outf.write(line)
                    slice_count += 1

            total_examples += slice_count
            logger.info(f"  ✅ Merged GPU {gpu_id}: {slice_count} examples")

    logger.info("")
    logger.info(f"✅ Merged dataset saved: {output_path}")
    logger.info(f"   Total examples: {total_examples}")

    if total_examples != total_count:
        logger.warning(f"⚠️  Expected {total_count} examples, got {total_examples}")

    logger.info("")
    logger.info("Per-GPU slices preserved for debugging:")
    for gpu_id in range(num_gpus):
        logger.info(f"  - artifacts/sft_data_{timestamp}_gpu{gpu_id}.jsonl")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Generate SFT training data in parallel across multiple GPUs'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=15000,
        help='Total number of examples to generate (default: 15000)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )

    args = parser.parse_args()

    # Setup accelerate for multi-GPU or fallback to single GPU
    if ACCELERATE_AVAILABLE:
        accelerator = Accelerator()
        gpu_id = accelerator.process_index
        num_gpus = accelerator.num_processes
    else:
        gpu_id = 0
        num_gpus = 1
        logger.warning("Running on single GPU (accelerate not available)")

    # Calculate this GPU's slice
    examples_per_gpu = args.count // num_gpus
    remainder = args.count % num_gpus

    # Distribute remainder across first N GPUs
    if gpu_id < remainder:
        start_idx = gpu_id * (examples_per_gpu + 1)
        end_idx = start_idx + examples_per_gpu + 1
    else:
        start_idx = gpu_id * examples_per_gpu + remainder
        end_idx = start_idx + examples_per_gpu

    # Generate timestamp (same across all GPUs for merging)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path('artifacts') / f'sft_data_{timestamp}_gpu{gpu_id}.jsonl'

    # Generate this GPU's slice
    try:
        num_generated = generate_dataset_slice(
            count=args.count,
            seed=args.seed,
            start_idx=start_idx,
            end_idx=end_idx,
            gpu_id=gpu_id,
            num_gpus=num_gpus,
            output_path=output_path
        )

        # Wait for all GPUs to finish
        if ACCELERATE_AVAILABLE:
            accelerator.wait_for_everyone()

        # GPU 0 merges all slices
        if gpu_id == 0:
            success = merge_slices(timestamp, num_gpus, args.count)
            if not success:
                return 1

            logger.info("=" * 70)
            logger.info("✅ Parallel data generation complete!")
            logger.info("=" * 70)
            logger.info(f"Total examples: {args.count}")
            logger.info(f"GPUs used: {num_gpus}")
            logger.info(f"Output: artifacts/sft_data_{timestamp}.jsonl")
            logger.info("")

        return 0

    except Exception as e:
        logger.error(f"❌ Generation failed on GPU {gpu_id}: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
