#!/bin/bash
# Regenerate shards that had >2% truncation rate

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

mkdir -p artifacts/regenerated_shards

echo "=========================================="
echo "REGENERATING TRUNCATED SHARDS"
echo "=========================================="
echo "19 shards total:"
echo "  - 6 baseline shards (100, 103-105, 107, 109)"
echo "  - 13 diversity shards (306, 311, 323, 325-327, 331, 338, 343, 348, 363, 371, 382)"
echo "=========================================="
echo ""

# Baseline shards (use pilot script)
BASELINE_SEEDS="100 103 104 105 107 109"

for seed in $BASELINE_SEEDS; do
    echo "--- Baseline shard $seed ---"
    echo "Started: $(date)"

    python scripts/generate_stage1_pilot_data.py \
        --seed $seed \
        --count 150 \
        --output artifacts/regenerated_shards/baseline_shard_${seed}.jsonl \
        --response-max-tokens 200

    if [ $? -eq 0 ]; then
        echo "✅ Shard $seed complete"
    else
        echo "❌ Shard $seed failed"
        exit 1
    fi
    echo ""
done

# Diversity shards (use diversity script)
DIVERSITY_SEEDS="306 311 323 325 326 327 331 338 343 348 363 371 382"

for seed in $DIVERSITY_SEEDS; do
    echo "--- Diversity shard $seed ---"
    echo "Started: $(date)"

    python scripts/generate_diversity_guided.py \
        --seed $seed \
        --count 100 \
        --existing data/stage1_sft_data_with_pilot.jsonl \
        --output artifacts/regenerated_shards/diversity_shard_${seed}.jsonl \
        --temperature 0.8 \
        --rep-penalty 1.3

    if [ $? -eq 0 ]; then
        echo "✅ Shard $seed complete"
    else
        echo "❌ Shard $seed failed"
        exit 1
    fi
    echo ""
done

echo "=========================================="
echo "✅ REGENERATION COMPLETE"
echo "=========================================="
echo "Completed: $(date)"
echo "Next: Merge regenerated shards with clean shards"
