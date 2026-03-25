## `vps-docker-single-task-00-500-full` vs `vps-docker-multi-task-00-500-10x50`

**Run Dirs**

| scenario | run_dir | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | /root/client-harness/out/20260325T150238Z_vps-docker-single-task-00-500-full | 500 | 500 | 0 |
| vps-docker-multi-task-00-500-10x50 | /root/client-harness/out/20260325T150547Z_vps-docker-multi-task-00-500-10x50 | 500 | 500 | 0 |

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
- ![strace Timeline](figures/strace_timeline.png)

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 297.011 | 272.935 | 384.514 | 403.824 |
| vps-docker-multi-task-00-500-10x50 | 2545.394 | 2517.716 | 2961.862 | 3968.590 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 80.510 | 1.056 | 278.546 | 17.384 | 297.011 |
| vps-docker-multi-task-00-500-10x50 | 956.693 | 1.944 | 2533.771 | 9.657 | 2545.394 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 1.387 | 5.995 | 251.336 | 364.335 | 386.228 | 23.766 | 34.818 | 384.514 | 403.824 |
| vps-docker-multi-task-00-500-10x50 | 2.082 | 11.203 | 2507.927 | 2946.515 | 3958.396 | 14.164 | 21.485 | 2961.862 | 3968.590 |

**Container Metrics Table**

| scenario | cpu_percent | mem_percent | block_read_bytes_per_s | block_write_bytes_per_s |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 62.645 | 3.720 | 0.000 | 13728.209 |
| vps-docker-multi-task-00-500-10x50 | 64.731 | 4.073 | 0.000 | 31568.793 |

**Process Metrics Table**

| scenario | cpu_percent | rss_kib | kb_wr_per_s | iodelay | cswch_per_s | nvcswch_per_s |
| --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 64.183 | 2503704.564 | 229.301 | 0.000 | 22098.556 | 0.181 |
| vps-docker-multi-task-00-500-10x50 | 64.598 | 2732345.515 | 276.970 | 0.000 | 22662.735 | 0.159 |

**Disk Metrics Table**

| scenario | busiest_device | pct_util | r_await | w_await | f_await | aqu_sz | wkb_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | vda | 0.682 | 0.000 | 1.332 | 0.014 | 0.095 | 2025.514 |
| vps-docker-multi-task-00-500-10x50 | vda | 0.553 | 0.000 | 1.214 | 0.015 | 0.023 | 1201.008 |

**System Metrics Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | perf_cache_misses | perf_context_switches | perf_cpu_migrations | perf_page_faults | perf_unsupported_events | strace_events_per_s_peak | strace_duration_ms_per_s_peak | strace_top_syscall | strace_top_syscall_total_duration_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 58063.624 | 102702.658 | 1.396 | - | 36.838 | 40.924 | 7.303 | cache-misses, cache-references | 4399.000 | 14339.846 | futex | 1178.036 |
| vps-docker-multi-task-00-500-10x50 | 59353.402 | 105562.106 | 1.530 | - | 37.871 | 41.912 | 196.683 | cache-misses, cache-references | 5851.000 | 9849.841 | futex | 1045.945 |

**Timeline Peaks Table**

| scenario | docker_cpu_peak | docker_cpu_peak_t_sec | docker_mem_peak | docker_mem_peak_t_sec | pidstat_cpu_peak | pidstat_cpu_peak_t_sec | pidstat_rss_peak | pidstat_rss_peak_t_sec | iostat_pct_util_peak | iostat_pct_util_peak_t_sec | iostat_w_await_peak | iostat_w_await_peak_t_sec | vmstat_interrupts_peak | vmstat_interrupts_peak_t_sec | vmstat_context_switches_peak | vmstat_context_switches_peak_t_sec | perf_context_switches_peak | perf_context_switches_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 81.530 | 2.522 | 4.250 | 75.666 | 142.000 | 24.000 | 2845320.000 | 24.000 | 5.500 | 96.000 | 12.350 | 126.000 | 86166.000 | 131.000 | 135490.000 | 131.000 | 42.335 | 100.103 |
| vps-docker-multi-task-00-500-10x50 | 119.600 | 22.699 | 4.250 | 22.699 | 132.000 | 130.000 | 2838872.000 | 23.000 | 2.500 | 69.000 | 8.870 | 54.000 | 83020.000 | 131.000 | 130335.000 | 131.000 | 42.243 | 93.099 |

**Top strace Syscalls: `vps-docker-single-task-00-500-full`**

| scenario | count | total_duration_sec |
| --- | --- | --- |
| futex | 105320 | 1178.036 |
| read | 257991 | 5.670 |
| write | 88248 | 2.600 |
| accept4 | 1 | 0.000 |

**Top strace Syscalls: `vps-docker-multi-task-00-500-10x50`**

| scenario | count | total_duration_sec |
| --- | --- | --- |
| futex | 121064 | 1045.945 |
| read | 159752 | 3.493 |
| write | 81790 | 2.385 |
| accept4 | 10 | 0.000 |

