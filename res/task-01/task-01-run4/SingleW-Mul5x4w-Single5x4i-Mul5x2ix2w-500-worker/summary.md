## `single-w` vs `multi-5x4w-stag500` vs `multi-inst-5x4i` vs `multi-inst-5x2ix2w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T134553Z_vps-docker-qwen3-235b8x2-single-20-worker | 1 | 20 | 20 | 0 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135418Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-worker | 1 | 20 | 20 | 0 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135628Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 4 | 20 | 20 | 0 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T140307Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-worker | 2 | 20 | 20 | 0 |

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
| single-w | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T134553Z_vps-docker-qwen3-235b8x2-single-20-worker | 2026-04-17T13:46:01.742580+00:00 | 2026-04-17T13:48:40.143615+00:00 | 158.401 | 2026-04-17T13:46:01.809182+00:00 | 2026-04-17T13:48:32.952401+00:00 | 151.143 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135418Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-worker | 2026-04-17T13:54:27.021504+00:00 | 2026-04-17T13:55:36.898371+00:00 | 69.877 | 2026-04-17T13:54:27.092274+00:00 | 2026-04-17T13:55:24.380321+00:00 | 57.288 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135628Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 2026-04-17T13:57:00.372979+00:00 | 2026-04-17T13:58:39.105337+00:00 | 98.732 | 2026-04-17T13:57:00.504245+00:00 | 2026-04-17T13:58:02.335545+00:00 | 61.831 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T140307Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-worker | 2026-04-17T14:03:23.896300+00:00 | 2026-04-17T14:04:56.316899+00:00 | 92.421 | 2026-04-17T14:03:23.962232+00:00 | 2026-04-17T14:04:32.839182+00:00 | 68.877 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 7557.113 | 5879.542 | 17114.873 | 25315.040 |
| multi-5x4w-stag500 | 10026.616 | 8580.281 | 15561.519 | 17774.751 |
| multi-inst-5x4i | 10815.844 | 10905.986 | 15320.315 | 15943.851 |
| multi-inst-5x2ix2w-500 | 10465.933 | 9581.437 | 15250.481 | 28845.977 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 66.260 | 5.246 | 7351.774 | 200.053 | 7557.113 |
| multi-5x4w-stag500 | 934.921 | 10.162 | 9814.524 | 201.893 | 10026.616 |
| multi-inst-5x4i | 1870.572 | 6.476 | 9992.334 | 816.997 | 10815.844 |
| multi-inst-5x2ix2w-500 | 4093.727 | 5.945 | 9885.278 | 574.674 | 10465.933 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 17.613 | 21.751 | 5854.740 | 13277.397 | 25302.961 | 21.814 | 3832.924 | 17114.873 | 25315.040 |
| multi-5x4w-stag500 | 19.564 | 123.881 | 8568.670 | 15544.922 | 17748.113 | 15.214 | 3866.449 | 15561.519 | 17774.751 |
| multi-inst-5x4i | 20.365 | 27.777 | 10790.197 | 13109.693 | 15935.016 | 4050.836 | 4177.976 | 15320.315 | 15943.851 |
| multi-inst-5x2ix2w-500 | 24.393 | 36.690 | 9552.522 | 12762.866 | 28835.661 | 4112.165 | 4119.961 | 15250.481 | 28845.977 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 29.461 | 23.623 | 5.838 | 0.032 |
| multi-5x4w-stag500 | 54.123 | 44.400 | 9.723 | 0.446 |
| multi-inst-5x4i | 130.955 | 104.971 | 25.984 | 0.359 |
| multi-inst-5x2ix2w-500 | 74.959 | 59.924 | 15.035 | 0.095 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 694701.429 |
| multi-5x4w-stag500 | 845903.815 |
| multi-inst-5x4i | 2532997.222 |
| multi-inst-5x2ix2w-500 | 1512333.463 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.449 | 0.006 | 0.356 | 0.054 | 4948.208 | 4905.273 |
| multi-5x4w-stag500 | sda | 0.654 | 0.000 | 0.671 | 0.117 | 8936.185 | 10418.585 |
| multi-inst-5x4i | sda | 1.218 | 0.000 | 0.727 | 0.262 | 16702.848 | 16240.318 |
| multi-inst-5x2ix2w-500 | sda | 0.818 | 0.000 | 0.933 | 0.270 | 13465.327 | 12330.014 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 903929.619 | 1422375.006 | 34.748 | 0.013 | 33.838 | 17.883 | 0.000 |
| multi-5x4w-stag500 | 775645.258 | 1302836.848 | 26.030 | 0.000 | 30.323 | 164.123 | 0.000 |
| multi-inst-5x4i | 771537.355 | 1341048.532 | 19.829 | 0.021 | 77.739 | 170.701 | 0.000 |
| multi-inst-5x2ix2w-500 | 790251.528 | 1327375.481 | 20.614 | 0.000 | 42.488 | 51.930 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 109.150 | 17.296 | 6.748 |
| multi-5x4w-stag500 | 20 | 68.000 | 7.645 | 5.454 |
| multi-inst-5x4i | 20 | 80.800 | 8.173 | 4.688 |
| multi-inst-5x2ix2w-500 | 20 | 73.000 | 7.597 | 4.589 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 65.312 | 93.500 | 23.570 |
| multi-5x4w-stag500 | 56.732 | 93.500 | 29.911 |
| multi-inst-5x4i | 43.089 | 93.530 | 22.930 |
| multi-inst-5x2ix2w-500 | 55.097 | 93.969 | 27.493 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 187.000 | 80.000 | 930912.000 | 67.000 | 10.400 | 44.000 | 2.940 | 85.000 | 1093995.000 | 96.000 | 1693588.000 | 96.000 | 72.000 | 13.000 | 92.812 | 57.516 | 31.000 | 57.516 | 93.500 | 0.000 |
| multi-5x4w-stag500 | 153.000 | 40.000 | 952264.000 | 28.000 | 6.000 | 9.000 | 4.580 | 3.000 | 989430.000 | 58.000 | 1675411.000 | 15.000 | 67.000 | 38.000 | 95.500 | 46.913 | 51.812 | 18.776 | 93.500 | 0.000 |
| multi-inst-5x4i | 394.000 | 25.000 | 3199080.000 | 16.000 | 5.625 | 8.000 | 2.550 | 34.000 | 872182.250 | 62.000 | 1414440.250 | 5.000 | 54.500 | 62.000 | 95.500 | 75.276 | 52.562 | 48.601 | 93.625 | 47.736 |
| multi-inst-5x2ix2w-500 | 245.000 | 9.000 | 1769572.000 | 33.000 | 4.800 | 16.000 | 5.940 | 16.000 | 924832.000 | 66.000 | 1530284.500 | 13.000 | 62.000 | 47.000 | 93.875 | 64.293 | 50.312 | 36.749 | 94.000 | 36.749 |
