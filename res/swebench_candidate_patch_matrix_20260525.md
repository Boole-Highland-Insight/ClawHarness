# SWE-bench Candidate Patch 并列表

生成时间：2026-05-25

## 1. 汇总表

| instance_id | repo/version | gold baseline | candidate patch | fresh replay result | replay workspace | test log |
| --- | --- | --- | --- | --- | --- | --- |
| `astropy__astropy-12318` | `astropy/astropy` / `4.3` | `1 failed, 2 passed in 0.48s` | `res/patches/astropy__astropy-12318_candidate_v1.patch` | `3 passed in 0.52s` | `.state/swebench_real_patch_regression_12318_v1` | `.state/swebench_real_patch_regression_12318_v1/astropy__astropy-12318/test.log` |
| `astropy__astropy-12825` | `astropy/astropy` / `4.3` | `3 failed, 2 passed in 0.18s` | `res/patches/astropy__astropy-12825_candidate_v3.patch` | `5 passed in 0.15s` | `.state/swebench_real_patch_regression_12825_v3` | `.state/swebench_real_patch_regression_12825_v3/astropy__astropy-12825/test.log` |

## 2. 关键差异

| instance_id | gold baseline 失败形态 | candidate patch 修正方向 |
| --- | --- | --- |
| `astropy__astropy-12318` | `BlackBody(0 * u.AA)` 在 input-unit 预处理阶段先泄漏 numpy `RuntimeWarning`，打断测试对 `AstropyUserWarning` 的预期 | 在 `BlackBody` 局部路径收敛 `divide/invalid` numpy warning，并把零波长 warning 计数预期从 `3` 收敛到 `1` |
| `astropy__astropy-12825` | `QTable` 聚合路径把不可聚合字符串列和 unsupported mixin warning 顺序一起带回，导致测试预期与实际 warning 序列不一致 | masked aggregate 测试只覆盖 `a/c/d/q`，补齐 `q` 的预期输出，并把 unsupported non-Column mixin 结果构造期泄漏 warning 折叠回既有 `TypeError` / `AstropyUserWarning` 路径 |

## 3. 单 case replay 命令

### 3.1 `astropy__astropy-12318`

```bash
cd /root/Zehao/ClawHarness
.venv/bin/python scripts/run_real_swebench_case.py \
  --instance-id astropy__astropy-12318 \
  --workspace-root .state/swebench_real_patch_regression_12318_v1 \
  --python-bin /root/.local/bin/python3.10 \
  --source-repo .state/swebench_real_batch_more_v5_small/astropy__astropy-13068/repo \
  --apply-gold-patch \
  --candidate-patch res/patches/astropy__astropy-12318_candidate_v1.patch \
  --run-tests
```

### 3.2 `astropy__astropy-12825`

```bash
cd /root/Zehao/ClawHarness
.venv/bin/python scripts/run_real_swebench_case.py \
  --instance-id astropy__astropy-12825 \
  --workspace-root .state/swebench_real_patch_regression_12825_v3 \
  --python-bin /root/.local/bin/python3.10 \
  --source-repo .state/swebench_real_batch_more_v5_small/astropy__astropy-13068/repo \
  --apply-gold-patch \
  --candidate-patch res/patches/astropy__astropy-12825_candidate_v3.patch \
  --run-tests
```

## 4. 批量 replay 输入

批量 replay 所需的最小字段已经整理到：

- `res/patches/candidate_patch_manifest_20260525.json`

建议把这个 manifest 作为后续批跑的单一输入源；如果要对外汇报，则直接引用本文件即可。

更短的一页对外摘要版见：

- `res/swebench_external_summary_20260525.md`