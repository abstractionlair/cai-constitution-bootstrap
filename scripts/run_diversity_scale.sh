#!/bin/bash
# Sequential diversity-guided scale generation
# Generates shards 300-357 (58 total) to reach 6k target

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

mkdir -p artifacts/diversity_scale

START_SEED=${1:-300}
END_SEED=${2:-357}

echo "=========================================="
echo "DIVERSITY SCALE GENERATION"
echo "=========================================="
echo "Seeds: $START_SEED to $END_SEED"
echo "Existing data: data/stage1_sft_data_with_pilot.jsonl (1361 examples)"
echo "Target: 6000 total unique examples"
echo "=========================================="
echo ""

for seed in $(seq $START_SEED $END_SEED); do
    echo "--- Shard $seed ---"
    echo "Started: $(date)"

    python scripts/generate_diversity_guided.py \
        --seed $seed \
        --count 100 \
        --existing data/stage1_sft_data_with_pilot.jsonl \
        --output artifacts/diversity_scale/diversity_shard_${seed}.jsonl \
        --temperature 0.8 \
        --rep-penalty 1.3 \
        2>&1 | tee artifacts/diversity_scale/diversity_${seed}.log

    if [ $? -eq 0 ]; then
        echo "✅ Shard $seed complete: $(date)"

        # Count results
        COUNT=$(wc -l < artifacts/diversity_scale/diversity_shard_${seed}.jsonl)
        echo "   Generated: $COUNT pairs"
    else
        echo "❌ Shard $seed failed: $(date)"
        exit 1
    fi

    echo ""
done

echo "=========================================="
echo "✅ SCALE GENERATION COMPLETE"
echo "=========================================="
echo "Completed: $(date)"
echo "Generated shards: $START_SEED to $END_SEED"
echo ""
echo "Next step: Merge and analyze results"
echo "  python scripts/merge_and_analyze_shards.py"
