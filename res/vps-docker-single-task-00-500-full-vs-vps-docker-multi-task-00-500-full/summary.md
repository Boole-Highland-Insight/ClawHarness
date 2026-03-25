## `vps-docker-single-task-00-500-full` vs `vps-docker-multi-task-00-500-full`

**Run Dirs**

| scenario | run_dir | requests_total | requests_ok | requests_failed |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | /root/client-harness/out/20260325T173324Z_vps-docker-single-task-00-500-full | 500 | 500 | 0 |
| vps-docker-multi-task-00-500-full | /root/client-harness/out/20260325T200959Z_vps-docker-multi-task-00-500-full | 500 | 500 | 0 |

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
- ![strace Mean Duration](figures/strace_mean_duration_ms.png)
- ![Gateway Runtime Timeline](figures/gateway_runtime_timeline.png)
- ![Node Focus Group Duration](figures/node_focus_group_duration_ms.png)
- ![Node Focus Timeline](figures/node_focus_timeline.png)
- ![Node Runtime Mean Duration](figures/node_runtime_mean_duration_ms.png)
- ![Node Runtime Timeline](figures/node_runtime_timeline.png)
- ![Runtime Category Samples](figures/runtime_category_pct.png)

**Latency Overview Table**

| scenario | total_mean | total_p50 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 1061.123 | 1190.892 | 1336.504 | 1410.841 |
| vps-docker-multi-task-00-500-full | 19700.302 | 20453.934 | 22529.980 | 29077.450 |

**Mean Latency by Phase Table**

| scenario | connect | send | wait | history | total |
| --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 225.969 | 2.847 | 973.591 | 84.659 | 1061.123 |
| vps-docker-multi-task-00-500-full | 6094.690 | 8.036 | 19620.559 | 71.682 | 19700.302 |

**Tail Latency Table**

| scenario | send_p95 | send_p99 | wait_p50 | wait_p95 | wait_p99 | history_p95 | history_p99 | total_p95 | total_p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 6.953 | 11.899 | 1155.519 | 1251.777 | 1313.980 | 130.959 | 149.266 | 1336.504 | 1410.841 |
| vps-docker-multi-task-00-500-full | 14.670 | 25.721 | 20381.900 | 22455.508 | 28904.365 | 133.085 | 219.221 | 22529.980 | 29077.450 |

**Container Metrics Table**

| scenario | cpu_percent | mem_percent | block_read_bytes_per_s | block_write_bytes_per_s |
| --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 44.936 | 2.070 | 0.000 | 196211.034 |
| vps-docker-multi-task-00-500-full | 43.324 | 2.166 | 0.000 | 702634.363 |

**Process Metrics Table**

| scenario | cpu_percent | rss_kib | kb_wr_per_s | iodelay | cswch_per_s | nvcswch_per_s |
| --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 44.131 | 1405880.256 | 1163.207 | 0.000 | 36571.294 | 0.085 |
| vps-docker-multi-task-00-500-full | 43.245 | 1499169.391 | 1191.841 | 0.000 | 36770.605 | 0.071 |

**Disk Metrics Table**

| scenario | busiest_device | pct_util | r_await | w_await | f_await | aqu_sz | wkb_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | vda | 0.390 | 0.000 | 1.276 | 0.012 | 0.032 | 2253.743 |
| vps-docker-multi-task-00-500-full | vda | 0.415 | 0.000 | 1.300 | 0.012 | 0.039 | 2393.045 |

**System Metrics Table**

| scenario | interrupts_per_s | system_context_switches_per_s | run_queue | perf_cache_misses | perf_context_switches | perf_cpu_migrations | perf_page_faults | perf_unsupported_events | strace_events_per_s_peak | strace_duration_ms_per_s_peak | strace_top_syscall | strace_top_syscall_total_duration_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 84897.087 | 158911.373 | 1.324 | - | 87.594 | 20.117 | 34.556 | cache-misses, cache-references | 3468.000 | 17977.786 | futex | 4230.283 |
| vps-docker-multi-task-00-500-full | 85293.759 | 159817.335 | 1.310 | - | 89.603 | 23.770 | 238.884 | cache-misses, cache-references | 3632.000 | 16909.616 | futex | 4239.576 |

**Timeline Peaks Table**

