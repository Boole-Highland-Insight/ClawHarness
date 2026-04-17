## `single-w` vs `multi-5x4w-stag500` vs `multi-inst-5x4i` vs `multi-inst-5x2ix2w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-w | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T190912Z_vps-docker-qwen3-235b8x2-single-20-worker | 1 | 20 | 20 | 0 |
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192006Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-worker | 1 | 20 | 20 | 0 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192337Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 4 | 20 | 20 | 0 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T193634Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-worker | 2 | 20 | 20 | 0 |

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
| multi-5x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192006Z_vps-docker-qwen3-235b8x2-multi-5x4w-stag500-worker | 2026-04-16T19:20:14.994463+00:00 | 2026-04-16T19:22:09.410353+00:00 | 114.416 | 2026-04-16T19:20:15.065341+00:00 | 2026-04-16T19:22:00.442789+00:00 | 105.377 |
| multi-inst-5x4i | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T192337Z_vps-docker-qwen3-235b8x2-single-inst-5x4i-worker | 2026-04-16T19:24:11.177609+00:00 | 2026-04-16T19:29:59.042137+00:00 | 347.865 | 2026-04-16T19:24:11.261403+00:00 | 2026-04-16T19:29:08.677323+00:00 | 297.416 |
| multi-inst-5x2ix2w-500 | /root/Zehao/ClawHarness/out/batch_run_2/task-01/20260416T193634Z_vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-worker | 2026-04-16T19:36:52.239739+00:00 | 2026-04-16T19:38:03.783395+00:00 | 71.544 | 2026-04-16T19:37:01.070022+00:00 | 2026-04-16T19:37:49.555006+00:00 | 48.485 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-w | 3829.793 | 2874.673 | 3741.048 | 21102.278 |
| multi-5x4w-stag500 | 16145.761 | 15351.649 | 20348.885 | 34730.049 |
| multi-inst-5x4i | 23619.184 | 14316.568 | 20082.315 | 216020.342 |
| multi-inst-5x2ix2w-500 | 8134.148 | 7631.887 | 17116.938 | 18439.092 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-w | 30612.099 | 3.397 | 3602.062 | 224.297 | 3829.793 |
| multi-5x4w-stag500 | 13417.075 | 21.579 | 15956.947 | 167.194 | 16145.761 |
| multi-inst-5x4i | 7123.832 | 8.777 | 22793.300 | 817.069 | 23619.184 |
| multi-inst-5x2ix2w-500 | 12441.406 | 93.587 | 7104.392 | 936.131 | 8134.148 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 4.355 | 22.625 | 2865.895 | 3733.289 | 16750.140 | 13.705 | 4347.731 | 3741.048 | 21102.278 |
| multi-5x4w-stag500 | 52.226 | 261.887 | 15336.905 | 20079.978 | 31720.558 | 76.778 | 3005.485 | 20348.885 | 34730.049 |
| multi-inst-5x4i | 33.698 | 39.300 | 13259.776 | 17850.009 | 216012.715 | 3986.259 | 4486.557 | 20082.315 | 216020.342 |
| multi-inst-5x2ix2w-500 | 688.190 | 701.276 | 6243.141 | 17103.185 | 18426.505 | 9275.135 | 9281.194 | 17116.938 | 18439.092 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-w | 52.063 | 43.288 | 8.775 | 0.054 |
| multi-5x4w-stag500 | 52.427 | 42.482 | 9.945 | 0.136 |
| multi-inst-5x4i | 54.527 | 44.483 | 10.044 | 0.094 |
| multi-inst-5x2ix2w-500 | 124.797 | 105.145 | 19.652 | 0.449 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-w | 736974.306 |
| multi-5x4w-stag500 | 1001194.618 |
| multi-inst-5x4i | 2533051.226 |
| multi-inst-5x2ix2w-500 | 1839959.826 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | sda | 0.638 | 0.000 | 0.463 | 0.112 | 8238.270 | 7908.000 |
| multi-5x4w-stag500 | sda | 0.718 | 0.000 | 0.595 | 0.114 | 8257.273 | 8448.800 |
| multi-inst-5x4i | sda | 0.547 | 0.028 | 0.364 | 0.108 | 8266.635 | 8901.214 |
| multi-inst-5x2ix2w-500 | sda | 1.362 | 0.058 | 0.935 | 0.344 | 21003.101 | 21372.522 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 787465.741 | 1351303.429 | 19.455 | 0.000 | 29.820 | 32.279 | 0.000 |
| multi-5x4w-stag500 | 786040.730 | 1305552.270 | 25.459 | 0.009 | 30.582 | 56.709 | 0.000 |
| multi-inst-5x4i | 881236.899 | 1406911.023 | 35.188 | 0.004 | 38.660 | 47.428 | 0.000 |
| multi-inst-5x2ix2w-500 | 764543.071 | 1313773.586 | 22.293 | 0.014 | 50.928 | 194.391 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-w | 20 | 39.500 | 13.336 | 6.843 |
| multi-5x4w-stag500 | 20 | 127.400 | 8.643 | 5.092 |
| multi-inst-5x4i | 20 | 98.400 | 7.992 | 6.142 |
| multi-inst-5x2ix2w-500 | 20 | 46.450 | 22.433 | 19.106 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-w | 33.557 | 92.000 | 12.161 |
| multi-5x4w-stag500 | 65.427 | 92.000 | 34.385 |
| multi-inst-5x4i | 69.897 | 92.000 | 27.425 |
| multi-inst-5x2ix2w-500 | 47.866 | 92.000 | 24.241 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-w | 178.000 | 37.000 | 965808.000 | 19.000 | 7.200 | 52.000 | 4.690 | 34.000 | 1027141.000 | 83.000 | 1712456.000 | 83.000 | 66.000 | 98.000 | 67.312 | 64.564 | 24.875 | 36.333 | 92.000 | 0.000 |
| multi-5x4w-stag500 | 129.000 | 1.000 | 1092216.000 | 100.000 | 15.600 | 33.000 | 5.410 | 39.000 | 984179.000 | 106.000 | 1665592.000 | 22.000 | 68.000 | 64.000 | 95.750 | 91.905 | 52.188 | 54.734 | 92.000 | 0.000 |
| multi-inst-5x4i | 489.000 | 1.000 | 4060164.000 | 35.000 | 8.350 | 0.000 | 2.130 | 9.000 | 1025223.500 | 223.000 | 1569370.250 | 223.000 | 64.750 | 280.000 | 96.000 | 67.642 | 52.500 | 49.179 | 92.000 | 0.000 |
| multi-inst-5x2ix2w-500 | 244.000 | 19.000 | 2099580.000 | 33.000 | 6.200 | 14.000 | 3.695 | 31.000 | 911767.500 | 58.000 | 1456434.500 | 45.000 | 59.500 | 45.000 | 92.500 | 50.250 | 50.875 | 50.250 | 92.000 | 0.000 |
