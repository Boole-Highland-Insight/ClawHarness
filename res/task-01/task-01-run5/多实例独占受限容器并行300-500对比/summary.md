## `多实例并行300` vs `多实例独占受限并行0` vs `多实例并行500` vs `多实例独占受限并行300`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| 多实例并行300 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T194433Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag300-limited-worker | 2 | 100 | 100 | 0 |
| 多实例独占受限并行0 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T193153Z_vps-docker-qwen3-235b-single-inst-25x4i-limited-worker | 4 | 100 | 100 | 0 |
| 多实例并行500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T195549Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-limited-worker | 2 | 100 | 100 | 0 |
| 多实例独占受限并行300 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T200819Z_vps-docker-qwen3-235b-single-inst-25x4i-stag300-limited-worker | 4 | 100 | 100 | 0 |

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
| 多实例并行300 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T194433Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag300-limited-worker | 2026-04-20T19:44:49.126987+00:00 | 2026-04-20T19:51:24.710726+00:00 | 395.584 | 2026-04-20T19:44:49.193657+00:00 | 2026-04-20T19:50:56.666807+00:00 | 367.473 |
| 多实例独占受限并行0 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T193153Z_vps-docker-qwen3-235b-single-inst-25x4i-limited-worker | 2026-04-20T19:32:26.350522+00:00 | 2026-04-20T19:39:16.144223+00:00 | 409.794 | 2026-04-20T19:32:26.471710+00:00 | 2026-04-20T19:38:28.987400+00:00 | 362.516 |
| 多实例并行500 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T195549Z_vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-limited-worker | 2026-04-20T19:56:04.852149+00:00 | 2026-04-20T20:03:38.174609+00:00 | 453.322 | 2026-04-20T19:56:04.998754+00:00 | 2026-04-20T20:03:16.290331+00:00 | 431.292 |
| 多实例独占受限并行300 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T200819Z_vps-docker-qwen3-235b-single-inst-25x4i-stag300-limited-worker | 2026-04-20T20:08:51.406852+00:00 | 2026-04-20T20:18:33.704028+00:00 | 582.297 | 2026-04-20T20:08:51.493728+00:00 | 2026-04-20T20:17:41.368351+00:00 | 529.875 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| 多实例并行300 | 12323.464 | 11217.732 | 19253.360 | 40618.018 |
| 多实例独占受限并行0 | 11033.728 | 9111.592 | 24321.906 | 70557.738 |
| 多实例并行500 | 12165.332 | 9431.340 | 20813.725 | 21834.523 |
| 多实例独占受限并行300 | 14128.457 | 14534.146 | 28468.426 | 31069.254 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| 多实例并行300 | 2321.828 | 10.495 | 12119.467 | 193.464 | 12323.464 |
| 多实例独占受限并行0 | 2207.881 | 5.499 | 10850.302 | 177.890 | 11033.728 |
| 多实例并行500 | 4050.936 | 11.799 | 12001.914 | 151.584 | 12165.332 |
| 多实例独占受限并行300 | 335.339 | 6.853 | 13940.959 | 180.606 | 14128.457 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 多实例并行300 | 9.811 | 40.899 | 11177.102 | 18134.274 | 40607.149 | 15.721 | 4336.900 | 19253.360 | 40618.018 |
| 多实例独占受限并行0 | 23.319 | 33.632 | 9089.207 | 20027.631 | 70543.205 | 22.561 | 4290.323 | 24321.906 | 70557.738 |
| 多实例并行500 | 19.593 | 42.195 | 9303.655 | 20720.914 | 21823.683 | 17.671 | 3566.817 | 20813.725 | 21834.523 |
| 多实例独占受限并行300 | 28.561 | 60.738 | 14519.101 | 28451.256 | 31058.345 | 28.800 | 4393.879 | 28468.426 | 31069.254 |

**System CPU Table**

