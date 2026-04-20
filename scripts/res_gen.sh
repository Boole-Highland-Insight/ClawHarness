echo "Task 01"

echo "910c multi-25x4w stagger 150 300 500 对比 worker 235b"
python3 scripts/export_tri_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_5/task-01 \
  --res-root res/task-01/task-01-run5 \
  --report-dir-name Multi-25x4w-Stag150-300-500-worker \
  --tri vps-docker-qwen3-235b-multi-25x4w-stag150-worker vps-docker-qwen3-235b-multi-25x4w-stag300-worker vps-docker-qwen3-235b-multi-25x4w-stag500-worker \
  --labels multi-25x4w-stag150 multi-25x4w-stag300 multi-25x4w-stag500

echo "910c multi-25x4w stagger 150 300 500 对比 req 235b"
python3 scripts/export_tri_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_5/task-01 \
  --res-root res/task-01/task-01-run5 \
  --report-dir-name Multi-25x4w-Stag150-300-500-request \
  --tri vps-docker-qwen3-235b-multi-25x4w-stag150-request vps-docker-qwen3-235b-multi-25x4w-stag300-request vps-docker-qwen3-235b-multi-25x4w-stag500-request \
  --labels multi-25x4w-stag150 multi-25x4w-stag300 multi-25x4w-stag500

echo "910c 4个对比 Single-w, Multi-25x4w-500, Inst 25x4i, 25x2ix2-500 worker 235b"
python3 scripts/export_quad_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_5/task-01 \
  --res-root res/task-01/task-01-run5 \
  --report-dir-name SingleW-Mul25x4w-Single25x4i-Mul25x2ix2w-500-worker \
  --quad vps-docker-qwen3-235b-single-100-worker vps-docker-qwen3-235b-multi-25x4w-stag500-worker vps-docker-qwen3-235b-single-inst-25x4i-worker vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-worker \
  --labels single-w multi-25x4w-stag500 multi-inst-25x4i multi-inst-25x2ix2w-500

echo "910c 4个对比 Single-w, Multi-25x4w-500, Inst 25x4i, 25x2ix2-500 req 235b"
python3 scripts/export_quad_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_5/task-01 \
  --res-root res/task-01/task-01-run5 \
  --report-dir-name SingleW-Mul25x4w-Single25x4i-Mul25x2ix2w-500-req \
  --quad vps-docker-qwen3-235b-single-100-request vps-docker-qwen3-235b-multi-25x4w-stag500-request vps-docker-qwen3-235b-single-inst-25x4i-request vps-docker-qwen3-235b-multi-inst-25x2ix2w-stag500-request \
  --labels single-w multi-25x4w-stag500 multi-inst-25x4i multi-inst-25x2ix2w-500

echo "910c 4个对比 Single-w, Single-q, Single-inst-w, Single-inst-r 235b"
python3 scripts/export_quad_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_5/task-01 \
  --res-root res/task-01/task-01-run5 \
  --report-dir-name SingleW-SingleQ-SingleInstW-SingleInstReq \
  --quad vps-docker-qwen3-235b-single-100-worker vps-docker-qwen3-235b-single-100-request vps-docker-qwen3-235b-single-inst-25x4i-worker vps-docker-qwen3-235b-single-inst-25x4i-request \
  --labels single-w single-r single-inst-w single-inst-r