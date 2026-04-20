## `single-w` vs `single-r` vs `single-inst-w` vs `single-inst-r`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T134553Z_vps-docker-qwen3-235b8x2-single-20-worker | 1 | 20 | 20 | 0 |
| single-r | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T134840Z_vps-docker-qwen3-235b8x2-single-20-request | 1 | 20 | 20 | 0 |
| single-inst-w | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135628Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 4 | 20 | 20 | 0 |
| single-inst-r | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135839Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 4 | 20 | 20 | 0 |

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
| single-r | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T134840Z_vps-docker-qwen3-235b8x2-single-20-request | 2026-04-17T13:48:47.361040+00:00 | 2026-04-17T13:49:48.646869+00:00 | 61.286 | 2026-04-17T13:48:47.455688+00:00 | 2026-04-17T13:49:37.487368+00:00 | 50.032 |
| single-inst-w | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135628Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 2026-04-17T13:57:00.372979+00:00 | 2026-04-17T13:58:39.105337+00:00 | 98.732 | 2026-04-17T13:57:00.504245+00:00 | 2026-04-17T13:58:02.335545+00:00 | 61.831 |
| single-inst-r | /root/Zehao/ClawHarness/out/batch_run_4/task-01/20260417T135839Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 2026-04-17T13:59:11.448713+00:00 | 2026-04-17T14:00:11.042251+00:00 | 59.594 | 2026-04-17T13:59:11.609570+00:00 | 2026-04-17T13:59:37.032925+00:00 | 25.423 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 7557.113 | 5879.542 | 17114.873 | 25315.040 |
| single-r | 2501.542 | 1699.190 | 1782.849 | 17767.614 |
| single-inst-w | 10815.844 | 10905.986 | 15320.315 | 15943.851 |
| single-inst-r | 4971.895 | 2559.325 | 15257.345 | 15369.184 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 66.260 | 5.246 | 7351.774 | 200.053 | 7557.113 |
| single-r | 94.302 | 2.674 | 2297.358 | 201.473 | 2501.542 |
| single-inst-w | 1870.572 | 6.476 | 9992.334 | 816.997 | 10815.844 |
| single-inst-r | 155.378 | 6.966 | 4172.369 | 792.522 | 4971.895 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 17.613 | 21.751 | 5854.740 | 13277.397 | 25302.961 | 21.814 | 3832.924 | 17114.873 | 25315.040 |
| single-r | 8.306 | 17.617 | 1692.205 | 1776.343 | 13839.042 | 6.372 | 3924.486 | 1782.849 | 17767.614 |
| single-inst-w | 20.365 | 27.777 | 10790.197 | 13109.693 | 15935.016 | 4050.836 | 4177.976 | 15320.315 | 15943.851 |
| single-inst-r | 25.862 | 29.170 | 2539.262 | 11351.013 | 11352.431 | 4012.823 | 4035.640 | 15257.345 | 15369.184 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 29.461 | 23.623 | 5.838 | 0.032 |
| single-r | 65.982 | 54.418 | 11.564 | 0.073 |
| single-inst-w | 130.955 | 104.971 | 25.984 | 0.359 |
| single-inst-r | 190.719 | 156.442 | 34.277 | 0.410 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 694701.429 |
| single-r | 877939.709 |
| single-inst-w | 2532997.222 |
| single-inst-r | 2667390.967 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.449 | 0.006 | 0.356 | 0.054 | 4948.208 | 4905.273 |
| single-r | sda | 0.936 | 0.000 | 0.903 | 0.253 | 12054.400 | 13222.473 |
| single-inst-w | sda | 1.218 | 0.000 | 0.727 | 0.262 | 16702.848 | 16240.318 |
| single-inst-r | sda | 1.721 | 0.000 | 0.866 | 0.417 | 25943.945 | 24042.204 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 903929.619 | 1422375.006 | 34.748 | 0.013 | 33.838 | 17.883 | 0.000 |
| single-r | 770304.982 | 1340610.696 | 16.018 | 0.000 | 39.400 | 39.491 | 0.000 |
| single-inst-w | 771537.355 | 1341048.532 | 19.829 | 0.021 | 77.739 | 170.701 | 0.000 |
| single-inst-r | 731501.174 | 1338274.955 | 11.993 | 0.009 | 88.997 | 172.326 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 109.150 | 17.296 | 6.748 |
| single-r | 20 | 16.050 | 9.058 | 9.058 |
| single-inst-w | 20 | 80.800 | 8.173 | 4.688 |
| single-inst-r | 20 | 16.000 | 5.561 | 5.561 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 65.312 | 93.500 | 23.570 |
| single-r | 27.552 | 93.500 | 10.792 |
| single-inst-w | 43.089 | 93.530 | 22.930 |
| single-inst-r | 16.284 | 93.570 | 8.099 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 187.000 | 80.000 | 930912.000 | 67.000 | 10.400 | 44.000 | 2.940 | 85.000 | 1093995.000 | 96.000 | 1693588.000 | 96.000 | 72.000 | 13.000 | 92.812 | 57.516 | 31.000 | 57.516 | 93.500 | 0.000 |
| single-r | 131.000 | 1.000 | 914220.000 | 50.000 | 9.600 | 40.000 | 5.740 | 22.000 | 936206.000 | 12.000 | 1484633.000 | 46.000 | 66.000 | 11.000 | 37.875 | 36.896 | 16.812 | 36.896 | 93.500 | 0.000 |
| single-inst-w | 394.000 | 25.000 | 3199080.000 | 16.000 | 5.625 | 8.000 | 2.550 | 34.000 | 872182.250 | 62.000 | 1414440.250 | 5.000 | 54.500 | 62.000 | 95.500 | 75.276 | 52.562 | 48.601 | 93.625 | 47.736 |
| single-inst-r | 366.000 | 2.000 | 3197428.000 | 9.000 | 6.300 | 9.000 | 2.388 | 29.000 | 795603.750 | 28.000 | 1414507.500 | 31.000 | 29.500 | 20.000 | 64.500 | 18.743 | 31.750 | 18.743 | 93.625 | 18.594 |
