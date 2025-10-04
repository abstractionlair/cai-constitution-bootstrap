# Persistent Project State
Last Updated: 2024-12-28 16:40

## 🟡 CRITICAL: Only 2 Real Bugs to Fix 🟡
**P0 Fixes Review Results - CORRECTED**:
- **Gemini**: ✅ Approved implementation architecture
- **Codex**: Found 2 real bugs, had 2 misunderstandings
- **Status**: Only 2 bugs need fixing (not 3)

## 📚 CRITICAL FILES FOR CLAUDE CODE TO READ
1. **START_HERE.md** - Project orientation and workflow
2. **REVIEW_PROTOCOL.md** - How to request and process reviews
3. **This file (PERSISTENT_STATE.md)** - Current status and issues
4. **P0_FIXES_REVIEW_SUMMARY_CORRECTED.md** - Corrected review findings

## 🚨 ALWAYS CHECK THESE DIRECTORIES 🚨
1. **Pending Tasks**: `/tasks/claude_code/pending/` - Implementation work for Claude Code
2. **Pending Reviews**: `/reviews/*/pending/` - Review requests for Gemini/Codex
3. **In Progress**: `/tasks/claude_code/in_progress/` - What's currently being worked on

## 🟡 ACTUAL CRITICAL BUGS (Only 2!) 🟡

### FATAL Bug #1: Template Placeholder Mismatch
- **Impact**: Will cause KeyError crash at runtime
- **Location**: `data_formatter.py` - `generate_generation_instructions` and `generate_response_instructions`
- **Issue**: Templates use `{content_type}/{topic}` but code formats with `prompt=...`
- **Fix Time**: 15 minutes
- **Task File**: `/tasks/claude_code/pending/P0_fix_template_placeholders.md`

### CRITICAL Bug #2: Cross-Run Data Leakage
- **Impact**: Evaluation data can overlap with training data
- **Location**: Evaluation doesn't check against saved training data
- **Issue**: Fresh eval generation each time, no persistence
- **Fix Time**: 1 hour
- **Task File**: `/tasks/claude_code/pending/P0_fix_data_leakage.md`

## ✅ NOT ACTUALLY BUGS (Codex Misunderstood)

### ~~Evaluation Prompt Mismatch~~ - CODEX WAS WRONG
- **Why it's not a bug**: The whole point of Stage 1 is teaching instruction following
- **Correct approach**: Test both models with raw instructions
- **Expected**: Base model fails, trained model succeeds
- **That's the improvement we're measuring!**
- **NO FIX NEEDED** - Evaluation is correct as designed

### ~~Constitution Tracking~~ - NOT RELEVANT TO STAGE 1
- **Why it doesn't matter**: Stage 1 is just about following instructions
- **Our design**: Sequential bootstrapping, not full CAI yet
- **Stage 6**: Where constitutional integration happens
- **NO FIX NEEDED** - Working as intended

## Task Tracking System

### P0 Tasks - ONLY 2 REAL ONES:
1. **Fix Template Placeholders** (15 min) - Will crash without this
2. **Fix Cross-Run Data Leakage** (1 hr) - Results invalid without this

### Cancelled Tasks:
- ~~Fix Evaluation Prompting~~ - Moved to `/tasks/claude_code/cancelled/`
- Reason: Codex misunderstood - current approach is correct

### Previous P0 Tasks (Completed):
- ✅ Fix Completion-Style Prompting - DONE (but has template bug to fix)
- ✅ Add Few-Shot Examples - DONE 
- ✅ Remove Instruction Templates - DONE
- ✅ Fix Evaluation Precision Mismatch - DONE correctly
- ✅ Fix Data Leakage - DONE for within-run only

### P1 Tasks (Nice to have, not blocking):
1. Improve few-shot examples (1 hr)
2. Expand data pools (1 hr)
3. Add statistical rigor (2 hrs)

**Total Critical Work**: ~1.25 hours (not 2!)

## What's Working (Per Reviews)
1. ✅ Completion-style prompting architecture correct
2. ✅ Few-shot examples properly structured
3. ✅ Within-run data leakage prevention working
4. ✅ 8-bit precision standardized
5. ✅ RunPod compatibility maintained
6. ✅ Evaluation approach correct for Stage 1 goals

## What Needs Fixing
1. ❌ Template placeholders don't match (FATAL - will crash)
2. ❌ Cross-run data leakage possible (CRITICAL - invalid results)
3. ⚠️ Few-shot examples could be better (NICE TO HAVE)
4. ⚠️ Pool sizes could be larger (NICE TO HAVE)
5. ⚠️ Statistical tests would be good (FOR PUBLICATION)

## Key Insight from Review Analysis
**Stage 1 Goal**: Teach base model to follow instructions AT ALL
- Base model only knows text completion
- We train it to recognize instruction patterns
- Success = model learns "Answer this:" means provide an answer
- **Evaluation should use raw instructions for both models**
- Base failing is expected, trained succeeding is the goal

## Current Status
- **Current Stage**: Stage 1 - Only 2 bugs to fix
- **Implementation Status**: Almost ready, just 2 fixes needed
- **RunPod Status**: Instance running at $1.74/hr
- **Next Action**: Fix 2 bugs, then deploy

## Critical Commands
```bash
# SSH to RunPod
ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

# After fixing 2 bugs, test locally first:
python scripts/test_small_sample.py --count 10

# Then deploy:
scp -r scripts/* tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/scripts/

# Run Stage 1:
python scripts/run_stage1_pipeline.py
```

## Budget Tracking
- **Spent so far**: ~$15-20 
- **Bug fixes**: ~$2.20 (1.25 hours @ $1.74/hr)
- **Stage 1 run**: ~$10 (6 hours)
- **Total budget**: $50-300
- **Remaining**: ~$18-268

## Next Steps (UPDATED)
1. Fix template placeholder bug (15 min)
2. Fix cross-run data leakage (1 hr)
3. Test with 10 examples locally
4. Deploy fixed code to RunPod
5. Run full Stage 1 pipeline
6. Monitor for 95% success gate
7. Consider P1 improvements if time allows

## Review History
### Round 3 Analysis (2024-12-28 16:30)
- Discovered Codex misunderstood Stage 1 goals
- Evaluation approach is correct as-is
- Only 2 real bugs, not 3
- Constitution tracking not needed for Stage 1

## File Organization
```
/Users/scottmcguire/MaximalCAI/
├── START_HERE.md     # PROJECT ORIENTATION
├── REVIEW_PROTOCOL.md # HOW TO MANAGE REVIEWS
├── PERSISTENT_STATE.md # THIS FILE
├── reviews/
│   ├── P0_FIXES_REVIEW_SUMMARY.md # Original
│   └── P0_FIXES_REVIEW_SUMMARY_CORRECTED.md # CORRECTED VERSION
├── tasks/
│   └── claude_code/
│       ├── pending/   # ONLY 2 P0 TASKS NOW
│       └── cancelled/ # Evaluation task moved here
└── scripts/          # 2 bugs to fix, then ready
```

## Important Notes
- Only 2 bugs actually block deployment
- Evaluation approach is correct - measures instruction following
- Constitutional tracking comes later (Stage 6)
- Stage 1 is simpler than Codex assumed
- We're doing sequential bootstrapping by design
