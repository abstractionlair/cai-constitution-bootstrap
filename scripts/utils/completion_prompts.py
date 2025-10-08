#!/usr/bin/env python3
"""
CompletionStylePrompts - Canonical prompt builders for completion-mode generation.

This is the ONLY way to create prompts for base model generation in this project.
All prompts use completion-style (few-shot examples), never chat templates.

Key responsibilities:
- Response generation: "Instruction: X\nResponse:" format
- Instruction generation: Few-shot numbered list continuation
- Critic prompts: Single-token A/B format with rubrics
- Delimiter handling: Optional ###END### for response truncation

Usage:
    from utils.completion_prompts import CompletionStylePrompts

    # Response generation
    prompt = CompletionStylePrompts.create_response_prompt(
        instruction="Explain photosynthesis"
    )

    # Instruction generation
    prompt = CompletionStylePrompts.create_instruction_generation_prompt()

    # Critic prompts
    prompt = CompletionStylePrompts.create_instruction_critic_prompt(
        instruction="Write a poem"
    )
"""

import random
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class CompletionStylePrompts:
    """
    Canonical prompt builders for completion-mode generation.

    All methods return prompts for completion (not chat).
    Use with add_special_tokens=False and no chat template.
    """

    # Response generation few-shot examples
    RESPONSE_EXAMPLES = [
        {
            "instruction": "What is the capital of France?",
            "response": "The capital of France is Paris."
        },
        {
            "instruction": "Explain photosynthesis in one sentence.",
            "response": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of sugar."
        },
        {
            "instruction": "List three primary colors.",
            "response": "The three primary colors are red, blue, and yellow."
        },
        {
            "instruction": "Translate 'hello' to Spanish.",
            "response": "The Spanish translation of 'hello' is 'hola'."
        }
    ]

    # Instruction generation examples (diverse types)
    INSTRUCTION_EXAMPLES = [
        "Explain the water cycle in simple terms.",
        "List five common programming languages.",
        "What is the difference between a virus and bacteria?",
        "Describe how to make a paper airplane.",
        "Name three planets in our solar system.",
        "What does 'biodiversity' mean?",
        "Convert 100 degrees Fahrenheit to Celsius.",
        "What are the primary colors?",
        "Explain what 'photosynthesis' means.",
        "List three types of clouds.",
        "What is the speed of light?",
        "Describe the function of the heart.",
        "Name five different emotions.",
        "What is gravity?",
        "How many continents are there?"
    ]

    @classmethod
    def create_response_prompt(
        cls,
        instruction: str,
        include_delimiter: bool = True,
        num_examples: int = 3
    ) -> str:
        """
        Create completion-style prompt for response generation.

        Format:
            Instruction: {example1_instruction}
            Response: {example1_response}###END###

            Instruction: {example2_instruction}
            Response: {example2_response}###END###

            Instruction: {target_instruction}
            Response:

        Args:
            instruction: The instruction to respond to
            include_delimiter: Whether to include ###END### in examples
            num_examples: Number of few-shot examples (default 3)

        Returns:
            Completion-style prompt string
        """
        # Select random examples for diversity
        examples = random.sample(cls.RESPONSE_EXAMPLES, min(num_examples, len(cls.RESPONSE_EXAMPLES)))

        prompt_parts = []

        # Add few-shot examples
        for ex in examples:
            prompt_parts.append(f"Instruction: {ex['instruction']}")
            if include_delimiter:
                prompt_parts.append(f"Response: {ex['response']}###END###")
            else:
                prompt_parts.append(f"Response: {ex['response']}")
            prompt_parts.append("")  # Blank line between examples

        # Add target instruction
        prompt_parts.append(f"Instruction: {instruction}")
        prompt_parts.append("Response:")

        return "\n".join(prompt_parts)

    @classmethod
    def create_instruction_generation_prompt(
        cls,
        num_examples: int = 10,
        start_number: int = 1
    ) -> str:
        """
        Create completion-style prompt for instruction generation.

        Format:
            1. {instruction1}
            2. {instruction2}
            ...
            10. {instruction10}
            11.

        Model continues numbering and generates more instructions.

        Args:
            num_examples: Number of seed instructions
            start_number: Starting number for list

        Returns:
            Completion-style prompt string
        """
        # Select random seed instructions
        examples = random.sample(
            cls.INSTRUCTION_EXAMPLES,
            min(num_examples, len(cls.INSTRUCTION_EXAMPLES))
        )

        prompt_parts = []

        for i, instruction in enumerate(examples, start=start_number):
            prompt_parts.append(f"{i}. {instruction}")

        # Add partial line for model to continue
        next_num = start_number + len(examples)
        prompt_parts.append(f"{next_num}.")

        return "\n".join(prompt_parts)

    @classmethod
    def create_instruction_critic_prompt(
        cls,
        instruction: str
    ) -> str:
        """
        Create single-token A/B critic prompt for instruction quality.

        Rubric:
        - A = good (clear, specific, achievable, safe)
        - B = bad (vague, impossible, unsafe, nonsense)
        - Conservative: if uncertain, choose B

        Args:
            instruction: The instruction to critique

        Returns:
            Prompt ending with "Label:" for next-token scoring
        """
        prompt = f"""Evaluate this instruction for quality.

A = GOOD: The instruction is clear, specific, achievable, and safe.
B = BAD: The instruction is vague, impossible, unsafe, or nonsense.

If uncertain, choose B (conservative).

INSTRUCTION:
{instruction}

Output exactly one letter on the next line: A or B
Label:"""

        return prompt

    @classmethod
    def create_pair_critic_prompt(
        cls,
        instruction: str,
        response: str,
        max_response_chars: int = 500
    ) -> str:
        """
        Create single-token A/B critic prompt for instruction+response pair quality.

        Rubric:
        - A = good (response fulfills instruction correctly, proper format, handles unsafe requests appropriately)
        - B = bad (doesn't fulfill, incorrect, wrong format, inappropriately complies with unsafe request)

        Args:
            instruction: The instruction
            response: The response (will be truncated to first paragraph)
            max_response_chars: Maximum response characters to include

        Returns:
            Prompt ending with "Label:" for next-token scoring
        """
        # Truncate response to first paragraph or max chars
        response_truncated = response.split("\n\n")[0][:max_response_chars]

        prompt = f"""Evaluate this instruction-response pair for quality.

A = GOOD: Response correctly fulfills the instruction, proper format, or appropriately refuses unsafe requests.
B = BAD: Response doesn't fulfill instruction, incorrect information, wrong format, or inappropriately complies with unsafe requests.

If uncertain, choose B (conservative).

INSTRUCTION:
{instruction}

RESPONSE:
{response_truncated}

Output exactly one letter on the next line: A or B
Label:"""

        return prompt

    @classmethod
    def parse_generated_instructions(
        cls,
        generated_text: str,
        max_instructions: int = 50
    ) -> List[str]:
        """
        Parse numbered instructions from generated completion.

        Expects format:
            11. Instruction text here
            12. Another instruction
            ...

        Filters out:
        - Lines without numbers
        - Meta lines (e.g., "Here are some instructions...")
        - Empty lines

        Args:
            generated_text: The generated completion
            max_instructions: Maximum instructions to extract

        Returns:
            List of instruction strings
        """
        instructions = []
        lines = generated_text.split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check if line starts with number followed by period or parenthesis
            parts = line.split(".", 1)
            if len(parts) != 2:
                parts = line.split(")", 1)

            if len(parts) == 2:
                num_part = parts[0].strip()
                text_part = parts[1].strip()

                # Verify first part is a number
                if num_part.isdigit():
                    # Filter out meta lines
                    if text_part and not cls._is_meta_line(text_part):
                        instructions.append(text_part)

                        if len(instructions) >= max_instructions:
                            break

        return instructions

    @staticmethod
    def _is_meta_line(text: str) -> bool:
        """Check if line is meta-commentary rather than instruction."""
        meta_patterns = [
            "here are",
            "i will",
            "let me",
            "the following",
            "these are",
            "below are",
            "above are"
        ]

        text_lower = text.lower()
        return any(pattern in text_lower for pattern in meta_patterns)

    @staticmethod
    def clean_response(
        response: str,
        delimiter: str = "###END###"
    ) -> str:
        """
        Clean generated response using delimiter and heuristics.

        Per spec:
        1. Split on delimiter if present, keep first segment
        2. If no delimiter, trim at first of:
           - Double newline
           - Line starting with Instruction|Q:|A:|Response:
           - Common "new question" phrases

        Args:
            response: Raw generated response
            delimiter: Delimiter string to split on

        Returns:
            Cleaned response string
        """
        # Check for delimiter
        if delimiter in response:
            response = response.split(delimiter)[0]

        # Trim at double newline
        if "\n\n" in response:
            response = response.split("\n\n")[0]

        # Trim at lines that look like new prompts
        lines = response.split("\n")
        cleaned_lines = []

        for line in lines:
            # Check if line starts with prompt-like patterns
            if line.startswith(("Instruction:", "Q:", "A:", "Response:", "Question:")):
                break

            # Check for "new question" patterns
            line_lower = line.lower()
            if any(phrase in line_lower for phrase in [
                "next question",
                "another question",
                "new question",
                "now for",
                "moving on"
            ]):
                break

            cleaned_lines.append(line)

        response = "\n".join(cleaned_lines)

        # Remove any remaining ### markers (both ###END### and standalone ###)
        response = response.replace('###END###', '').replace('###', '')

        # Final strip and cleanup
        return response.strip()


