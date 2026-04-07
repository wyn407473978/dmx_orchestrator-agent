#!/usr/bin/env python3
"""
Orchestrator Tools - 实现 orchestrator 命令工具

这些工具供 Orchestrator Agent 调用，用于管理项目状态和启动 Agent。

功能：
1. orchestrator_init_project - 初始化项目
2. orchestrator_get_status - 查看状态
3. orchestrator_start_stage - 启动阶段 + Agent 健康监控
4. orchestrator_spawn_parallel - 并行开发 + 健康监控
5. orchestrator_advance_stage - 推进阶段
6. orchestrator_approve_stage - 审批通过
7. orchestrator_save_artifact - 保存产出物
8. orchestrator_get_artifacts - 获取产出物
9. orchestrator_verify_api - 验证 API 文档 ⭐ 新增
10. orchestrator_health_check - 健康检查 ⭐ 新增
"""

import json
import os
import sys
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# ============ 配置 ============

ORCHESTRATOR_BASE_DIR = Path.home() / ".openclaw" / "orchestrator" / "projects"
SCRIPTS_DIR = Path(__file__).parent

# 8 阶段定义
STAGES = [
    "INIT",
    "STAGE_1_REQUIREMENTS",
    "STAGE_2_ARCHITECTURE",
    "STAGE_2_5_API_REVIEW",
    "STAGE_3_UI_DESIGN",
    "STAGE_4_5_PARALLEL_DEV",
    "STAGE_6_TESTING",
    "STAGE_7_DEPLOY",
    "DONE"
]

STAGE_NAMES = {
    "INIT": "初始化",
    "STAGE_1_REQUIREMENTS": "需求收集",
    "STAGE_2_ARCHITECTURE": "技术方案",
    "STAGE_2_5_API_REVIEW": "API接口确认",
    "STAGE_3_UI_DESIGN": "UI设计",
    "STAGE_4_5_PARALLEL_DEV": "前后端并行开发",
    "STAGE_6_TESTING": "测试验证",
    "STAGE_7_DEPLOY": "部署上线",
    "DONE": "完成"
}

# 阶段需要的 Agent
STAGE_AGENTS = {
    "STAGE_1_REQUIREMENTS": ["product_manager"],
    "STAGE_2_ARCHITECTURE": ["tech_lead", "backend"],
    "STAGE_2_5_API_REVIEW": ["tech_lead", "backend", "frontend"],
    "STAGE_3_UI_DESIGN": ["ui_designer", "frontend"],
    "STAGE_4_5_PARALLEL_DEV": ["backend", "frontend"],
    "STAGE_6_TESTING": ["qa", "backend", "frontend"],
    "STAGE_7_DEPLOY": ["devops"],
}

# 需要人工审批的阶段转换
HUMAN_APPROVAL_REQUIRED = {
    "STAGE_1_REQUIREMENTS": "STAGE_2_ARCHITECTURE",
    "STAGE_2_5_API_REVIEW": "STAGE_3_UI_DESIGN",
    "STAGE_3_UI_DESIGN": "STAGE_4_5_PARALLEL_DEV",
    "STAGE_6_TESTING": "STAGE_7_DEPLOY",
    "STAGE_7_DEPLOY": "DONE",
}

# Agent 定义
AGENTS = {
    "product_manager": {"name": "Product Manager", "color": "🔵"},
    "tech_lead": {"name": "Tech Lead", "color": "🟣"},
    "backend": {"name": "Backend Agent", "color": "🟢"},
    "frontend": {"name": "Frontend Agent", "color": "🟠"},
    "ui_designer": {"name": "UI Designer", "color": "🟡"},
    "qa": {"name": "QA Agent", "color": "🔴"},
    "devops": {"name": "DevOps Agent", "color": "⚪"},
}


# ============ 工具实现 ============

