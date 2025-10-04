# Post-Training Approaches: Beyond PPO/GRPO

**Context**: This project uses CAI-inspired auto-labeling to generate training data (instruction following, truthfulness, harmlessness, reasoning). This document explores whether we can do better than PPO/GRPO given this capability.

**TL;DR**: Yes. RL-free preference learning (DPO/SimPO/ORPO) is usually more stable, cost-effective, and sample-efficient for our use case.

---

## Why RL-Free Works Better Here

**Key insight**: Our labels come from offline judges (AI feedback, constitutional principles), not from interactive environments. PPO/GRPO's strengths (on-policy rollouts, exploration bonuses, credit assignment over long horizons) don't provide much value when we're already producing high-quality preference pairs at scale.

**Benefits of RL-free approaches**:
- Each preference pair carries strong signal ("prefer A over B" vs. noisy scalar reward)
- Offline generation + reuse (no need for fresh on-policy rollouts)
- No value model or advantage estimates (reduces variance)
- More sample-efficient for instruction/truthfulness/harmlessness domains

---

## Recommended Approach: Preference Optimization

### Primary Methods

**DPO (Direct Preference Optimization)** - Default choice
- Use when you have (chosen, rejected) pairs
- Simple, stable, fast
- Use SFT model as reference
- Settings: β ≈ 0.1–0.3

**SimPO / ORPO** - Reference-free alternatives
- SimPO: Adds margin to better separate winners from losers
- ORPO: Clean single-stage loss
- Use when you don't want to maintain a reference model

**KTO (Kahneman-Tversky Optimization)** - For unary feedback
- Use when you only have good/bad labels for single outputs
- Weaker signal per sample (~1.5–2× more data needed)

---

## High-Quality Pair Construction

**The key to sample efficiency is generating high-precision pairs:**

### 1. Best-of-N (BoN) → Pairs
- Sample k candidates per instruction
- Judge picks the best
- Generates k-1 pairs: (best, each other candidate)
- More pairs from same prompts

### 2. Confidence Weighting
- Compute judge margin (log-prob gap or majority vote)
- Train only on high-margin pairs (or oversample them)
- Abstain > guess: quality beats quantity

### 3. Hard Negatives (Critical!)
Include diverse rejection types:
- Unwarranted refusals
- Wrong facts / hallucinations
- Off-topic responses
- Format violations
- Excessive verbosity
- Under-explanation

**Why**: Hard negatives move the model most effectively

### 4. Verifier Gating
For math/code tasks:
- Gate "chosen" through unit tests/checkers
- Everything that fails becomes "rejected"
- Provides objective ground truth

---

## Multi-Objective Alignment (No PPO Needed)

Align helpfulness, truthfulness, harmlessness, reasoning together:

### Mixed Batches
Interleave pairs from different domains:
- Helpful vs. hedging
- Truthful vs. hallucinated
- Safe refusal vs. unsafe compliance
- Reasoning-improved vs. baseline

### Decouple Refusal Bias
Include both:
- Safe prompts where refusals are rejected (should answer)
- Unsafe prompts where refusals are chosen (should refuse)

Model learns the boundary, not blanket refusals.

### Process-Aware Pairs (Optional)
If collecting critique→rewrite traces:
- Pair A₁ (post-critique) as chosen
- vs. A₀ (original) as rejected
- No need to train on hidden CoT

---

## "Online" Improvement Without PPO

**Online-DPO style loops** (still RL-free):

1. Use current policy to sample candidates
2. Judge pairs (A/B margin; checklist fallback)
3. Add high-confidence pairs to replay buffer
4. Fine-tune with DPO/SimPO
5. Repeat

**Benefits**:
- Iterative improvement like RL
- No reward model optimization instability
- Cheaper than PPO on-policy rollouts

---

## Sample Efficiency

### Expected Data Requirements
(Conservative estimates for clean, diverse data using LoRA/QLoRA, 4k context)

| Model Size | SFT (positives) | Preference pairs (clear win) | "Great" tier |
|------------|-----------------|------------------------------|--------------|
| 7-9B | 2-5k | 5-10k pairs | 20-30k |
| 13-14B | 3-8k | 8-15k pairs | 25-40k |
| 27-32B | 5-10k | 10-30k pairs | 40-80k |

