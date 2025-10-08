#!/usr/bin/env python3
"""
InstructionCritic - Canonical implementation of single-token A/B critique via logprobs.

This is the ONLY way to perform automated quality judgments in this project.
All critics use logprob-based decisions (no sampling), following the single-token A/B contract.

Key responsibilities:
- Extract next-token logprobs for 'A' and 'B' tokens
- Handle variants (with/without leading space)
- Compute margin and confidence
- Return structured critique results

Usage:
    from utils.instruction_critic import InstructionCritic
    from utils.clean_model_loader import load_clean_base_model
    from utils.completion_prompts import CompletionStylePrompts

    model, tokenizer, _ = load_clean_base_model()
    critic = InstructionCritic(model, tokenizer)

    # Critique instruction quality
    result = critic.critique_instruction(
        instruction="What is photosynthesis?",
        confidence_threshold=1.0
    )

    # Critique instruction+response pair
    result = critic.critique_pair(
        instruction="What is 2+2?",
        response="The answer is 4.",
        confidence_threshold=1.0
    )
"""

import torch
import logging
from typing import Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CritiqueResult:
    """Structured result from A/B critique."""
    is_good: bool  # True if A (good), False if B (bad)
    predicted_label: str  # 'A' or 'B'
    logp_a: float  # Log probability of 'A'
    logp_b: float  # Log probability of 'B'
    margin: float  # Absolute difference |logp_a - logp_b|
    confident: bool  # True if margin >= threshold
    confidence_threshold: float  # Threshold used

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_good": self.is_good,
            "predicted_label": self.predicted_label,
            "logp_a": self.logp_a,
            "logp_b": self.logp_b,
            "margin": self.margin,
            "confident": self.confident,
            "confidence_threshold": self.confidence_threshold
        }


