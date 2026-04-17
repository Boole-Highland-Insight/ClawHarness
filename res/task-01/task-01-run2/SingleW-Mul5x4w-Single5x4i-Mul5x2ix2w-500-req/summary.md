## `single-w` vs `multi-5x4w-stag500` vs `multi-inst-5x4i` vs `multi-inst-5x2ix2w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T191122Z_vps-docker-qwen3-235b8x2-single-20-request | 1 | 20 | 20 | 0 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192209Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request | 1 | 20 | 20 | 0 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192959Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 4 | 20 | 20 | 0 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T193804Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-request | 2 | 20 | 20 | 0 |

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
| single-w | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T191122Z_vps-docker-qwen3-235b8x2-single-20-request | 2026-04-16T19:11:32.744164+00:00 | 2026-04-16T19:13:35.127188+00:00 | 122.383 | 2026-04-16T19:11:32.820609+00:00 | 2026-04-16T19:13:20.476059+00:00 | 107.655 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192209Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request | 2026-04-16T19:22:19.067103+00:00 | 2026-04-16T19:23:37.597116+00:00 | 78.530 | 2026-04-16T19:22:35.411254+00:00 | 2026-04-16T19:23:30.284609+00:00 | 54.873 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192959Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-request | 2026-04-16T19:30:34.477731+00:00 | 2026-04-16T19:32:38.411778+00:00 | 123.934 | 2026-04-16T19:30:34.562898+00:00 | 2026-04-16T19:31:39.354804+00:00 | 64.792 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T193804Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-request | 2026-04-16T19:38:20.617239+00:00 | 2026-04-16T19:39:48.351054+00:00 | 87.734 | 2026-04-16T19:38:20.683769+00:00 | 2026-04-16T19:39:34.874600+00:00 | 74.191 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 5382.726 | 4659.412 | 5324.246 | 18552.410 |
| multi-5x4w-stag500 | 10380.260 | 9172.508 | 19902.753 | 20081.845 |
| multi-inst-5x4i | 11038.935 | 8480.940 | 19634.753 | 37387.220 |
| multi-inst-5x2ix2w-500 | 11870.157 | 8973.713 | 20555.677 | 38120.917 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 76.176 | 5.688 | 5172.102 | 204.896 | 5382.726 |
| multi-5x4w-stag500 | 15635.413 | 31.763 | 9474.687 | 873.770 | 10380.260 |
| multi-inst-5x4i | 2535.749 | 8.023 | 10255.945 | 774.924 | 11038.935 |
| multi-inst-5x2ix2w-500 | 9324.409 | 11.245 | 11112.151 | 746.727 | 11870.157 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 11.023 | 22.391 | 4651.527 | 5313.565 | 14581.131 | 8.588 | 3966.402 | 5324.246 | 18552.410 |
| multi-5x4w-stag500 | 149.812 | 207.624 | 9145.180 | 19874.123 | 19915.018 | 8620.867 | 8622.728 | 19902.753 | 20081.845 |
| multi-inst-5x4i | 27.454 | 35.562 | 8472.471 | 15847.561 | 33515.782 | 3867.856 | 3944.455 | 19634.753 | 37387.220 |
| multi-inst-5x2ix2w-500 | 37.475 | 43.133 | 8923.419 | 17165.637 | 34142.645 | 3973.701 | 4013.136 | 20555.677 | 38120.917 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 34.961 | 27.631 | 7.330 | 0.089 |
| multi-5x4w-stag500 | 71.959 | 61.068 | 10.892 | 0.122 |
| multi-inst-5x4i | 160.992 | 134.327 | 26.665 | 0.250 |
| multi-inst-5x2ix2w-500 | 116.275 | 97.682 | 18.593 | 0.394 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 1015687.893 |
| multi-5x4w-stag500 | 801675.135 |
| multi-inst-5x4i | 3227186.451 |
| multi-inst-5x2ix2w-500 | 1723885.376 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.640 | 0.000 | 0.399 | 0.075 | 6401.500 | 6402.683 |
| multi-5x4w-stag500 | sda | 0.927 | 0.000 | 0.602 | 0.151 | 11338.270 | 11251.622 |
| multi-inst-5x4i | sda | 1.564 | 0.150 | 0.824 | 0.350 | 24263.307 | 26942.268 |
| multi-inst-5x2ix2w-500 | sda | 1.463 | 0.030 | 0.780 | 0.203 | 18314.672 | 18468.254 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 849986.522 | 1382521.115 | 30.991 | 0.000 | 31.515 | 34.070 | 0.000 |
| multi-5x4w-stag500 | 751041.573 | 1290073.813 | 25.173 | 0.027 | 40.824 | 53.378 | 0.000 |
| multi-inst-5x4i | 775969.573 | 1344737.595 | 21.852 | 0.017 | 74.776 | 124.097 | 0.000 |
| multi-inst-5x2ix2w-500 | 771396.615 | 1312154.121 | 23.687 | 0.006 | 58.995 | 170.330 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 16.150 | 3.342 | 3.342 |
| multi-5x4w-stag500 | 18 | 16.778 | 1.722 | 1.722 |
| multi-inst-5x4i | 20 | 16.850 | 1.932 | 1.932 |
| multi-inst-5x2ix2w-500 | 20 | 16.500 | 1.714 | 1.714 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 57.344 | 92.000 | 20.052 |
| multi-5x4w-stag500 | 49.016 | 92.000 | 26.352 |
| multi-inst-5x4i | 43.668 | 92.000 | 21.392 |
| multi-inst-5x2ix2w-500 | 53.997 | 92.000 | 27.587 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 130.000 | 1.000 | 1103524.000 | 99.000 | 8.000 | 27.000 | 3.000 | 2.000 | 1086235.000 | 64.000 | 1740078.000 | 64.000 | 66.000 | 46.000 | 73.875 | 65.946 | 27.562 | 65.946 | 92.000 | 0.000 |
| multi-5x4w-stag500 | 177.000 | 38.000 | 1011980.000 | 33.000 | 11.600 | 7.000 | 5.470 | 19.000 | 862663.000 | 23.000 | 1654555.000 | 23.000 | 92.000 | 28.000 | 86.875 | 55.021 | 47.688 | 55.021 | 92.000 | 0.000 |
| multi-inst-5x4i | 479.000 | 1.000 | 4042440.000 | 24.000 | 8.200 | 9.000 | 3.315 | 27.000 | 879478.750 | 63.000 | 1474842.500 | 86.000 | 58.250 | 46.000 | 91.188 | 66.390 | 48.688 | 37.198 | 92.000 | 0.000 |
| multi-inst-5x2ix2w-500 | 343.000 | 48.000 | 2030104.000 | 33.000 | 10.400 | 36.000 | 3.515 | 12.000 | 881682.500 | 30.000 | 1501874.000 | 81.000 | 68.500 | 32.000 | 90.125 | 27.433 | 47.438 | 27.433 | 92.000 | 0.000 |
