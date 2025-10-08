#!/usr/bin/env python3
"""
Merge Additional Shards and Analyze Results

Merges new shards with existing clean data, deduplicates, and analyzes:
- Total unique examples
- Duplication rate in new shards
- Quality metrics
- Decision recommendations

Usage:
    python scripts/merge_and_analyze_shards.py
"""

import json
import logging
from pathlib import Path
from collections import Counter
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


def load_jsonl(path: Path):
    """Load JSONL file."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def analyze_duplication(data, label="Dataset"):
    """Analyze duplication patterns."""
    instructions = [ex['instruction'] for ex in data]
    unique = set(instructions)
    counts = Counter(instructions)

    logger.info(f"\n📊 {label} Duplication Analysis")
    logger.info(f"   Total examples: {len(instructions)}")
    logger.info(f"   Unique instructions: {len(unique)}")
    logger.info(f"   Duplication rate: {(1 - len(unique)/len(instructions))*100:.1f}%")

    # Top duplicates
    top_dupes = counts.most_common(5)
    if any(count > 1 for _, count in top_dupes):
        logger.info(f"\n   Top 5 duplicates:")
        for inst, count in top_dupes:
            if count > 1:
                logger.info(f"     {count}× {inst[:60]}...")

    return len(unique), len(instructions)


def main():
    """Main merge and analysis workflow."""
    logger.info("=" * 60)
    logger.info("MERGE AND ANALYZE ADDITIONAL SHARDS")
    logger.info("=" * 60)

    # Load existing clean data
    existing_path = Path('data/stage1_sft_data_clean.jsonl')
    logger.info(f"\n📥 Loading existing clean data: {existing_path}")
    existing_data = load_jsonl(existing_path)
    logger.info(f"   Existing: {len(existing_data)} examples")

    # Load new shards
    shard_dir = Path('artifacts/additional_shards')
    shard_files = sorted(shard_dir.glob('shard_*.jsonl'))

    if not shard_files:
        logger.error(f"❌ No shards found in {shard_dir}")
        return 1

    logger.info(f"\n📥 Loading {len(shard_files)} new shards")
    new_data = []
    for shard_file in shard_files:
        shard_data = load_jsonl(shard_file)
        logger.info(f"   {shard_file.name}: {len(shard_data)} examples")
        new_data.extend(shard_data)

    logger.info(f"\n   Total new examples: {len(new_data)}")

    # Analyze new shards BEFORE merge
    new_unique, new_total = analyze_duplication(new_data, "New Shards (before dedup)")

    # Combine with existing
    logger.info(f"\n🔄 Merging with existing data")
    combined_data = existing_data + new_data
    logger.info(f"   Combined total: {len(combined_data)} examples")

    # Deduplicate combined
    logger.info(f"\n🔄 Deduplicating combined dataset")
    seen = set()
    deduped = []

    existing_instructions = set(ex['instruction'].strip().lower() for ex in existing_data)
    new_unique_added = 0

    for ex in combined_data:
        inst = ex['instruction'].strip().lower()
        if inst not in seen:
            seen.add(inst)
            deduped.append(ex)

            # Track new unique additions
            if inst not in existing_instructions:
                new_unique_added += 1

    logger.info(f"   After dedup: {len(deduped)} unique examples")
    logger.info(f"   New unique added: {new_unique_added}")

    # Save merged data
    output_path = Path('data/stage1_sft_data_merged.jsonl')
    logger.info(f"\n💾 Saving merged data: {output_path}")
    with open(output_path, 'w') as f:
        for ex in deduped:
            f.write(json.dumps(ex) + '\n')
    logger.info(f"   ✅ Saved {len(deduped)} examples")

    # Final analysis
    logger.info("\n" + "=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"   Existing data: {len(existing_data)} examples")
    logger.info(f"   New shards generated: {new_total} examples")
    logger.info(f"   New shard duplication: {(1 - new_unique/new_total)*100:.1f}%")
    logger.info(f"   New unique added: {new_unique_added}")
    logger.info(f"   Final unique total: {len(deduped)}")
    logger.info("=" * 60)

    # Decision recommendations
    logger.info("\n🎯 RECOMMENDATIONS")

    final_count = len(deduped)
    target_min = 6000
    duplication_rate = (1 - new_unique/new_total)

    if final_count >= target_min:
        logger.info(f"   ✅ Target reached: {final_count} >= {target_min}")
        logger.info(f"   → READY FOR SFT TRAINING")
    elif final_count >= 2000:
        logger.info(f"   ⚠️  Below target: {final_count} < {target_min}")
        logger.info(f"   → OPTIONS:")
        logger.info(f"      A) Train now, iterate if insufficient")
        logger.info(f"      B) Generate {int((target_min - final_count) / new_unique * 10)} more shards")
    else:
        logger.info(f"   ❌ Insufficient data: {final_count} < 2000 minimum")
        logger.info(f"   → MUST generate more data")

    if duplication_rate > 0.6:
        logger.info(f"\n   ⚠️  High duplication rate: {duplication_rate*100:.1f}%")
        logger.info(f"   → Consider higher temperature parameters")
        logger.info(f"      - instruction_temperature: 0.7 → 0.9")
        logger.info(f"      - repetition_penalty: 1.1 → 1.3")

    logger.info("=" * 60)

    # Save analysis
    analysis = {
        'existing_examples': len(existing_data),
        'new_examples_generated': new_total,
        'new_unique': new_unique,
        'new_duplication_rate': float(duplication_rate),
        'new_unique_added': new_unique_added,
        'final_unique_total': final_count,
        'target': target_min,
        'target_met': final_count >= target_min
    }

    with open('artifacts/merge_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)

    logger.info(f"\n📄 Analysis saved: artifacts/merge_analysis.json")

    return 0


if __name__ == '__main__':
    exit(main())
