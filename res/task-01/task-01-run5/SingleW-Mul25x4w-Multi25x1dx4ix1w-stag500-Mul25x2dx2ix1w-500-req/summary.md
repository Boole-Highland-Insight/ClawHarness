## `single-q` vs `multi-25x4w-stag500` vs `multi-inst-25x1dx4ix1w-stag500` vs `multi-inst-25x2dx2ix1w-500`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-q | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T124419Z_vps-docker-qwen3-235b-single-100-request | 1 | 100 | 100 | 0 |
| multi-25x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T132533Z_vps-docker-qwen3-235b-multi-25x4w-stag500-request | 1 | 100 | 100 | 0 |
| multi-inst-25x1dx4ix1w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T154058Z_vps-docker-qwen3-235b-multi-inst-25x1dx4ix1w-stag500-request | 1 | 100 | 100 | 0 |
| multi-inst-25x2dx2ix1w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T145553Z_vps-docker-qwen3-235b-multi-inst-25x2dx2ix1w-stag500-request | 2 | 100 | 100 | 0 |

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
| single-q | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T124419Z_vps-docker-qwen3-235b-single-100-request | 2026-04-20T12:44:27.799062+00:00 | 2026-04-20T12:53:13.276954+00:00 | 525.478 | 2026-04-20T12:44:27.865302+00:00 | 2026-04-20T12:53:09.539178+00:00 | 521.674 |
| multi-25x4w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T132533Z_vps-docker-qwen3-235b-multi-25x4w-stag500-request | 2026-04-20T13:25:41.795349+00:00 | 2026-04-20T13:30:10.959344+00:00 | 269.164 | 2026-04-20T13:25:49.265092+00:00 | 2026-04-20T13:29:58.331433+00:00 | 249.066 |
| multi-inst-25x1dx4ix1w-stag500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T154058Z_vps-docker-qwen3-235b-multi-inst-25x1dx4ix1w-stag500-request | 2026-04-20T15:41:07.232786+00:00 | 2026-04-20T15:46:05.376928+00:00 | 298.144 | 2026-04-20T15:41:07.796681+00:00 | 2026-04-20T15:45:36.412029+00:00 | 268.615 |
| multi-inst-25x2dx2ix1w-500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T145553Z_vps-docker-qwen3-235b-multi-inst-25x2dx2ix1w-stag500-request | 2026-04-20T14:56:09.723427+00:00 | 2026-04-20T15:01:08.152652+00:00 | 298.429 | 2026-04-20T14:56:09.797846+00:00 | 2026-04-20T15:00:48.923640+00:00 | 279.126 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-q | 5216.692 | 5048.535 | 5551.443 | 5732.552 |
| multi-25x4w-stag500 | 9819.878 | 9417.068 | 11295.614 | 21724.197 |
| multi-inst-25x1dx4ix1w-stag500 | 8591.464 | 9938.590 | 16300.769 | 23824.061 |
| multi-inst-25x2dx2ix1w-500 | 7234.692 | 8391.302 | 13951.057 | 22866.213 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-q | 65.913 | 10.157 | 5154.916 | 51.582 | 5216.692 |
| multi-25x4w-stag500 | 6780.303 | 19.943 | 9591.069 | 208.826 | 9819.878 |
| multi-inst-25x1dx4ix1w-stag500 | 5827.732 | 4.673 | 8402.169 | 184.586 | 8591.464 |
| multi-inst-25x2dx2ix1w-500 | 2025.713 | 5.463 | 7053.261 | 175.931 | 7234.692 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-q | 28.701 | 32.891 | 5031.352 | 5542.047 | 5705.789 | 17.145 | 23.607 | 5551.443 | 5732.552 |
| multi-25x4w-stag500 | 42.924 | 225.228 | 9381.231 | 11281.706 | 21695.922 | 26.114 | 9692.420 | 11295.614 | 21724.197 |
| multi-inst-25x1dx4ix1w-stag500 | 11.789 | 31.596 | 9912.587 | 16266.343 | 19355.974 | 17.002 | 4493.744 | 16300.769 | 23824.061 |
| multi-inst-25x2dx2ix1w-500 | 17.735 | 32.121 | 8367.615 | 13520.877 | 18555.308 | 19.587 | 4286.695 | 13951.057 | 22866.213 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_usr | pct_cpu_system | pct_cpu_wait |
| --- | --- | --- | --- | --- |
| single-q | 29.739 | 23.827 | 5.912 | 0.046 |
| multi-25x4w-stag500 | 53.938 | 43.379 | 10.559 | 0.146 |
| multi-inst-25x1dx4ix1w-stag500 | 96.339 | - | - | - |
| multi-inst-25x2dx2ix1w-500 | 74.529 | - | - | - |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-q | 801357.739 |
| multi-25x4w-stag500 | 1008802.330 |
| multi-inst-25x1dx4ix1w-stag500 | 2265659.143 |
| multi-inst-25x2dx2ix1w-500 | 2297561.055 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-q | sda | 0.606 | 0.006 | 0.475 | 0.046 | 4538.347 | 4445.465 |
| multi-25x4w-stag500 | sda | 0.910 | 0.000 | 0.747 | 0.144 | 8679.264 | 8779.893 |
| multi-inst-25x1dx4ix1w-stag500 | sda | 0.972 | 0.007 | 0.738 | 0.200 | 11186.673 | 5533.060 |
| multi-inst-25x2dx2ix1w-500 | sda | 0.937 | 0.007 | 0.709 | 0.215 | 11224.913 | 9748.681 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-q | 857937.178 | 1381653.107 | 30.688 | 0.004 | 33.463 | 23.732 | 0.000 |
| multi-25x4w-stag500 | 782008.307 | 1282399.421 | 29.575 | 0.011 | 42.900 | 55.374 | 0.000 |
| multi-inst-25x1dx4ix1w-stag500 | 804660.627 | 1299132.889 | 32.790 | 0.004 | - | - | - |
| multi-inst-25x2dx2ix1w-500 | 813312.134 | 1318569.475 | 31.561 | 0.005 | - | - | - |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-q | 100 | 16.760 | 3.293 | 3.293 |
| multi-25x4w-stag500 | 98 | 16.541 | 1.721 | 1.721 |
| multi-inst-25x1dx4ix1w-stag500 | 0 | 0.000 | 0.000 | 0.000 |
| multi-inst-25x2dx2ix1w-500 | 0 | 0.000 | 0.000 | 0.000 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-q | 61.873 | 94.287 | 21.512 |
| multi-25x4w-stag500 | 78.446 | 95.000 | 40.924 |
| multi-inst-25x1dx4ix1w-stag500 | 78.272 | 97.000 | 38.280 |
| multi-inst-25x2dx2ix1w-500 | 78.068 | 96.000 | 38.058 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-q | 156.000 | 411.000 | 994180.000 | 262.000 | 10.800 | 44.000 | 3.590 | 517.000 | 1097385.000 | 74.000 | 1747789.000 | 496.000 | 70.000 | 157.000 | 75.938 | 66.073 | 26.812 | 170.683 | 94.500 | 302.612 |
| multi-25x4w-stag500 | 183.000 | 88.000 | 1162908.000 | 257.000 | 7.600 | 12.000 | 5.500 | 119.000 | 975251.000 | 240.000 | 1623700.000 | 240.000 | 69.000 | 157.000 | 95.625 | 242.138 | 51.688 | 242.138 | 95.000 | 0.000 |
| multi-inst-25x1dx4ix1w-stag500 | 534.710 | 30.364 | 3680501.760 | 22.771 | 11.200 | 5.000 | 4.970 | 18.000 | 1034981.000 | 30.000 | 1643759.000 | 30.000 | 74.000 | 128.000 | 90.812 | 157.928 | 49.000 | 73.968 | 97.000 | 0.000 |
| multi-inst-25x2dx2ix1w-500 | 345.150 | 0.000 | 2893021.184 | 0.000 | 11.400 | 13.000 | 3.575 | 9.000 | 911564.500 | 153.000 | 1495759.500 | 160.000 | 68.000 | 142.000 | 94.312 | 212.117 | 47.625 | 152.639 | 96.000 | 0.000 |
