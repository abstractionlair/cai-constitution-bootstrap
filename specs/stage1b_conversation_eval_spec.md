# Stage 1B: Conversation Ability Evaluation Spec

**Status**: DRAFT v3 (tightened gates and baselines)
**Created**: 2025-10-13
**Last Updated**: 2025-10-13
**Purpose**: Evaluate multi-turn conversation ability to identify genuine capability gap between base and Instruct models

---

## Objective

Provide a rigorous, validated evaluation framework to measure multi-turn conversation ability - specifically the capacity to:
- Track context across conversation turns
- Reference information from previous turns
- Resolve implicit references ("it", "that", "the earlier topic")
- Maintain conversation state and coherence

**Critical constraint**: Must demonstrate base model FAILS and Instruct model SUCCEEDS before any training work begins.

---

## Motivation (Why We Need This)

### Stage 1 Failure Post-Mortem

Stage 1 targeted "explicit instruction-following" but discovered:
- Base model (Qwen/Qwen2.5-32B) already follows simple instructions with format `"Instruction: X\nResponse:"`
- Achieved 100% success when recount ignores broken length heuristic
- SFT training only taught brevity/style, not fundamental capability
- Evaluation gate was invalid due to broken scoring

**Lesson learned**: Never train on a capability without first proving the base model lacks it.

### Why Conversation Should Show a Gap

**Hypothesis**: Multi-turn conversation requires capabilities that:
- Are NOT learned during pretraining (documents vs dialogues)
- ARE learned during post-training (Instruct models)
- Can be objectively measured and scored

**If this hypothesis is false** (base model can already converse), we must pivot to a different capability.

---

## Evaluation Design

### Test Set Structure

**Size (full benchmark)**: ≥ 300 multi-turn conversations
- **Power analysis**: 300 paired samples with p₁≈0.3 vs p₂≈0.8 retains >0.99 McNemar power at α=0.01 and strengthens per-category analysis
- **Per-category**: ≥ 75 conversations each → tighter Wilson CIs and meaningful BH-adjusted per-category tests

**Conversation structure**: Each conversation has 3-5 turns
- **Turn 1**: Initial user message (establishes context)
- **Turn 2**: Follow-up requiring context from Turn 1
- **Turn 3+**: Additional turns testing deeper context tracking

**Data structure** (machine-checkable):
Each conversation stored with:
- Full transcript (turns and responses)
- **Expected entities**: Names, numbers, preferences mentioned in early turns
- **Required references**: Which turns must recall which entities
- **Acceptable constraints**: Whitelisted ingredients/topics for constraint tracking
- Enables automated validation and auditability

**Context dependency types**:

1. **Explicit Memory** (30% of conversations)
   - Turn 1: "My name is Alice"
   - Turn 2: "What's my name?"
   - Success criterion: Response mentions "Alice"

2. **Preference Tracking** (25% of conversations)
   - Turn 1: "I'm allergic to peanuts"
   - Turn 2: "Suggest a snack for me"
   - Success criterion: Suggested snack doesn't contain peanuts

3. **Topic Continuity** (25% of conversations)
   - Turn 1: "Explain photosynthesis"
   - Turn 2: "What role does chlorophyll play in that process?"
   - Success criterion: Response connects to photosynthesis explanation

4. **Constraint Updates** (20% of conversations)
   - Turn 1: "I need a pasta recipe"
   - Turn 2: "Make it vegetarian"
   - Success criterion: Recipe modified to be vegetarian

### Example Conversations

**Example 1: Explicit Memory**
```
Turn 1:
User: "I live in Seattle and work as a software engineer."
Expected: Model acknowledges/responds appropriately

Turn 2:
User: "What city did I say I live in?"
Expected (Success): "Seattle" or "You said Seattle"
Expected (Failure): Generic answer, "I don't have that information", or hallucinated city

Turn 3:
User: "What's my profession?"
Expected (Success): "Software engineer" or "You're a software engineer"
Expected (Failure): Generic answer or wrong profession
```

**Example 2: Preference Tracking**
```
Turn 1:
User: "I'm looking for a recipe. I'm vegetarian and allergic to soy."
Expected: Model acknowledges constraints

Turn 2:
User: "Can you suggest a dinner recipe for me?"
Expected (Success): Vegetarian recipe with no soy
Expected (Failure): Recipe contains meat or soy, or ignores constraints

Turn 3:
User: "Is that recipe suitable for my dietary restrictions?"
Expected (Success): Confirms it's vegetarian and soy-free
Expected (Failure): Doesn't reference the earlier constraints
```

