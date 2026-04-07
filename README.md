# dmx_orchestrator-agent

OpenClaw 项目 Orchestrator Agent - 负责协调多 Agent 完成软件开发。

## 功能

- 8 阶段状态机驱动
- 自动启动相关 Agent
- 前后端并行开发
- 人工审批门禁
- 产出物管理

## 工具

- `orchestrator_init_project` - 初始化项目
- `orchestrator_get_status` - 查看状态
- `orchestrator_start_stage` - 启动阶段
- `orchestrator_spawn_parallel` - 并行开发
- `orchestrator_advance_stage` - 推进阶段
- `orchestrator_approve_stage` - 审批通过
- `orchestrator_save_artifact` - 保存产出物
- `orchestrator_get_artifacts` - 获取产出物

## 使用

```bash
# 初始化项目
python3 scripts/orchestrator_tools.py init my-project --description "项目描述"

# 查看状态
python3 scripts/orchestrator_tools.py status my-project

# 启动并行开发
python3 scripts/orchestrator_tools.py parallel my-project
```
