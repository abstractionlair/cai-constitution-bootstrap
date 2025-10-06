# Subagent Orchestration for Autonomous Work

**Concept**: Main Claude orchestrates, subagents do focused work with fresh context.

**Benefit**: Indirect control over context - subagents have bounded context, main agent stays lean.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Main Claude (Orchestrator)                              │
│ - Reads project status                                  │
│ - Creates work plans                                    │
│ - Spawns subagents for each task                        │
│ - Collects results                                      │
│ - Updates status                                        │
│ Context: ~50k (lean, just orchestration logic)          │
└─────────────────────────────────────────────────────────┘
              │
              ├─────────────────────────────┬──────────────────────┐
              ▼                             ▼                      ▼
    ┌──────────────────┐        ┌──────────────────┐   ┌──────────────────┐
    │ Subagent 1       │        │ Subagent 2       │   │ Subagent 3       │
    │ Analyze codebase │        │ Implement #4     │   │ Test impl        │
    │ Context: 500k    │        │ Context: 300k    │   │ Context: 100k    │
    │ Output: analysis │        │ Output: code     │   │ Output: results  │
    └──────────────────┘        └──────────────────┘   └──────────────────┘
```

---

## Implementation via MCP

Claude Code can run as MCP server. Main Claude orchestrates via MCP calls.

### Setup

```json
# ~/.config/claude-code/mcp.json
{
  "mcpServers": {
    "claude-worker": {
      "command": "claude",
      "args": ["mcp", "serve"],
      "env": {
        "WORKER_MODE": "true"
      }
    }
  }
}
```

### Main Orchestrator Script

```python
#!/usr/bin/env python3
"""
Main orchestrator for autonomous CAI implementation.
Spawns subagents for focused tasks.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any

class SubagentOrchestrator:
    """Orchestrates work via subagents."""

    def __init__(self):
        self.work_dir = Path("/workspace/MaximalCAI")
        self.status_file = self.work_dir / "status/CURRENT_WORK_STATUS.md"
        self.results_dir = self.work_dir / "artifacts/subagent_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def spawn_subagent(
        self,
        task_name: str,
        task_description: str,
        context_files: list[str],
        output_file: str,
        max_tokens: int = 200000  # Or 1M for complex tasks
    ) -> Dict[str, Any]:
        """
        Spawn a subagent to complete a focused task.

        Args:
            task_name: Short name (e.g., "analyze_codebase")
            task_description: Detailed task description
            context_files: Files to load into subagent context
            output_file: Where subagent writes results
            max_tokens: Context limit for this subagent

        Returns:
            Dict with success status and results path
        """

        # Create task specification
        task_spec = {
            "task": task_name,
            "description": task_description,
            "context": context_files,
            "output": output_file,
            "constraints": {
                "max_tokens": max_tokens,
                "checkpoint_frequency": "high"
            }
        }

        task_file = self.results_dir / f"{task_name}_spec.json"
        with open(task_file, 'w') as f:
            json.dump(task_spec, f, indent=2)

        # Build subagent command
        prompt = self._build_subagent_prompt(task_spec)

        cmd = [
            "claude-code",
            "--api-mode",  # Use API for 1M context if needed
            "--full-auto",  # No approval prompts
            "--cd", str(self.work_dir),
            prompt
        ]

        # Run subagent
        print(f"🤖 Spawning subagent: {task_name}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.work_dir,
            timeout=7200  # 2 hour timeout
        )

        if result.returncode == 0:
            print(f"✅ Subagent {task_name} completed")
            return {
                "success": True,
                "output_file": output_file,
                "task_spec": str(task_file)
            }
        else:
            print(f"❌ Subagent {task_name} failed: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr,
                "task_spec": str(task_file)
            }

    def _build_subagent_prompt(self, task_spec: Dict[str, Any]) -> str:
        """Build prompt for subagent."""

        prompt = f"""You are a subagent working on: {task_spec['task']}

**Task Description**:
{task_spec['description']}

**Context Files to Read**:
"""
        for file in task_spec['context']:
            prompt += f"- {file}\n"

        prompt += f"""
**Your Output**:
Write your results to: {task_spec['output']}

**Important**:
1. Read the context files listed above
2. Complete the task as specified
3. Write detailed results to the output file
4. Include what you did, what you changed, any issues found
5. This is a focused task - complete it and exit

**Constraints**:
- Checkpoint frequently (write progress to output file)
- If task is too large, write partial results and note what's remaining
- Be thorough but focused on this specific task