def orchestrator_init_project(project_name: str, description: str = "") -> Dict[str, Any]:
    """初始化新项目"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    artifacts_dir = project_dir / "artifacts"
    events_dir = project_dir / "events"
    messages_dir = project_dir / "messages"
    api_contract_dir = project_dir / "api-contract"
    designs_dir = project_dir / "designs"

    # 创建目录
    for d in [artifacts_dir, events_dir, messages_dir, api_contract_dir, designs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    state_file = project_dir / "state.json"

    # 初始化状态
    state = {
        "project_name": project_name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "current_stage": "STAGE_1_REQUIREMENTS",
        "stage_history": [
            {
                "from": "INIT",
                "to": "STAGE_1_REQUIREMENTS",
                "reason": "项目初始化",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "pending_approvals": [],
        "artifacts": [],
        "agent_outputs": [],
        "active_agents": {},  # 新增：活跃 Agent 列表
        "events": [],
        "blockers": []
    }

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return {
        "ok": True,
        "project_path": str(project_dir),
        "state_file": str(state_file),
        "current_stage": "STAGE_1_REQUIREMENTS",
        "stage_name": STAGE_NAMES["STAGE_1_REQUIREMENTS"],
        "message": f"""✅ 项目 '{project_name}' 初始化完成！

📍 当前阶段: {STAGE_NAMES['STAGE_1_REQUIREMENTS']}
👥 需要 Agent: {AGENTS['product_manager']['color']} Product Manager

目录结构:
  {project_dir}/
  ├── state.json          # 项目状态
  ├── artifacts/          # 产出物
  ├── api-contract/       # API 文档
  ├── designs/           # UI 设计 (.pen)
  ├── events/            # 事件日志
  └── messages/          # 消息队列

下一步: 启动 PM Agent 进行需求收集"""
    }


def orchestrator_get_status(project_name: str) -> Dict[str, Any]:
    """获取项目状态"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {
            "ok": False,
            "error": f"项目 '{project_name}' 不存在"
        }

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    current_stage = state["current_stage"]
    stage_agents = STAGE_AGENTS.get(current_stage, [])
    pending_approvals = [p for p in state.get("pending_approvals", []) if not p.get("approved")]
    blockers = [b for b in state.get("blockers", []) if not b.get("resolved")]
    active_agents = state.get("active_agents", {})

    # 构建 Agent 显示
    agent_display = []
    for agent_id in stage_agents:
        agent_info = AGENTS.get(agent_id, {})
        agent_display.append(f"{agent_info.get('color', '')} {agent_info.get('name', agent_id)}")

    message_parts = [
        f"📁 项目: {project_name}",
        f"📍 当前阶段: {STAGE_NAMES.get(current_stage, current_stage)}",
    ]

    if agent_display:
        message_parts.append(f"👥 当前 Agent: {', '.join(agent_display)}")

    if active_agents:
        message_parts.append(f"🔄 活跃会话: {len(active_agents)} 个")

    if pending_approvals:
        message_parts.append(f"⏳ 待审批: {len(pending_approvals)} 个")

    if blockers:
        message_parts.append(f"⚠️ 阻塞: {len(blockers)} 个")
        for b in blockers[:3]:
            message_parts.append(f"   - {b.get('blocker', '')}")

    message_parts.append(f"\n📦 产出物: {len(state.get('artifacts', []))} 个")

    # 添加下一步提示
    if current_stage == "STAGE_1_REQUIREMENTS":
        message_parts.append("\n命令: '确认需求' → 推进到技术方案")
    elif current_stage == "STAGE_2_5_API_REVIEW":
        message_parts.append("\n命令: '确认API' → 推进到UI设计")
    elif current_stage == "STAGE_4_5_PARALLEL_DEV":
        message_parts.append("\n命令: '启动联调' → 进入测试阶段")
    elif current_stage == "DONE":
        message_parts.append("\n🎉 项目已完成！")

    return {
        "ok": True,
        "current_stage": current_stage,
        "stage_name": STAGE_NAMES.get(current_stage, current_stage),
        "agents": stage_agents,
        "active_agents_count": len(active_agents),
        "pending_approvals_count": len(pending_approvals),
        "blockers_count": len(blockers),
        "artifacts_count": len(state.get("artifacts", [])),
        "message": "\n".join(message_parts)
    }


