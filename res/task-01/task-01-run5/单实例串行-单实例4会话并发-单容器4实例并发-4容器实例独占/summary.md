## `单实例串行` vs `单实例4会话并发` vs `单容器4实例并发` vs `4容器实例独占`

**Run Dirs**

| scenario | run_dir | instance_num | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- | --- |
| 单实例串行 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T122607Z_vps-docker-qwen3-235b-single-100-worker | 1 | 100 | 100 | 0 |
| 单实例4会话并发 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T131723Z_vps-docker-qwen3-235b-multi-25x4w-stag500-worker | 1 | 100 | 100 | 0 |
| 单容器4实例并发 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T153103Z_vps-docker-qwen3-235b-multi-inst-25x1dx4ix1w-stag500-worker | 1 | 100 | 100 | 0 |
| 4容器实例独占 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133011Z_vps-docker-qwen3-235b-single-inst-25x4i-worker | 4 | 100 | 100 | 0 |

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
| 单实例串行 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T122607Z_vps-docker-qwen3-235b-single-100-worker | 2026-04-20T12:26:14.982918+00:00 | 2026-04-20T12:44:18.873534+00:00 | 1083.891 | 2026-04-20T12:26:15.050496+00:00 | 2026-04-20T12:44:06.666027+00:00 | 1071.616 |
| 单实例4会话并发 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T131723Z_vps-docker-qwen3-235b-multi-25x4w-stag500-worker | 2026-04-20T13:17:32.152036+00:00 | 2026-04-20T13:25:32.847096+00:00 | 480.695 | 2026-04-20T13:17:32.222626+00:00 | 2026-04-20T13:25:19.059390+00:00 | 466.837 |
| 单容器4实例并发 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T153103Z_vps-docker-qwen3-235b-multi-inst-25x1dx4ix1w-stag500-worker | 2026-04-20T15:31:12.180525+00:00 | 2026-04-20T15:40:57.872852+00:00 | 585.692 | 2026-04-20T15:31:13.248357+00:00 | 2026-04-20T15:40:30.400265+00:00 | 557.152 |
| 4容器实例独占 | /root/Zehao/ClawHarness/out/batch_run_5/task-01/20260420T133011Z_vps-docker-qwen3-235b-single-inst-25x4i-worker | 2026-04-20T13:30:42.370662+00:00 | 2026-04-20T13:38:19.584830+00:00 | 457.214 | 2026-04-20T13:30:42.463602+00:00 | 2026-04-20T13:37:29.342570+00:00 | 406.879 |

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| 单实例串行 | 10716.112 | 10587.211 | 11609.176 | 28131.085 |
| 单实例4会话并发 | 15793.655 | 14126.145 | 19222.430 | 40556.523 |
| 单容器4实例并发 | 14649.957 | 12456.189 | 34271.329 | 47058.792 |
| 4容器实例独占 | 11431.218 | 11228.398 | 21382.561 | 24126.145 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| 单实例串行 | 67.328 | 3.743 | 10659.810 | 52.524 | 10716.112 |
| 单实例4会话并发 | 898.628 | 8.495 | 15743.316 | 41.806 | 15793.655 |
| 单容器4实例并发 | 5649.086 | 4.581 | 14463.244 | 182.092 | 14649.957 |
| 4容器实例独占 | 2331.294 | 6.289 | 11241.889 | 183.002 | 11431.218 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 单实例串行 | 4.989 | 11.338 | 10577.986 | 11599.220 | 23612.275 | 10.934 | 17.260 | 11609.176 | 28131.085 |
| 单实例4会话并发 | 23.974 | 56.965 | 14114.849 | 19210.958 | 40541.727 | 16.970 | 33.874 | 19222.430 | 40556.523 |
| 单容器4实例并发 | 13.643 | 40.919 | 12446.958 | 34261.942 | 47041.983 | 22.523 | 4289.627 | 34271.329 | 47058.792 |
| 4容器实例独占 | 26.177 | 40.431 | 11218.410 | 18914.857 | 24114.181 | 31.825 | 4425.834 | 21382.561 | 24126.145 |

**System CPU Table**

| scenario | pct_cpu_total | pct_cpu_user | pct_cpu_system |
| --- | --- | --- | --- |
| 单实例串行 | 14.967 | 11.854 | 3.114 |
| 单实例4会话并发 | 28.929 | 22.785 | 6.145 |
| 单容器4实例并发 | 47.836 | 8.875 | 9.654 |
| 4容器实例独占 | 57.117 | 45.252 | 11.865 |

