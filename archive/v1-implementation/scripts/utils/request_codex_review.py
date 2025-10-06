#!/usr/bin/env python3
"""
Request review from Codex (GPT-5) from within Claude Code session.

Allows autonomous Claude Code agent on pod to call in Codex for:
- Methodology validation
- Strategic decisions
- Priority guidance
- Second opinions

Usage (from Claude Code):
    from utils.request_codex_review import request_codex_review

    response = request_codex_review(
        topic="methodology_validation",
        question="Should we use Best-of-N with k=3 or k=5?",
        context={
            "current_approach": "k=3",
            "concern": "May not have enough diversity",
            "budget": "15 GPU hours"
        }
    )

    # Response contains Codex's advice
    print(response['recommendation'])
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def request_codex_review(
    topic: str,
    question: str,
    context: Optional[Dict[str, Any]] = None,
    review_type: str = "methodology",
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Request review from Codex (GPT-5) via subprocess.

    Args:
        topic: Brief topic (e.g., "best_of_n_decision")
        question: The specific question to ask Codex
        context: Dict of relevant context (files, data, concerns)
        review_type: Type of review ("methodology", "priority", "strategy", "second_opinion")
        timeout: Seconds to wait for Codex response (default 5 min)

    Returns:
        Dict with:
            - success: bool
            - recommendation: str (Codex's response)
            - review_file: Path (for audit trail)
            - error: str (if failed)
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    review_dir = Path("/workspace/MaximalCAI/reviews/autonomous")
    review_dir.mkdir(parents=True, exist_ok=True)

    request_file = review_dir / f"{timestamp}_{topic}_request.md"
    response_file = review_dir / f"{timestamp}_{topic}_codex_response.md"

    # Build review request in markdown format
    request_md = f"""# Autonomous Review Request: {topic}

**Requester**: Claude Code (autonomous agent on pod)
**Date**: {datetime.now().isoformat()}
**Type**: {review_type}

---

## Question

{question}

---

## Context

"""

    if context:
        for key, value in context.items():
            request_md += f"**{key}**:\n```\n{value}\n```\n\n"

    request_md += """
---

## Required Response Format

Please provide:
1. **Recommendation**: Clear, actionable recommendation
2. **Reasoning**: Brief justification (2-3 sentences)
3. **Risks**: Any risks or concerns with the recommendation
4. **Approval**: Yes/No - should Claude proceed with this approach?

Keep response concise (< 500 words). This is for autonomous decision-making.
"""

    # Write request file
    with open(request_file, 'w') as f:
        f.write(request_md)

    logger.info(f"📝 Review request written to {request_file}")

    # Construct Codex command
    # Using `codex exec` for non-interactive execution
    codex_prompt = f"""You are reviewing a request from an autonomous Claude Code agent.

Read the review request at: {request_file}

Provide a concise, actionable response following the format specified in the request.

Focus on methodology correctness and strategic soundness."""

    cmd = [
        "codex",
        "exec",  # Non-interactive mode
        "--model", "o3-mini",  # Fast, high-reasoning model for reviews
        "--full-auto",  # No approval prompts (agent can't respond)
        codex_prompt
    ]

    try:
        logger.info(f"🤖 Calling Codex for review...")

        # Run Codex
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/workspace/MaximalCAI"
        )

        if result.returncode != 0:
            error_msg = f"Codex exec failed: {result.stderr}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "review_file": str(request_file)
            }

        # Parse Codex response
        codex_output = result.stdout.strip()

        # Save response
        with open(response_file, 'w') as f:
            f.write(f"# Codex Review Response: {topic}\n\n")
            f.write(f"**Date**: {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")
            f.write(codex_output)

        logger.info(f"✅ Codex response saved to {response_file}")

        # Extract key parts (simple parsing)
        recommendation = _extract_section(codex_output, "Recommendation")
        approval = _extract_approval(codex_output)

        return {
            "success": True,
            "recommendation": recommendation if recommendation else codex_output,
            "full_response": codex_output,
            "approved": approval,
            "review_file": str(response_file),
            "request_file": str(request_file)
        }

    except subprocess.TimeoutExpired:
        error_msg = f"Codex review timed out after {timeout}s"
        logger.error(f"⏰ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "review_file": str(request_file)
        }

    except Exception as e:
        error_msg = f"Unexpected error calling Codex: {e}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "review_file": str(request_file)
        }


def _extract_section(text: str, section_name: str) -> Optional[str]:
    """Extract content from a markdown section."""
    lines = text.split('\n')
    in_section = False
    section_lines = []

    for line in lines:
        if f"**{section_name}**:" in line or f"## {section_name}" in line:
            in_section = True
            continue

        if in_section:
            if line.startswith('**') or line.startswith('##'):
                break
            section_lines.append(line)

    return '\n'.join(section_lines).strip() if section_lines else None


def _extract_approval(text: str) -> Optional[bool]:
    """Extract approval decision from response."""
    text_lower = text.lower()

    # Look for explicit approval markers
    if "approval: yes" in text_lower or "should proceed: yes" in text_lower:
        return True
    if "approval: no" in text_lower or "should proceed: no" in text_lower:
        return False

    return None


# Convenience functions for common review types

def request_methodology_review(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Request methodology validation from Codex."""
    return request_codex_review(
        topic="methodology",
        question=question,
        context=context,
        review_type="methodology"
    )


def request_priority_guidance(options: list, context: Dict[str, Any]) -> Dict[str, Any]:
    """Request prioritization guidance from Codex."""
    question = f"Which option should I prioritize?\n\nOptions:\n"
    for i, opt in enumerate(options, 1):
        question += f"{i}. {opt}\n"

    return request_codex_review(
        topic="prioritization",
        question=question,
        context=context,
        review_type="priority"
    )


def request_second_opinion(concern: str, proposed_solution: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Request second opinion on a technical decision."""
    question = f"""I have a concern and proposed solution. Please validate:

**Concern**: {concern}

**Proposed Solution**: {proposed_solution}

Is this approach sound?"""

    return request_codex_review(
        topic="second_opinion",
        question=question,
        context=context,
        review_type="second_opinion"
    )


if __name__ == "__main__":
    # Test the review request system
    print("Testing Codex review request system...")

    response = request_methodology_review(
        question="Should I use Best-of-N sampling with k=3 or k=5 for DPO preference pairs?",
        context={
            "current_implementation": "Single response per instruction",
            "budget": "15 GPU hours for full dataset",
            "concern": "k=5 gives more diversity but costs more GPU time",
            "dataset_size": "15000 examples"
        }
    )

    if response['success']:
        print("\n✅ Review request successful!")
        print(f"\nRecommendation:\n{response['recommendation']}")
        print(f"\nApproved: {response['approved']}")
        print(f"\nFull response at: {response['review_file']}")
    else:
        print(f"\n❌ Review request failed: {response['error']}")
