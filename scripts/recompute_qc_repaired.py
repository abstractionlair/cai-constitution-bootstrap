#!/usr/bin/env python3
"""
Recompute QC on Repaired Stage 1 Data

Uses the corrected runaway heuristic (pattern-based detection).

Usage:
    python scripts/recompute_qc_repaired.py
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def load_data(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL data."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def is_runaway(response: str) -> bool:
    """
    Detect runaway responses using pattern-based heuristic.

    A response is a runaway if it contains prompt artifacts like:
    - Starts generating new instructions
    - Contains chat template markers
    - Shows signs of continuing the prompt pattern

    This is the CORRECTED heuristic (not the buggy len > 200 check).
    """
    runaway_patterns = [
        '\n\nInstruction:',
        '\n\nQuestion:',
        '\n\nQ:',
        '\nUser:',
        '\nAssistant:',
        '\nHuman:',
        '<|im_start|>',
        '<|im_end|>'
    ]

    # Check for prompt continuation patterns
    for pattern in runaway_patterns:
        if pattern in response:
            return True

    # Also flag extremely long responses as potential runaways
    # (but much more lenient than the old 200 char limit)
    if len(response) > 500:
        return True

    return False


def compute_qc(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute QC metrics on repaired data using corrected heuristic.
    """
    logger.info("Computing QC metrics...")

    # Count checks
    total = len(data)
    delimiter_found = 0
    hit_token_limit = 0

    # Acceptance counts
    instructions_good = 0
    pairs_good = 0

    # Token stats
    token_lengths = []

    # Runaway detection (corrected)
    runaway_count = 0

    for example in data:
        response = example['response']

        # Check for delimiter artifacts (should be 0 after cleanup)
        if '###' in response:
            delimiter_found += 1

        # Token length (approximate by character count / 4)
        approx_tokens = len(response) // 4
        token_lengths.append(approx_tokens)

        # Check if hit token limit (max_tokens was 100 in generation)
        if approx_tokens >= 90:  # Close to limit
            hit_token_limit += 1

        # Runaway detection (CORRECTED HEURISTIC)
        if is_runaway(response):
            runaway_count += 1

        # Instruction critique acceptance
        if 'instruction_critique' in example:
            if example['instruction_critique'].get('is_good', False):
                instructions_good += 1

        # Pair critique acceptance
        if 'pair_critique' in example:
            if example['pair_critique'].get('is_good', False):
                pairs_good += 1

    # Compute token statistics
    token_stats = {
        'median': float(np.median(token_lengths)),
        'mean': float(np.mean(token_lengths)),
        'p95': float(np.percentile(token_lengths, 95)),
        'min': int(np.min(token_lengths)),
        'max': int(np.max(token_lengths))
    }

    # Compute rates
    runaway_rate = runaway_count / total if total > 0 else 0
    delimiter_leakage_rate = delimiter_found / total if total > 0 else 0
    token_limit_rate = hit_token_limit / total if total > 0 else 0
    instruction_acceptance = instructions_good / total if total > 0 else 0
    pair_acceptance = pairs_good / total if total > 0 else 0

    # Check thresholds (from spec)
    thresholds = {
        'runaway_rate_max': 0.05,  # 5%
        'token_limit_hits_max': 0.10,  # 10%
        'delimiter_leakage': 0,  # Must be 0
        'median_tokens_max': 40,
        'instruction_acceptance_min': 0.5,  # 50%
        'pair_acceptance_min': 0.5  # 50%
    }

    # Evaluate thresholds
    failed_reasons = []
    if runaway_rate > thresholds['runaway_rate_max']:
        failed_reasons.append(
            f"Runaway rate {runaway_rate * 100:.1f}% >= {thresholds['runaway_rate_max'] * 100:.1f}%"
        )
    if token_limit_rate > thresholds['token_limit_hits_max']:
        failed_reasons.append(
            f"Token limit hits {token_limit_rate * 100:.1f}% >= {thresholds['token_limit_hits_max'] * 100:.1f}%"
        )
    if delimiter_found > 0:
        failed_reasons.append(
            f"Delimiter leakage detected: {delimiter_found} instances"
        )
    if token_stats['median'] > thresholds['median_tokens_max']:
        failed_reasons.append(
            f"Median tokens {token_stats['median']} > {thresholds['median_tokens_max']}"
        )
    if instruction_acceptance < thresholds['instruction_acceptance_min']:
        failed_reasons.append(
            f"Instruction acceptance {instruction_acceptance * 100:.1f}% < {thresholds['instruction_acceptance_min'] * 100:.1f}%"
        )
    if pair_acceptance < thresholds['pair_acceptance_min']:
        failed_reasons.append(
            f"Pair acceptance {pair_acceptance * 100:.1f}% < {thresholds['pair_acceptance_min'] * 100:.1f}%"
        )

    thresholds_passed = len(failed_reasons) == 0

    # Build QC summary
    qc_summary = {
        'timestamp': datetime.now().isoformat(),
        'data_file': 'data/stage1_sft_data_repaired.jsonl',
        'heuristic': 'pattern_based_corrected',
        'counts': {
            'total_examples': total,
            'delimiter_found': delimiter_found,
            'hit_token_limit': hit_token_limit,
            'runaway_detected': runaway_count
        },
        'acceptance': {
            'instructions_good': instructions_good,
            'pairs_good': pairs_good
        },
        'token_stats': token_stats,
        'thresholds': thresholds,
        'thresholds_passed': thresholds_passed,
        'failed_reasons': failed_reasons,
        'rates': {
            'runaway_rate': runaway_rate,
            'delimiter_leakage_rate': delimiter_leakage_rate,
            'token_limit_rate': token_limit_rate,
            'instruction_acceptance': instruction_acceptance,
            'pair_acceptance': pair_acceptance
        }
    }

    return qc_summary


