## `single-w` vs `multi-25x4w-stag500` vs `multi-inst-25x4i` vs `multi-inst-25x2ix2w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T124419Z_vps-docker-qwen3-235b-single-100-request | 1 | 100 | 100 | 0 |
| multi-25x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T132533Z_vps-docker-qwen3-235b-multi-25x4w-stag500-request | 1 | 100 | 100 | 0 |
| multi-inst-25x4i | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133820Z_vps-docker-qwen3-235b-single-inst-25x4i-request | 4 | 100 | 100 | 0 |
| multi-inst-25x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T141506Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-request | 2 | 100 | 100 | 0 |

**Aggregation Policy**

- `pidstat` per-process metrics are summed across instances.
- `iostat` and `vmstat` host-wide metrics are averaged across instance collectors.
- This makes multi-instance runs comparable with single-instance runs at the whole-machine level.

**Figures**

- ![Latency Overview](figures/latency_overview.png)
- ![Latency Phase Means](figures/latency_phase_means.png)
- ![Latency Tail](figures/latency_tail.png)
- ![Latency Timeline](figures/latency_timeline.png)
- ![Request Gantt Timeline](figures/actual_request_timeline.png)
- ![AICore vs Request Activity](figures/aicore_request_alignment.png)
- ![System CPU Metrics](figures/system_cpu_metrics.png)
- ![System CPU Timeline](figures/system_cpu_timeline.png)
- ![System Memory Metrics](figures/system_memory_metrics.png)
- ![System Memory Timeline](figures/system_memory_timeline.png)
- ![System Disk Metrics](figures/system_disk_metrics.png)
- ![System I/O Timeline](figures/system_io_timeline.png)
- ![System Activity Metrics](figures/system_activity_metrics.png)
- ![System Activity Timeline](figures/system_activity_timeline.png)
- ![Token Throughput Metrics](figures/token_throughput_metrics.png)
- ![NPU Metrics](figures/npu_metrics.png)
- ![NPU Timeline](figures/npu_timeline.png)

**Run Timing Table**

