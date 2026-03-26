## `vps-docker-single-task-00-500-light` vs `vps-docker-multi-task-00-500-light`

**Run Dirs**

| scenario | run_dir | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | /root/client-harness/out/20260326T120941Z_vps-docker-single-task-00-500-light | 500 | 500 | 0 |
| vps-docker-multi-task-00-500-light | /root/client-harness/out/20260326T121410Z_vps-docker-multi-task-00-500-light | 500 | 500 | 0 |

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
| vps-docker-single-task-00-500-light | 118.591 | 114.308 | 134.288 | 150.500 |
| vps-docker-multi-task-00-500-light | 1041.093 | 1004.444 | 1330.842 | 2382.452 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | 72.561 | 0.745 | 107.445 | 10.377 | 118.591 |
| vps-docker-multi-task-00-500-light | 241.797 | 1.835 | 1033.055 | 6.180 | 1041.093 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | 0.750 | 4.595 | 102.208 | 121.738 | 135.285 | 13.970 | 15.463 | 134.288 | 150.500 |
| vps-docker-multi-task-00-500-light | 1.193 | 34.547 | 998.626 | 1318.619 | 2375.731 | 9.969 | 14.222 | 1330.842 | 2382.452 |

**Container Metrics Table**

| scenario | cpu_percent | mem_percent | block_read_bytes_per_s | block_write_bytes_per_s |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | 103.985 | 4.129 | 0.000 | 34661.030 |
| vps-docker-multi-task-00-500-light | 105.241 | 4.130 | 0.000 | 77629.391 |

**Process Metrics Table**

| scenario | cpu_percent | rss_kib | kb_wr_per_s | iodelay | cswch_per_s | nvcswch_per_s |
| --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | 103.271 | 2792252.881 | 575.322 | 0.000 | 307.881 | 3.373 |
| vps-docker-multi-task-00-500-light | 104.426 | 2793042.000 | 671.481 | 0.000 | 100.167 | 4.204 |

**Disk Metrics Table**

| scenario | busiest_device | pct_util | r_await | w_await | f_await | aqu_sz | wkb_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | vda | 0.780 | 0.000 | 1.006 | 0.017 | 0.021 | 701.559 |
| vps-docker-multi-task-00-500-light | vda | 0.830 | 0.000 | 1.016 | 0.037 | 0.021 | 833.778 |

**System Metrics Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | perf_cache_misses | perf_context_switches | perf_cpu_migrations | perf_page_faults | perf_unsupported_events | strace_events_per_s_peak | strace_duration_ms_per_s_peak | strace_top_syscall | strace_top_syscall_total_duration_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | 11841.883 | 15533.217 | 1.333 | - | - | - | - |  | - | - |  | - |
| vps-docker-multi-task-00-500-light | 11948.291 | 16426.218 | 1.236 | - | - | - | - |  | - | - |  | - |

**Timeline Peaks Table**

| scenario | docker_cpu_peak | docker_cpu_peak_t_sec | docker_mem_peak | docker_mem_peak_t_sec | pidstat_cpu_peak | pidstat_cpu_peak_t_sec | pidstat_rss_peak | pidstat_rss_peak_t_sec | iostat_pct_util_peak | iostat_pct_util_peak_t_sec | iostat_w_await_peak | iostat_w_await_peak_t_sec | vmstat_interrupts_peak | vmstat_interrupts_peak_t_sec | vmstat_context_switches_peak | vmstat_context_switches_peak_t_sec | perf_context_switches_peak | perf_context_switches_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | 140.700 | 10.090 | 4.240 | 27.747 | 146.000 | 11.000 | 2938192.000 | 11.000 | 1.800 | 34.000 | 7.350 | 34.000 | 23481.000 | 25.000 | 17815.000 | 18.000 | - | - |
| vps-docker-multi-task-00-500-light | 142.140 | 10.090 | 4.250 | 10.090 | 143.000 | 10.000 | 2865108.000 | 10.000 | 1.700 | 28.000 | 5.820 | 34.000 | 13198.000 | 28.000 | 18682.000 | 38.000 | - | - |

