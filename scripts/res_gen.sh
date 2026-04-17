echo "Task 01"

echo "910c multi-5x4w stagger 150 300 500 对比 worker 235b"
python3 scripts/export_tri_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_2/task-01 \
  --res-root res/task-01-run2 \
  --report-dir-name Multi-5x4w-Stag150-300-500-worker \
  --tri vps-docker-qwen3-235b8x2-multi-5x4w-stag150-worker vps-docker-qwen3-235b8x2-multi-5x4w-stag300-worker vps-docker-qwen3-235b8x2-multi-5x4w-stag500-worker \
  --labels multi-5x4w-stag150 multi-5x4w-stag300 multi-5x4w-stag500

echo "910c multi-5x4w stagger 150 300 500 对比 req 235b"
python3 scripts/export_tri_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_2/task-01 \
  --res-root res/task-01-run2 \
  --report-dir-name Multi-5x4w-Stag150-300-500-request \
  --tri vps-docker-qwen3-235b8x2-multi-5x4w-stag150-request vps-docker-qwen3-235b8x2-multi-5x4w-stag300-request vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request \
  --labels multi-5x4w-stag150 multi-5x4w-stag300 multi-5x4w-stag500

echo "910c 4个对比 Single-w, Multi-5x4w-500, Inst 5x4i, 5x2ix2-500 worker 235b"
python3 scripts/export_quad_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_2/task-01 \
  --res-root res/task-01-run2 \
  --report-dir-name SingleW-Mul5x4w-Single5x4i-Mul5x2ix2w-500-worker \
  --quad vps-docker-qwen3-235b8x2-single-20-worker vps-docker-qwen3-235b8x2-multi-5x4w-stag500-worker vps-docker-qwen3-235b8x2-single-inst-5x4i-worker vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-worker \
  --labels single-w multi-5x4w-stag500 multi-inst-5x4i multi-inst-5x2ix2w-500

echo "910c 4个对比 Single-w, Multi-5x4w-500, Inst 5x4i, 5x2ix2-500 req 235b"
python3 scripts/export_quad_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_2/task-01 \
  --res-root res/task-01-run2 \
  --report-dir-name SingleW-Mul5x4w-Single5x4i-Mul5x2ix2w-500-req \
  --quad vps-docker-qwen3-235b8x2-single-20-request vps-docker-qwen3-235b8x2-multi-5x4w-stag500-request vps-docker-qwen3-235b8x2-single-inst-5x4i-request vps-docker-qwen3-235b8x2-multi-inst-5x2ix2w-stag500-request \
  --labels single-w multi-5x4w-stag500 multi-inst-5x4i multi-inst-5x2ix2w-500

echo "910c 4个对比 Single-w, Single-q, Single-inst-w, Single-inst-r 235b"
python3 scripts/export_quad_sys_report.py \
  --out-root /root/Zehao/ClawHarness/out/batch_run_2/task-01 \
  --res-root res/task-01-run2 \
  --report-dir-name SingleW-SingleQ-SingleInstW-SingleInstReq \
  --quad vps-docker-qwen3-235b8x2-single-20-worker vps-docker-qwen3-235b8x2-single-20-request vps-docker-qwen3-235b8x2-single-inst-5x4i-worker vps-docker-qwen3-235b8x2-single-inst-5x4i-request \
  --labels single-w single-r single-inst-w single-inst-r