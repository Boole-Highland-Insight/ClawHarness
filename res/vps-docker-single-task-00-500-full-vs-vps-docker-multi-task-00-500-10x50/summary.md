## `vps-docker-single-task-00-500-full` vs `vps-docker-multi-task-00-500-10x50`

**Run Dirs**

| scenario | run_dir | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | /root/client-harness/out/20260325T142928Z_vps-docker-single-task-00-500-full | 500 | 500 | 0 |
| vps-docker-multi-task-00-500-10x50 | /root/client-harness/out/20260325T141404Z_vps-docker-multi-task-00-500-10x50 | 500 | 500 | 0 |

**Figures**

- ![Latency Overview](figures/latency_overview.png)
- ![Latency Phase Means](figures/latency_phase_means.png)
- ![Latency Tail](figures/latency_tail.png)
- ![Container CPU and Memory](figures/container_cpu_mem.png)
- ![Latency Timeline](figures/latency_timeline.png)
- ![CPU Load Timeline](figures/cpu_load_timeline.png)
- ![Memory Load Timeline](figures/mem_load_timeline.png)
- ![I/O Load Timeline](figures/io_load_timeline.png)
- ![Interrupt Timeline](figures/interrupts_timeline.png)
- ![Context Switch Timeline](figures/context_switch_timeline.png)

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 126.002 | 121.223 | 142.324 | 163.832 |
| vps-docker-multi-task-00-500-10x50 | 1042.240 | 1010.361 | 1317.441 | 2210.858 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 61.865 | 0.806 | 114.509 | 10.663 | 126.002 |
| vps-docker-multi-task-00-500-10x50 | 289.716 | 2.632 | 1033.416 | 6.168 | 1042.240 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 0.822 | 4.627 | 108.746 | 128.882 | 145.965 | 14.380 | 15.915 | 142.324 | 163.832 |
| vps-docker-multi-task-00-500-10x50 | 4.224 | 110.008 | 1004.365 | 1306.792 | 2204.824 | 9.845 | 15.681 | 1317.441 | 2210.858 |

**Container Metrics Table**

| scenario | cpu_percent | mem_percent | block_read_bytes_per_s | block_write_bytes_per_s |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 96.607 | 4.149 | 0.000 | 32208.337 |
| vps-docker-multi-task-00-500-10x50 | 105.578 | 4.124 | 0.000 | 77252.083 |

**Process Metrics Table**

| scenario | cpu_percent | rss_kib | kb_wr_per_s | iodelay | cswch_per_s | nvcswch_per_s |
| --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 99.125 | 2776471.938 | 533.375 | 0.000 | 294.016 | 2.625 |
| vps-docker-multi-task-00-500-10x50 | 0.000 | 672.000 | 0.000 | 0.000 | 1.000 | 0.000 |

**Disk Metrics Table**

| scenario | busiest_device | pct_util | r_await | w_await | f_await | aqu_sz | wkb_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | vda | 1.044 | 0.000 | 1.061 | 0.008 | 0.030 | 1314.032 |
| vps-docker-multi-task-00-500-10x50 | vda | 0.867 | 0.000 | 0.935 | 0.009 | 0.020 | 700.074 |

**System Metrics Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | perf_cache_misses | perf_context_switches | perf_cpu_migrations | perf_page_faults | perf_unsupported_events | strace_events_per_s_peak | strace_duration_ms_per_s_peak | strace_top_syscall | strace_top_syscall_total_duration_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 15084.156 | 15701.125 | 1.219 | - | 726.837 | 4.729 | 9.482 | cache-misses, cache-references | - | - |  | - |
| vps-docker-multi-task-00-500-10x50 | 12258.036 | 17637.182 | 1.345 | - | 68.448 | 4.903 | 0.000 | cache-misses, cache-references | - | - |  | - |

**Timeline Peaks Table**

| scenario | docker_cpu_peak | docker_cpu_peak_t_sec | docker_mem_peak | docker_mem_peak_t_sec | pidstat_cpu_peak | pidstat_cpu_peak_t_sec | pidstat_rss_peak | pidstat_rss_peak_t_sec | iostat_pct_util_peak | iostat_pct_util_peak_t_sec | iostat_w_await_peak | iostat_w_await_peak_t_sec | vmstat_interrupts_peak | vmstat_interrupts_peak_t_sec | vmstat_context_switches_peak | vmstat_context_switches_peak_t_sec | perf_context_switches_peak | perf_context_switches_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 125.290 | 0.000 | 4.260 | 32.785 | 155.000 | 11.000 | 2847400.000 | 11.000 | 2.700 | 33.000 | 5.870 | 33.000 | 16424.000 | 21.000 | 18303.000 | 31.000 | 896.428 | 14.015 |
| vps-docker-multi-task-00-500-10x50 | 145.050 | 10.091 | 4.250 | 10.091 | 0.000 | 0.000 | 672.000 | 0.000 | 2.000 | 13.000 | 3.730 | 13.000 | 14040.000 | 22.000 | 20671.000 | 33.000 | 88.051 | 8.009 |