**Notes**:
- High-quality pairs (BoN + strong judge + verifier gating + hard negatives) → lower end of range
- Our Stage 1 baseline: 200 SFT examples, 188 preference pairs (pilot scale)
- Full Stage 1: Target 500-1000 SFT, 1000-2000 preference pairs

### Comparison to PPO/GRPO
- **Fewer unique prompts** needed
- **Fewer total tokens** generated
- **No on-policy rollout costs**
- **Better stability** (no value function training)

---

## When to Use RL

**Keep a tiny PPO/GRPO budget only for:**
- Tool-use with delayed success signals
- Interactive environments
- Non-differentiable objectives that can't be cast as preferences
- Long-horizon tasks where credit assignment is genuinely needed

**Even then**: Start with DPO-pretrained policy, do short RL polish (not RL from scratch)

---

## Practical Settings

### DPO/SimPO Configuration
```python
β = 0.1 - 0.3  # Lower = stay closer to reference
lora_r = 32 - 64
eval_steps = 100 - 200
learning_rate = 5e-5 - 1e-4
```

### Sampling Temperatures
```python
answers = 0.7        # Diverse candidate generation
critiques = 0.2-0.3  # Focused, consistent feedback
rewrites = 0.5       # Balanced improvement
```

### Quality Control
- **Length control**: Include format-violation and over-verbose negatives to prevent "longer is better" drift
- **Refusal balance**: Track refusal rate on safe vs. unsafe holdouts to avoid over-refusal
- **Margin threshold**: Only train on pairs with clear judge confidence

---

## Recommended Stack for This Project

### Stage 1 (Current)
1. ✅ **SFT** on clean positives (200 examples pilot)
2. 📋 **DPO** on high-margin pairs (188 pairs pilot)
3. 📋 **Evaluation** on held-out test set (130 instructions)

### Full Stage 1 Run
1. **SFT** on expanded dataset (500-1000 examples)
2. **DPO** with BoN pair generation (1000-2000 pairs from SFT model)
3. **Online refresh**: Regenerate with DPO model, relabel, train again

### Future Stages
- Same pattern: SFT → DPO → Online refresh
- Multi-objective batches as capabilities expand
- Consider SimPO for reference-free approach in later stages

### Optional
- Tiny PPO polish only if we add tool-use or interactive evaluation in later stages

---

## Key Takeaways

1. **DPO/SimPO/ORPO** usually deliver better accuracy-per-dollar and smoother engineering than PPO/GRPO for our domains
2. **High-quality pair construction** is more important than quantity
3. **Hard negatives** and **confidence filtering** are critical for sample efficiency
4. **BoN pair generation** gets more signal from same prompts
5. **Online refresh loops** provide iterative improvement without RL instability
6. **Save RL** for truly interactive/long-horizon cases (which we may never need)

---

## Project Implications

### Current Stage 1 Plan
Our Stage 1 already uses SFT → DPO, which aligns with these recommendations. Key refinements:

- ✅ We're using DPO (not PPO/GRPO)
- 📋 Consider BoN sampling during preference pair generation
- 📋 Add confidence filtering to pair acceptance
- 📋 Expand hard negative diversity
- 📋 Implement online refresh after initial DPO training

### Budget Impact
RL-free approach likely **reduces** our GPU budget:
- No on-policy rollout costs
- Fewer total tokens needed
- More stable training (less trial-and-error)
- Can batch-generate and reuse data

### Sample Size Planning
For Qwen-2.5-32B (our model):
- **Target SFT**: 500-1000 examples (currently have 200 ✅)
- **Target DPO**: 1000-2000 pairs (currently have 188 ✅)
- **Quality focus**: BoN + confidence filtering + hard negatives

This aligns with our ~$150 budget and should be sufficient for strong Stage 1 results.

---

**References**:
- DPO paper: Rafailov et al. 2023
- SimPO: Song et al. 2024
- ORPO: Hong et al. 2024
- KTO: Ethayarajh et al. 2024
- Constitutional AI: Bai et al. 2022

**See also**:
- `/docs/TECHNICAL_SETUP.md` - Current training approach
- `/docs/IMPLEMENTATION_REGISTRY.md` - Existing DPO implementation
- `ROADMAP.md` - Stage 1 training plans