| scenario | docker_cpu_peak | docker_cpu_peak_t_sec | docker_mem_peak | docker_mem_peak_t_sec | pidstat_cpu_peak | pidstat_cpu_peak_t_sec | pidstat_rss_peak | pidstat_rss_peak_t_sec | iostat_pct_util_peak | iostat_pct_util_peak_t_sec | iostat_w_await_peak | iostat_w_await_peak_t_sec | vmstat_interrupts_peak | vmstat_interrupts_peak_t_sec | vmstat_context_switches_peak | vmstat_context_switches_peak_t_sec | perf_context_switches_peak | perf_context_switches_peak_t_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 115.050 | 80.707 | 4.260 | 80.707 | 129.000 | 81.000 | 2843484.000 | 81.000 | 8.700 | 227.000 | 17.160 | 391.000 | 94849.000 | 487.000 | 178991.000 | 487.000 | 113.099 | 133.148 |
| vps-docker-multi-task-00-500-full | 118.630 | 88.275 | 4.330 | 88.275 | 117.000 | 198.000 | 2990176.000 | 89.000 | 7.000 | 457.000 | 25.020 | 387.000 | 94697.000 | 448.000 | 177249.000 | 263.000 | 114.166 | 3.003 |

**strace Key Syscalls Table**

| scenario | run_dir | openat_count | openat_total_sec | openat_mean_ms | statx_count | statx_total_sec | statx_mean_ms | newfstatat_count | newfstatat_total_sec | newfstatat_mean_ms | pread64_count | pread64_total_sec | pread64_mean_ms | clone_count | clone_total_sec | clone_mean_ms | sched_yield_count | sched_yield_total_sec | sched_yield_mean_ms | futex_count | futex_total_sec | futex_mean_ms | read_count | read_total_sec | read_mean_ms | write_count | write_total_sec | write_mean_ms | futex_total_sec_per_request | futex_total_sec_per_wall_sec | statx_total_sec_per_request | statx_total_sec_per_wall_sec | openat_total_sec_per_request | openat_total_sec_per_wall_sec | estimated_makespan_sec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | /root/client-harness/out/20260325T173324Z_vps-docker-single-task-00-500-full | 159096 | 4.405 | 0.028 | 798797 | 17.343 | 0.022 | 33660 | 0.720 | 0.021 | 70 | 0.002 | 0.021 | 35 | 0.192 | 5.494 | 2 | 0.000 | 0.030 | 103536 | 4230.283 | 40.858 | 278760 | 6.170 | 0.022 | 88553 | 2.697 | 0.030 | 8.461 | 7.037 | 0.035 | 0.029 | 0.009 | 0.007 | 601.173 |
| vps-docker-multi-task-00-500-full | /root/client-harness/out/20260325T200959Z_vps-docker-multi-task-00-500-full | 160329 | 4.547 | 0.028 | 809799 | 17.701 | 0.022 | 33630 | 0.723 | 0.021 | 71 | 0.001 | 0.020 | 36 | 0.219 | 6.078 | 1 | 0.000 | 0.019 | 108268 | 4239.576 | 39.158 | 184784 | 4.057 | 0.022 | 81996 | 2.525 | 0.031 | 8.479 | 7.128 | 0.035 | 0.030 | 0.009 | 0.008 | 594.789 |

**strace Mean Duration Table**

| scenario | vps-docker-single-task-00-500-full | vps-docker-multi-task-00-500-full |
| --- | --- | --- |
| openat | 0.028 | 0.028 |
| statx | 0.022 | 0.022 |
| newfstatat | 0.021 | 0.021 |
| pread64 | 0.021 | 0.020 |
| clone | 5.494 | 6.078 |
| sched_yield | 0.030 | 0.019 |
| futex | 40.858 | 39.158 |
| read | 0.022 | 0.022 |
| write | 0.030 | 0.031 |

**Gateway Runtime Stage Table**

| scenario | bootstrap_load_mean_ms | skills_mean_ms | context_bundle_mean_ms | execution_admission_wait_mean_ms | reply_dispatch_queue_wait_mean_ms | reply_dispatch_queue_hold_mean_ms | reply_dispatch_pending_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 2.758 | 698.850 | 742.934 | 0.143 | 0.002 | 0.003 | 2.000 |
| vps-docker-multi-task-00-500-full | - | - | - | - | - | - | - |

**Node Focus Groups Table**

| scenario | sessions_lock_total_ms | sessions_lock_count | sessions_dir_enum_total_ms | sessions_dir_enum_count | sessions_json_total_ms | sessions_json_count | sessions_tmp_total_ms | sessions_tmp_count | bootstrap_files_total_ms | bootstrap_files_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 298.634 | 272.000 | 77.678 | 68.000 | 164.106 | 68.000 | 327.700 | 272.000 | 6459.129 | 884.000 |
| vps-docker-multi-task-00-500-full | - | - | - | - | - | - | - | - | - | - |

