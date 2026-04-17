## `single-w` vs `multi-5x4w-stag500` vs `multi-inst-5x4i` vs `multi-inst-5x2ix2w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T094635Z_vps-docker-qwen3-235b8x2-single-20-request | 1 | 20 | 20 | 0 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T095802Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request | 1 | 20 | 20 | 0 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T100212Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 4 | 20 | 20 | 0 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T101101Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-request | 2 | 20 | 20 | 0 |

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
| single-w | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T094635Z_vps-docker-qwen3-235b8x2-single-20-request | 2026-04-17T09:46:42.364230+00:00 | 2026-04-17T09:48:51.772497+00:00 | 129.408 | 2026-04-17T09:46:42.435141+00:00 | 2026-04-17T09:48:39.649807+00:00 | 117.215 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T095802Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request | 2026-04-17T09:58:09.681480+00:00 | 2026-04-17T09:59:20.953831+00:00 | 71.272 | 2026-04-17T09:58:09.746683+00:00 | 2026-04-17T09:59:08.069477+00:00 | 58.323 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T100212Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 2026-04-17T10:02:44.051889+00:00 | 2026-04-17T10:04:13.964148+00:00 | 89.912 | 2026-04-17T10:02:44.170530+00:00 | 2026-04-17T10:03:44.251022+00:00 | 60.080 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T101101Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-request | 2026-04-17T10:11:17.022253+00:00 | 2026-04-17T10:12:37.944181+00:00 | 80.922 | 2026-04-17T10:11:17.090495+00:00 | 2026-04-17T10:12:22.294094+00:00 | 65.204 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 5860.686 | 4861.988 | 5158.431 | 24784.400 |
| multi-5x4w-stag500 | 10067.963 | 9249.640 | 12467.021 | 19433.761 |
| multi-inst-5x4i | 11248.847 | 9063.101 | 22376.036 | 23549.777 |
| multi-inst-5x2ix2w-500 | 11425.035 | 9535.048 | 21148.653 | 21372.811 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 70.545 | 3.430 | 5645.378 | 211.837 | 5860.686 |
| multi-5x4w-stag500 | 6041.591 | 5.625 | 9904.054 | 158.251 | 10067.963 |
| multi-inst-5x4i | 2124.389 | 10.538 | 10352.446 | 885.825 | 11248.847 |
| multi-inst-5x2ix2w-500 | 4147.438 | 8.831 | 10844.540 | 571.622 | 11425.035 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 7.147 | 18.233 | 4852.591 | 5151.154 | 20677.747 | 9.170 | 4102.638 | 5158.431 | 24784.400 |
| multi-5x4w-stag500 | 8.957 | 29.428 | 9240.930 | 12456.642 | 16416.381 | 15.963 | 3013.230 | 12467.021 | 19433.761 |
| multi-inst-5x4i | 34.375 | 46.589 | 9024.259 | 18123.244 | 18787.094 | 4455.489 | 4758.419 | 22376.036 | 23549.777 |
| multi-inst-5x2ix2w-500 | 44.726 | 54.977 | 9518.534 | 17769.506 | 20722.353 | 3598.227 | 4232.830 | 21148.653 | 21372.811 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 42.836 | 34.426 | 8.410 | 0.049 |
| multi-5x4w-stag500 | 55.875 | 45.828 | 10.047 | 0.062 |
| multi-inst-5x4i | 166.981 | 133.060 | 33.921 | 0.306 |
| multi-inst-5x2ix2w-500 | 93.446 | 75.797 | 17.649 | 0.162 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 818349.967 |
| multi-5x4w-stag500 | 925797.062 |
| multi-inst-5x4i | 2410097.082 |
| multi-inst-5x2ix2w-500 | 1250742.324 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.776 | 0.000 | 0.373 | 0.071 | 7244.656 | 7453.869 |
| multi-5x4w-stag500 | sda | 0.667 | 0.000 | 0.617 | 0.112 | 8156.875 | 7456.188 |
| multi-inst-5x4i | sda | 1.385 | 0.012 | 0.973 | 0.621 | 28898.168 | 31921.687 |
| multi-inst-5x2ix2w-500 | sda | 1.135 | 0.000 | 0.624 | 0.226 | 14096.027 | 11185.081 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 845172.902 | 1385974.894 | 29.220 | 0.024 | 32.041 | 26.402 | 0.000 |
| multi-5x4w-stag500 | 775116.108 | 1295361.923 | 25.631 | 0.000 | 35.156 | 35.406 | 0.000 |
| multi-inst-5x4i | 787868.630 | 1346129.848 | 24.822 | 0.009 | 109.616 | 145.437 | 0.000 |
| multi-inst-5x2ix2w-500 | 786730.662 | 1313561.339 | 27.489 | 0.013 | 61.324 | 82.973 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 16.500 | 3.267 | 3.267 |
| multi-5x4w-stag500 | 20 | 16.950 | 1.763 | 1.763 |
| multi-inst-5x4i | 20 | 16.900 | 1.760 | 1.760 |
| multi-inst-5x2ix2w-500 | 20 | 17.000 | 1.713 | 1.713 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 52.990 | 92.000 | 19.125 |
| multi-5x4w-stag500 | 62.125 | 92.000 | 32.366 |
| multi-inst-5x4i | 51.056 | 92.000 | 25.786 |
| multi-inst-5x2ix2w-500 | 62.258 | 92.000 | 32.375 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 147.000 | 98.000 | 959528.000 | 33.000 | 13.600 | 30.000 | 2.060 | 60.000 | 1026767.000 | 78.000 | 1586957.000 | 120.000 | 66.000 | 77.000 | 73.750 | 64.900 | 26.562 | 45.485 | 92.000 | 0.000 |
| multi-5x4w-stag500 | 156.000 | 32.000 | 975012.000 | 59.000 | 5.600 | 9.000 | 5.080 | 33.000 | 973963.000 | 35.000 | 1623638.000 | 35.000 | 99.000 | 51.000 | 87.000 | 37.151 | 48.375 | 37.151 | 92.000 | 0.000 |
| multi-inst-5x4i | 513.000 | 24.000 | 3405768.000 | 16.000 | 6.100 | 8.000 | 3.420 | 24.000 | 866540.500 | 61.000 | 1450004.250 | 16.000 | 54.500 | 56.000 | 92.062 | 66.309 | 48.625 | 66.309 | 92.000 | 0.000 |
| multi-inst-5x2ix2w-500 | 309.000 | 9.000 | 1743812.000 | 22.000 | 7.200 | 65.000 | 4.180 | 12.000 | 895636.500 | 28.000 | 1440547.000 | 28.000 | 63.500 | 22.000 | 91.062 | 27.998 | 47.938 | 27.998 | 92.000 | 0.000 |
