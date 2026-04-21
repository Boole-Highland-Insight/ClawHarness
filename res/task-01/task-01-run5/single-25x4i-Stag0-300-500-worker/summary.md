## `single-inst-25x4i-stag0` vs `single-inst-25x4i-0-lim` vs `single-inst-25x4i-stag300-lim` vs `single-inst-25x4i-stag500-lim`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133011Z_vps-docker-qwen3-235b-single-inst-25x4i-worker | 4 | 100 | 100 | 0 |
| single-inst-25x4i-0-lim | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T193153Z_vps-docker-qwen3-235b-single-inst-25x4i-limited-worker | 4 | 100 | 100 | 0 |
| single-inst-25x4i-stag300-lim | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T200819Z_vps-docker-qwen3-235b-single-inst-25x4i-stag300-limited-worker | 4 | 100 | 100 | 0 |
| single-inst-25x4i-stag500-lim | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260421T083731Z_vps-docker-qwen3-235b-single-inst-25x4i-stag500-limited-worker | 4 | 100 | 100 | 0 |

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
| single-inst-25x4i-stag0 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133011Z_vps-docker-qwen3-235b-single-inst-25x4i-worker | 2026-04-20T13:30:42.370662+00:00 | 2026-04-20T13:38:19.584830+00:00 | 457.214 | 2026-04-20T13:30:42.463602+00:00 | 2026-04-20T13:37:29.342570+00:00 | 406.879 |
| single-inst-25x4i-0-lim | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T193153Z_vps-docker-qwen3-235b-single-inst-25x4i-limited-worker | 2026-04-20T19:32:26.350522+00:00 | 2026-04-20T19:39:16.144223+00:00 | 409.794 | 2026-04-20T19:32:26.471710+00:00 | 2026-04-20T19:38:28.987400+00:00 | 362.516 |
| single-inst-25x4i-stag300-lim | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T200819Z_vps-docker-qwen3-235b-single-inst-25x4i-stag300-limited-worker | 2026-04-20T20:08:51.406852+00:00 | 2026-04-20T20:18:33.704028+00:00 | 582.297 | 2026-04-20T20:08:51.493728+00:00 | 2026-04-20T20:17:41.368351+00:00 | 529.875 |
| single-inst-25x4i-stag500-lim | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260421T083731Z_vps-docker-qwen3-235b-single-inst-25x4i-stag500-limited-worker | 2026-04-21T08:38:03.349542+00:00 | 2026-04-21T08:46:08.736821+00:00 | 485.387 | 2026-04-21T08:38:03.504094+00:00 | 2026-04-21T08:45:16.006899+00:00 | 432.503 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 11431.218 | 11228.398 | 21382.561 | 24126.145 |
| single-inst-25x4i-0-lim | 11033.728 | 9111.592 | 24321.906 | 70557.738 |
| single-inst-25x4i-stag300-lim | 14128.457 | 14534.146 | 28468.426 | 31069.254 |
| single-inst-25x4i-stag500-lim | 13346.006 | 11431.900 | 24590.342 | 37922.371 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 2331.294 | 6.289 | 11241.889 | 183.002 | 11431.218 |
| single-inst-25x4i-0-lim | 2207.881 | 5.499 | 10850.302 | 177.890 | 11033.728 |
| single-inst-25x4i-stag300-lim | 335.339 | 6.853 | 13940.959 | 180.606 | 14128.457 |
| single-inst-25x4i-stag500-lim | 149.295 | 4.707 | 13159.323 | 181.939 | 13346.006 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 26.177 | 40.431 | 11218.410 | 18914.857 | 24114.181 | 31.825 | 4425.834 | 21382.561 | 24126.145 |
| single-inst-25x4i-0-lim | 23.319 | 33.632 | 9089.207 | 20027.631 | 70543.205 | 22.561 | 4290.323 | 24321.906 | 70557.738 |
| single-inst-25x4i-stag300-lim | 28.561 | 60.738 | 14519.101 | 28451.256 | 31058.345 | 28.800 | 4393.879 | 28468.426 | 31069.254 |
| single-inst-25x4i-stag500-lim | 17.984 | 37.185 | 11415.200 | 24578.737 | 37901.565 | 27.576 | 4363.536 | 24590.342 | 37922.371 |

**System CPU Table**

