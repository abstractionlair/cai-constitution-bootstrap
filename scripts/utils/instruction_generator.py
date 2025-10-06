#!/usr/bin/env python3
"""
Model-Generated Instruction Creator

Generates diverse instructions via completion prompting instead of templates.
Leverages base model's knowledge to create natural, varied instructions.
"""

import re
import random
import logging
from typing import List, Dict, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstructionGenerator:
    """Generate diverse instructions using model completion"""

    def __init__(self, seed: int = 42):
        """Initialize with reproducible seed"""
        self.seed = seed
        random.seed(seed)
        logger.info(f"🎲 Initialized InstructionGenerator with seed {seed}")

    def create_instruction_generation_prompt(
        self,
        count: int = 20,
        start_index: int = 1
    ) -> str:
        """
        Create completion-style prompt for generating diverse instructions.

        Args:
            count: Total number of instructions to generate
            start_index: Where to start numbering (usually 1)

        Returns:
            Prompt string that ends mid-list for model to continue
        """

        # Few-shot examples covering different instruction types
        examples = [
            "Answer this question: What is the capital of France?",
            "Complete this sentence: The sun rises in the",
            "List five types of animals",
            "Explain what photosynthesis is",
            "Sort these items: zebra, apple, moon, banana",
            "Count the number of words in: hello world foo",
            "From this list, select only fruits: apple, car, banana, tree",
            "Translate to Spanish: hello",
            "Write a short sentence about winter",
            "Tell me three facts about dogs"
        ]

        # Randomize examples for diversity
        selected_examples = random.sample(examples, min(len(examples), 8))

        # Build prompt
        prompt = f"""The Instruction-Following Training and Evaluation team created a diverse set of {count} example instructions for testing basic capabilities:

"""

        # Add examples (numbered)
        for i, example in enumerate(selected_examples, start=start_index):
            prompt += f"{i}. {example}\n"

        # Add one more number for model to continue
        next_num = start_index + len(selected_examples)
        prompt += f"{next_num}."

        return prompt

    def parse_generated_instructions(
        self,
        completion: str,
        max_instructions: Optional[int] = None
    ) -> List[str]:
        """
        Parse numbered list of instructions from model completion.

        Args:
            completion: Raw text from model
            max_instructions: Maximum number to extract (None = all)

        Returns:
            List of instruction strings
        """
        instructions = []

        # Split into lines and process
        lines = completion.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match numbered items (e.g., "11. Do something" or "11) Do something")
            match = re.match(r'^\d+[\.)]\s*(.+)$', line)
            if match:
                instruction = match.group(1).strip()

                # Filter out meta-text or incomplete entries
                if self._is_valid_instruction(instruction):
                    instructions.append(instruction)

                    if max_instructions and len(instructions) >= max_instructions:
                        break

        return instructions

    def _is_valid_instruction(self, instruction: str) -> bool:
        """
        Check if instruction is valid (not meta-text or garbage).

        Args:
            instruction: Candidate instruction string

        Returns:
            True if valid instruction
        """
        # Too short
        if len(instruction) < 10:
            return False

        # Too long (probably run-on)
        if len(instruction) > 200:
            return False

        # Contains meta-text indicators
        meta_indicators = [
            'instruction',
            'example',
            'following',
            'team',
            'created',
            'testing',
            '...',
            '[',
            ']',
        ]

        lower_inst = instruction.lower()
        if any(indicator in lower_inst for indicator in meta_indicators):
            # Exception: "instruction" in "follow these instructions" is ok
            if 'follow' not in lower_inst:
                return False

        # Starts with meta-text
        if instruction.lower().startswith(('the', 'this', 'these', 'those', 'an example')):
            return False

        return True

    def generate_instructions_via_completion(
        self,
        model,
        tokenizer,
        count: int,
        max_new_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1
    ) -> List[Dict[str, Any]]:
        """
        Generate diverse instructions using model completion.

        Args:
            model: Language model
            tokenizer: Tokenizer
            count: Number of instructions to generate
            max_new_tokens: Maximum tokens for generation
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            repetition_penalty: Penalty for repetition

        Returns:
            List of dicts with 'instruction' and 'generation_seed' fields
        """
        logger.info(f"Generating {count} instructions via completion prompting...")

        # Create prompt
        prompt = self.create_instruction_generation_prompt(
            count=count,
            start_index=1
        )

        # Generate completion
        from utils.clean_model_loader import CleanModelLoader
        loader = CleanModelLoader()

        completion = loader.generate(
            model, tokenizer, prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            do_sample=True,
            return_full_text=False
        )

        # Parse instructions
        instructions = self.parse_generated_instructions(
            completion,
            max_instructions=count
        )

        logger.info(f"✅ Parsed {len(instructions)} valid instructions from completion")

        # If we didn't get enough, we'll need to generate more in batches
        # For now, just return what we got
        if len(instructions) < count:
            logger.warning(f"⚠️  Only got {len(instructions)}/{count} instructions")

        # Package as dicts with metadata
        instruction_dicts = []
        for i, instruction in enumerate(instructions[:count]):
            instruction_dicts.append({
                'instruction': instruction,
                'generation_seed': self.seed + i,
                'generation_method': 'model_completion'
            })

        return instruction_dicts

    def generate_instructions_in_batches(
        self,
        model,
        tokenizer,
        count: int,
        batch_size: int = 20,
        **generation_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate instructions in multiple batches to reach target count.

        Args:
            model: Language model
            tokenizer: Tokenizer
            count: Total number of instructions needed
            batch_size: Instructions per generation batch
            **generation_kwargs: Passed to generate_instructions_via_completion

        Returns:
            List of instruction dicts
        """
        all_instructions = []
        batches_needed = (count + batch_size - 1) // batch_size

        logger.info(f"Generating {count} instructions in {batches_needed} batches of ~{batch_size}")

        for batch_num in range(batches_needed):
            remaining = count - len(all_instructions)
            batch_target = min(batch_size, remaining)

            logger.info(f"Batch {batch_num + 1}/{batches_needed}: Generating {batch_target} instructions...")

            batch_instructions = self.generate_instructions_via_completion(
                model, tokenizer,
                count=batch_target,
                **generation_kwargs
            )

            # Update seeds to be unique across batches
            for inst_dict in batch_instructions:
                inst_dict['generation_seed'] = self.seed + len(all_instructions)
                all_instructions.append(inst_dict)

                if len(all_instructions) >= count:
                    break

            if len(all_instructions) >= count:
                break

        logger.info(f"✅ Generated {len(all_instructions)} total instructions across {batch_num + 1} batches")

        return all_instructions[:count]


if __name__ == "__main__":
    # Test instruction generation prompt
    generator = InstructionGenerator(seed=42)

    print("=" * 70)
    print("Test: Instruction Generation Prompt")
    print("=" * 70)
    prompt = generator.create_instruction_generation_prompt(count=20)
    print(prompt)
    print("\n" + "=" * 70)

    # Test parsing
    sample_completion = """11. Describe the water cycle
12. Name three planets in our solar system
13. Convert 100 Celsius to Fahrenheit
14. What is the largest mammal on Earth?
15. Finish this sentence: A square has ___ sides
16. Put these in chronological order: 1900, 1850, 1950
17. Identify which of these is a vegetable: apple, carrot, orange
18. Respond to: How was your day?
19. Generate a greeting message
20. Summarize the concept of gravity"""

    print("\nTest: Parsing Generated Instructions")
    print("=" * 70)
    instructions = generator.parse_generated_instructions(sample_completion)
    print(f"Parsed {len(instructions)} instructions:")
    for i, inst in enumerate(instructions, 1):
        print(f"  {i}. {inst}")
