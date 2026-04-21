## `multi-25x4w-500` vs `25x2ix2w-300` vs `multi-25x1dx4ix1w-500` vs `multi-25x2dx2ix1w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| multi-25x4w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T131723Z_vps-docker-qwen3-235b-multi-25x4w-stag500-worker | 1 | 100 | 100 | 0 |
| 25x2ix2w-300 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T135500Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag300-worker | 2 | 100 | 100 | 0 |
| multi-25x1dx4ix1w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T153103Z_vps-docker-qwen3-235b-multi-inst-25x1dx4ix1w-stag500-worker | 1 | 100 | 100 | 0 |
| multi-25x2dx2ix1w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T144926Z_vps-docker-qwen3-235b-multi-inst-25x2dx2ix1w-stag500-worker | 2 | 100 | 100 | 0 |

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
| multi-25x4w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T131723Z_vps-docker-qwen3-235b-multi-25x4w-stag500-worker | 2026-04-20T13:17:32.152036+00:00 | 2026-04-20T13:25:32.847096+00:00 | 480.695 | 2026-04-20T13:17:32.222626+00:00 | 2026-04-20T13:25:19.059390+00:00 | 466.837 |
| 25x2ix2w-300 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T135500Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag300-worker | 2026-04-20T13:55:15.952829+00:00 | 2026-04-20T14:01:25.010506+00:00 | 369.058 | 2026-04-20T13:55:16.023138+00:00 | 2026-04-20T14:01:02.293645+00:00 | 346.271 |
| multi-25x1dx4ix1w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T153103Z_vps-docker-qwen3-235b-multi-inst-25x1dx4ix1w-stag500-worker | 2026-04-20T15:31:12.180525+00:00 | 2026-04-20T15:40:57.872852+00:00 | 585.692 | 2026-04-20T15:31:13.248357+00:00 | 2026-04-20T15:40:30.400265+00:00 | 557.152 |
| multi-25x2dx2ix1w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T144926Z_vps-docker-qwen3-235b-multi-inst-25x2dx2ix1w-stag500-worker | 2026-04-20T14:49:42.870884+00:00 | 2026-04-20T14:55:53.047390+00:00 | 370.177 | 2026-04-20T14:49:42.940011+00:00 | 2026-04-20T14:55:21.120355+00:00 | 338.180 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| multi-25x4w-500 | 15793.655 | 14126.145 | 19222.430 | 40556.523 |
| 25x2ix2w-300 | 10585.110 | 8269.535 | 19529.335 | 43253.250 |
| multi-25x1dx4ix1w-500 | 14649.957 | 12456.189 | 34271.329 | 47058.792 |
| multi-25x2dx2ix1w-500 | 12696.395 | 12318.753 | 15518.988 | 27211.727 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| multi-25x4w-500 | 898.628 | 8.495 | 15743.316 | 41.806 | 15793.655 |
| 25x2ix2w-300 | 4030.526 | 12.014 | 10443.978 | 129.082 | 10585.110 |
| multi-25x1dx4ix1w-500 | 5649.086 | 4.581 | 14463.244 | 182.092 | 14649.957 |
| multi-25x2dx2ix1w-500 | 2311.869 | 4.329 | 12508.649 | 183.377 | 12696.395 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multi-25x4w-500 | 23.974 | 56.965 | 14114.849 | 19210.958 | 40541.727 | 16.970 | 33.874 | 19222.430 | 40556.523 |
| 25x2ix2w-300 | 37.879 | 263.395 | 8259.421 | 18498.190 | 43240.202 | 18.018 | 3834.907 | 19529.335 | 43253.250 |
| multi-25x1dx4ix1w-500 | 13.643 | 40.919 | 12446.958 | 34261.942 | 47041.983 | 22.523 | 4289.627 | 34271.329 | 47058.792 |
| multi-25x2dx2ix1w-500 | 10.526 | 31.706 | 12285.103 | 15217.580 | 22792.475 | 17.965 | 4413.615 | 15518.988 | 27211.727 |

**System CPU Table**

