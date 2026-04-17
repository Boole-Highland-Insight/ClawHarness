## `single-w` vs `single-r` vs `single-inst-w` vs `single-inst-r`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T094403Z_vps-docker-qwen3-235b8x2-single-20-worker | 1 | 20 | 20 | 0 |
| single-r | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T094635Z_vps-docker-qwen3-235b8x2-single-20-request | 1 | 20 | 20 | 0 |
| single-inst-w | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T095921Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 4 | 20 | 20 | 0 |
| single-inst-r | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T100212Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 4 | 20 | 20 | 0 |

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
| single-w | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T094403Z_vps-docker-qwen3-235b8x2-single-20-worker | 2026-04-17T09:44:12.057519+00:00 | 2026-04-17T09:46:35.017522+00:00 | 142.960 | 2026-04-17T09:44:19.271621+00:00 | 2026-04-17T09:46:28.550811+00:00 | 129.279 |
| single-r | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T094635Z_vps-docker-qwen3-235b8x2-single-20-request | 2026-04-17T09:46:42.364230+00:00 | 2026-04-17T09:48:51.772497+00:00 | 129.408 | 2026-04-17T09:46:42.435141+00:00 | 2026-04-17T09:48:39.649807+00:00 | 117.215 |
| single-inst-w | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T095921Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 2026-04-17T09:59:53.069073+00:00 | 2026-04-17T10:02:12.155674+00:00 | 139.087 | 2026-04-17T09:59:53.230402+00:00 | 2026-04-17T10:01:32.701214+00:00 | 99.471 |
| single-inst-r | /root/Zehao/ClawHarness/out/batch_run_3/task-01/20260417T100212Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 2026-04-17T10:02:44.051889+00:00 | 2026-04-17T10:04:13.964148+00:00 | 89.912 | 2026-04-17T10:02:44.170530+00:00 | 2026-04-17T10:03:44.251022+00:00 | 60.080 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 6463.907 | 4960.111 | 19077.865 | 27671.770 |
| single-r | 5860.686 | 4861.988 | 5158.431 | 24784.400 |
| single-inst-w | 16953.204 | 14750.209 | 29105.079 | 44384.492 |
| single-inst-r | 11248.847 | 9063.101 | 22376.036 | 23549.777 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 7213.745 | 4.949 | 6251.778 | 207.136 | 6463.907 |
| single-r | 70.545 | 3.430 | 5645.378 | 211.837 | 5860.686 |
| single-inst-w | 155.630 | 9.290 | 16072.201 | 871.674 | 16953.204 |
| single-inst-r | 2124.389 | 10.538 | 10352.446 | 885.825 | 11248.847 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 12.813 | 17.486 | 4932.883 | 15093.321 | 27660.346 | 22.146 | 3979.985 | 19077.865 | 27671.770 |
| single-r | 7.147 | 18.233 | 4852.591 | 5151.154 | 20677.747 | 9.170 | 4102.638 | 5158.431 | 24784.400 |
| single-inst-w | 31.824 | 33.747 | 14677.987 | 29097.284 | 44372.283 | 4190.817 | 4823.283 | 29105.079 | 44384.492 |
| single-inst-r | 34.375 | 46.589 | 9024.259 | 18123.244 | 18787.094 | 4455.489 | 4758.419 | 22376.036 | 23549.777 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 36.085 | 29.213 | 6.872 | 0.142 |
| single-r | 42.836 | 34.426 | 8.410 | 0.049 |
| single-inst-w | 104.186 | 84.647 | 19.539 | 0.271 |
| single-inst-r | 166.981 | 133.060 | 33.921 | 0.306 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 698423.830 |
| single-r | 818349.967 |
| single-inst-w | 2348106.970 |
| single-inst-r | 2410097.082 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.598 | 0.000 | 0.323 | 0.051 | 6219.291 | 6262.610 |
| single-r | sda | 0.776 | 0.000 | 0.373 | 0.071 | 7244.656 | 7453.869 |
| single-inst-w | sda | 1.133 | 0.016 | 0.646 | 0.362 | 20175.376 | 20503.219 |
| single-inst-r | sda | 1.385 | 0.012 | 0.973 | 0.621 | 28898.168 | 31921.687 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 881022.000 | 1410798.345 | 28.261 | 0.007 | 32.929 | 68.404 | 0.000 |
| single-r | 845172.902 | 1385974.894 | 29.220 | 0.024 | 32.041 | 26.402 | 0.000 |
| single-inst-w | 808216.391 | 1355873.085 | 25.125 | 0.008 | 77.919 | 120.578 | 0.000 |
| single-inst-r | 787868.630 | 1346129.848 | 24.822 | 0.009 | 109.616 | 145.437 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 80.800 | 15.747 | 9.408 |
| single-r | 20 | 16.500 | 3.267 | 3.267 |
| single-inst-w | 20 | 91.150 | 6.942 | 4.717 |
| single-inst-r | 20 | 16.900 | 1.760 | 1.760 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 59.083 | 92.000 | 21.358 |
| single-r | 52.990 | 92.000 | 19.125 |
| single-inst-w | 61.524 | 92.000 | 30.849 |
| single-inst-r | 51.056 | 92.000 | 25.786 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 210.000 | 131.000 | 934328.000 | 65.000 | 10.400 | 90.000 | 2.260 | 4.000 | 1082605.000 | 30.000 | 1662831.000 | 30.000 | 69.000 | 69.000 | 89.500 | 74.426 | 31.375 | 64.999 | 92.000 | 0.000 |
| single-r | 147.000 | 98.000 | 959528.000 | 33.000 | 13.600 | 30.000 | 2.060 | 60.000 | 1026767.000 | 78.000 | 1586957.000 | 120.000 | 66.000 | 77.000 | 73.750 | 64.900 | 26.562 | 45.485 | 92.000 | 0.000 |
| single-inst-w | 470.000 | 2.000 | 3370684.000 | 15.000 | 7.200 | 5.000 | 2.138 | 16.000 | 926861.000 | 97.000 | 1506629.750 | 109.000 | 51.750 | 59.000 | 96.188 | 66.622 | 52.500 | 66.622 | 92.000 | 0.000 |
| single-inst-r | 513.000 | 24.000 | 3405768.000 | 16.000 | 6.100 | 8.000 | 3.420 | 24.000 | 866540.500 | 61.000 | 1450004.250 | 16.000 | 54.500 | 56.000 | 92.062 | 66.309 | 48.625 | 66.309 | 92.000 | 0.000 |