| scenario | benchmark_pct_cpu_total | benchmark_pct_cpu_usr | benchmark_pct_cpu_system | benchmark_pct_cpu_wait | system_cpu_user_pct | system_cpu_system_pct | system_cpu_iowait_pct | system_cpu_idle_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 57.117 | 45.252 | 11.865 | 0.096 | 8.392 | 8.710 | 0.000 | 82.938 |
| single-inst-25x4i-0-lim | 63.223 | 50.833 | 12.389 | 2.038 | 8.386 | 8.381 | 0.000 | 83.229 |
| single-inst-25x4i-stag300-lim | 44.564 | 35.777 | 8.787 | 1.639 | 8.538 | 8.940 | 0.000 | 82.559 |
| single-inst-25x4i-stag500-lim | 54.774 | 43.697 | 11.077 | 1.604 | 8.276 | 8.597 | 0.000 | 83.160 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| single-inst-25x4i-stag0 | 2277830.766 |
| single-inst-25x4i-0-lim | 2050618.541 |
| single-inst-25x4i-stag300-lim | 2016066.453 |
| single-inst-25x4i-stag500-lim | 2068741.767 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | sda | 0.647 | 0.004 | 0.497 | 0.143 | 8810.673 | 8840.185 |
| single-inst-25x4i-0-lim | sda | 0.795 | 0.021 | 0.435 | 0.111 | 9180.763 | 9780.513 |
| single-inst-25x4i-stag300-lim | sda | 0.539 | 0.023 | 0.367 | 0.078 | 6402.488 | 6495.436 |
| single-inst-25x4i-stag500-lim | sda | 0.675 | 0.004 | 0.377 | 0.092 | 7673.956 | 7271.976 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 837190.940 | 1361502.428 | 31.625 | 0.003 | 67.961 | 48.463 | 0.000 |
| single-inst-25x4i-0-lim | 824756.293 | 1347034.089 | 30.154 | 0.006 | 72.234 | 55.842 | 0.000 |
| single-inst-25x4i-stag300-lim | 841936.283 | 1358672.437 | 31.877 | 0.005 | 62.513 | 45.675 | 0.000 |
| single-inst-25x4i-stag500-lim | 829490.980 | 1348551.233 | 30.508 | 0.008 | 67.947 | 44.841 | 0.013 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 100 | 107.710 | 9.089 | 4.520 |
| single-inst-25x4i-0-lim | 100 | 84.820 | 8.444 | 4.050 |
| single-inst-25x4i-stag300-lim | 100 | 146.720 | 9.411 | 4.636 |
| single-inst-25x4i-stag500-lim | 100 | 122.780 | 9.936 | 4.645 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 78.938 | 95.000 | 37.920 |
| single-inst-25x4i-0-lim | 77.189 | 97.000 | 37.799 |
| single-inst-25x4i-stag300-lim | 82.619 | 97.000 | 39.670 |
| single-inst-25x4i-stag500-lim | 78.943 | 97.500 | 38.508 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-inst-25x4i-stag0 | 469.000 | 2.000 | 3358476.000 | 15.000 | 5.600 | 8.000 | 3.853 | 8.000 | 1020849.750 | 382.000 | 1582224.750 | 382.000 | 60.000 | 398.000 | 96.938 | 142.389 | 53.375 | 122.867 | 95.000 | 0.000 |
| single-inst-25x4i-0-lim | 488.000 | 0.000 | 2296928.000 | 35.000 | 10.300 | 17.000 | 2.645 | 17.000 | 1004748.750 | 339.000 | 1542421.250 | 339.000 | 63.250 | 131.000 | 96.688 | 241.073 | 53.250 | 57.726 | 97.000 | 0.000 |
| single-inst-25x4i-stag300-lim | 424.000 | 0.000 | 2232592.000 | 31.000 | 9.100 | 10.000 | 2.230 | 0.000 | 997202.000 | 530.000 | 1534735.000 | 465.000 | 63.250 | 157.000 | 96.938 | 278.841 | 53.375 | 98.439 | 97.000 | 0.000 |
| single-inst-25x4i-stag500-lim | 515.000 | 0.000 | 2283812.000 | 15.000 | 8.500 | 5.000 | 1.788 | 1.000 | 992156.250 | 407.000 | 1531036.000 | 422.000 | 62.750 | 132.000 | 96.562 | 204.105 | 52.688 | 58.260 | 97.500 | 0.000 |