| scenario | run_dir | run_started_at | run_finished_at | run_wall_clock_sec | first_request_started_at | last_request_finished_at | request_window_sec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T124419Z_vps-docker-qwen3-235b-single-100-request | 2026-04-20T12:44:27.799062+00:00 | 2026-04-20T12:53:13.276954+00:00 | 525.478 | 2026-04-20T12:44:27.865302+00:00 | 2026-04-20T12:53:09.539178+00:00 | 521.674 |
| multi-25x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T132533Z_vps-docker-qwen3-235b-multi-25x4w-stag500-request | 2026-04-20T13:25:41.795349+00:00 | 2026-04-20T13:30:10.959344+00:00 | 269.164 | 2026-04-20T13:25:49.265092+00:00 | 2026-04-20T13:29:58.331433+00:00 | 249.066 |
| multi-inst-25x4i | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133820Z_vps-docker-qwen3-235b-single-inst-25x4i-request | 2026-04-20T13:38:50.850510+00:00 | 2026-04-20T13:43:46.887582+00:00 | 296.037 | 2026-04-20T13:38:50.982407+00:00 | 2026-04-20T13:42:49.316268+00:00 | 238.334 |
| multi-inst-25x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T141506Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-request | 2026-04-20T14:15:21.285984+00:00 | 2026-04-20T14:19:50.772220+00:00 | 269.486 | 2026-04-20T14:15:21.352356+00:00 | 2026-04-20T14:19:26.089175+00:00 | 244.737 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 5216.692 | 5048.535 | 5551.443 | 5732.552 |
| multi-25x4w-stag500 | 9819.878 | 9417.068 | 11295.614 | 21724.197 |
| multi-inst-25x4i | 9403.671 | 8876.570 | 9524.048 | 21767.570 |
| multi-inst-25x2ix2w-500 | 9626.567 | 9120.179 | 9881.827 | 21588.170 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 65.913 | 10.157 | 5154.916 | 51.582 | 5216.692 |
| multi-25x4w-stag500 | 6780.303 | 19.943 | 9591.069 | 208.826 | 9819.878 |
| multi-inst-25x4i | 1975.968 | 5.562 | 9218.579 | 179.495 | 9403.671 |
| multi-inst-25x2ix2w-500 | 2772.034 | 16.985 | 9487.020 | 122.526 | 9626.567 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 28.701 | 32.891 | 5031.352 | 5542.047 | 5705.789 | 17.145 | 23.607 | 5551.443 | 5732.552 |
| multi-25x4w-stag500 | 42.924 | 225.228 | 9381.231 | 11281.706 | 21695.922 | 26.114 | 9692.420 | 11295.614 | 21724.197 |
| multi-inst-25x4i | 14.230 | 30.370 | 8865.024 | 9491.228 | 17599.009 | 20.622 | 4237.117 | 9524.048 | 21767.570 |
| multi-inst-25x2ix2w-500 | 36.563 | 241.431 | 9094.588 | 9871.552 | 17921.015 | 16.907 | 4137.825 | 9881.827 | 21588.170 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 29.739 | 23.827 | 5.912 | 0.046 |
| multi-25x4w-stag500 | 53.938 | 43.379 | 10.559 | 0.146 |
| multi-inst-25x4i | 85.233 | 68.639 | 16.594 | 0.118 |
| multi-inst-25x2ix2w-500 | 65.176 | 52.909 | 12.267 | 0.082 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 801357.739 |
| multi-25x4w-stag500 | 1008802.330 |
| multi-inst-25x4i | 2452171.630 |
| multi-inst-25x2ix2w-500 | 1338164.074 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.606 | 0.006 | 0.475 | 0.046 | 4538.347 | 4445.465 |
| multi-25x4w-stag500 | sda | 0.910 | 0.000 | 0.747 | 0.144 | 8679.264 | 8779.893 |
| multi-inst-25x4i | sda | 1.083 | 0.021 | 0.664 | 0.232 | 13887.655 | 13618.943 |
| multi-inst-25x2ix2w-500 | sda | 1.041 | 0.000 | 0.732 | 0.178 | 10736.191 | 10538.826 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 857937.178 | 1381653.107 | 30.688 | 0.004 | 33.463 | 23.732 | 0.000 |
| multi-25x4w-stag500 | 782008.307 | 1282399.421 | 29.575 | 0.011 | 42.900 | 55.374 | 0.000 |
| multi-inst-25x4i | 794327.602 | 1323452.459 | 28.547 | 0.015 | 82.506 | 62.048 | 0.000 |
| multi-inst-25x2ix2w-500 | 788925.081 | 1294633.502 | 31.170 | 0.004 | 57.247 | 42.344 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 100 | 16.760 | 3.293 | 3.293 |
| multi-25x4w-stag500 | 98 | 16.541 | 1.721 | 1.721 |
| multi-inst-25x4i | 100 | 16.790 | 1.854 | 1.854 |
| multi-inst-25x2ix2w-500 | 100 | 16.530 | 1.784 | 1.784 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 61.873 | 94.287 | 21.512 |
| multi-25x4w-stag500 | 78.446 | 95.000 | 40.924 |
| multi-inst-25x4i | 69.705 | 95.000 | 36.817 |
| multi-inst-25x2ix2w-500 | 76.891 | 95.500 | 40.279 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 156.000 | 411.000 | 994180.000 | 262.000 | 10.800 | 44.000 | 3.590 | 517.000 | 1097385.000 | 74.000 | 1747789.000 | 496.000 | 70.000 | 157.000 | 75.938 | 66.073 | 26.812 | 170.683 | 94.500 | 302.612 |
| multi-25x4w-stag500 | 183.000 | 88.000 | 1162908.000 | 257.000 | 7.600 | 12.000 | 5.500 | 119.000 | 975251.000 | 240.000 | 1623700.000 | 240.000 | 69.000 | 157.000 | 95.625 | 242.138 | 51.688 | 242.138 | 95.000 | 0.000 |
| multi-inst-25x4i | 416.000 | 9.000 | 3263880.000 | 21.000 | 4.600 | 13.000 | 2.755 | 32.000 | 860014.750 | 231.000 | 1428292.000 | 9.000 | 64.000 | 140.000 | 91.000 | 114.164 | 50.750 | 208.581 | 95.000 | 0.000 |
| multi-inst-25x2ix2w-500 | 271.000 | 28.000 | 1882948.000 | 24.000 | 5.600 | 5.000 | 4.360 | 71.000 | 915027.000 | 207.000 | 1551666.000 | 261.000 | 65.500 | 95.000 | 91.438 | 243.622 | 49.375 | 113.681 | 95.500 | 0.000 |
