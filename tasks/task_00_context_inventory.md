---
id: task_00_context_inventory
name: Context Inventory
category: local_agent_interaction
description: 比 /context list 更贴近真实使用的上下文检查任务。
prompt: |
  请检查当前 OpenClaw 会话上下文，并完成下面三件事：
  1. 用简短语言概括你当前可见的上下文类型。
  2. 说明哪些信息最可能影响后续执行质量。
  3. 给出一个你建议的下一步动作。
  请用 3-5 条简洁要点回答。
---

# Context Inventory

适合本地稳定压测的轻量任务，用于替代单纯的 `/context list`。
