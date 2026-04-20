## `single-w` vs `multi-25x4w-stag500` vs `multi-inst-25x4i` vs `multi-inst-25x2ix2w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T122607Z_vps-docker-qwen3-235b-single-100-worker | 1 | 100 | 100 | 0 |
| multi-25x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T131723Z_vps-docker-qwen3-235b-multi-25x4w-stag500-worker | 1 | 100 | 100 | 0 |
| multi-inst-25x4i | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133011Z_vps-docker-qwen3-235b-single-inst-25x4i-worker | 4 | 100 | 100 | 0 |
| multi-inst-25x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T140612Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-worker | 2 | 100 | 100 | 0 |

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
| single-w | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T122607Z_vps-docker-qwen3-235b-single-100-worker | 2026-04-20T12:26:14.982918+00:00 | 2026-04-20T12:44:18.873534+00:00 | 1083.891 | 2026-04-20T12:26:15.050496+00:00 | 2026-04-20T12:44:06.666027+00:00 | 1071.616 |
| multi-25x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T131723Z_vps-docker-qwen3-235b-multi-25x4w-stag500-worker | 2026-04-20T13:17:32.152036+00:00 | 2026-04-20T13:25:32.847096+00:00 | 480.695 | 2026-04-20T13:17:32.222626+00:00 | 2026-04-20T13:25:19.059390+00:00 | 466.837 |
| multi-inst-25x4i | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133011Z_vps-docker-qwen3-235b-single-inst-25x4i-worker | 2026-04-20T13:30:42.370662+00:00 | 2026-04-20T13:38:19.584830+00:00 | 457.214 | 2026-04-20T13:30:42.463602+00:00 | 2026-04-20T13:37:29.342570+00:00 | 406.879 |
| multi-inst-25x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T140612Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-worker | 2026-04-20T14:06:27.214079+00:00 | 2026-04-20T14:15:05.829235+00:00 | 518.615 | 2026-04-20T14:06:28.039077+00:00 | 2026-04-20T14:14:39.671904+00:00 | 491.633 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 10716.112 | 10587.211 | 11609.176 | 28131.085 |
| multi-25x4w-stag500 | 15793.655 | 14126.145 | 19222.430 | 40556.523 |
| multi-inst-25x4i | 11431.218 | 11228.398 | 21382.561 | 24126.145 |
| multi-inst-25x2ix2w-500 | 14234.744 | 14867.862 | 24593.755 | 49043.411 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 67.328 | 3.743 | 10659.810 | 52.524 | 10716.112 |
| multi-25x4w-stag500 | 898.628 | 8.495 | 15743.316 | 41.806 | 15793.655 |
| multi-inst-25x4i | 2331.294 | 6.289 | 11241.889 | 183.002 | 11431.218 |
| multi-inst-25x2ix2w-500 | 4052.876 | 17.690 | 14000.414 | 216.601 | 14234.744 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 4.989 | 11.338 | 10577.986 | 11599.220 | 23612.275 | 10.934 | 17.260 | 11609.176 | 28131.085 |
| multi-25x4w-stag500 | 23.974 | 56.965 | 14114.849 | 19210.958 | 40541.727 | 16.970 | 33.874 | 19222.430 | 40556.523 |
| multi-inst-25x4i | 26.177 | 40.431 | 11218.410 | 18914.857 | 24114.181 | 31.825 | 4425.834 | 21382.561 | 24126.145 |
| multi-inst-25x2ix2w-500 | 13.064 | 607.758 | 14856.026 | 24575.436 | 49032.395 | 16.033 | 10314.694 | 24593.755 | 49043.411 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 14.967 | 11.854 | 3.114 | 0.014 |
| multi-25x4w-stag500 | 28.929 | 22.785 | 6.145 | 0.032 |
| multi-inst-25x4i | 57.117 | 45.252 | 11.865 | 0.096 |
| multi-inst-25x2ix2w-500 | 35.332 | 28.122 | 7.210 | 0.039 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 611623.254 |
| multi-25x4w-stag500 | 752520.502 |
| multi-inst-25x4i | 2277830.766 |
| multi-inst-25x2ix2w-500 | 1270060.897 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.275 | 0.002 | 0.244 | 0.022 | 2324.190 | 2284.369 |
| multi-25x4w-stag500 | sda | 0.468 | 0.003 | 0.472 | 0.053 | 4451.498 | 4323.413 |
| multi-inst-25x4i | sda | 0.647 | 0.004 | 0.497 | 0.143 | 8810.673 | 8840.185 |
| multi-inst-25x2ix2w-500 | sda | 0.489 | 0.000 | 0.406 | 0.075 | 5502.977 | 5434.809 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 922447.791 | 1423632.536 | 37.467 | 0.003 | 30.419 | 7.982 | 0.000 |
| multi-25x4w-stag500 | 821966.960 | 1316656.806 | 32.304 | 0.002 | 29.161 | 17.327 | 0.000 |
| multi-inst-25x4i | 837190.940 | 1361502.428 | 31.625 | 0.003 | 67.961 | 48.463 | 0.000 |
| multi-inst-25x2ix2w-500 | 819283.966 | 1321281.156 | 31.830 | 0.004 | 42.759 | 20.387 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 100 | 200.660 | 19.605 | 13.736 |
| multi-25x4w-stag500 | 100 | 144.120 | 10.210 | 5.862 |
| multi-inst-25x4i | 100 | 107.710 | 9.089 | 4.520 |
| multi-inst-25x2ix2w-500 | 100 | 131.430 | 10.737 | 6.366 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 79.860 | 94.000 | 28.425 |
| multi-25x4w-stag500 | 87.409 | 95.000 | 44.374 |
| multi-inst-25x4i | 78.938 | 95.000 | 37.920 |
| multi-inst-25x2ix2w-500 | 85.807 | 95.446 | 43.034 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 187.000 | 93.000 | 918832.000 | 21.000 | 19.600 | 35.000 | 2.120 | 559.000 | 1152746.000 | 82.000 | 1786788.000 | 82.000 | 105.000 | 877.000 | 94.062 | 704.451 | 34.875 | 966.791 | 94.000 | 0.000 |
| multi-25x4w-stag500 | 168.000 | 129.000 | 952960.000 | 229.000 | 10.800 | 54.000 | 5.230 | 3.000 | 1053689.000 | 432.000 | 1654277.000 | 432.000 | 72.000 | 157.000 | 96.375 | 375.020 | 53.125 | 121.326 | 95.000 | 0.000 |
| multi-inst-25x4i | 469.000 | 2.000 | 3358476.000 | 15.000 | 5.600 | 8.000 | 3.853 | 8.000 | 1020849.750 | 382.000 | 1582224.750 | 382.000 | 60.000 | 398.000 | 96.938 | 142.389 | 53.375 | 122.867 | 95.000 | 0.000 |
| multi-inst-25x2ix2w-500 | 312.000 | 41.000 | 1915264.000 | 24.000 | 7.200 | 61.000 | 3.290 | 31.000 | 976120.500 | 470.000 | 1533704.000 | 497.000 | 66.500 | 86.000 | 97.125 | 303.267 | 52.812 | 123.129 | 95.500 | 102.799 |
