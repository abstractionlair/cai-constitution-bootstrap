#!/usr/bin/env python3
"""
Instruction Quality Critic (Logprob-Based)

Uses single-token probability method (A/B) to judge instruction quality.
Based on GPT-2 style completion prompting for binary classification.
"""

import torch
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_token_logprobs(model, tokenizer, prompt: str, candidate_tokens: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Get log probabilities for candidate tokens at the next position.

    Args:
        model: Language model
        tokenizer: Tokenizer
        prompt: Input prompt
        candidate_tokens: List of tokens to get probabilities for (e.g., ['A', 'B'])

    Returns:
        Dict mapping token_text -> {'logprob': float, 'token_id': int}
    """
    # Tokenize the prompt
    inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=1600)
    inputs = inputs.to(model.device)

    # Get model logits
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0, -1, :]  # Last position logits

    # Convert to log probabilities
    log_probs = torch.nn.functional.log_softmax(logits, dim=-1)

    # Get log probabilities for candidate tokens
    token_logprobs = {}
    for token_text in candidate_tokens:
        # Try different variations of token encoding
        token_variations = [
            token_text,
            f" {token_text}",  # With leading space
        ]

        best_logprob = float('-inf')
        best_token_id = None

        for variation in token_variations:
            try:
                token_ids = tokenizer.encode(variation, add_special_tokens=False)
                if len(token_ids) == 1:  # Single token
                    token_id = token_ids[0]
                    logprob = log_probs[token_id].item()
                    if logprob > best_logprob:
                        best_logprob = logprob
                        best_token_id = token_id
            except:
                continue

        token_logprobs[token_text] = {
            'logprob': best_logprob,
            'token_id': best_token_id
        }

    return token_logprobs


def create_instruction_quality_prompt(instruction: str) -> str:
    """
    Create prompt for judging instruction quality via single-token completion.

    Args:
        instruction: The instruction to judge

    Returns:
        Prompt ending with "Label:" for A/B completion
    """
    prompt = """Instruction Quality Judge (binary)

Labels: A = good instruction, B = bad instruction

Rules (succinct):
- A if the instruction is clear, specific, achievable, and safe to follow
- A if the instruction is a reasonable task someone might ask an AI to do
- B if the instruction is vague, impossible, unsafe, or nonsensical
- B if uncertain

INSTRUCTION:
{instruction}

Output exactly one letter on the next line: A or B
Label:""".format(instruction=instruction)

    return prompt


def critique_instruction_quality(
    model,
    tokenizer,
    instruction: str,
    confidence_threshold: float = 1.0
) -> Dict[str, Any]:
    """
    Judge instruction quality using logprob-based A/B classification.

    Args:
        model: Language model
        tokenizer: Tokenizer
        instruction: Instruction to judge
        confidence_threshold: Minimum log-prob margin for confident judgment

    Returns:
        Dict with:
            - is_good: bool (True if judged as good instruction)
            - predicted_label: 'A' or 'B'
            - logp_a: float (log probability of 'A')
            - logp_b: float (log probability of 'B')
            - margin: float (abs difference between logp_a and logp_b)
            - confident: bool (True if margin >= threshold)
    """
    # Create prompt
    prompt = create_instruction_quality_prompt(instruction)

    # Get log probabilities for A and B
    candidate_tokens = ['A', 'B']
    token_logprobs = get_token_logprobs(model, tokenizer, prompt, candidate_tokens)

    logp_a = token_logprobs['A']['logprob']
    logp_b = token_logprobs['B']['logprob']

    # Choose the token with higher log probability
    if logp_a > logp_b:
        predicted_label = 'A'  # good
        is_good = True
    else:
        predicted_label = 'B'  # bad
        is_good = False

    # Calculate confidence margin
    margin = abs(logp_a - logp_b)
    confident = margin >= confidence_threshold

    return {
        'is_good': is_good,
        'predicted_label': predicted_label,
        'logp_a': logp_a,
        'logp_b': logp_b,
        'margin': margin,
        'confident': confident
    }


def create_instruction_response_quality_prompt(instruction: str, response: str) -> str:
    """
    Create prompt for judging instruction+response pair quality.

    Args:
        instruction: The instruction
        response: The response to judge

    Returns:
        Prompt ending with "Label:" for A/B completion
    """
    # Clean up the response - take first paragraph only
    clean_response = response.split('\n\n')[0].strip()

    prompt = """Instruction-Following Judge (binary)

Labels: A = good response, B = bad response

Rules (succinct):
- A if RESPONSE directly fulfills the INSTRUCTION, is correct (for factual asks), follows stated format/length, and is safe
- A if the INSTRUCTION is unsafe and the RESPONSE refuses briefly and (optionally) suggests safer alternatives
- Otherwise B. If uncertain, choose B

INSTRUCTION:
{instruction}

RESPONSE:
{response}

Output exactly one letter on the next line: A or B
Label:""".format(instruction=instruction, response=clean_response)

    return prompt


def critique_instruction_response_pair(
    model,
    tokenizer,
    instruction: str,
    response: str,
    confidence_threshold: float = 1.0
) -> Dict[str, Any]:
    """
    Judge instruction+response pair quality using logprob-based A/B classification.

    Args:
        model: Language model
        tokenizer: Tokenizer
        instruction: The instruction
        response: The response to judge
        confidence_threshold: Minimum log-prob margin for confident judgment

    Returns:
        Dict with:
            - is_good: bool (True if judged as good pair)
            - predicted_label: 'A' or 'B'
            - logp_a: float (log probability of 'A')
            - logp_b: float (log probability of 'B')
            - margin: float (abs difference between logp_a and logp_b)
            - confident: bool (True if margin >= threshold)
    """
    # Create prompt
    prompt = create_instruction_response_quality_prompt(instruction, response)

    # Get log probabilities for A and B
    candidate_tokens = ['A', 'B']
    token_logprobs = get_token_logprobs(model, tokenizer, prompt, candidate_tokens)

    logp_a = token_logprobs['A']['logprob']
    logp_b = token_logprobs['B']['logprob']

    # Choose the token with higher log probability
    if logp_a > logp_b:
        predicted_label = 'A'  # good
        is_good = True
    else:
        predicted_label = 'B'  # bad
        is_good = False

    # Calculate confidence margin
    margin = abs(logp_a - logp_b)
    confident = margin >= confidence_threshold

    return {
        'is_good': is_good,
        'predicted_label': predicted_label,
        'logp_a': logp_a,
        'logp_b': logp_b,
        'margin': margin,
        'confident': confident
    }


if __name__ == "__main__":
    # Test prompt generation
    print("=" * 70)
    print("Test: Instruction Quality Prompt")
    print("=" * 70)

    test_instruction = "List five types of animals"
    prompt = create_instruction_quality_prompt(test_instruction)
    print(prompt)
    print("\n" + "=" * 70)

    print("\nTest: Instruction+Response Quality Prompt")
    print("=" * 70)

    test_response = "1. Dog\n2. Cat\n3. Elephant\n4. Lion\n5. Bear"
    prompt = create_instruction_response_quality_prompt(test_instruction, test_response)
    print(prompt)
    print("\n" + "=" * 70)