def orchestrator_start_stage(project_name: str, stage: str = None) -> Dict[str, Any]:
    """启动指定阶段的 Agent，同时启动健康监控"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    # 如果没指定 stage，使用当前 stage
    if stage is None:
        stage = state["current_stage"]

    agents = STAGE_AGENTS.get(stage, [])

    if not agents:
        return {
            "ok": True,
            "stage": stage,
            "spawned_agents": [],
            "message": f"阶段 {STAGE_NAMES.get(stage, stage)} 没有需要启动的 Agent"
        }

    # 生成 spawn 命令
    spawned = []
    for agent_id in agents:
        agent_info = AGENTS.get(agent_id, {})
        session_label = f"{project_name}_{agent_id}_{stage.lower()}"
        task = _generate_agent_task(agent_id, stage, project_name)

        spawned.append({
            "agent_id": agent_id,
            "session_label": session_label,
            "agent_name": agent_info.get("name", agent_id),
            "color": agent_info.get("color", ""),
            "task": task,
            "spawn_command": f'sessions_spawn --task "{task}" --agent {agent_id} --label {session_label} --background'
        })

        # 注册到活跃 Agent 列表
        state.setdefault("active_agents", {})[session_label] = {
            "agent_id": agent_id,
            "session_label": session_label,
            "stage": stage,
            "task": task,
            "started_at": datetime.now().isoformat(),
            "restart_count": 0
        }

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 启动健康监控
    _start_health_monitor(project_name)

    agent_names = [AGENTS.get(a, {}).get("color", "") + " " + AGENTS.get(a, {}).get("name", a) for a in agents]

    return {
        "ok": True,
        "stage": stage,
        "stage_name": STAGE_NAMES.get(stage, stage),
        "spawned_agents": spawned,
        "health_monitor": "已启动",
        "message": f"""✅ 已启动 {STAGE_NAMES.get(stage, stage)} 阶段的 Agent:

{chr(10).join(['- ' + a for a in agent_names])}

🔄 健康监控已启动
⏳ Agent 正在运行中..."""
    }


def orchestrator_spawn_parallel(project_name: str) -> Dict[str, Any]:
    """启动前后端并行开发 + 健康监控"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    backend_info = AGENTS["backend"]
    frontend_info = AGENTS["frontend"]

    # 更新状态，注册活跃 Agent
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    backend_label = f"{project_name}_backend_parallel"
    frontend_label = f"{project_name}_frontend_parallel"

    backend_task = """你是一个 Backend Agent，负责后端开发。

当前项目: {project}
当前阶段: Stage 4 - 后端开发

你的任务:
1. 读取 api-contract/openapi.yaml 了解接口规范
2. 使用 TDD 方式开发后端 API
3. 每个 API 开发完成后，更新 artifacts/backend_api_status.md
4. 完成后通过 sessions_send 通知 Orchestrator

项目目录: ~/.openclaw/orchestrator/projects/{project}/artifacts/""".format(project=project_name)

    frontend_task = """你是一个 Frontend Agent，负责前端开发。

当前项目: {project}
当前阶段: Stage 5 - 前端开发

你的任务:
1. 读取 designs/pages/*.pen 了解 UI 设计
2. 使用 Mock 数据先开发 UI 组件
3. 当后端 API 准备好后，切换到真实接口对接
4. 完成后通过 sessions_send 通知 Orchestrator

项目目录: ~/.openclaw/orchestrator/projects/{project}/artifacts/""".format(project=project_name)

    state.setdefault("active_agents", {})[backend_label] = {
        "agent_id": "backend",
        "session_label": backend_label,
        "stage": "STAGE_4_5_PARALLEL_DEV",
        "task": backend_task,
        "started_at": datetime.now().isoformat(),
        "restart_count": 0
    }

    state["active_agents"][frontend_label] = {
        "agent_id": "frontend",
        "session_label": frontend_label,
        "stage": "STAGE_4_5_PARALLEL_DEV",
        "task": frontend_task,
        "started_at": datetime.now().isoformat(),
        "restart_count": 0
    }

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 启动健康监控
    _start_health_monitor(project_name)

    return {
        "ok": True,
        "stage": "STAGE_4_5_PARALLEL_DEV",
        "spawned_agents": [
            {
                "agent_id": "backend",
                "session_label": backend_label,
                "agent_name": backend_info["name"],
                "color": backend_info["color"],
                "task": backend_task,
                "spawn_command": f'sessions_spawn --task "执行后端开发任务" --agent backend --label {backend_label} --background'
            },
            {
                "agent_id": "frontend",
                "session_label": frontend_label,
                "agent_name": frontend_info["name"],
                "color": frontend_info["color"],
                "task": frontend_task,
                "spawn_command": f'sessions_spawn --task "执行前端开发任务" --agent frontend --label {frontend_label} --background'
            }
        ],
        "health_monitor": "已启动",
        "message": f"""🚀 前后端并行开发已启动！

{backend_info['color']} Backend Agent:
   - 实现 API 接口
   - 使用 TDD 方式
   - 按 openapi.yaml 规范

{frontend_info['color']} Frontend Agent:
   - 开发 UI 组件
   - 使用 Mock 数据先跑通
   - 读取 designs/*.pen 对接 UI

🔄 健康监控已启动
⏳ 前后端正在并行开发中...
联调将在 Stage 6 进行"""
    }


