---
id: swebench_smoke_astropy_astropy_12057
name: SWE smoke astropy__astropy-12057
category: swebench
description: Prompt-level SWE smoke task generated from local SWE-bench parquet data.
prompt: |
  You are given a compact SWE-bench Verified issue instance for prompt-level benchmarking.
  This harness run does not execute the repository test environment or score an official SWE-bench patch.
  Instead, analyze the issue and return a concise debugging and fix plan.
  Base your answer only on the issue material below.
  Do not use web_search, web_fetch, browser navigation, external network access, or repository inspection tools.
  Do not assume the repository is checked out locally.

  Output format:
  1. Root cause hypothesis
  2. Files or functions most likely involved
  3. Minimal patch strategy
  4. Risks or edge cases to verify

  Instance ID: astropy__astropy-12057
  Repository: astropy/astropy
  Base commit: b6769c18c0881b6d290e543e9334c25043018b3f
  Version: 4.3

  Problem statement:
  Add helpers to convert between different types of uncertainties

  Focus only on the likely library fix strategy. Do not propose broad API redesign unless it is necessary.
---

Source dataset path: `/root/ziruiw/ascend_fabric/multi_replica_20260426T075224Z/ai_profiler_cleaning/post7_datasets/swebench/data/test-00000-of-00001.parquet`
Original instance id: `astropy__astropy-12057`
Repository: `astropy/astropy`
Base commit: `b6769c18c0881b6d290e543e9334c25043018b3f`
