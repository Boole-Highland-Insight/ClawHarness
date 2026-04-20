## `single-w` vs `multi-5x4w-stag500` vs `multi-inst-5x4i` vs `multi-inst-5x2ix2w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T134840Z_vps-docker-qwen3-235b8x2-single-20-request | 1 | 20 | 20 | 0 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135537Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request | 1 | 20 | 20 | 0 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135839Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 4 | 20 | 20 | 0 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T140456Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-request | 2 | 20 | 20 | 0 |

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
| single-w | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T134840Z_vps-docker-qwen3-235b8x2-single-20-request | 2026-04-17T13:48:47.361040+00:00 | 2026-04-17T13:49:48.646869+00:00 | 61.286 | 2026-04-17T13:48:47.455688+00:00 | 2026-04-17T13:49:37.487368+00:00 | 50.032 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135537Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request | 2026-04-17T13:55:44.330650+00:00 | 2026-04-17T13:56:28.199288+00:00 | 43.869 | 2026-04-17T13:55:44.402296+00:00 | 2026-04-17T13:56:20.479295+00:00 | 36.077 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135839Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 2026-04-17T13:59:11.448713+00:00 | 2026-04-17T14:00:11.042251+00:00 | 59.594 | 2026-04-17T13:59:11.609570+00:00 | 2026-04-17T13:59:37.032925+00:00 | 25.423 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T140456Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-request | 2026-04-17T14:05:10.290849+00:00 | 2026-04-17T14:06:24.063320+00:00 | 73.772 | 2026-04-17T14:05:10.357046+00:00 | 2026-04-17T14:05:56.007609+00:00 | 45.651 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 2501.542 | 1699.190 | 1782.849 | 17767.614 |
| multi-5x4w-stag500 | 6249.994 | 3272.718 | 21220.160 | 21792.138 |
| multi-inst-5x4i | 4971.895 | 2559.325 | 15257.345 | 15369.184 |
| multi-inst-5x2ix2w-500 | 6914.424 | 3102.909 | 14518.505 | 18375.589 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 94.302 | 2.674 | 2297.358 | 201.473 | 2501.542 |
| multi-5x4w-stag500 | 3400.160 | 268.155 | 5780.848 | 200.956 | 6249.994 |
| multi-inst-5x4i | 155.378 | 6.966 | 4172.369 | 792.522 | 4971.895 |
| multi-inst-5x2ix2w-500 | 805.283 | 34.751 | 6219.818 | 659.817 | 6914.424 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 8.306 | 17.617 | 1692.205 | 1776.343 | 13839.042 | 6.372 | 3924.486 | 1782.849 | 17767.614 |
| multi-5x4w-stag500 | 413.900 | 4409.743 | 3227.596 | 17373.795 | 17380.856 | 26.197 | 3835.357 | 21220.160 | 21792.138 |
| multi-inst-5x4i | 25.862 | 29.170 | 2539.262 | 11351.013 | 11352.431 | 4012.823 | 4035.640 | 15257.345 | 15369.184 |
| multi-inst-5x2ix2w-500 | 28.554 | 610.506 | 2952.528 | 14509.429 | 18363.472 | 2804.957 | 10258.548 | 14518.505 | 18375.589 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 65.982 | 54.418 | 11.564 | 0.073 |
| multi-5x4w-stag500 | 108.946 | 90.162 | 18.784 | 0.108 |
| multi-inst-5x4i | 190.719 | 156.442 | 34.277 | 0.410 |
| multi-inst-5x2ix2w-500 | 104.165 | 85.614 | 18.551 | 0.134 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 877939.709 |
| multi-5x4w-stag500 | 890973.730 |
| multi-inst-5x4i | 2667390.967 |
| multi-inst-5x2ix2w-500 | 1487708.408 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.936 | 0.000 | 0.903 | 0.253 | 12054.400 | 13222.473 |
| multi-5x4w-stag500 | sda | 1.243 | 0.000 | 1.107 | 0.242 | 14063.568 | 15262.811 |
| multi-inst-5x4i | sda | 1.721 | 0.000 | 0.866 | 0.417 | 25943.945 | 24042.204 |
| multi-inst-5x2ix2w-500 | sda | 0.975 | 0.000 | 0.982 | 0.282 | 13898.232 | 13907.356 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 770304.982 | 1340610.696 | 16.018 | 0.000 | 39.400 | 39.491 | 0.000 |
| multi-5x4w-stag500 | 731952.526 | 1291726.316 | 14.105 | 0.000 | 43.514 | 65.081 | 0.000 |
| multi-inst-5x4i | 731501.174 | 1338274.955 | 11.993 | 0.009 | 88.997 | 172.326 | 0.000 |
| multi-inst-5x2ix2w-500 | 764137.665 | 1312433.002 | 20.930 | 0.000 | 53.771 | 66.562 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 16.050 | 9.058 | 9.058 |
| multi-5x4w-stag500 | 20 | 16.000 | 4.744 | 4.744 |
| multi-inst-5x4i | 20 | 16.000 | 5.561 | 5.561 |
| multi-inst-5x2ix2w-500 | 19 | 16.158 | 4.185 | 4.185 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 27.552 | 93.500 | 10.792 |
| multi-5x4w-stag500 | 28.609 | 93.500 | 15.281 |
| multi-inst-5x4i | 16.284 | 93.570 | 8.099 |
| multi-inst-5x2ix2w-500 | 43.462 | 94.000 | 22.176 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 131.000 | 1.000 | 914220.000 | 50.000 | 9.600 | 40.000 | 5.740 | 22.000 | 936206.000 | 12.000 | 1484633.000 | 46.000 | 66.000 | 11.000 | 37.875 | 36.896 | 16.812 | 36.896 | 93.500 | 0.000 |
| multi-5x4w-stag500 | 151.000 | 25.000 | 968888.000 | 36.000 | 6.400 | 25.000 | 5.940 | 31.000 | 889589.000 | 32.000 | 1430881.000 | 32.000 | 67.000 | 25.000 | 87.688 | 27.701 | 46.500 | 27.701 | 93.500 | 0.000 |
| multi-inst-5x4i | 366.000 | 2.000 | 3197428.000 | 9.000 | 6.300 | 9.000 | 2.388 | 29.000 | 795603.750 | 28.000 | 1414507.500 | 31.000 | 29.500 | 20.000 | 64.500 | 18.743 | 31.750 | 18.743 | 93.625 | 18.594 |
| multi-inst-5x2ix2w-500 | 246.000 | 9.000 | 1926032.000 | 34.000 | 5.200 | 59.000 | 5.555 | 25.000 | 882413.500 | 37.000 | 1458338.000 | 32.000 | 50.500 | 38.000 | 83.688 | 36.857 | 43.875 | 18.379 | 94.000 | 0.000 |