def orchestrator_advance_stage(project_name: str) -> Dict[str, Any]:
    """推进到下一阶段（自动）"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    current_stage = state["current_stage"]

    # 找到下一个阶段
    try:
        current_idx = STAGES.index(current_stage)
        if current_idx >= len(STAGES) - 1:
            return {"ok": False, "error": "已经是最后一个阶段"}
        next_stage = STAGES[current_idx + 1]
    except ValueError:
        return {"ok": False, "error": f"未知阶段: {current_stage}"}

    # 检查是否需要审批
    required_approval = HUMAN_APPROVAL_REQUIRED.get(current_stage)
    if required_approval and required_approval == next_stage:
        pending = {
            "id": f"approval_{len(state.get('pending_approvals', []))}",
            "from_stage": current_stage,
            "to_stage": next_stage,
            "timestamp": datetime.now().isoformat(),
            "approved": False
        }
        state.setdefault("pending_approvals", []).append(pending)

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        return {
            "ok": False,
            "requires_approval": True,
            "from_stage": current_stage,
            "to_stage": next_stage,
            "from_stage_name": STAGE_NAMES.get(current_stage, current_stage),
            "to_stage_name": STAGE_NAMES.get(next_stage, next_stage),
            "message": f"""⏳ 需要人工审批才能进入下一阶段

当前阶段: {STAGE_NAMES.get(current_stage, current_stage)}
目标阶段: {STAGE_NAMES.get(next_stage, next_stage)}

请说"确认"或"审批通过"来继续"""
        }

    # 直接推进
    state["current_stage"] = next_stage
    state["stage_history"].append({
        "from": current_stage,
        "to": next_stage,
        "reason": "自动推进",
        "timestamp": datetime.now().isoformat()
    })

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    next_agents = STAGE_AGENTS.get(next_stage, [])

    return {
        "ok": True,
        "from_stage": current_stage,
        "to_stage": next_stage,
        "from_stage_name": STAGE_NAMES.get(current_stage, current_stage),
        "to_stage_name": STAGE_NAMES.get(next_stage, next_stage),
        "requires_approval": False,
        "next_agents": next_agents,
        "message": f"""✅ 已进入 {STAGE_NAMES.get(next_stage, next_stage)} 阶段

