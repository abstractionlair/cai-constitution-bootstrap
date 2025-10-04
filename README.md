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
2. **[ROADMAP.md](ROADMAP.md)** - Milestones and progress
3. **[/docs/TECHNICAL_SETUP.md](/docs/TECHNICAL_SETUP.md)** - Model, hardware, training details
4. **[/docs/STANDARDS.md](/docs/STANDARDS.md)** - How we work
5. **[/status/PROJECT_STATUS.md](/status/PROJECT_STATUS.md)** - Current focus

**Want to understand the code?**

- **[/docs/IMPLEMENTATION_REGISTRY.md](/docs/IMPLEMENTATION_REGISTRY.md)** - Catalog of scripts
- **[/docs/KNOWN_BUGS_AND_FIXES.md](/docs/KNOWN_BUGS_AND_FIXES.md)** - Bug history
- **[/docs/BASE_MODEL_TRUTH.md](/docs/BASE_MODEL_TRUTH.md)** - Critical quirks
- **[/scripts/](/scripts/)** - Implementation

**For AI agents:**

- **Claude Code** (implementer): [CLAUDE.md](CLAUDE.md)
- **Gemini** (technical review): [GEMINI.md](GEMINI.md)
- **Codex** (methodology review): [codex.md](codex.md)

---

## Current Status

Working on Stage 1 (teaching explicit instruction following). See [ROADMAP.md](ROADMAP.md) for progress.

---

## About

This is a personal research project exploring automated post-training methods. It's heavily AI-assisted (Claude Code for implementation, Gemini and Codex for review), which is itself an experiment in human-AI collaboration for research.

---

**Questions?** See `/docs/STANDARDS.md` for how things work, or `/status/PROJECT_STATUS.md` for current context.