**System Memory Table**

| scenario | rss_kib_total |
| --- | --- |
| 单实例串行 | 611623.254 |
| 单实例4会话并发 | 752520.502 |
| 单容器4实例并发 | 2009671.477 |
| 4容器实例独占 | 2277830.766 |

**System Disk Table**

| scenario | busiest_device | pct_util | r_await | w_await | aqu_sz | system_wkb_s | benchmark_kb_wr_per_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 单实例串行 | sda | 0.275 | 0.002 | 0.244 | 0.022 | 2324.190 | 2284.369 |
| 单实例4会话并发 | sda | 0.468 | 0.003 | 0.472 | 0.053 | 4451.498 | 4323.413 |
| 单容器4实例并发 | sda | 0.487 | 0.000 | 0.428 | 0.088 | 5700.329 | 2357.017 |
| 4容器实例独占 | sda | 0.647 | 0.004 | 0.497 | 0.143 | 8810.673 | 8840.185 |

**System Activity Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | blocked_processes | benchmark_cswch_per_s | benchmark_nvcswch_per_s | benchmark_iodelay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 单实例串行 | 922447.791 | 1423632.536 | 37.467 | 0.003 | 30.419 | 7.982 | 0.000 |
| 单实例4会话并发 | 821966.960 | 1316656.806 | 32.304 | 0.002 | 29.161 | 17.327 | 0.000 |
| 单容器4实例并发 | 842955.488 | 1337455.441 | 33.129 | 0.009 | - | - | - |
| 4容器实例独占 | 837190.940 | 1361502.428 | 31.625 | 0.003 | 67.961 | 48.463 | 0.000 |

**Token Throughput Table**

| scenario | overall_output_tps |
| --- | --- |
| 单实例串行 | 18.725 |
| 单实例4会话并发 | 30.872 |
| 单容器4实例并发 | 25.216 |
| 4容器实例独占 | 26.472 |

**NPU Table**

| scenario | utilization_pct | hbm_usage_pct | aicore_usage_pct |
| --- | --- | --- | --- |
| 单实例串行 | 79.860 | 94.000 | 28.425 |
| 单实例4会话并发 | 87.409 | 95.000 | 44.374 |
| 单容器4实例并发 | 87.436 | 96.929 | 40.951 |
| 4容器实例独占 | 78.938 | 95.000 | 37.920 |

**System Timeline Peaks Table**

| scenario | benchmark_cpu_peak | benchmark_cpu_peak_t_sec | benchmark_rss_peak_kib | benchmark_rss_peak_t_sec | system_disk_pct_util_peak | system_disk_pct_util_peak_t_sec | system_disk_w_await_peak | system_disk_w_await_peak_t_sec | system_interrupts_peak | system_interrupts_peak_t_sec | system_context_switches_peak | system_context_switches_peak_t_sec | system_run_queue_peak | system_run_queue_peak_t_sec | npu_utilization_peak | npu_utilization_peak_t_sec | npu_aicore_peak | npu_aicore_peak_t_sec | npu_hbm_peak | npu_hbm_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 单实例串行 | 187.000 | 93.000 | 918832.000 | 21.000 | 19.600 | 35.000 | 2.120 | 559.000 | 1152746.000 | 82.000 | 1786788.000 | 82.000 | 105.000 | 877.000 | 94.062 | 704.451 | 34.875 | 966.791 | 94.000 | 0.000 |
| 单实例4会话并发 | 168.000 | 129.000 | 952960.000 | 229.000 | 10.800 | 54.000 | 5.230 | 3.000 | 1053689.000 | 432.000 | 1654277.000 | 432.000 | 72.000 | 157.000 | 96.375 | 375.020 | 53.125 | 121.326 | 95.000 | 0.000 |
| 单容器4实例并发 | 494.880 | 10.115 | 3770679.296 | 22.776 | 12.800 | 12.000 | 4.790 | 13.000 | 1114377.000 | 389.000 | 1787602.000 | 389.000 | 72.000 | 388.000 | 96.688 | 253.384 | 52.375 | 37.372 | 97.000 | 112.938 |
| 4容器实例独占 | 469.000 | 2.000 | 3358476.000 | 15.000 | 5.600 | 8.000 | 3.853 | 8.000 | 1020849.750 | 382.000 | 1582224.750 | 382.000 | 60.000 | 398.000 | 96.938 | 142.389 | 53.375 | 122.867 | 95.000 | 0.000 |