**Example 3: Topic Continuity with Implicit Reference**
```
Turn 1:
User: "Explain how internal combustion engines work."
Expected: Provides explanation

Turn 2:
User: "What are the main efficiency limitations of that design?"
Expected (Success): Discusses ICE efficiency limitations (references "that design" = ICE)
Expected (Failure): Generic answer about engines, or asks "which design?"

Turn 3:
User: "How do electric motors compare?"
Expected (Success): Compares electric motors to ICEs from Turn 1
Expected (Failure): Discusses electric motors without comparison context
```

**Example 4: Constraint Update**
```
Turn 1:
User: "Give me a simple chicken soup recipe."
Expected: Provides chicken soup recipe

Turn 2:
User: "Actually, make it vegan instead."
Expected (Success): Modifies recipe to be vegan (no chicken, no dairy)
Expected (Failure): Still mentions chicken, or provides unrelated vegan recipe

Turn 3:
User: "How long will that take to cook?"
Expected (Success): Gives time for the vegan soup from Turn 2
Expected (Failure): Gives time for original chicken soup or generic answer
```

---

## Prompt Format & Generation Loop

### Multi-Turn Conversation Format

For all model conditions, conversation history is concatenated as:

```
User: {turn_1_user}
Assistant: {turn_1_assistant}
User: {turn_2_user}
Assistant: {turn_2_assistant}
User: {turn_n_user}
Assistant:
```

**No special tokens**: Use raw text format, no `<|im_start|>` or chat templates
**Separator**: Simple "User:" and "Assistant:" labels for all conditions
**Generation**: Model generates after final "Assistant:" label

### Iterative Generation Loop (All Conditions)

**Algorithm for generating conversation responses**:

```python
# Initialize
conversation_history = ""

for turn_num, user_message in enumerate(conversation.turns):
    # Construct prompt with full history
    prompt = conversation_history + f"User: {user_message}\nAssistant:"

    # Tokenize (CleanModelLoader ensures no chat template)
    inputs = tokenizer(
        prompt,
        add_special_tokens=False,  # REQUIRED
        return_tensors="pt"
    ).to(model.device)

    # Generate response
    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        do_sample=False,
        temperature=None,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id
    )

    # Extract assistant response
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    assistant_response = generated_text[len(prompt):].strip()

    # Clean response (remove any "User:" that model might have generated)
    assistant_response = clean_response(assistant_response)

    # Update conversation history for next turn
    conversation_history += f"User: {user_message}\nAssistant: {assistant_response}\n"

    # Store response for evaluation
    responses[turn_num] = assistant_response
```

**Critical properties**:
- Same generation loop for all four conditions (base-raw, base-formatted, instruct, alt-base)
- CleanModelLoader used for all models (ensures contamination guards)
- Deterministic decoding (temperature=0, seed=42)
- History accumulates across turns (enables context tracking)
- No differences except model weights

### Example Formatted Conversation

```
User: My name is Alice and I study biology.
Assistant: {model_generates_turn_1}
User: What's my name?
Assistant: {model_generates_turn_2}
User: What subject do I study?
Assistant: {model_generates_turn_3}
```

**Note**: Decoding parameters are identical across conditions. We intentionally include a minimal-scaffolding "base-raw" ablation (see Baselines) to quantify format effects separately from training effects; other conditions use the `User:`/`Assistant:` transcript.

---

## Contamination Guards & Provenance (Required)

All evaluations MUST comply with `specs/CONTAMINATION_GUARD_SPEC.md`:

- Load base models via `CleanModelLoader`; ensure `tokenizer.chat_template=None` and `add_special_tokens=False`.
- Token-ID delta check on sentinel prompts; abort if any delta indicates template injection.
- Run base-model sentinel tests and log outcomes.
- Record provenance in the evaluation manifest: `loader_version`, `template_disabled: true`, `add_special_tokens: false`, `sentinel_tests_passed: true`, environment versions, SHAs, decoding params.

---

## Decoding Parameters

**Deterministic decoding for reproducibility**:
- `temperature = 0`
- `do_sample = False`
- `max_new_tokens = 150` (enough for conversation responses)
- `seed = 42` (fixed across all evaluations)
- `pad_token_id` and `eos_token_id` set correctly

