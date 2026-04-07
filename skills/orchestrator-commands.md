# Orchestrator 命令工具

## orchestrator_init_project

初始化新项目，创建状态目录和 state.json。

**输入**:
```json
{
  "project_name": "项目名称",
  "description": "项目描述（可选）"
}
```

**输出**:
```json
{
  "ok": true,
  "project_path": "~/.openclaw/orchestrator/projects/<项目名>",
  "state_file": "~/.openclaw/orchestrator/projects/<项目名>/state.json",
  "current_stage": "STAGE_1_REQUIREMENTS",
  "message": "项目初始化完成，PM Agent 已就绪"
}
```

---

## orchestrator_get_status

获取项目当前状态。

**输入**:
```json
{
  "project_name": "项目名称"
}
```

**输出**:
```json
{
  "ok": true,
  "current_stage": "STAGE_1_REQUIREMENTS",
  "stage_name": "需求收集",
  "agents": ["product_manager"],
  "pending_approvals": [],
  "blockers": [],
  "artifacts_count": 0,
  "message": "📍 当前阶段: 需求收集\n👥 Agent: PM Agent\n⏳ 等待需求确认..."
}
```

---

## orchestrator_start_stage

为指定阶段启动相关 Agent。

**输入**:
```json
{
  "project_name": "项目名称",
  "stage": "STAGE_1_REQUIREMENTS"
}
```

**输出**:
```json
{
  "ok": true,
  "stage": "STAGE_1_REQUIREMENTS",
  "spawned_agents": [
    {
      "agent_id": "product_manager",
      "session_label": "xxx_project_pm_STAGE_1",
      "status": "spawned"
    }
  ],
  "message": "✅ PM Agent 已启动"
}
```

---

## orchestrator_spawn_parallel

启动前后端并行开发。

**输入**:
```json
{
  "project_name": "项目名称"
}
```

**输出**:
```json
{
  "ok": true,
  "stage": "STAGE_4_5_PARALLEL_DEV",
  "spawned_agents": [
    {
      "agent_id": "backend",
      "session_label": "xxx_project_backend_parallel",
      "status": "spawned"
    },
    {
      "agent_id": "frontend", 
      "session_label": "xxx_project_frontend_parallel",
      "status": "spawned"
    }
  ],
  "message": "🚀 前后端并行开发已启动\n- Backend Agent: 实现 API\n- Frontend Agent: 开发 UI"
}
```

---

## orchestrator_advance_stage

推进到下一阶段。

**输入**:
```json
{
  "project_name": "项目名称"
}
```

**输出**:
```json
{
  "ok": true,
  "from_stage": "STAGE_1_REQUIREMENTS",
  "to_stage": "STAGE_2_ARCHITECTURE",
  "requires_approval": false,
  "message": "✅ 已进入技术方案阶段"
}
```

或需要审批时：

```json
{
  "ok": false,
  "requires_approval": true,
  "from_stage": "STAGE_1_REQUIREMENTS",
  "to_stage": "STAGE_2_ARCHITECTURE",
  "message": "⏳ 需要人工审批才能进入技术方案阶段\n命令: orchestrator_approve_stage"
}
```

---

## orchestrator_approve_stage

人工审批通过，进入下一阶段。

**输入**:
```json
{
  "project_name": "项目名称",
  "from_stage": "STAGE_1_REQUIREMENTS",
  "to_stage": "STAGE_2_ARCHITECTURE"
}
```

**输出**:
```json
{
  "ok": true,
  "new_stage": "STAGE_2_ARCHITECTURE",
  "message": "✅ 审批通过，已进入技术方案阶段"
}
```

---

## orchestrator_save_artifact

保存阶段产出物。

**输入**:
```json
{
  "project_name": "项目名称",
  "stage": "STAGE_1_REQUIREMENTS",
  "artifact_name": "prd.md",
  "content": "# PRD 文档内容..."
}
```

**输出**:
```json
{
  "ok": true,
  "artifact_path": "~/.openclaw/orchestrator/projects/<项目名>/artifacts/STAGE_1_prd.md",
  "message": "✅ 产出物已保存"
}
```

---

## orchestrator_add_blocker

添加阻塞问题。

**输入**:
```json
{
  "project_name": "项目名称",
  "blocker": "后端接口文档不完整",
  "agent": "frontend"
}
```

**输出**:
```json
{
  "ok": true,
  "blocker_id": "blocker_001",
  "message": "⚠️ 阻塞问题已记录：后端接口文档不完整"
}
```

---

## orchestrator_get_artifacts

获取项目的所有产出物。

**输入**:
```json
{
  "project_name": "项目名称"
}
```

**输出**:
```json
{
  "ok": true,
  "artifacts": [
    {
      "stage": "STAGE_1_REQUIREMENTS",
      "name": "prd.md",
      "path": "artifacts/STAGE_1_prd.md",
      "timestamp": "2026-04-07T05:30:00Z"
    },
    {
      "stage": "STAGE_2_ARCHITECTURE", 
      "name": "architecture.md",
      "path": "artifacts/STAGE_2_architecture.md",
      "timestamp": "2026-04-07T06:00:00Z"
    }
  ],
  "message": "📦 共 2 个产出物"
}
```

---

## 使用示例

### 用户: "开始做电商后台项目"

```
Orchestrator:
1. 调用 orchestrator_init_project
   → {"project_name": "ecommerce-admin", "current_stage": "STAGE_1_REQUIREMENTS"}

2. 调用 orchestrator_start_stage
   → {"spawned_agents": [{"agent_id": "product_manager", ...}]}

3. 向用户汇报:
   📁 项目: ecommerce-admin
   📍 当前阶段: 需求收集
   👥 Agent: PM Agent (启动中)
   ⏳ 请描述您的需求...
```

### 用户: "确认需求，可以进入技术方案了"

```
Orchestrator:
1. 调用 orchestrator_approve_stage
   → {"ok": true, "new_stage": "STAGE_2_ARCHITECTURE"}

2. 调用 orchestrator_start_stage
   → {"spawned_agents": [{"agent_id": "tech_lead", ...}, {"agent_id": "backend", ...}]}

3. 向用户汇报:
   ✅ 已进入技术方案阶段
   👥 Agent: Tech Lead, Backend Agent
   ⏳ 正在设计架构...
```

### 用户: "启动并行开发"

```
Orchestrator:
1. 确认当前阶段是 STAGE_4_5_PARALLEL_DEV
2. 调用 orchestrator_spawn_parallel
   → {"spawned_agents": [{"agent_id": "backend", ...}, {"agent_id": "frontend", ...}]}

3. 向用户汇报:
   🚀 前后端并行开发已启动！
   - Backend: 实现 API 接口
   - Frontend: 开发 UI + Mock
   ⏳ 联调将在 Stage 6 进行
```