**strace Key Syscalls Table**

| scenario | run_dir | openat_count | openat_total_sec | openat_mean_ms | statx_count | statx_total_sec | statx_mean_ms | newfstatat_count | newfstatat_total_sec | newfstatat_mean_ms | pread64_count | pread64_total_sec | pread64_mean_ms | clone_count | clone_total_sec | clone_mean_ms | sched_yield_count | sched_yield_total_sec | sched_yield_mean_ms | futex_count | futex_total_sec | futex_mean_ms | read_count | read_total_sec | read_mean_ms | write_count | write_total_sec | write_mean_ms | futex_total_sec_per_request | futex_total_sec_per_wall_sec | statx_total_sec_per_request | statx_total_sec_per_wall_sec | openat_total_sec_per_request | openat_total_sec_per_wall_sec | estimated_makespan_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | /root/client-harness/out/20260326T120941Z_vps-docker-single-task-00-500-light | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 60.968 |
| vps-docker-multi-task-00-500-light | /root/client-harness/out/20260326T121410Z_vps-docker-multi-task-00-500-light | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 55.907 |

**strace Mean Duration Table**

| scenario | vps-docker-single-task-00-500-light | vps-docker-multi-task-00-500-light |
| --- | --- | --- |
| openat | - | - |
| statx | - | - |
| newfstatat | - | - |
| pread64 | - | - |
| clone | - | - |
| sched_yield | - | - |
| futex | - | - |
| read | - | - |
| write | - | - |

**Gateway Runtime Stage Table**

| scenario | bootstrap_load_mean_ms | skills_mean_ms | context_bundle_mean_ms | execution_admission_wait_mean_ms | reply_dispatch_queue_wait_mean_ms | reply_dispatch_queue_hold_mean_ms | reply_dispatch_pending_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | - | - | - | - | - | - | - |
| vps-docker-multi-task-00-500-light | - | - | - | - | - | - | - |

**Node Focus Groups Table**

| scenario | sessions_lock_total_ms | sessions_lock_count | sessions_dir_enum_total_ms | sessions_dir_enum_count | sessions_json_total_ms | sessions_json_count | sessions_tmp_total_ms | sessions_tmp_count | bootstrap_files_total_ms | bootstrap_files_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | - | - | - | - | - | - | - | - | - | - |
| vps-docker-multi-task-00-500-light | - | - | - | - | - | - | - | - | - | - |

**Runtime Category Samples Table**

| scenario | run_dir | sample_count | fs_worker_exec_count | fs_worker_exec_pct | fs_callback_count | fs_callback_pct | event_loop_poll_count | event_loop_poll_pct | microtask_count | microtask_pct | futex_sync_count | futex_sync_pct | worker_message_count | worker_message_pct | json_parse_count | json_parse_pct | libuv_worker_other_count | libuv_worker_other_pct | gateway_main_other_count | gateway_main_other_pct | v8_worker_count | v8_worker_pct | other_count | other_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-light | /root/client-harness/out/20260326T120941Z_vps-docker-single-task-00-500-light | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| vps-docker-multi-task-00-500-light | /root/client-harness/out/20260326T121410Z_vps-docker-multi-task-00-500-light | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |

**Runtime Category Percent Table**

| scenario | vps-docker-single-task-00-500-light | vps-docker-multi-task-00-500-light |
| --- | --- | --- |
| fs_worker_exec | - | - |
| fs_callback | - | - |
| event_loop_poll | - | - |
| microtask | - | - |
| futex_sync | - | - |
| worker_message | - | - |
| json_parse | - | - |
| libuv_worker_other | - | - |
| gateway_main_other | - | - |
| v8_worker | - | - |
| other | - | - |

