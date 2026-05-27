---
id: swebench_smoke_astropy_astropy_11693
name: SWE smoke astropy__astropy-11693
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

  Instance ID: astropy__astropy-11693
  Repository: astropy/astropy
  Base commit: 3832210580d516365ddae1a62071001faf94d416
  Version: 4.2

  Problem statement:
  'WCS.all_world2pix' failed to converge when plotting WCS with non linear distortions

  Focus only on the likely library fix strategy. Do not propose broad API redesign unless it is necessary.
---

Source dataset path: `/root/ziruiw/ascend_fabric/multi_replica_20260426T075224Z/ai_profiler_cleaning/post7_datasets/swebench/data/test-00000-of-00001.parquet`
Original instance id: `astropy__astropy-11693`
Repository: `astropy/astropy`
Base commit: `3832210580d516365ddae1a62071001faf94d416`