Begin."""

        return prompt

    def orchestrate_findings(self) -> Dict[str, Any]:
        """
        Orchestrate implementation of remaining findings.
        """

        print("🎯 Main Orchestrator Starting")
        print("=" * 60)

        # Read current status
        status = self._read_status()
        print(f"Current status: {status.get('completed', [])} completed")

        results = {}

        # Task 1: Analyze Finding #4 requirements
        print("\n📋 Task 1: Analyze Best-of-N requirements")
        results['analyze_finding4'] = self.spawn_subagent(
            task_name="analyze_finding4",
            task_description="""
Analyze requirements for implementing Best-of-N sampling in preference pairs.

Read:
- reviews/responses/20251006_methodology_audit_codex.md (Finding #2)
- docs/POST_TRAINING_APPROACHES.md (Best-of-N section)
- scripts/generate_preference_pairs_logprob.py (current implementation)
- scripts/utils/instruction_critic.py (available utilities)

Output detailed implementation plan covering:
1. What needs to be modified
2. How to add k-parameter
3. How to sample multiple responses
4. How to rank and pair them
5. Estimated effort and risks

Write to: artifacts/finding4_analysis.md
""",
            context_files=[
                "reviews/responses/20251006_methodology_audit_codex.md",
                "docs/POST_TRAINING_APPROACHES.md",
                "scripts/generate_preference_pairs_logprob.py",
                "scripts/utils/instruction_critic.py"
            ],
            output_file="artifacts/finding4_analysis.md",
            max_tokens=500000  # Large for thorough analysis
        )

        if not results['analyze_finding4']['success']:
            print("❌ Analysis failed, aborting")
            return results

        # Ask Codex for review of plan before implementing
        print("\n🤔 Requesting Codex review of plan...")
        codex_review = self._request_codex_review(
            "finding4_analysis",
            "artifacts/finding4_analysis.md"
        )

        if not codex_review.get('approved', False):
            print("⚠️  Codex recommends revision")
            print(f"Recommendation: {codex_review.get('recommendation')}")
            # Could spawn another subagent to revise plan
            return results

        # Task 2: Implement Finding #4
        print("\n🛠️  Task 2: Implement Best-of-N")
        results['implement_finding4'] = self.spawn_subagent(
            task_name="implement_finding4",
            task_description="""
Implement Best-of-N sampling according to the approved plan.

Read:
- artifacts/finding4_analysis.md (your implementation plan)
- scripts/generate_preference_pairs_logprob.py (file to modify)

Follow the plan exactly. Implement:
1. k-parameter addition
2. Multiple response sampling
3. Ranking via logprob margins
4. Pair creation (best vs others)

Write modified script and detailed implementation notes.

Outputs:
- Modified: scripts/generate_preference_pairs_logprob.py
- Notes: artifacts/finding4_implementation.md
""",
            context_files=[
                "artifacts/finding4_analysis.md",
                "scripts/generate_preference_pairs_logprob.py"
            ],
            output_file="artifacts/finding4_implementation.md",
            max_tokens=300000  # Medium - focused implementation
        )

        if not results['implement_finding4']['success']:
            print("❌ Implementation failed")
            return results

        # Task 3: Test implementation
        print("\n🧪 Task 3: Test Best-of-N implementation")
        results['test_finding4'] = self.spawn_subagent(
            task_name="test_finding4",
            task_description="""
Test the Best-of-N implementation.

Read:
- artifacts/finding4_implementation.md (what was changed)
- scripts/generate_preference_pairs_logprob.py (modified script)

Create and run a test that:
1. Generates 10 preference pairs with k=3
2. Verifies pairs are created correctly
3. Checks margin calculations
4. Validates output format

Write test results and any issues found.

Outputs:
- Test script: tests/test_best_of_n.py
- Results: artifacts/finding4_test_results.md
""",
            context_files=[
                "artifacts/finding4_implementation.md",
                "scripts/generate_preference_pairs_logprob.py"
            ],
            output_file="artifacts/finding4_test_results.md",
            max_tokens=200000  # Small - focused testing
        )

        # Task 4: Similarly for Finding #5
        # (Would spawn more subagents here)

        print("\n" + "=" * 60)
        print("✅ Orchestration complete")
        return results

    def _read_status(self) -> Dict[str, Any]:
        """Read current work status."""
        # Parse CURRENT_WORK_STATUS.md
        # Return dict with completed/remaining work
        pass

    def _request_codex_review(self, topic: str, file: str) -> Dict[str, Any]:
        """Request Codex review of a result file."""
        # Use request_codex_review.py utility
        pass


if __name__ == "__main__":
    orchestrator = SubagentOrchestrator()
    results = orchestrator.orchestrate_findings()

    print("\n📊 Final Results:")
    for task, result in results.items():
        status = "✅" if result['success'] else "❌"
        print(f"{status} {task}: {result.get('output_file', 'N/A')}")
```

---

## Benefits of Subagent Approach

### 1. **Context Management**
- **Main agent**: Stays lean (~50k tokens)
- **Subagents**: Fresh context per task
- **No compaction needed**: Subagents terminate when done

### 2. **Parallelization Potential**
```python
# Could spawn multiple subagents concurrently
with ThreadPoolExecutor() as executor:
    futures = {
        executor.submit(spawn_subagent, "analyze_finding4", ...),
        executor.submit(spawn_subagent, "analyze_finding5", ...),
    }
    results = [f.result() for f in futures]
```

### 3. **Fault Isolation**
- Subagent failure doesn't crash orchestrator
- Can retry failed tasks
- Can delegate to different subagent

### 4. **Resource Control**
```python
# Allocate context based on task complexity
spawn_subagent("simple_task", max_tokens=200000)   # 200k is enough
spawn_subagent("complex_analysis", max_tokens=1000000)  # Use 1M
```

### 5. **Codex Integration**
```python
# Main orchestrator can call Codex at strategic points
plan = subagent_analyze()
codex_review = request_codex_review(plan)

if codex_review['approved']:
    subagent_implement(plan)
else:
    subagent_revise(plan, codex_review)
```

---

## Comparison: Checkpoint vs Subagent

### Checkpoint Approach (Original)
```python
# Single Claude session
analyze_codebase()           # 500k context
write_checkpoint()
# [Compaction happens - uncontrolled timing]
read_checkpoint()
implement_changes()          # 300k context
write_checkpoint()
# [Compaction happens again]
```

**Pros**: Simple, single session
**Cons**: Unpredictable compaction timing, context grows indefinitely

### Subagent Approach (New)
```python
# Orchestrator
results = {}
results['analyze'] = spawn_subagent("analyze", max_tokens=500k)
# Subagent terminates, context cleared

results['implement'] = spawn_subagent("implement", max_tokens=300k)
# Subagent terminates, context cleared
```

**Pros**: Controlled context lifecycle, parallelization, fault isolation
**Cons**: More complex setup, inter-agent coordination overhead

---

## Hybrid Approach (Best of Both)

**Use subagents for major phases, checkpoints within phases**:

```python
# Orchestrator spawns subagent for Finding #4
spawn_subagent(
    "implement_finding4",
    description="""
    Implement Best-of-N.

    Within this task, use checkpoint pattern:
    1. Create plan → checkpoint
    2. Implement part 1 → checkpoint
    3. Implement part 2 → checkpoint
    4. Test → checkpoint
    """,
    max_tokens=1000000  # 1M for this subagent
)
```

**Benefits**:
- Subagents give you control over context lifecycle
- Checkpoints within subagents handle auto-compaction
- Best of both worlds

---

## Decision Matrix

| Approach | Setup Complexity | Context Control | Cost | Best For |
|----------|-----------------|-----------------|------|----------|
| **Checkpoint only** | Low | Reactive | Low | Simple tasks, single phase |
| **Subagents only** | High | Proactive | Medium | Complex multi-phase work |
| **Hybrid** | Medium | Excellent | Medium | Long autonomous sessions |

---

## Recommendation for Your Project

**Use hybrid approach**:

1. **Orchestrator** (main Claude):
   - Read status
   - Spawn subagent for Finding #4
   - Request Codex review of results
   - Spawn subagent for Finding #5
   - Update final status

2. **Subagents** (worker Claudes):
   - Get fresh context per finding
   - Use checkpoint pattern within task
   - Write detailed results
   - Terminate (context cleared)

3. **Codex** (reviewer):
   - Called by orchestrator at decision points
   - Reviews subagent outputs
   - Provides go/no-go decisions

**Setup effort**: ~2-3 hours to build orchestrator
**Ongoing benefit**: Full control over context, clean task separation
**Cost**: ~$50-100 for 1M context in subagents (same as before)

---

## Next Steps

1. **Test MCP server setup**: Verify Claude Code can spawn subagents
2. **Build simple orchestrator**: Start with 2-task example
3. **Add Codex integration**: Orchestrator calls Codex for reviews
4. **Run pilot**: Test with Finding #4 implementation

This gives you **true autonomous operation** with indirect context control.
