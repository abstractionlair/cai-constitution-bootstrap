#!/usr/bin/env python3
"""
Generate Additional Training Shards

Generate 10 more shards (seeds 110-119) to expand dataset diversity.

Usage:
    python scripts/generate_additional_shards.py
"""

import subprocess
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Generate 10 additional shards."""
    logger.info("=" * 60)
    logger.info("GENERATING ADDITIONAL TRAINING SHARDS")
    logger.info("=" * 60)

    output_dir = Path('artifacts/additional_shards')
    output_dir.mkdir(parents=True, exist_ok=True)

    seeds = range(110, 120)  # 110-119
    target_per_shard = 150

    logger.info(f"\nGenerating {len(list(seeds))} shards")
    logger.info(f"  Seeds: {list(seeds)}")
    logger.info(f"  Target per shard: {target_per_shard} examples")
    logger.info(f"  Output: {output_dir}")

    for i, seed in enumerate(seeds, 1):
        logger.info(f"\n--- Shard {i}/10 (seed={seed}) ---")

        output_file = output_dir / f"shard_{seed}.jsonl"

        # Run pilot script for this shard
        cmd = [
            'python', 'scripts/generate_stage1_pilot_data.py',
            '--seed', str(seed),
            '--count', str(target_per_shard),
            '--output', str(output_file)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes per shard
            )

            # Parse output for key metrics
            for line in result.stdout.split('\n'):
                if any(keyword in line for keyword in ['Generated', 'QC', 'examples', 'PASS', 'FAIL']):
                    logger.info(f"  {line}")

            if result.returncode != 0:
                logger.error(f"  ❌ Shard {seed} failed!")
                logger.error(f"  {result.stderr[:200]}")
            else:
                logger.info(f"  ✅ Shard {seed} complete")

        except subprocess.TimeoutExpired:
            logger.error(f"  ❌ Shard {seed} timed out after 5 minutes")
        except Exception as e:
            logger.error(f"  ❌ Shard {seed} error: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("✅ SHARD GENERATION COMPLETE")
    logger.info("=" * 60)

    # Count results
    shard_files = list(output_dir.glob('shard_*.jsonl'))
    logger.info(f"  Generated shards: {len(shard_files)}")

    total_examples = 0
    for shard_file in shard_files:
        count = sum(1 for _ in open(shard_file))
        total_examples += count

    logger.info(f"  Total examples: {total_examples}")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    exit(main())
