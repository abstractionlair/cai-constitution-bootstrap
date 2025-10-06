# Automated Post-Training Experiment

## The Core Idea

One of my takeaways from reading about constitutional AI was that base models already "understand" many concepts, harmlessness just being one example. They just don't reliably express them without post-training.

This project explores: **How much post-training can we automate using that observation?** Beyond just safety.

Can a base model generate its own training data, critique itself using principles it already understands, and bootstrap its way to aligned behavior—with minimal human intervention?

---

## The Approach

Instead of jumping straight to full Constitutional AI, we teach capabilities progressively:

**Stage 1**: Explicit instruction following (foundation) ← *Currently here*
**Stage 2**: Implicit instructions (questions & context)
**Stage 3**: Generation tasks (create examples)
**Stage 4**: Evaluation tasks (judge quality)
**Stage 5**: Revision tasks (improve text)
**Stage 6**: Constitutional integration (full CAI)

Each stage produces a functional model that helps generate training data for the next stage. True bootstrapping.

---

## Goals

- **Maximum automation** in the training pipeline
- **Progressive capability building** (each stage enables the next)
- **Reproducible methodology** (all steps scriptable and documented)
- **Budget-friendly research** (~$150 total)
- **Publication-quality results** with comprehensive documentation


---

## Navigation

**New to this project?**

1. **This file** - Project goals and approach
2. **[/specs/stage_1_explicit_instructions.md](/specs/stage_1_explicit_instructions.md)** - Current stage methodology
3. **[/specs/complete_pipeline.md](/specs/complete_pipeline.md)** - Full pipeline architecture
4. **[/docs/TECHNICAL_SETUP.md](/docs/TECHNICAL_SETUP.md)** - Model, hardware, training details
5. **[/docs/STANDARDS.md](/docs/STANDARDS.md)** - How we work

**Critical lessons learned (v1 → v2):**

- **[/docs/BASE_MODEL_TRUTH.md](/docs/BASE_MODEL_TRUTH.md)** - Chat template contamination (critical!)
- **[/docs/KNOWN_BUGS_AND_FIXES.md](/docs/KNOWN_BUGS_AND_FIXES.md)** - Bugs we've fixed
- **[/docs/POST_TRAINING_APPROACHES.md](/docs/POST_TRAINING_APPROACHES.md)** - Methodology references

**For AI agents:**

- **Claude Code** (implementer): [CLAUDE.md](CLAUDE.md)
- **Gemini** (technical review): [GEMINI.md](GEMINI.md)
- **Codex** (methodology review): [codex.md](codex.md)

---

## Current Status

**V2 Clean Restart**: Building Stage 1 from scratch via autonomous agentic sessions.

- V1 implementation archived to `archive/v1-implementation/` (28 methodology discrepancies found)
- V2 builds clean implementation from specs via session-based approach
- GPT-5 writing high-level session specifications
- Claude Code executing autonomous implementation sessions on pod

---

## About

This is a personal research project exploring automated post-training methods. It's heavily AI-assisted (Claude Code for implementation, Gemini and Codex for review), which is itself an experiment in human-AI collaboration for research.

**Architecture**: V2 uses autonomous agentic sessions where Claude Code builds implementation from specs with minimal human intervention. See [CLAUDE.md](CLAUDE.md) for details.

---

**Questions?** See `/docs/STANDARDS.md` for how things work, or [CLAUDE.md](CLAUDE.md) for autonomous session architecture.
