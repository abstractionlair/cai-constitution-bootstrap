#!/usr/bin/env python3
"""
Generate sample SFT training data for manual inspection.

Purpose: Create 50-100 examples with full provenance metadata for quality review
         before committing to expensive full data generation.

Cost: ~$1-2 (15-30 minutes on H100 @ $2.69/hr)
Output: artifacts/sample_sft_data_<timestamp>.jsonl

Why: "Measure twice, cut once" - catch issues at low cost before full run

Usage:
    python3 scripts/generate_sample_data.py --count 50
    python3 scripts/generate_sample_data.py --count 100 --seed 42

Then inspect:
    head -20 artifacts/sample_sft_data_*.jsonl | jq '.'
    jq '.metadata' artifacts/sample_sft_data_*.jsonl | head -1
    jq '.response' artifacts/sample_sft_data_*.jsonl | head -10
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Instruction templates for different task types
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


def generate_sample_dataset(count: int = 50, seed: int = 42):
    """
    Generate sample SFT training data.

    Args:
        count: Number of examples to generate (default 50)
        seed: Random seed for reproducibility (default 42)
    """
    logger.info("=" * 70)
    logger.info("Sample SFT Data Generation")
    logger.info("=" * 70)
    logger.info(f"Count: {count}")
    logger.info(f"Seed: {seed}")
    logger.info("")

    # Initialize model loader
    # Check for local model path (avoids HF cache writes on quota-limited filesystems)
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

    # Initialize prompt formatter
    prompt_formatter = CompletionStylePrompts()

    # Distribute examples across instruction types
    instruction_types = list(INSTRUCTION_TEMPLATES.keys())
    examples_per_type = count // len(instruction_types)
    remainder = count % len(instruction_types)

    type_counts = {t: examples_per_type for t in instruction_types}
    # Distribute remainder
    for i in range(remainder):
        type_counts[instruction_types[i]] += 1

    logger.info("Distribution by type:")
    for itype, icount in type_counts.items():
        logger.info(f"  {itype}: {icount}")
    logger.info("")

    # Generate examples with QC tracking (Codex review: automated metrics)
    examples = []
    example_idx = 0
    qc_metrics = {
        'delimiter_found': 0,
        'delimiter_missing': 0,
        'heuristic_cutoff': 0,
        'hit_token_limit': 0,
        'token_counts': [],
        'forbidden_markers_found': 0,
    }

    for instruction_type, type_count in type_counts.items():
        logger.info(f"Generating {type_count} '{instruction_type}' examples...")

        for i in range(type_count):
            # Generate instruction
            inst_seed = seed + example_idx
            inst_data = generate_instruction(instruction_type, inst_seed)

            # Create completion prompt
            prompt = prompt_formatter.create_response_generation_prompt(
                inst_data['instruction']
            )

            # Generate response with conservative parameters to reduce runaway risk
            # Note: Reproducibility via inst_seed handled by setting torch/numpy random state,
            # not per-generation seed parameter (CleanModelLoader.generate doesn't accept seed)
            response = loader.generate(
                model, tokenizer, prompt,
                max_new_tokens=80,  # Reduced from 150 (Codex: most responses <50 tokens)
                temperature=0.4,    # Reduced from 0.7 (Codex: 0.3-0.5 for focused generation)
                top_p=0.9,
                repetition_penalty=1.1,
                do_sample=True
            )

            # Track raw response stats for QC
            raw_response = response
            raw_token_count = len(tokenizer.encode(response))

            # Clean up response with layered guards (Codex review: multi-guard approach)
            # 1. Stop at ###END### delimiter (primary guard)
            delimiter_found = '###END###' in response
            if delimiter_found:
                response = response.split('###END###')[0]
                qc_metrics['delimiter_found'] += 1
            else:
                qc_metrics['delimiter_missing'] += 1

            # 2. Heuristic cutoff at common continuation markers (backup guard)
            #    Stop at first occurrence of patterns that indicate multi-QA chaining
            import re
            heuristic_cutoff_applied = False
            continuation_patterns = [
                r'\n\n(?:Instruction|Q:|A:|Response:)',  # New Q&A block
                r'\n(?:What |How |Why |When |Where |Who |Can |Should )',  # New question
            ]
            for pattern in continuation_patterns:
                match = re.search(pattern, response)
                if match:
                    response = response[:match.start()]
                    heuristic_cutoff_applied = True
                    break

            if heuristic_cutoff_applied:
                qc_metrics['heuristic_cutoff'] += 1

            # 3. Remove trailing whitespace, extra newlines
            response = response.strip()

            # Track cleaned response stats
            clean_token_count = len(tokenizer.encode(response))
            qc_metrics['token_counts'].append(clean_token_count)

            # Check if hit token limit (approximately - within 5 tokens of max)
            if raw_token_count >= 75:  # 80 - 5 token buffer
                qc_metrics['hit_token_limit'] += 1

            # Check for forbidden markers in final cleaned response
            forbidden_markers = ['###END###', 'Instruction:', 'Q:', 'Response:']
            if any(marker in response for marker in forbidden_markers):
                qc_metrics['forbidden_markers_found'] += 1

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
                    artifact_type='sample_training_data',
                    seed=inst_seed,
                    temperature=0.7,
                    max_new_tokens=150,
                    do_sample=True,
                    example_index=example_idx,
                    sample_size=count
                )
            }

            examples.append(example)
            example_idx += 1

            # Log progress every 10 examples
            if (example_idx % 10) == 0:
                logger.info(f"  Generated {example_idx}/{count} examples...")

    logger.info(f"✅ Generated {len(examples)} examples")
    logger.info("")

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path('artifacts') / f'sample_sft_data_{timestamp}.jsonl'
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

    logger.info(f"✅ Saved to: {output_path}")
    logger.info("")

    # Compute and display QC metrics (Codex review: automated validation)
    import statistics
    token_counts = qc_metrics['token_counts']
    median_tokens = statistics.median(token_counts) if token_counts else 0
    mean_tokens = statistics.mean(token_counts) if token_counts else 0

    pct_delimiter_found = (qc_metrics['delimiter_found'] / count * 100) if count > 0 else 0
    pct_delimiter_missing = (qc_metrics['delimiter_missing'] / count * 100) if count > 0 else 0
    pct_heuristic_cutoff = (qc_metrics['heuristic_cutoff'] / count * 100) if count > 0 else 0
    pct_hit_limit = (qc_metrics['hit_token_limit'] / count * 100) if count > 0 else 0
    pct_forbidden = (qc_metrics['forbidden_markers_found'] / count * 100) if count > 0 else 0

    logger.info("=" * 70)
    logger.info("Quality Control Metrics (Codex Review Criteria)")
    logger.info("=" * 70)
    logger.info(f"Total examples: {len(examples)}")
    logger.info("")
    logger.info("Delimiter Performance:")
    logger.info(f"  Delimiter found: {qc_metrics['delimiter_found']} ({pct_delimiter_found:.1f}%) [Target: >80%]")
    logger.info(f"  Delimiter missing: {qc_metrics['delimiter_missing']} ({pct_delimiter_missing:.1f}%)")
    logger.info(f"  Heuristic cutoff applied: {qc_metrics['heuristic_cutoff']} ({pct_heuristic_cutoff:.1f}%)")
    logger.info("")
    logger.info("Token Usage:")
    logger.info(f"  Median tokens: {median_tokens:.0f} [Target: <40]")
    logger.info(f"  Mean tokens: {mean_tokens:.1f}")
    logger.info(f"  Hit token limit: {qc_metrics['hit_token_limit']} ({pct_hit_limit:.1f}%) [Target: <10%]")
    logger.info("")
    logger.info("Contamination:")
    logger.info(f"  Forbidden markers in responses: {qc_metrics['forbidden_markers_found']} ({pct_forbidden:.1f}%) [Target: 0%]")
    logger.info("")

    # Pass/fail assessment
    passed = (
        pct_delimiter_found >= 80 and
        pct_hit_limit < 10 and
        median_tokens < 40 and
        qc_metrics['forbidden_markers_found'] == 0
    )

    if passed:
        logger.info("✅ QC PASSED - All thresholds met, safe to proceed to full generation")
    else:
        logger.info("❌ QC FAILED - Thresholds not met:")
        if pct_delimiter_found < 80:
            logger.info(f"   - Delimiter found rate too low: {pct_delimiter_found:.1f}% < 80%")
        if pct_hit_limit >= 10:
            logger.info(f"   - Too many responses hit token limit: {pct_hit_limit:.1f}% >= 10%")
        if median_tokens >= 40:
            logger.info(f"   - Median tokens too high: {median_tokens:.0f} >= 40")
        if qc_metrics['forbidden_markers_found'] > 0:
            logger.info(f"   - Forbidden markers found in {qc_metrics['forbidden_markers_found']} responses")
        logger.info("")
        logger.info("⚠️  DO NOT proceed to 15k generation until issues resolved")

    logger.info("")
    logger.info("=" * 70)
    logger.info("Manual Inspection Commands")
    logger.info("=" * 70)
    logger.info("  1. Inspect sample data:")
    logger.info(f"     jq '.' {output_path} | head -50")
    logger.info("  2. Check metadata:")
    logger.info(f"     jq '.metadata' {output_path} | head -1")
    logger.info("  3. Review responses:")
    logger.info(f"     jq '.response' {output_path} | head -20")
    logger.info("  4. Check for runaway generation:")
    logger.info(f"     jq '.response' {output_path} | grep -E '(What|How|Why|Instruction)' | head -10")
    logger.info("")
    logger.info("Output file: {output_path}")
    logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description='Generate sample SFT training data for inspection'
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
        generate_sample_dataset(count=args.count, seed=args.seed)
        return 0
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