**Same parameters for all models** (base, instruct, alternate base) to ensure fair comparison.

---

## Scoring Method

### Primary: LLM-as-Judge with Human Calibration

**Primary gate**: LLM-as-judge scoring validated against human calibration (κ ≥ 0.7)

### Secondary: Automated Heuristics (Diagnostic/Triage Only)

**Role**: Triage and audit tool, NOT a gate
- Flag suspicious conversations for manual review
- Track disagreement rate with LLM judge
- Require ≤10% disagreement rate

Per-turn automated checks:
- **Context entity present**: Does response mention required entities from previous turns?
  - Only applies to conversations with templated, machine-checkable entities
- **No hallucination**: Doesn't introduce contradictory facts
- **No requests for clarification**: Doesn't ask "which X?" when context clearly provides it
- **Length sanity**: 10-1000 characters (not empty, not excessive)
  - **NOTE**: Length is NOT a failure criterion, only flags for review

**Heuristic disagreement protocol**:
- If heuristics and judge disagree: Flag for human review
- Target: ≤10% disagreement rate across full benchmark
- All disagreements manually adjudicated and documented

### LLM-as-Judge (Primary Scoring)

**Judge model**: Claude 3.5 Sonnet (claude-3-5-sonnet-20241022) as primary
- **Spot-check**: 10% of conversations with GPT-4 to monitor drift
- **Temperature**: 0 (deterministic)
- **Validation**: κ against calibration set tracked every run

**Judge prompt template**:
```
You are evaluating whether an AI assistant correctly tracked context across a multi-turn conversation.

CONVERSATION HISTORY:
{full_conversation_with_assistant_responses}

EVALUATION CRITERIA:
For each turn after the first, check:
1. Does the assistant's response reference or use information from previous turns when required?
2. Does the assistant correctly resolve implicit references ("it", "that", etc.)?
3. Does the assistant maintain consistency with earlier statements?
4. Is there any hallucination of facts not in the conversation?

For each turn (2 through N), answer:
- Turn 2: PASS / FAIL - [one sentence justification]
- Turn 3: PASS / FAIL - [one sentence justification]
- ...

Overall conversation: PASS / FAIL

Output format:
{
  "turn_2": {"result": "PASS/FAIL", "reason": "..."},
  "turn_3": {"result": "PASS/FAIL", "reason": "..."},
  "overall": "PASS/FAIL"
}
```

**Judge decision**: Conversation passes if ALL turns pass

#### Single-Token Variant (Optional, for margin analysis)

To enable single-token margin analysis and reduce parsing variance, prepend a one-line label request. The judge decides based on the rubric but outputs the overall decision as a single token immediately after `Label:`:

```
Decide if the assistant demonstrated multi-turn conversation ability.
Output exactly one letter on the next line: A = PASS, B = FAIL
Label:
```

Then include the structured JSON for auditability. When used, compute logprobs for next token on `"A"` vs `"B"` to derive judge margin.

### Final Score Reconciliation

**Conversation marked SUCCESS based on**:
- **Primary**: LLM judge decision (PASS/FAIL)
- **Secondary**: Heuristics used for triage/audit only

**Disagreement handling**:
- Track heuristic vs judge disagreement rate
- Require ≤10% disagreement across full benchmark
- All disagreements flagged for human review
- Document resolution of disagreements

**Final score**: LLM judge decision (after human review of flagged cases)

---

## Validation & Calibration

### Human Calibration Set (Required Before Scaling)

**Size**: 30 conversations (stratified sample)
- 10 conversations × 3 models (base, instruct, alt-base)