class InstructionCritic:
    """
    Canonical implementation of single-token A/B critique via logprobs.

    All automated quality judgments must use this utility.
    No duplicate implementations allowed (DRY principle).
    """

    def __init__(self, model, tokenizer):
        """
        Initialize critic.

        Args:
            model: Loaded model (from CleanModelLoader)
            tokenizer: Tokenizer (from CleanModelLoader)
        """
        self.model = model
        self.tokenizer = tokenizer
        self.device = model.device

        # Pre-compute token IDs for A and B (with and without space)
        self.token_ids = self._get_label_token_ids()

    def _get_label_token_ids(self) -> Dict[str, int]:
        """
        Get token IDs for 'A' and 'B' labels (with and without leading space).

        Returns:
            Dict with keys: 'A', ' A', 'B', ' B'
        """
        token_ids = {}

        for label in ['A', 'B']:
            # Without space
            tokens = self.tokenizer.encode(label, add_special_tokens=False)
            if len(tokens) == 1:
                token_ids[label] = tokens[0]
            else:
                logger.warning(f"Label '{label}' tokenizes to {len(tokens)} tokens: {tokens}")
                token_ids[label] = tokens[0]  # Use first token

            # With leading space
            tokens_space = self.tokenizer.encode(f" {label}", add_special_tokens=False)
            if len(tokens_space) == 1:
                token_ids[f" {label}"] = tokens_space[0]
            else:
                # Might tokenize as [space_token, label_token]
                # Try to find the right token
                token_ids[f" {label}"] = tokens_space[-1]  # Use last token

        logger.debug(f"Label token IDs: {token_ids}")
        return token_ids

    def get_next_token_logprobs(
        self,
        prompt: str,
        token_ids: list
    ) -> Dict[int, float]:
        """
        Get log probabilities for specific next tokens.

        Args:
            prompt: The prompt to evaluate
            token_ids: List of token IDs to get logprobs for

        Returns:
            Dict mapping token_id -> log_prob
        """
        # Tokenize prompt
        inputs = self.tokenizer(
            prompt,
            add_special_tokens=False,
            return_tensors="pt"
        ).to(self.device)

        # Get model outputs
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits

        # Get logits for next token (after last input token)
        next_token_logits = logits[0, -1, :]

        # Convert to log probabilities
        log_probs = torch.nn.functional.log_softmax(next_token_logits, dim=-1)

        # Extract requested token log probs
        result = {}
        for token_id in token_ids:
            result[token_id] = log_probs[token_id].item()

        return result

    def critique_instruction(
        self,
        instruction: str,
        confidence_threshold: float = 1.0
    ) -> CritiqueResult:
        """
        Critique instruction quality using single-token A/B scoring.

        A = good (clear, specific, achievable, safe)
        B = bad (vague, impossible, unsafe, nonsense)

        Args:
            instruction: The instruction to critique
            confidence_threshold: Minimum margin for confidence

        Returns:
            CritiqueResult with verdict and logprobs
        """
        # Import here to avoid circular dependency
        from utils.completion_prompts import CompletionStylePrompts

        # Create critic prompt
        prompt = CompletionStylePrompts.create_instruction_critic_prompt(instruction)

        # Get logprobs for A and B variants
        token_ids = [
            self.token_ids['A'],
            self.token_ids[' A'],
            self.token_ids['B'],
            self.token_ids[' B']
        ]

        logprobs = self.get_next_token_logprobs(prompt, token_ids)

        # Take max logprob across variants (with/without space)
        logp_a = max(
            logprobs.get(self.token_ids['A'], float('-inf')),
            logprobs.get(self.token_ids[' A'], float('-inf'))
        )

        logp_b = max(
            logprobs.get(self.token_ids['B'], float('-inf')),
            logprobs.get(self.token_ids[' B'], float('-inf'))
        )

        # Compute margin and decision
        margin = abs(logp_a - logp_b)
        is_good = logp_a > logp_b
        predicted_label = 'A' if is_good else 'B'
        confident = margin >= confidence_threshold

        return CritiqueResult(
            is_good=is_good,
            predicted_label=predicted_label,
            logp_a=logp_a,
            logp_b=logp_b,
            margin=margin,
            confident=confident,
            confidence_threshold=confidence_threshold
        )

    def critique_pair(
        self,
        instruction: str,
        response: str,
        confidence_threshold: float = 1.0
    ) -> CritiqueResult:
        """
        Critique instruction+response pair quality using single-token A/B scoring.

        A = good (fulfills instruction, correct format, handles unsafe appropriately)
        B = bad (doesn't fulfill, incorrect, wrong format, inappropriate compliance)

        Args:
            instruction: The instruction
            response: The response
            confidence_threshold: Minimum margin for confidence

        Returns:
            CritiqueResult with verdict and logprobs
        """
        # Import here to avoid circular dependency
        from utils.completion_prompts import CompletionStylePrompts

        # Create critic prompt
        prompt = CompletionStylePrompts.create_pair_critic_prompt(instruction, response)

        # Get logprobs for A and B variants
        token_ids = [
            self.token_ids['A'],
            self.token_ids[' A'],
            self.token_ids['B'],
            self.token_ids[' B']
        ]

        logprobs = self.get_next_token_logprobs(prompt, token_ids)

        # Take max logprob across variants (with/without space)
        logp_a = max(
            logprobs.get(self.token_ids['A'], float('-inf')),
            logprobs.get(self.token_ids[' A'], float('-inf'))
        )

        logp_b = max(
            logprobs.get(self.token_ids['B'], float('-inf')),
            logprobs.get(self.token_ids[' B'], float('-inf'))
        )

        # Compute margin and decision
        margin = abs(logp_a - logp_b)
        is_good = logp_a > logp_b
        predicted_label = 'A' if is_good else 'B'
        confident = margin >= confidence_threshold

        return CritiqueResult(
            is_good=is_good,
            predicted_label=predicted_label,
            logp_a=logp_a,
            logp_b=logp_b,
            margin=margin,
            confident=confident,
            confidence_threshold=confidence_threshold
        )

    def batch_critique_instructions(
        self,
        instructions: list,
        confidence_threshold: float = 1.0,
        batch_size: int = 8
    ) -> list:
        """
        Critique multiple instructions in batches for efficiency.

        Args:
            instructions: List of instruction strings
            confidence_threshold: Minimum margin for confidence
            batch_size: Number of instructions per batch

        Returns:
            List of CritiqueResult objects
        """
        results = []

        for i in range(0, len(instructions), batch_size):
            batch = instructions[i:i + batch_size]

            for instruction in batch:
                result = self.critique_instruction(
                    instruction,
                    confidence_threshold=confidence_threshold
                )
                results.append(result)

        return results

    def batch_critique_pairs(
        self,
        pairs: list,
        confidence_threshold: float = 1.0,
        batch_size: int = 8
    ) -> list:
        """
        Critique multiple instruction-response pairs in batches.

        Args:
            pairs: List of (instruction, response) tuples
            confidence_threshold: Minimum margin for confidence
            batch_size: Number of pairs per batch

        Returns:
            List of CritiqueResult objects
        """
        results = []

        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]

            for instruction, response in batch:
                result = self.critique_pair(
                    instruction,
                    response,
                    confidence_threshold=confidence_threshold
                )
                results.append(result)

        return results


# Convenience function for scripts
def create_critic(model, tokenizer) -> InstructionCritic:
    """Convenience wrapper to create critic."""
    return InstructionCritic(model, tokenizer)


if __name__ == "__main__":
    # Test the critic (without actual model)
    print("Testing InstructionCritic...")
    print("=" * 60)

    print("✅ InstructionCritic module loaded successfully")
    print("✅ All dependencies available")
    print("\nTo test critique, use:")
    print("  model, tokenizer, _ = load_clean_base_model()")
    print("  critic = InstructionCritic(model, tokenizer)")
    print("  result = critic.critique_instruction('What is AI?')")
