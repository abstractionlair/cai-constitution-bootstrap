#!/usr/bin/env python3
"""
Generate held-out test instructions for evaluation.

Creates a diverse set of test instructions for evaluating Stage 1 models.
These instructions MUST be distinct from training data to prevent data leakage.

Usage:
    python generate_test_instructions.py \
      --count 200 \
      --output data/test_instructions.jsonl \
      --seed 999

Outputs:
    - test_instructions.jsonl (held-out instructions with types)
"""

import argparse
import json
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Diverse test instruction templates by type
TEST_INSTRUCTION_TEMPLATES = {
    "factual": [
        "What is the capital of {country}?",
        "When was {event} invented?",
        "How many {object}s are in {container}?",
        "What does '{term}' mean?",
        "Who invented the {invention}?",
        "What is the chemical formula for {compound}?",
        "How long does it take for {planet} to orbit the sun?",
        "What year did {event} happen?",
    ],
    "explanation": [
        "Explain how {process} works in simple terms.",
        "Describe the process of {natural_phenomenon}.",
        "What is the difference between {thing1} and {thing2}?",
        "How does {device} function?",
        "Why is {fact} true?",
        "Explain {concept} to a beginner.",
    ],
    "list_generation": [
        "List {number} {category}.",
        "Name {number} examples of {category}.",
        "What are {number} types of {thing}?",
        "Give {number} reasons for {situation}.",
    ],
    "instruction_following": [
        "Translate '{phrase}' to {language}.",
        "Convert {number} {unit1} to {unit2}.",
        "Write a {adjective} sentence about {topic}.",
        "Summarize {topic} in one sentence.",
        "Define {term} briefly.",
    ],
    "creative": [
        "Write a short {adjective} description of {thing}.",
        "Create a simple analogy for {concept}.",
        "Describe {object} using only {number} words.",
    ]
}

# Fillers for templates
FILLERS = {
    "country": ["France", "Japan", "Brazil", "Canada", "Egypt"],
    "event": ["the telephone", "the light bulb", "the airplane", "the computer"],
    "object": ["leg", "wheel", "side"],
    "container": ["a triangle", "a square", "a bicycle"],
    "term": ["photosynthesis", "gravity", "democracy", "ecosystem"],
    "invention": ["telephone", "bicycle", "telescope"],
    "compound": ["water", "salt", "carbon dioxide"],
    "planet": ["Mars", "Venus", "Jupiter"],
    "process": ["photosynthesis", "evaporation", "digestion"],
    "natural_phenomenon": ["rain", "seasons", "tides"],
    "thing1": ["weather", "speed", "mass"],
    "thing2": ["climate", "velocity", "weight"],
    "device": ["a thermometer", "a compass", "a lever"],
    "fact": ["the sky blue", "ice cold", "metal conductive"],
    "concept": ["fractions", "gravity", "photosynthesis"],
    "number": ["three", "five", "four"],
    "category": ["primary colors", "continents", "planets", "seasons", "senses"],
    "thing": ["cloud", "rock", "tree"],
    "situation": ["exercising daily", "reading books", "saving money"],
    "phrase": ["hello", "thank you", "good morning"],
    "language": ["Spanish", "French", "German"],
    "unit1": ["meters", "pounds", "Celsius"],
    "unit2": ["feet", "kilograms", "Fahrenheit"],
    "adjective": ["short", "simple", "clear"],
    "topic": ["the water cycle", "the solar system", "volcanoes"]
}


def fill_template(template: str, fillers: Dict[str, List[str]]) -> str:
    """
    Fill template with random fillers.

    Args:
        template: Template string with {placeholders}
        fillers: Dict of placeholder -> possible values

    Returns:
        Filled template string
    """
    result = template

    # Extract all placeholders
    import re
    placeholders = re.findall(r'\{(\w+)\}', template)

    for placeholder in placeholders:
        if placeholder in fillers:
            value = random.choice(fillers[placeholder])
            result = result.replace(f"{{{placeholder}}}", value, 1)

    return result


def generate_test_instructions(
    count_per_type: int,
    seed: int = 999
) -> List[Dict[str, Any]]:
    """
    Generate test instructions.

    Args:
        count_per_type: Number of instructions per type
        seed: Random seed

    Returns:
        List of instruction dicts with type labels
    """
    random.seed(seed)

    instructions = []

    for inst_type, templates in TEST_INSTRUCTION_TEMPLATES.items():
        for _ in range(count_per_type):
            template = random.choice(templates)
            instruction = fill_template(template, FILLERS)

            instructions.append({
                "instruction": instruction,
                "type": inst_type,
                "template": template,
                "generated_at": datetime.utcnow().isoformat()
            })

    # Shuffle
    random.shuffle(instructions)

    return instructions


def main():
    parser = argparse.ArgumentParser(
        description="Generate held-out test instructions"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=200,
        help="Total number of test instructions (default: 200, ~40 per type)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/test_instructions.jsonl",
        help="Output path (default: data/test_instructions.jsonl)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=999,
        help="Random seed (default: 999)"
    )

    args = parser.parse_args()

    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate count per type
    num_types = len(TEST_INSTRUCTION_TEMPLATES)
    count_per_type = args.count // num_types

    logger.info(f"Generating {count_per_type} instructions per type ({num_types} types)")

    # Generate instructions
    instructions = generate_test_instructions(count_per_type, args.seed)

    # Save
    with open(output_path, 'w') as f:
        for inst in instructions:
            f.write(json.dumps(inst) + '\n')

    logger.info(f"✅ Generated {len(instructions)} test instructions")
    logger.info(f"✅ Saved to: {output_path}")

    # Print type distribution
    from collections import Counter
    type_counts = Counter(inst['type'] for inst in instructions)

    logger.info("\nType distribution:")
    for inst_type, count in sorted(type_counts.items()):
        logger.info(f"  {inst_type}: {count}")


if __name__ == "__main__":
    main()