| scenario | benchmark_pct_cpu_total | benchmark_pct_cpu_usr | benchmark_pct_cpu_system | benchmark_pct_cpu_wait | system_cpu_user_pct | system_cpu_system_pct | system_cpu_iowait_pct | system_cpu_idle_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multi-25x4w-500 | 28.929 | 22.785 | 6.145 | 0.032 | 8.817 | 8.664 | 0.000 | 82.562 |
| 25x2ix2w-300 | 47.117 | 37.483 | 9.634 | 0.058 | 8.560 | 8.394 | 0.000 | 83.064 |
| multi-25x1dx4ix1w-500 | 47.836 | - | - | - | 8.875 | 9.654 | 0.000 | 81.473 |
| multi-25x2dx2ix1w-500 | 76.842 | - | - | - | 8.731 | 7.936 | 0.000 | 83.402 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| multi-25x4w-500 | 752520.502 |
| 25x2ix2w-300 | 1208486.515 |
| multi-25x1dx4ix1w-500 | 2009671.477 |
| multi-25x2dx2ix1w-500 | 2230756.284 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| multi-25x4w-500 | sda | 0.468 | 0.003 | 0.472 | 0.053 | 4451.498 | 4323.413 |
| 25x2ix2w-300 | sda | 0.644 | 0.003 | 0.465 | 0.094 | 6911.128 | 6676.697 |
| multi-25x1dx4ix1w-500 | sda | 0.487 | 0.000 | 0.428 | 0.088 | 5700.329 | 2357.017 |
| multi-25x2dx2ix1w-500 | sda | 0.829 | 0.010 | 0.592 | 0.143 | 9302.209 | 3527.293 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| multi-25x4w-500 | 821966.960 | 1316656.806 | 32.304 | 0.002 | 29.161 | 17.327 | 0.000 |
| 25x2ix2w-300 | 817087.835 | 1321615.663 | 30.873 | 0.003 | 50.442 | 30.807 | 0.000 |
| multi-25x1dx4ix1w-500 | 842955.488 | 1337455.441 | 33.129 | 0.009 | - | - | - |
| multi-25x2dx2ix1w-500 | 803880.982 | 1306945.387 | 30.880 | 0.000 | - | - | - |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| multi-25x4w-500 | 100 | 144.120 | 10.210 | 5.862 |
| 25x2ix2w-300 | 100 | 87.950 | 9.032 | 4.856 |
| multi-25x1dx4ix1w-500 | 0 | 0.000 | 0.000 | 0.000 |
| multi-25x2dx2ix1w-500 | 0 | 0.000 | 0.000 | 0.000 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| multi-25x4w-500 | 87.409 | 95.000 | 44.374 |
| 25x2ix2w-300 | 82.779 | 95.000 | 41.784 |
| multi-25x1dx4ix1w-500 | 87.436 | 96.929 | 40.951 |
| multi-25x2dx2ix1w-500 | 83.686 | 96.000 | 44.028 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multi-25x4w-500 | 168.000 | 129.000 | 952960.000 | 229.000 | 10.800 | 54.000 | 5.230 | 3.000 | 1053689.000 | 432.000 | 1654277.000 | 432.000 | 72.000 | 157.000 | 96.375 | 375.020 | 53.125 | 121.326 | 95.000 | 0.000 |
| 25x2ix2w-300 | 321.000 | 89.000 | 1742364.000 | 22.000 | 5.600 | 36.000 | 3.420 | 12.000 | 984411.000 | 336.000 | 1552910.500 | 266.000 | 67.000 | 179.000 | 97.000 | 65.363 | 53.250 | 65.363 | 95.000 | 0.000 |
| multi-25x1dx4ix1w-500 | 494.880 | 10.115 | 3770679.296 | 22.776 | 12.800 | 12.000 | 4.790 | 13.000 | 1114377.000 | 389.000 | 1787602.000 | 389.000 | 72.000 | 388.000 | 96.688 | 253.384 | 52.375 | 37.372 | 97.000 | 112.938 |
| multi-25x2dx2ix1w-500 | 324.650 | 0.000 | 2884632.576 | 0.000 | 12.800 | 36.000 | 9.660 | 29.000 | 915567.000 | 119.000 | 1503106.000 | 119.000 | 65.000 | 53.000 | 96.250 | 180.598 | 52.562 | 86.478 | 96.000 | 0.000 |