| scenario | benchmark_pct_cpu_total | benchmark_pct_cpu_usr | benchmark_pct_cpu_system | benchmark_pct_cpu_wait | system_cpu_user_pct | system_cpu_system_pct | system_cpu_iowait_pct | system_cpu_idle_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 多实例并行300 | 45.064 | 35.388 | 9.676 | 0.084 | 8.683 | 8.287 | 0.000 | 83.013 |
| 多实例独占受限并行0 | 63.223 | 50.833 | 12.389 | 2.038 | 8.386 | 8.381 | 0.000 | 83.229 |
| 多实例并行500 | 39.911 | 31.418 | 8.493 | 0.083 | 8.622 | 8.470 | 0.000 | 82.944 |
| 多实例独占受限并行300 | 44.564 | 35.777 | 8.787 | 1.639 | 8.538 | 8.940 | 0.000 | 82.559 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| 多实例并行300 | 1395039.229 |
| 多实例独占受限并行0 | 2050618.541 |
| 多实例并行500 | 1281421.552 |
| 多实例独占受限并行300 | 2016066.453 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 多实例并行300 | sda | 0.636 | 0.024 | 0.440 | 0.087 | 6834.272 | 6951.699 |
| 多实例独占受限并行0 | sda | 0.795 | 0.021 | 0.435 | 0.111 | 9180.763 | 9780.513 |
| 多实例并行500 | sda | 0.572 | 0.013 | 0.395 | 0.081 | 6118.329 | 6015.825 |
| 多实例独占受限并行300 | sda | 0.539 | 0.023 | 0.367 | 0.078 | 6402.488 | 6495.436 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 多实例并行300 | 813121.168 | 1313606.639 | 30.859 | 0.005 | 44.917 | 27.459 | 0.000 |
| 多实例独占受限并行0 | 824756.293 | 1347034.089 | 30.154 | 0.006 | 72.234 | 55.842 | 0.000 |
| 多实例并行500 | 820630.493 | 1320030.435 | 31.685 | 0.009 | 46.794 | 23.788 | 0.004 |
| 多实例独占受限并行300 | 841936.283 | 1358672.437 | 31.877 | 0.005 | 62.513 | 45.675 | 0.000 |

**Token Throughput Table**

| scenario | rows_with_usage | output_tokens_mean | output_tps_request_mean | output_tps_session_delta_mean |
| --- | --- | --- | --- | --- |
| 多实例并行300 | 100 | 104.300 | 27.140 | 22.280 |
| 多实例独占受限并行0 | 100 | 84.820 | 8.444 | 4.050 |
| 多实例并行500 | 100 | 104.240 | 23.512 | 18.050 |
| 多实例独占受限并行300 | 100 | 146.720 | 9.411 | 4.636 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| 多实例并行300 | 82.307 | 97.000 | 41.908 |
| 多实例独占受限并行0 | 77.189 | 97.000 | 37.799 |
| 多实例并行500 | 85.165 | 97.000 | 42.244 |
| 多实例独占受限并行300 | 82.619 | 97.000 | 39.670 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 多实例并行300 | 246.000 | 9.000 | 1906832.000 | 24.000 | 6.900 | 42.000 | 3.875 | 8.000 | 981685.000 | 348.000 | 1560240.500 | 355.000 | 65.000 | 144.000 | 96.438 | 197.747 | 53.188 | 140.782 | 97.000 | 0.000 |
| 多实例独占受限并行0 | 488.000 | 0.000 | 2296928.000 | 35.000 | 10.300 | 17.000 | 2.645 | 17.000 | 1004748.750 | 339.000 | 1542421.250 | 339.000 | 63.250 | 131.000 | 96.688 | 241.073 | 53.250 | 57.726 | 97.000 | 0.000 |
| 多实例并行500 | 252.000 | 0.000 | 1915944.000 | 24.000 | 9.600 | 37.000 | 3.705 | 8.000 | 1027464.500 | 404.000 | 1590592.500 | 397.000 | 69.500 | 99.000 | 96.750 | 362.585 | 52.438 | 121.556 | 97.000 | 0.000 |
| 多实例独占受限并行300 | 424.000 | 0.000 | 2232592.000 | 31.000 | 9.100 | 10.000 | 2.230 | 0.000 | 997202.000 | 530.000 | 1534735.000 | 465.000 | 63.250 | 157.000 | 96.938 | 278.841 | 53.375 | 98.439 | 97.000 | 0.000 |
