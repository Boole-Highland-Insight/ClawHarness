## `single-w` vs `single-r` vs `single-inst-w` vs `single-inst-r`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T190912Z_vps-docker-qwen3-235b8x2-single-20-worker | 1 | 20 | 20 | 0 |
| single-r | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T191122Z_vps-docker-qwen3-235b8x2-single-20-request | 1 | 20 | 20 | 0 |
| single-inst-w | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192337Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 4 | 20 | 20 | 0 |
| single-inst-r | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192959Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 4 | 20 | 20 | 0 |

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
| single-w | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T190912Z_vps-docker-qwen3-235b8x2-single-20-worker | 2026-04-16T19:09:21.355065+00:00 | 2026-04-16T19:11:22.784692+00:00 | 121.430 | 2026-04-16T19:09:51.967445+00:00 | 2026-04-16T19:11:08.564225+00:00 | 76.597 |
| single-r | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T191122Z_vps-docker-qwen3-235b8x2-single-20-request | 2026-04-16T19:11:32.744164+00:00 | 2026-04-16T19:13:35.127188+00:00 | 122.383 | 2026-04-16T19:11:32.820609+00:00 | 2026-04-16T19:13:20.476059+00:00 | 107.655 |
| single-inst-w | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192337Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 2026-04-16T19:24:11.177609+00:00 | 2026-04-16T19:29:59.042137+00:00 | 347.865 | 2026-04-16T19:24:11.261403+00:00 | 2026-04-16T19:29:08.677323+00:00 | 297.416 |
| single-inst-r | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192959Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 2026-04-16T19:30:34.477731+00:00 | 2026-04-16T19:32:38.411778+00:00 | 123.934 | 2026-04-16T19:30:34.562898+00:00 | 2026-04-16T19:31:39.354804+00:00 | 64.792 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 3829.793 | 2874.673 | 3741.048 | 21102.278 |
| single-r | 5382.726 | 4659.412 | 5324.246 | 18552.410 |
| single-inst-w | 23619.184 | 14316.568 | 20082.315 | 216020.342 |
| single-inst-r | 11038.935 | 8480.940 | 19634.753 | 37387.220 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 30612.099 | 3.397 | 3602.062 | 224.297 | 3829.793 |
| single-r | 76.176 | 5.688 | 5172.102 | 204.896 | 5382.726 |
| single-inst-w | 7123.832 | 8.777 | 22793.300 | 817.069 | 23619.184 |
| single-inst-r | 2535.749 | 8.023 | 10255.945 | 774.924 | 11038.935 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 4.355 | 22.625 | 2865.895 | 3733.289 | 16750.140 | 13.705 | 4347.731 | 3741.048 | 21102.278 |
| single-r | 11.023 | 22.391 | 4651.527 | 5313.565 | 14581.131 | 8.588 | 3966.402 | 5324.246 | 18552.410 |
| single-inst-w | 33.698 | 39.300 | 13259.776 | 17850.009 | 216012.715 | 3986.259 | 4486.557 | 20082.315 | 216020.342 |
| single-inst-r | 27.454 | 35.562 | 8472.471 | 15847.561 | 33515.782 | 3867.856 | 3944.455 | 19634.753 | 37387.220 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 52.063 | 43.288 | 8.775 | 0.054 |
| single-r | 34.961 | 27.631 | 7.330 | 0.089 |
| single-inst-w | 54.527 | 44.483 | 10.044 | 0.094 |
| single-inst-r | 160.992 | 134.327 | 26.665 | 0.250 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 736974.306 |
| single-r | 1015687.893 |
| single-inst-w | 2533051.226 |
| single-inst-r | 3227186.451 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.638 | 0.000 | 0.463 | 0.112 | 8238.270 | 7908.000 |
| single-r | sda | 0.640 | 0.000 | 0.399 | 0.075 | 6401.500 | 6402.683 |
| single-inst-w | sda | 0.547 | 0.028 | 0.364 | 0.108 | 8266.635 | 8901.214 |
| single-inst-r | sda | 1.564 | 0.150 | 0.824 | 0.350 | 24263.307 | 26942.268 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 787465.741 | 1351303.429 | 19.455 | 0.000 | 29.820 | 32.279 | 0.000 |
| single-r | 849986.522 | 1382521.115 | 30.991 | 0.000 | 31.515 | 34.070 | 0.000 |
| single-inst-w | 881236.899 | 1406911.023 | 35.188 | 0.004 | 38.660 | 47.428 | 0.000 |
| single-inst-r | 775969.573 | 1344737.595 | 21.852 | 0.017 | 74.776 | 124.097 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 39.500 | 13.336 | 6.843 |
| single-r | 20 | 16.150 | 3.342 | 3.342 |
| single-inst-w | 20 | 98.400 | 7.992 | 6.142 |
| single-inst-r | 20 | 16.850 | 1.932 | 1.932 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 33.557 | 92.000 | 12.161 |
| single-r | 57.344 | 92.000 | 20.052 |
| single-inst-w | 69.897 | 92.000 | 27.425 |
| single-inst-r | 43.668 | 92.000 | 21.392 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 178.000 | 37.000 | 965808.000 | 19.000 | 7.200 | 52.000 | 4.690 | 34.000 | 1027141.000 | 83.000 | 1712456.000 | 83.000 | 66.000 | 98.000 | 67.312 | 64.564 | 24.875 | 36.333 | 92.000 | 0.000 |
| single-r | 130.000 | 1.000 | 1103524.000 | 99.000 | 8.000 | 27.000 | 3.000 | 2.000 | 1086235.000 | 64.000 | 1740078.000 | 64.000 | 66.000 | 46.000 | 73.875 | 65.946 | 27.562 | 65.946 | 92.000 | 0.000 |
| single-inst-w | 489.000 | 1.000 | 4060164.000 | 35.000 | 8.350 | 0.000 | 2.130 | 9.000 | 1025223.500 | 223.000 | 1569370.250 | 223.000 | 64.750 | 280.000 | 96.000 | 67.642 | 52.500 | 49.179 | 92.000 | 0.000 |
| single-inst-r | 479.000 | 1.000 | 4042440.000 | 24.000 | 8.200 | 9.000 | 3.315 | 27.000 | 879478.750 | 63.000 | 1474842.500 | 86.000 | 58.250 | 46.000 | 91.188 | 66.390 | 48.688 | 37.198 | 92.000 | 0.000 |
