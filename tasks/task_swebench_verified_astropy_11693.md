---
id: swebench_verified_astropy_11693
name: SWE-bench Verified astropy astropy-11693
category: swebench
description: Prompt-level smoke task derived from a locally cached SWE-bench Verified sample.
prompt: |
  You are given a compact SWE-bench Verified issue instance for prompt-level benchmarking.
  This harness run does not execute the repository test environment or score an official SWE-bench patch.
  Instead, analyze the issue and return a concise debugging and fix plan.
  Base your answer only on the issue material below.
  Do not use web_search, web_fetch, browser navigation, external network access, or repository inspection tools.
  Treat the repository as unavailable unless it is explicitly quoted in the prompt.

  Output format:
  1. Root cause hypothesis
  2. Files or functions most likely involved
  3. Minimal patch strategy
  4. Risks or edge cases to verify

  Instance ID: astropy__astropy-11693
  Repository: astropy/astropy
  Base commit: 3832210580d516365ddae1a62071001faf94d416
  Version: 4.2

  Issue summary:
  Plotting an image with a WCS projection that includes strong non-linear SIP distortion fails because `WCS.all_world2pix` raises `NoConvergence` when called through the FITS WCS APE14 wrapper.

  Expected behavior:
  The plotting path should degrade more gracefully. Using `quiet=True` on the direct `all_world2pix` call yields a usable plot, so callers want warning-tolerant behavior rather than a hard exception in this path.

  Relevant code path:
  - `astropy/wcs/wcsapi/fitswcs.py`, line around `world_to_pixel_values`
  - direct call: `pixel = self.all_world2pix(*world_arrays, 0)`

  Observed failure:
  - `astropy/wcs/wcs.py`: `NoConvergence: 'WCS.all_world2pix' failed to converge to the requested accuracy.`
  - Maintainer discussion suggests the cleanest fix is likely in the FITS WCS APE14 wrapper so this path emits a warning or otherwise handles non-convergence more gracefully instead of hard-failing plotting.

  Repro sketch:
  A synthetic WCS with large SIP distortion is used for plotting; the grid draw path triggers `world_to_pixel_values`, which eventually calls `all_world2pix` and raises `NoConvergence`.

  Focus only on the likely library fix strategy. Do not propose broad API redesign unless it is necessary.
---

Source dataset path: `/root/ziruiw/ascend_fabric/multi_replica_20260426T075224Z/ai_profiler_cleaning/post7_datasets/swebench/data/test-00000-of-00001.parquet`
Original instance id: `astropy__astropy-11693`