**Runtime Category Samples Table**

| scenario | run_dir | sample_count | fs_worker_exec_count | fs_worker_exec_pct | fs_callback_count | fs_callback_pct | event_loop_poll_count | event_loop_poll_pct | microtask_count | microtask_pct | futex_sync_count | futex_sync_pct | worker_message_count | worker_message_pct | json_parse_count | json_parse_pct | libuv_worker_other_count | libuv_worker_other_pct | gateway_main_other_count | gateway_main_other_pct | v8_worker_count | v8_worker_pct | other_count | other_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | /root/client-harness/out/20260325T173324Z_vps-docker-single-task-00-500-full | 909005 | 480 | 0.053 | - | - | 60562 | 6.662 | 716422 | 78.814 | - | - | 16 | 0.002 | - | - | 5915 | 0.651 | 87316 | 9.606 | 33904 | 3.730 | 4390 | 0.483 |
| vps-docker-multi-task-00-500-full | /root/client-harness/out/20260325T200959Z_vps-docker-multi-task-00-500-full | 894080 | 562 | 0.063 | 7.000 | 0.001 | 55260 | 6.181 | 706170 | 78.983 | - | - | 6 | 0.001 | - | - | 6010 | 0.672 | 89233 | 9.980 | 32183 | 3.600 | 4649 | 0.520 |

**Runtime Category Percent Table**

| scenario | vps-docker-single-task-00-500-full | vps-docker-multi-task-00-500-full |
| --- | --- | --- |
| fs_worker_exec | 0.053 | 0.063 |
| fs_callback | - | 0.001 |
| event_loop_poll | 6.662 | 6.181 |
| microtask | 78.814 | 78.983 |
| futex_sync | - | - |
| worker_message | 0.002 | 0.001 |
| json_parse | - | - |
| libuv_worker_other | 0.651 | 0.672 |
| gateway_main_other | 9.606 | 9.980 |
| v8_worker | 3.730 | 3.600 |
| other | 0.483 | 0.520 |

**Top strace Syscalls: `vps-docker-single-task-00-500-full`**

| scenario | count | total_duration_sec |
| --- | --- | --- |
| futex | 103536 | 4230.283 |
| statx | 798797 | 17.343 |
| read | 278760 | 6.170 |
| openat | 159096 | 4.405 |
| write | 88553 | 2.697 |

**Top strace Syscalls: `vps-docker-multi-task-00-500-full`**

| scenario | count | total_duration_sec |
| --- | --- | --- |
| futex | 108268 | 4239.576 |
| statx | 809799 | 17.701 |
| openat | 160329 | 4.547 |
| read | 184784 | 4.057 |
| write | 81996 | 2.525 |

**Node Runtime Metrics Table**

| scenario | fs_async_mean_ms | fs_callback_mean_ms | promise_callback_mean_ms | event_loop_immediate_mean_ms | event_loop_timers_mean_ms | fs_async_count | fs_callback_count | promise_callback_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vps-docker-single-task-00-500-full | 143.511 | 163.739 | 2.741 | 1.546 | 4.423 | 262759.000 | 339.000 | 22113.000 |
| vps-docker-multi-task-00-500-full | - | - | - | - | - | - | - | - |

**Node Runtime Mean Duration Table**

| scenario | vps-docker-single-task-00-500-full | vps-docker-multi-task-00-500-full |
| --- | --- | --- |
| fs_async | 143.511 | - |
| fs_callback | 163.739 | - |
| promise_callback | 2.741 | - |
| event_loop_immediate | 1.546 | - |
| event_loop_timers | 4.423 | - |

**Top Node FS Paths: `vps-docker-single-task-00-500-full`**

| scenario | count | total_duration_ms |
| --- | --- | --- |
| /home/node/.openclaw/agents/main/sessions/sessions.json.lock | 272 | 298.634 |
| /home/node/.openclaw/workspace/HEARTBEAT.md | 136 | 716.657 |
| /home/node/.openclaw/workspace/USER.md | 136 | 841.987 |
| /home/node/.openclaw/workspace/IDENTITY.md | 136 | 965.654 |
| /home/node/.openclaw/workspace/TOOLS.md | 136 | 1098.315 |

**Node FS Path Categories: `vps-docker-single-task-00-500-full`**

| scenario | count | total_duration_ms |
| --- | --- | --- |
| workspace_bootstrap | 884 | 6459.129 |
| openclaw_runtime | 842 | 1965.928 |
| markdown_docs | 68 | 375.310 |
| git_metadata | 68 | 251.230 |

