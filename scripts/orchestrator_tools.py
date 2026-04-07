#!/usr/bin/env python3
"""
Orchestrator Tools - 实现 orchestrator 命令工具

这些工具供 Orchestrator Agent 调用，用于管理项目状态和启动 Agent。
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# ============ 配置 ============

ORCHESTRATOR_BASE_DIR = Path.home() / ".openclaw" / "orchestrator" / "projects"

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

    # 创建目录
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)
    messages_dir.mkdir(parents=True, exist_ok=True)

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
    elif current_stage == "STAGE_4_5_PARALLEL_DEV":
        message_parts.append("\n命令: '启动联调' → 进入测试阶段")
    elif current_stage == "DONE":
        message_parts.append("\n🎉 项目已完成！")

    return {
        "ok": True,
        "current_stage": current_stage,
        "stage_name": STAGE_NAMES.get(current_stage, current_stage),
        "agents": stage_agents,
        "pending_approvals_count": len(pending_approvals),
        "blockers_count": len(blockers),
        "artifacts_count": len(state.get("artifacts", [])),
        "message": "\n".join(message_parts)
    }


def orchestrator_start_stage(project_name: str, stage: str = None) -> Dict[str, Any]:
    """启动指定阶段的 Agent"""
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

        spawned.append({
            "agent_id": agent_id,
            "session_label": session_label,
            "agent_name": agent_info.get("name", agent_id),
            "color": agent_info.get("color", ""),
            "spawn_command": f'sessions_spawn --task "执行 {agent_info.get("name")} 任务" --agent {agent_id} --label {session_label}'
        })

    agent_names = [AGENTS.get(a, {}).get("color", "") + " " + AGENTS.get(a, {}).get("name", a) for a in agents]

    return {
        "ok": True,
        "stage": stage,
        "stage_name": STAGE_NAMES.get(stage, stage),
        "spawned_agents": spawned,
        "message": f"""✅ 已准备好启动 {STAGE_NAMES.get(stage, stage)} 阶段的 Agent:

{chr(10).join(['- ' + a for a in agent_names])}

下一步将调用 sessions_spawn 启动这些 Agent"""
    }


def orchestrator_spawn_parallel(project_name: str) -> Dict[str, Any]:
    """启动前后端并行开发"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    state_file = project_dir / "state.json"

    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    backend_info = AGENTS["backend"]
    frontend_info = AGENTS["frontend"]

    return {
        "ok": True,
        "stage": "STAGE_4_5_PARALLEL_DEV",
        "spawned_agents": [
            {
                "agent_id": "backend",
                "session_label": f"{project_name}_backend_parallel",
                "agent_name": backend_info["name"],
                "color": backend_info["color"],
                "spawn_command": f'sessions_spawn --task "执行后端开发任务" --agent backend --label {project_name}_backend_parallel --background'
            },
            {
                "agent_id": "frontend",
                "session_label": f"{project_name}_frontend_parallel",
                "agent_name": frontend_info["name"],
                "color": frontend_info["color"],
                "spawn_command": f'sessions_spawn --task "执行前端开发任务" --agent frontend --label {project_name}_frontend_parallel --background'
            }
        ],
        "message": f"""🚀 前后端并行开发已准备好！

{backend_info['color']} Backend Agent:
   - 实现 API 接口
   - 使用 TDD 方式
   - 按 openapi.yaml 规范

{frontend_info['color']} Frontend Agent:
   - 开发 UI 组件
   - 使用 Mock 数据先跑通
   - 读取 designs/*.pen 对接 UI

下一步: 调用 sessions_spawn 同时启动这两个 Agent"""
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
        # 添加待审批
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

    # 如果没指定，使用第一个待审批
    pending_list = [p for p in state.get("pending_approvals", []) if not p.get("approved")]

    if not pending_list:
        return {"ok": False, "error": "没有待审批的阶段"}

    approval = pending_list[0]
    from_s = approval["from_stage"]
    to_s = approval["to_stage"]

    # 更新审批状态
    approval["approved"] = True
    approval["approved_at"] = datetime.now().isoformat()

    # 更新当前阶段
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

    # 更新 state.json
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
        lines.append(f"  [{a['stage']}] {a['name']} - {a.get('timestamp', '')}")

    return {
        "ok": True,
        "artifacts": artifacts,
        "message": "\n".join(lines)
    }


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
    }

    if args.command is None:
        parser.print_help()
    else:
        result = commands[args.command]()
        print(json.dumps(result, ensure_ascii=False, indent=2))
