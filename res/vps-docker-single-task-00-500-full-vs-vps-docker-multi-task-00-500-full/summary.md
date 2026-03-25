## `vps-docker-single-task-00-500-full` vs `vps-docker-multi-task-00-500-full`

**Run Dirs**

| scenario | run_dir | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | /root/client-harness/out/20260324T183523Z_vps-docker-single-task-00-500-full | 500 | 500 | 0 |
| vps-docker-multi-task-00-500-full | /root/client-harness/out/20260324T183647Z_vps-docker-multi-task-00-500-full | 500 | 500 | 0 |

**Figures**

- ![Latency Overview](figures/latency_overview.png)
- ![Latency Phase Means](figures/latency_phase_means.png)
- ![Latency Tail](figures/latency_tail.png)
- ![Container CPU and Memory](figures/container_cpu_mem.png)
- ![Latency Timeline](figures/latency_timeline.png)

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 117.949 | 112.396 | 138.049 | 149.266 |
| vps-docker-multi-task-00-500-full | 2000.369 | 1942.718 | 3206.884 | 3750.755 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 67.011 | 0.720 | 105.016 | 12.188 | 117.949 |
| vps-docker-multi-task-00-500-full | 389.055 | 4.914 | 1989.450 | 5.980 | 2000.369 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 0.734 | 4.602 | 100.739 | 124.863 | 139.965 | 13.991 | 15.075 | 138.049 | 149.266 |
| vps-docker-multi-task-00-500-full | 11.813 | 122.814 | 1937.666 | 3190.944 | 3713.961 | 10.093 | 22.291 | 3206.884 | 3750.755 |

**Container Metrics Table**

| scenario | cpu_percent | mem_percent | block_read_bytes_per_s | block_write_bytes_per_s |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 104.185 | 4.138 | 0.000 | 34999.779 |
| vps-docker-multi-task-00-500-full | 102.546 | 4.145 | 0.000 | 118635.584 |

**Process Metrics Table**

| scenario | cpu_percent | rss_kib | kb_wr_per_s | iodelay | cswch_per_s | nvcswch_per_s |
| --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 0.000 | 980.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| vps-docker-multi-task-00-500-full | 0.000 | 980.000 | 0.000 | 0.000 | 0.000 | 1.000 |

**Disk Metrics Table**

| scenario | busiest_device | pct_util | r_await | w_await | f_await | aqu_sz | wkb_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | vda | 0.810 | 0.000 | 1.027 | 0.068 | 0.025 | 819.661 |
| vps-docker-multi-task-00-500-full | vda | 0.947 | 0.000 | 1.018 | 0.019 | 0.021 | 734.994 |

**System Metrics Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | perf_cache_misses | perf_context_switches | perf_cpu_migrations | perf_page_faults | perf_unsupported_events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 11810.800 | 17328.600 | 1.167 | - | 69.127 | 3.535 | 0.000 | cache-misses, cache-references |
| vps-docker-multi-task-00-500-full | 12701.037 | 18710.685 | 1.315 | - | 66.976 | 2.384 | 0.000 | cache-misses, cache-references |