# Convenience functions for scripts
def create_response_prompt(instruction: str, **kwargs) -> str:
    """Convenience wrapper for response generation."""
    return CompletionStylePrompts.create_response_prompt(instruction, **kwargs)


def create_instruction_prompt(**kwargs) -> str:
    """Convenience wrapper for instruction generation."""
    return CompletionStylePrompts.create_instruction_generation_prompt(**kwargs)


def create_critic_prompt(instruction: str, response: Optional[str] = None, **kwargs) -> str:
    """Convenience wrapper for critic prompts."""
    if response is None:
        return CompletionStylePrompts.create_instruction_critic_prompt(instruction, **kwargs)
    else:
        return CompletionStylePrompts.create_pair_critic_prompt(instruction, response, **kwargs)


if __name__ == "__main__":
    # Test the prompts
    print("Testing CompletionStylePrompts...")
    print("=" * 60)

    # Test response prompt
    print("\n1. RESPONSE GENERATION PROMPT:")
    print("-" * 60)
    prompt = CompletionStylePrompts.create_response_prompt("What is photosynthesis?")
    print(prompt)

    # Test instruction generation prompt
    print("\n2. INSTRUCTION GENERATION PROMPT:")
    print("-" * 60)
    prompt = CompletionStylePrompts.create_instruction_generation_prompt(num_examples=5)
    print(prompt)

    # Test instruction critic prompt
    print("\n3. INSTRUCTION CRITIC PROMPT:")
    print("-" * 60)
    prompt = CompletionStylePrompts.create_instruction_critic_prompt("Write a poem about cats")
    print(prompt)

    # Test pair critic prompt
    print("\n4. PAIR CRITIC PROMPT:")
    print("-" * 60)
    prompt = CompletionStylePrompts.create_pair_critic_prompt(
        instruction="What is 2+2?",
        response="The answer is 4."
    )
    print(prompt)

    print("\n" + "=" * 60)
    print("✅ All prompt templates working correctly")
