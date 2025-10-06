# Data Schemas & Provenance (Manifests & Records)

SFT Example Record (JSONL)
- instruction: string
- response: string
- prompt: string (optional, audit)
- completion: string (optional, audit)
- instruction_critique: { is_good: bool, predicted_label: 'A'|'B', logp_a: float, logp_b: float, margin: float, confident: bool }
- pair_critique: { ... same fields ... }
- metadata: create_artifact_metadata(...), including:
  - git_commit (full SHA), timestamp, loader_version (SHA), model_name, quantization, template_disabled: true
  - script_name, artifact_type
  - generation params (seed, temperature, max_new_tokens, do_sample)

QC Summary (JSON)
- counts: { generated, kept, delimiter_found, delimiter_missing, heuristic_cutoff, hit_token_limit }
- acceptance: { instructions_good, instructions_bad, instructions_low_confidence, pairs_good, pairs_bad, pairs_low_confidence }
- token_stats: { median, mean, p95 }
- margins: { instruction: histogram/stats, pair: histogram/stats }
- thresholds_passed: bool, failed_reasons: []

Session Manifest (JSON)
- session_id, session_start, git_commit, git_branch, git_dirty
- environment: { hostname, python, torch, transformers, cuda|rocm, gpu, gpu_memory_gb }
- planned_artifacts: []
- artifacts_generated: []
- loader_version, budgets: { gpu_hours_estimate }, timeouts
- notes: free text

Training Manifest (JSON)
- dataset_path, dataset_sha (optional), qc_summary_path
- hyperparams: { epochs, lr, batch, grad_accum, seq_len, lora: { r, alpha, dropout } }
- checkpoint_paths, training_success_marker
- eval_summary_path

Evaluation Output (JSON)
- overall: { n, base_rate, base_ci, sft_rate, sft_ci, lift, lift_ci_bootstrap, mcnemar_chi2, mcnemar_p, cohens_h, discordant_pairs: { n01, n10 } }
- by_type: { type: same as overall + mcnemar_p_adjusted, significant_after_bh }
- bh_correction: { fdr, n_tests, n_significant_raw, n_significant_adjusted }
- metadata: { labels, confidence_level, bootstrap_samples, random_seed }