{"👥 准备启动: " + ", ".join([AGENTS.get(a, {}).get("color", "") + " " + AGENTS.get(a, {}).get("name", a) for a in next_agents]) if next_agents else ""}"""
    }


def orchestrator_approve_stage(project_name: str, from_stage: str = None, to_stage: str = None) -> Dict[str, Any]:
    """人工审批通过"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    pending_list = [p for p in state.get("pending_approvals", []) if not p.get("approved")]

    if not pending_list:
        return {"ok": False, "error": "没有待审批的阶段"}

    approval = pending_list[0]
    from_s = approval["from_stage"]
    to_s = approval["to_stage"]

    approval["approved"] = True
    approval["approved_at"] = datetime.now().isoformat()
    state["current_stage"] = to_s
    state["stage_history"].append({
        "from": from_s,
        "to": to_s,
        "reason": f"人工审批通过: {from_s} → {to_s}",
        "timestamp": datetime.now().isoformat()
    })

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    next_agents = STAGE_AGENTS.get(to_s, [])

    return {
        "ok": True,
        "new_stage": to_s,
        "new_stage_name": STAGE_NAMES.get(to_s, to_s),
        "approved_from": from_s,
        "approved_to": to_s,
        "message": f"""✅ 审批通过！

已从 {STAGE_NAMES.get(from_s, from_s)} 进入 {STAGE_NAMES.get(to_s, to_s)} 阶段

{"👥 将启动: " + ", ".join([AGENTS.get(a, {}).get("color", "") + " " + AGENTS.get(a, {}).get("name", a) for a in next_agents]) if next_agents else "🎉 项目完成！"}"""
    }


def orchestrator_save_artifact(project_name: str, stage: str, artifact_name: str, content: str) -> Dict[str, Any]:
    """保存产出物"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    artifacts_dir = project_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifact_file = artifacts_dir / f"{stage}_{artifact_name}"

    with open(artifact_file, 'w', encoding='utf-8') as f:
        f.write(content)

    state_file = project_dir / "state.json"
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    artifact_entry = {
        "stage": stage,
        "name": artifact_name,
        "path": str(artifact_file),
        "timestamp": datetime.now().isoformat()
    }
    state.setdefault("artifacts", []).append(artifact_entry)

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return {
        "ok": True,
        "artifact_path": str(artifact_file),
        "message": f"✅ 产出物已保存: {artifact_name}"
    }


def orchestrator_get_artifacts(project_name: str) -> Dict[str, Any]:
    """获取所有产出物"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    artifacts = state.get("artifacts", [])

    if not artifacts:
        return {
            "ok": True,
            "artifacts": [],
            "message": "📦 暂无产出物"
        }

    lines = ["📦 产出物列表:"]
    for a in artifacts:
        stage_name = STAGE_NAMES.get(a['stage'], a['stage'])
        lines.append(f"  [{stage_name}] {a['name']} - {a.get('timestamp', '')[:19]}")

    return {
        "ok": True,
        "artifacts": artifacts,
        "message": "\n".join(lines)
    }


def orchestrator_verify_api(project_name: str) -> Dict[str, Any]:
    """验证 API 文档"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    api_contract_dir = project_dir / "api-contract"

    # 检查 openapi.yaml 是否存在
    openapi_file = api_contract_dir / "openapi.yaml"
    if not openapi_file.exists():
        openapi_file = api_contract_dir / "openapi.json"

    if not openapi_file.exists():
        return {
            "ok": False,
            "error": "API 文档不存在，请先运行 generate 命令",
            "message": """❌ openapi.yaml 不存在

请先创建 API 文档:
1. 手动创建 api-contract/openapi.yaml
2. 或使用 openapi-tools generate 命令扫描代码"""
        }

    # 验证 API 文档
    try:
        import subprocess
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "openapi_tools.py"), "verify", project_name],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout + result.stderr

        if "✅ 通过" in output or "没有发现问题" in output:
            return {
                "ok": True,
                "verified": True,
                "message": "✅ API 文档验证通过！\n\n所有接口定义正确，可以进入下一阶段。"
            }
        else:
            # 提取问题
            issues = []
            for line in output.split('\n'):
                if line.strip().startswith(('-', '1.', '2.', '3.')):
                    issues.append(line.strip())

            return {
                "ok": False,
                "verified": False,
                "issues": issues,
                "message": f"""❌ API 文档验证失败

发现 {len(issues)} 个问题:
{chr(10).join(issues)}