**Process**:
1. User + Claude Code independently score all 30
2. Compute inter-rater agreement (Cohen's κ)
3. Require κ ≥ 0.7 before trusting automated scoring
4. Resolve disagreements and refine rubric
5. Archive calibration set with gold labels

**Purpose**: Establish ground truth for what "conversation ability" means

---

## Three-Way Evaluation (Required)

### Models to Test

1. **Base model — Raw (minimal scaffolding)**
   - Model: Qwen/Qwen2.5-32B
   - Format: Concatenate turns without `User:`/`Assistant:` labels. Use plain newlines between utterances; append `Assistant:` only before the generation position to mark who speaks next.
   - Example:
     ```
     My name is Alice.
     [assistant_response_turn_1]
     What's my name?
     Assistant:
     ```
   - Purpose: Quantify format effects separately from training effects

2. **Base model - Formatted prompts**
   - Model: Qwen/Qwen2.5-32B
   - Format: "User: X\nAssistant: Y\n..." format
   - Purpose: Isolate effect of conversation format vs SFT training

3. **Instruct model - Formatted prompts**
   - Model: Qwen/Qwen2.5-32B-Instruct
   - Format: Same "User: X\nAssistant: Y\n..." format
   - Purpose: Target performance level

4. **Alternative base model - Formatted prompts** (Sanity check)
   - Model: meta-llama/Llama-3.1-8B (or Mistral-7B-v0.3)
   - Format: Same conversation format
   - Purpose: Verify Qwen base isn't special

### Expected Results

**For pivot to be valid**:
- Base-raw: ≤ 20% success (truly can't converse)
- Base-formatted: ≤ 30% success (format helps but insufficient)
- Instruct-formatted: ≥ 80% success (clear capability gap)
- Alt-base-formatted: ≤ 40% success (confirms Qwen base isn't uniquely good)

**Statistical requirements**:
- McNemar test: p < 0.01 comparing base-formatted vs instruct-formatted
- Effect size: Cohen's h ≥ 0.5
- No overlap in Wilson 95% CIs

**Abort conditions**:
- If base-formatted ≥ 60%: Conversation isn't hard enough, need different target
- If alt-base ≥ 60%: All modern base models can converse, need different target
- If instruct < 80%: Target is too hard even for Instruct model

---

## Pilot Sampling & Statistics

### Pilot Phase (Before Full Benchmark)

**Pilot size**: 40 conversations total (10 per category)
- Balanced across: Explicit Memory, Preference Tracking, Topic Continuity, Constraint Updates
- Models: Base-raw, Base-formatted, Instruct-formatted (Alt-base optional for pilot)
- Purpose: Verify gap, validate scoring, estimate variance, confirm rubric fidelity

### Full Benchmark (Only After Pilot Passes)

**Size**: ≥ 300 conversations
- ≥ 75 per category for robust per-category stats
- Powered for h ≥ 0.5 with α = 0.01
- Benjamini–Hochberg correction (FDR=0.10) across category tests

---

## Scoring Rubric Details

### Per-Turn Success Criteria

**A turn is successful if**:

1. **Context Integration** (PRIMARY)
   - Turn explicitly requires info from previous turns (e.g., "What's my name?" after name given)
   - Response correctly uses that information
   - Response doesn't ask for clarification when context provides answer

2. **Implicit Reference Resolution**
   - Turn uses pronouns or references ("it", "that process", "the earlier topic")
   - Response correctly resolves reference to prior context
   - Response doesn't treat reference as ambiguous when context is clear

3. **Consistency**
   - Response doesn't contradict earlier turns
   - Maintains constraints from previous turns (dietary restrictions, preferences, etc.)
   - Doesn't hallucinate facts not in conversation

4. **No Meta-Gaming**
   - Doesn't say "you mentioned X" when trying to identify base vs instruct models
   - Gives natural conversational responses
   - Doesn't explicitly narrate context tracking

### Conversation-Level Success

**Conversation marked PASS if**:
- ALL turns (2 through N) individually pass
- No turn shows context failure
- Overall coherence maintained

**Strict criterion**: One failed turn = entire conversation fails

**Rationale**: We want models that reliably track context, not mostly track it

---

## Automated Heuristic Checks

### Deterministic String Checks (Fast, Auditable)

For each conversation, extract:
- **Tracked entities**: Names, numbers, preferences mentioned in Turn 1
- **Required references**: Turns that explicitly ask about these entities

**Heuristic rules**:

1. **Entity Recall Check**
   - If Turn N asks "What's my name?" and Turn 1 contained "My name is Alice"
   - Expected: Response contains "Alice"
   - Check: `"alice" in response.lower()`

2. **Constraint Adherence Check**
   - If Turn 1 says "I'm vegetarian" and Turn 2 asks for recipe
   - Expected: Recipe contains no meat
   - Check: No meat words in response (`["chicken", "beef", "pork", "fish"]`)

3. **No Clarification Request Check**
   - If context clearly provides answer to question
   - Expected: Direct answer
   - Check: Response doesn't contain `["which", "what do you mean", "could you clarify"]`

4. **Length Sanity Check**
   - Expected: 10-500 characters per turn
   - Check: Catches empty or runaway responses
   - **NOTE**: Length alone is NOT a failure criterion, just sanity check

**Heuristic pass rate**: Percentage of conversations where all heuristics pass

---

## LLM-as-Judge Scoring

### Judge Prompt (Per Conversation)

```
You are evaluating multi-turn conversation ability. The assistant must track context across turns and use information from previous turns when required.

CONVERSATION:
---
{full_conversation_transcript}
---

EVALUATION:

For each assistant turn after the first, evaluate whether the assistant correctly used context from previous turns.

Turn 2:
- Required context: {what_info_from_turn_1_is_needed}
- Did assistant use this context correctly? YES / NO
- Reason: [one sentence]

Turn 3:
- Required context: {what_info_from_earlier_turns_is_needed}
- Did assistant use this context correctly? YES / NO
- Reason: [one sentence]

[... for all turns ...]

OVERALL ASSESSMENT:
- Did the assistant demonstrate multi-turn conversation ability? PASS / FAIL
- Summary: [one sentence]

Output your evaluation as JSON:
{
  "turn_2": {"pass": true/false, "reason": "..."},
  "turn_3": {"pass": true/false, "reason": "..."},
  "overall": "PASS/FAIL",
  "summary": "..."
}
```

### Judge Configuration

- **Model**: Claude 3.5 Sonnet (claude-3-5-sonnet-20241022) or GPT-4-turbo
- **Temperature**: 0 (deterministic)
- **Seed**: Fixed per conversation (for reproducibility)
- **Output**: Structured JSON for automated parsing

### Agreement Requirements

**Before trusting judge**:
- Human calibration on 30 conversations
- Judge vs human agreement: ≥ 80% on overall PASS/FAIL
- Cohen's κ ≥ 0.7 for inter-rater reliability

**During evaluation**:
- If heuristics and judge disagree: Flag for manual review
- Track disagreement rate (should be < 10%)
- Manual audit of all flagged conversations

---

## Models to Evaluate

**Note**: Per Codex feedback, all conditions now use "User:"/"Assistant:" separators to ensure well-defined multi-turn task. The distinction is in model weights and any additional formatting, not in the basic conversation structure.

### 1. Base Model - Minimal Format

**Model**: Qwen/Qwen2.5-32B
**Prompt format**: Multi-turn with minimal labels but consistent separators
```
User: My name is Alice.
Assistant: [turn_1_response]
User: What's my name?
Assistant:
```

**Key properties**:
- Uses "User:"/"Assistant:" labels for turn separation (required for well-defined task)
- No system prompt or helpful instructions
- Same iterative generation loop as other conditions
- CleanModelLoader with completion mode, `add_special_tokens=False`

**Purpose**: Measure baseline conversation ability
**Expected**: Should fail most conversations (< 30%)

**Note**: Since all conditions now use the same basic format, this is no longer "raw" but represents the base model's conversation capability with standard turn structure.

### 2. Base Model - With System Prompt (Optional Condition)

**Model**: Qwen/Qwen2.5-32B
**Prompt format**: Same conversation format but with system instruction
```
System: You are a helpful assistant. Track context across turns.

User: My name is Alice.
Assistant: {turn_1_response}
User: What's my name?
Assistant:
```

**Purpose**: Measure if system prompts help base model (may not test this initially)
**Expected**: May help somewhat but still below Instruct performance (< 50%)

### 3. Instruct Model - Standard Format

**Model**: Qwen/Qwen2.5-32B-Instruct
**Prompt format**: Same conversation format as base model (User:/Assistant: labels)
**Purpose**: Target performance (what post-training achieves)
**Expected**: Should succeed at conversations (≥ 80%)

**Note**: Uses same format as base model to ensure fair comparison

### 4. Alternative Base Model - Structured Format (Sanity Check)

**Primary alternative**: meta-llama/Llama-3.1-8B
**Secondary alternative** (optional): mistralai/Mistral-7B-v0.3
**Prompt format**: Same conversation format as Qwen base-formatted
**Purpose**: Verify Qwen base model isn't uniquely capable
**Expected**: Should also fail (< 40%)

**Rationale**: If alternative base models ALSO pass conversation tests, then modern base models generally have this capability and we need a harder target.

**Implementation**:
- Start with Llama 3.1 8B on pilot (30-40 conversations)
- Add Mistral 7B only if Llama results are ambiguous

---

## Statistical Analysis

### Primary Test: McNemar (Paired)

**Comparison**: Base-formatted vs Instruct-formatted on same conversations

**Null hypothesis**: No difference in conversation ability
**Alternative**: Instruct model has better conversation ability

**Requirements**:
- p < 0.01 (highly significant)
- Cohen's h ≥ 0.5 (medium-to-large effect)
- Wilson 95% CIs don't overlap

**Discordant pairs**:
- n01: Base fails, Instruct succeeds (expect many)
- n10: Base succeeds, Instruct fails (expect few)
- Ratio n01:n10 should be > 5:1

### Secondary Tests

**Base-raw vs Base-formatted**: Measures format effect
**Base-formatted vs Alt-base-formatted**: Tests if Qwen is special
**Per-category analysis**: Memory, preferences, continuity, constraints

**Multiple testing correction**: Benjamini–Hochberg (FDR = 0.10) for category comparisons; report adjusted p-values and `significant_after_bh`

---

## Gate Criteria (Must ALL Pass)

### Primary Gates

1. **Base model clearly fails**
   - Base-formatted success rate: ≤ 30%
   - Wilson CI upper bound: < 40%

2. **Instruct model clearly succeeds**
   - Instruct-formatted success rate: ≥ 80%
   - Wilson CI lower bound: > 70%

3. **Statistically significant gap**
   - McNemar p-value: < 0.01
   - Cohen's h effect size: ≥ 0.5

4. **No overlap in confidence intervals**
   - Base CI and Instruct CI must not overlap

5. **Lopsided discordant pairs**
   - Ratio n01:n10 ≥ 5:1 (at least 5× more base-fail-instruct-succeed than reverse)

### Validation Gates

6. **Scoring methods agree**
   - Heuristics vs LLM-judge agreement: ≥ 80%
   - Disagreements manually reviewed and resolved

7. **Human calibration validates**
   - User reviews sample of 30 conversations
   - Confirms gap looks real
   - No obvious scoring bugs

8. **Alternative base model fails too**
   - Alt-base success rate: ≤ 40%
   - Confirms Qwen base isn't uniquely capable

9. **Per-category robustness**
   - After BH correction (FDR=0.10), at least 3/4 categories significant (adjusted p < 0.10)

### Abort Conditions

**Do NOT proceed to training if**:
- Base-formatted ≥ 60% (capability gap too small)
- Alt-base ≥ 60% (all base models can do this)
- Instruct < 70% (target too hard)
- Methods disagree > 20% (scoring unreliable)
- User review finds scoring bugs

---

## Outputs & Provenance

### Evaluation Artifacts

**Per-model outputs**:
- `results/conversation_eval/{model_name}_conversations.jsonl`
  - Full conversation transcripts with responses
  - Per-turn scores (heuristic + judge)
  - Overall conversation success
  - Metadata (tokens, entities tracked, etc.)

**Statistical results**:
- `results/conversation_eval/evaluation_results.json`
  - Success rates for all models
  - Wilson 95% CIs
  - McNemar test results (chi2, p-value, discordant pairs)
  - Cohen's h effect sizes
  - Per-category breakdowns
  - Benjamini–Hochberg adjusted p-values and `significant_after_bh`

**Human-readable summary**:
- `results/conversation_eval/evaluation_summary.txt`
  - Table of success rates
  - Gate decision (PASS/FAIL with reasoning)
  - Recommendations

### Provenance Requirements

Every evaluation artifact must include:
- Git commit SHA
- Model names and versions
- Decoding parameters (temperature, seed, max_tokens)
- Scoring method details (heuristic version, judge model)
- Human calibration results (κ score, agreement %)
- Contamination guard metadata: `loader_version`, `template_disabled: true`, `add_special_tokens: false`, `sentinel_tests_passed: true`
- Timestamp
- Test set path and size

---

## Pilot Phase (Required Before Full Benchmark)

### Pilot Design

**Size**: 30-40 conversations
- 10 conversations × 3 primary models (base-raw, base-formatted, instruct)
- 10 conversations × 1 alternative base model

**Purpose**:
- Validate evaluation methodology
- Verify expected gap exists
- Calibrate scoring methods
- Estimate variance for power analysis

**Timeline**: < 2 hours to run

### Pilot Gates

**Proceed to full benchmark only if**:
- Base-raw: ≤ 30% success
- Base-formatted: ≤ 40% success
- Instruct: ≥ 70% success
- Gap is directionally correct (p < 0.05 acceptable for pilot)
- Scoring methods agree (≥ 75%)
- User confirms gap looks real after reviewing sample

**If pilot fails**: Pivot to different capability before scaling

---

## Alternative Capability Targets (Fallback)

If conversation ability doesn't show a clear gap, consider:

### 1. Structured JSON Output
- Test: Generate valid JSON matching schema
- Expected base failure mode: Malformed JSON, missing fields
- Expected instruct success: Valid, complete JSON

### 2. System Prompt Adherence
- Test: Follow role constraints ("You are a pirate", "Respond in haiku")
- Expected base failure mode: Ignores role, normal responses
- Expected instruct success: Maintains role consistently

### 3. Long-Form Coherent Generation (2K+ tokens)
- Test: Generate coherent essay/story of 2000+ tokens
- Expected base failure mode: Topic drift, repetition, incoherence
- Expected instruct success: Maintains coherence throughout

### 4. Implicit Instruction Following
- Test: Questions that imply instructions ("How do I...?" should give steps)
- Expected base failure mode: Explains rather than instructs
- Expected instruct success: Provides actionable steps

**Selection criterion**: Pick the capability where gap is largest and most measurable

---

## Implementation Plan

### Phase 1: Spec & Review (This Document)
1. Draft this specification
2. Submit to Codex for review
3. Incorporate feedback
4. Get GO decision from Codex

### Phase 2: Tooling & Calibration
1. Implement conversation benchmark generator
2. Generate 30-40 pilot conversations
3. Implement heuristic scoring
4. Implement LLM-as-judge scoring
5. Run human calibration (30 conversations)
6. Validate inter-rater agreement (κ ≥ 0.7)

### Phase 3: Pilot Evaluation
1. Download Qwen/Qwen2.5-32B-Instruct
2. Download alternative base model (Llama or Mistral)
3. Run 4-way evaluation (40 conversations × 4 models)
4. Compare automated vs human scores
5. Verify expected gaps
6. Get user confirmation

### Phase 4: Full Benchmark (Only If Pilot Passes Gates)
1. Generate full 150-200 conversation benchmark
2. Run complete evaluation on all models
3. Compute full statistics
4. Submit results to Codex for gate decision

### Phase 5: Only If Gate Passes
1. Design conversation data generation pipeline
2. Generate training data
3. Train SFT model
4. Re-evaluate
5. Compare to Instruct model

---

## Success Criteria Summary

### This Evaluation Spec Succeeds If

- ✅ Demonstrates clear capability gap (base fails, instruct succeeds)
- ✅ Scoring is validated (human agreement ≥ 80%, κ ≥ 0.7)
- ✅ Results are reproducible (deterministic scoring, fixed seeds)
- ✅ Statistical tests are valid (paired data, proper corrections)
- ✅ User confirms gap is real after manual review
- ✅ Codex approves methodology

### This Evaluation Spec Fails If

- ❌ Base model succeeds at conversations (no gap to close)
- ❌ Instruct model fails at conversations (target too hard)
- ❌ Scoring methods unreliable (low agreement, bugs found)
- ❌ Alternative base models also succeed (target not differentiating)
- ❌ User finds flaws in methodology

---

## Open Questions for Codex Review

1. **Is conversation format adequate?** Simple "User:/Assistant:" labels vs more structured format?

2. **Is 150-200 conversations enough?** Or do we need more for robust per-category analysis?

3. **Should we test chat template format too?** Compare base model with vs without Qwen's chat template?

4. **LLM judge model choice?** Claude 3.5 Sonnet vs GPT-4 vs both for redundancy?

5. **Heuristic design?** Are the proposed entity-tracking checks sufficient?

6. **Alternative base model choice?** Llama 3.1 8B vs Mistral 7B vs both?

7. **Should we probe other capabilities first?** Quick 10-item tests for JSON, system prompts, etc. before committing to conversation?

---

## Risk Mitigation

### Risk: Base Model Can Already Converse

**Mitigation**:
- Four-way testing (including alternative base model)
- Pilot before full benchmark
- Abort if base ≥ 60%
- Have fallback capability targets ready

### Risk: Scoring Method Has Bugs

**Mitigation**:
- Dual scoring (heuristics + LLM judge)
- Human calibration required (30 conversations)
- Agreement metrics tracked
- User reviews sample before trusting results

### Risk: Conversation Too Hard Even for Instruct

**Mitigation**:
- Start with simple conversations
- Test on Instruct model first
- Adjust difficulty if Instruct < 70%
- Have simpler fallback conversations ready

### Risk: Wasting GPU Budget on Wrong Target

**Mitigation**:
- All evaluation work is CPU/small model (< $2)
- No GPU training until gap proven
- Pilot phase catches problems early
- Codex review at every gate

---

## Appendix: Conversation Examples (Full Transcripts)

### Category 1: Explicit Memory

**Conversation A1**:
```
Turn 1:
User: My favorite color is blue and I have a dog named Max.
Assistant: [model responds]

Turn 2:
User: What's my dog's name?
Assistant: [model should say "Max"]

Turn 3:
User: What color do I like?
Assistant: [model should say "blue"]
```

**Conversation A2**:
```
Turn 1:
User: I'm planning a trip to Japan in March.
Assistant: [model responds]

Turn 2:
User: Where am I traveling to?
Assistant: [model should say "Japan"]

Turn 3:
User: What month is my trip?
Assistant: [model should say "March"]
```

### Category 2: Preference Tracking

**Conversation B1**:
```
Turn 1:
User: I'm vegan and I love Italian food.
Assistant: [model responds]

Turn 2:
User: Suggest a dinner recipe for me.
Assistant: [model should suggest vegan Italian recipe]

Turn 3:
User: Does that recipe fit my dietary restrictions?
Assistant: [model should confirm it's vegan]
```

**Conversation B2**:
```
Turn 1:
User: I'm learning Python and I prefer practical examples over theory.
Assistant: [model responds]

Turn 2:
User: Can you help me understand functions?
Assistant: [model should use practical Python examples, not theoretical explanation]

Turn 3:
User: Show me another example using my preferred learning style.
Assistant: [model should provide another practical example]
```

### Category 3: Topic Continuity

**Conversation C1**:
```
Turn 1:
User: Explain how photosynthesis works.
Assistant: [model explains photosynthesis]

Turn 2:
User: What role does chlorophyll play in that process?
Assistant: [model should connect to photosynthesis explanation from Turn 1]

Turn 3:
User: Why is that important for plants?
Assistant: [model should connect chlorophyll's role to plant survival]
```

**Conversation C2**:
```
Turn 1:
User: What are the main causes of climate change?
Assistant: [model lists causes]

Turn 2:
User: How does the first cause you mentioned contribute to global warming?
Assistant: [model should reference the first cause from Turn 1]

Turn 3:
User: What can individuals do to reduce their impact on that specific issue?
Assistant: [model should connect to the cause discussed in Turn 2]
```

### Category 4: Constraint Updates

**Conversation D1**:
```
Turn 1:
User: Give me a recipe for chocolate chip cookies.
Assistant: [model provides recipe]

Turn 2:
User: Actually, make it gluten-free.
Assistant: [model should modify recipe to be gluten-free]

Turn 3:
User: How many cookies will that recipe make?
Assistant: [model should reference the gluten-free version from Turn 2]
```

**Conversation D2**:
```
Turn 1:
User: Suggest a 30-minute workout routine.
Assistant: [model suggests routine]

Turn 2:
User: I don't have access to any equipment. Can you adjust it?
Assistant: [model should modify to bodyweight-only exercises]

Turn 3:
User: How many calories will that routine burn?
Assistant: [model should reference the no-equipment version from Turn 2]
```

---

## Acceptance Criteria

This specification is accepted if:

1. ✅ Codex reviews and approves methodology
2. ✅ Pilot phase demonstrates expected gap
3. ✅ Scoring methods are validated (human agreement ≥ 80%)
4. ✅ User confirms evaluation approach is sound
5. ✅ No methodology flaws discovered during pilot

This specification is rejected if:

1. ❌ Codex identifies flaws in design
2. ❌ Pilot shows base model can already converse
3. ❌ Scoring methods unreliable or buggy
4. ❌ User identifies problems during review
5. ❌ Better alternative capability target identified

---

**Next step**: Submit this spec to Codex for review before implementing.