def main():
    """Main QC recomputation workflow."""
    logger.info("=" * 60)
    logger.info("RECOMPUTE QC ON REPAIRED DATA")
    logger.info("=" * 60)

    # Load repaired data
    input_path = Path('data/stage1_sft_data_repaired.jsonl')
    if not input_path.exists():
        logger.error(f"❌ Repaired data not found: {input_path}")
        logger.error("   Run scripts/repair_stage1_data.py first")
        return 1

    logger.info(f"\n📥 Loading repaired data from {input_path}")
    data = load_data(input_path)
    logger.info(f"   Loaded {len(data)} examples")

    # Compute QC
    qc_summary = compute_qc(data)

    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("📊 QC RESULTS (Corrected Heuristic)")
    logger.info("=" * 60)
    logger.info(f"   Total examples: {qc_summary['counts']['total_examples']}")
    logger.info(f"   Runaway rate: {qc_summary['rates']['runaway_rate'] * 100:.1f}%")
    logger.info(f"   Delimiter leakage: {qc_summary['counts']['delimiter_found']} instances")
    logger.info(f"   Token limit hits: {qc_summary['rates']['token_limit_rate'] * 100:.1f}%")
    logger.info(f"   Median tokens: {qc_summary['token_stats']['median']}")
    logger.info(f"   Instruction acceptance: {qc_summary['rates']['instruction_acceptance'] * 100:.1f}%")
    logger.info(f"   Pair acceptance: {qc_summary['rates']['pair_acceptance'] * 100:.1f}%")
    logger.info("")

    if qc_summary['thresholds_passed']:
        logger.info("✅ ALL QC THRESHOLDS PASSED")
    else:
        logger.warning("❌ QC THRESHOLDS FAILED:")
        for reason in qc_summary['failed_reasons']:
            logger.warning(f"   - {reason}")

    logger.info("=" * 60)

    # Save QC summary
    output_path = Path('artifacts/qc_summary_repaired.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(qc_summary, f, indent=2)

    logger.info(f"\n💾 QC summary saved: {output_path}")

    return 0


if __name__ == '__main__':
    exit(main())