请修复后重新验证。"""
            }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": f"❌ 验证过程出错: {str(e)}"
        }


def orchestrator_health_check(project_name: str) -> Dict[str, Any]:
    """Agent 健康检查"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    active_agents = state.get("active_agents", {})

    if not active_agents:
        return {
            "ok": True,
            "healthy": [],
            "unhealthy": [],
            "message": "📊 健康检查完成\n\n没有活跃的 Agent"
        }

    healthy = []
    unhealthy = []

    # 检查每个 Agent
    for session_label, agent_info in active_agents.items():
        agent_id = agent_info.get("agent_id")
        agent_name = AGENTS.get(agent_id, {}).get("name", agent_id)
        restart_count = agent_info.get("restart_count", 0)

        # 简单检查：看 session 是否存在
        try:
            result = subprocess.run(
                ["openclaw", "sessions", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and session_label in result.stdout:
                healthy.append({
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "session_label": session_label,
                    "restart_count": restart_count,
                    "last_seen": agent_info.get("last_heartbeat", agent_info.get("started_at"))
                })
            else:
                unhealthy.append({
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "session_label": session_label,
                    "restart_count": restart_count,
                    "reason": "Session not found"
                })

        except Exception as e:
            unhealthy.append({
                "agent_id": agent_id,
                "agent_name": agent_name,
                "session_label": session_label,
                "restart_count": restart_count,
                "reason": str(e)
            })

    status = "✅ 健康" if not unhealthy else f"⚠️ {len(unhealthy)} 个异常"

    lines = [f"📊 健康检查完成 - {status}"]
    lines.append(f"\n活跃 Agent: {len(healthy)} 个")

    if healthy:
        lines.append("\n✅ 正常运行的 Agent:")
        for a in healthy:
            lines.append(f"   {AGENTS.get(a['agent_id'], {}).get('color', '')} {a['agent_name']}")

    if unhealthy:
        lines.append(f"\n⚠️ 异常的 Agent ({len(unhealthy)} 个):")
        for a in unhealthy:
            lines.append(f"   {a['agent_name']}: {a['reason']}")
            if a['restart_count'] > 0:
                lines.append(f"      已重启 {a['restart_count']} 次")

    return {
        "ok": True,
        "healthy_count": len(healthy),
        "unhealthy_count": len(unhealthy),
        "healthy": healthy,
        "unhealthy": unhealthy,
        "message": "\n".join(lines)
    }


# ============ 辅助函数 ============

def _generate_agent_task(agent_id: str, stage: str, project_name: str) -> str:
    """生成 Agent 任务描述"""
    tasks = {
        "product_manager": f"""你是一个 Product Manager (产品经理)，负责需求分析。

当前项目: {project_name}
当前阶段: {STAGE_NAMES.get(stage, stage)}

你的任务:
1. 与用户进行需求访谈，了解核心功能、目标用户、使用场景
2. 整理需求，生成 PRD 文档
3. 确保需求清晰、无歧义后才算完成

项目目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/

开始执行需求收集任务！""",

        "tech_lead": f"""你是一个 Tech Lead (技术负责人)，负责架构设计。

当前项目: {project_name}
当前阶段: {STAGE_NAMES.get(stage, stage)}

你的任务:
1. 设计系统架构（单体/微服务/模块化）
2. 设计数据库 schema
3. 输出 API 设计（OpenAPI 规范）
4. 产出: architecture.md, database.md, openapi.yaml

项目目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/

开始执行技术方案设计！""",

        "backend": f"""你是一个 Backend Agent，负责后端开发。

当前项目: {project_name}
当前阶段: {STAGE_NAMES.get(stage, stage)}

你的任务:
1. 实现后端 API 接口
2. 使用 TDD 方式：先写测试 → 写实现 → 重构
3. 确保 CI Gate 通过

项目目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/

开始执行后端开发！""",

        "frontend": f"""你是一个 Frontend Agent，负责前端开发。

当前项目: {project_name}
当前阶段: {STAGE_NAMES.get(stage, stage)}

你的任务:
1. 读取 designs/pages/*.pen 了解 UI 设计
2. 实现前端 UI 组件
3. 对接后端 API

项目目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/

开始执行前端开发！""",

        "ui_designer": f"""你是一个 UI Designer，负责界面设计。

当前项目: {project_name}
当前阶段: {STAGE_NAMES.get(stage, stage)}

你的任务:
1. 根据需求设计 UI 界面
2. 生成 UI Spec JSON
3. 使用 pencil-canvas 生成 .pen 文件

项目目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/

开始执行 UI 设计！""",

        "qa": f"""你是一个 QA Agent，负责测试验证。

当前项目: {project_name}
当前阶段: {STAGE_NAMES.get(stage, stage)}

你的任务:
1. 执行测试用例
2. 进行边界测试和异常测试
3. 输出测试报告

项目目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/

开始执行测试验证！""",

        "devops": f"""你是一个 DevOps Agent，负责部署上线。

当前项目: {project_name}
当前阶段: {STAGE_NAMES.get(stage, stage)}

你的任务:
1. 构建 Docker 镜像
2. 部署到服务器
3. 执行部署验证

项目目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/

开始执行部署上线！""",
    }

    return tasks.get(agent_id, f"执行 {agent_id} 在阶段 {stage} 的任务")


def _start_health_monitor(project_name: str):
    """启动健康监控（在后台运行）"""
    try:
        # 检查是否已经在运行
        result = subprocess.run(
            ["pgrep", "-f", f"agent_health.py.*{project_name}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:  # 没有运行，启动它
            subprocess.Popen(
                ["python3", str(SCRIPTS_DIR / "agent_health.py"), "monitor", project_name, "start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"[Orchestrator] 🔄 健康监控已启动: {project_name}")
    except Exception as e:
        print(f"[Orchestrator] ⚠️ 启动健康监控失败: {str(e)}")


# ============ CLI 入口 ============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrator Tools")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    p_init = subparsers.add_parser("init", help="初始化项目")
    p_init.add_argument("project", help="项目名称")
    p_init.add_argument("--description", "-d", default="")

    p_status = subparsers.add_parser("status", help="查看状态")
    p_status.add_argument("project", help="项目名称")

    p_start = subparsers.add_parser("start", help="启动阶段")
    p_start.add_argument("project", help="项目名称")
    p_start.add_argument("--stage", "-s", default=None)

    p_parallel = subparsers.add_parser("parallel", help="并行开发")
    p_parallel.add_argument("project", help="项目名称")

    p_advance = subparsers.add_parser("advance", help="推进阶段")
    p_advance.add_argument("project", help="项目名称")

    p_approve = subparsers.add_parser("approve", help="审批通过")
    p_approve.add_argument("project", help="项目名称")

    p_save = subparsers.add_parser("save", help="保存产出物")
    p_save.add_argument("project", help="项目名称")
    p_save.add_argument("--stage", "-s", required=True)
    p_save.add_argument("--name", "-n", required=True)
    p_save.add_argument("--content", "-c", required=True)

    p_artifacts = subparsers.add_parser("artifacts", help="查看产出物")
    p_artifacts.add_argument("project", help="项目名称")

    p_verify = subparsers.add_parser("verify-api", help="验证API文档")
    p_verify.add_argument("project", help="项目名称")

    p_health = subparsers.add_parser("health", help="健康检查")
    p_health.add_argument("project", help="项目名称")

    args = parser.parse_args()

    commands = {
        "init": lambda: orchestrator_init_project(args.project, args.description),
        "status": lambda: orchestrator_get_status(args.project),
        "start": lambda: orchestrator_start_stage(args.project, args.stage),
        "parallel": lambda: orchestrator_spawn_parallel(args.project),
        "advance": lambda: orchestrator_advance_stage(args.project),
        "approve": lambda: orchestrator_approve_stage(args.project),
        "save": lambda: orchestrator_save_artifact(args.project, args.stage, args.name, args.content),
        "artifacts": lambda: orchestrator_get_artifacts(args.project),
        "verify-api": lambda: orchestrator_verify_api(args.project),
        "health": lambda: orchestrator_health_check(args.project),
    }

    if args.command is None:
        parser.print_help()
    else:
        result = commands[args.command]()
        print(json.dumps(result, ensure_ascii=False, indent=2))
