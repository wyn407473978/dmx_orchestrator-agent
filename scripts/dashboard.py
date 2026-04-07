#!/usr/bin/env python3
"""
Dashboard - 项目可视化面板

功能：
1. 终端 UI 显示项目状态
2. ASCII 进度条
3. 实时刷新

Dashboard 布局：
┌─────────────────────────────────────────────────────────────┐
│  📁 项目名称                                    [状态: 运行中]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📍 当前阶段: 前后端并行开发                                 │
│                                                             │
│  进度: ████████████░░░░░░░░ 60%                            │
│                                                             │
│  👥 Agent 状态                                              │
│  ┌────────────┬────────┬────────┐                         │
│  │ Agent      │ 状态   │ 重启   │                         │
│  ├────────────┼────────┼────────┤                         │
│  │ 🔵 PM      │ ✅ 完成 │   0    │                         │
│  │ 🟢 Backend │ 🔄 运行 │   0    │                         │
│  │ 🟠 Frontend│ 🔄 运行 │   0    │                         │
│  └────────────┴────────┴────────┘                         │
│                                                             │
│  📦 产出物 (3)                                              │
│  ├── PRD文档.md                                             │
│  ├── architecture.md                                        │
│  └── openapi.yaml                                           │
│                                                             │
│  ⏳ 待审批 (1)                                              │
│  └── STAGE_3 → STAGE_4_5_PARALLEL_DEV                     │
│                                                             │
│  ⚠️ 阻塞 (0)                                                │
│  └── 无                                                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  更新: 2026-04-07 05:42:30          [刷新: 3秒后]         │
└─────────────────────────────────────────────────────────────┘
"""

import json
import sys
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


# ============ 配置 ============

ORCHESTRATOR_BASE_DIR = Path.home() / ".openclaw" / "orchestrator" / "projects"
REFRESH_INTERVAL = 5  # 秒


# ============ Agent 定义 ============

AGENTS = {
    "product_manager": {"name": "PM", "color": "🔵", "icon": "P"},
    "tech_lead": {"name": "TL", "color": "🟣", "icon": "T"},
    "backend": {"name": "BE", "color": "🟢", "icon": "B"},
    "frontend": {"name": "FE", "color": "🟠", "icon": "F"},
    "ui_designer": {"name": "UI", "color": "🟡", "icon": "U"},
    "qa": {"name": "QA", "color": "🔴", "icon": "Q"},
    "devops": {"name": "OP", "color": "⚪", "icon": "D"},
}

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

STAGE_AGENTS = {
    "STAGE_1_REQUIREMENTS": ["product_manager"],
    "STAGE_2_ARCHITECTURE": ["tech_lead", "backend"],
    "STAGE_2_5_API_REVIEW": ["tech_lead", "backend", "frontend"],
    "STAGE_3_UI_DESIGN": ["ui_designer", "frontend"],
    "STAGE_4_5_PARALLEL_DEV": ["backend", "frontend"],
    "STAGE_6_TESTING": ["qa", "backend", "frontend"],
    "STAGE_7_DEPLOY": ["devops"],
}

STAGE_ORDER = [
    "STAGE_1_REQUIREMENTS",
    "STAGE_2_ARCHITECTURE",
    "STAGE_2_5_API_REVIEW",
    "STAGE_3_UI_DESIGN",
    "STAGE_4_5_PARALLEL_DEV",
    "STAGE_6_TESTING",
    "STAGE_7_DEPLOY",
    "DONE"
]


# ============ 状态获取 ============

def get_project_state(project_name: str) -> Optional[Dict[str, Any]]:
    """获取项目状态"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return None

    with open(state_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_agent_status(state: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    """获取 Agent 状态"""
    active_agents = state.get("active_agents", {})

    for session_label, agent_info in active_agents.items():
        if agent_info.get("agent_id") == agent_id:
            return {
                "status": "running",
                "session": session_label,
                "started_at": agent_info.get("started_at", ""),
                "restart_count": agent_info.get("restart_count", 0)
            }

    # 检查是否已完成
    completed_agents = state.get("agent_outputs", [])
    for output in completed_agents:
        if isinstance(output, dict) and output.get("agent") == agent_id:
            return {
                "status": "completed",
                "completed_at": output.get("timestamp", ""),
                "restart_count": 0
            }

    # 检查是否在当前阶段需要
    current_stage = state.get("current_stage", "")
    if agent_id in STAGE_AGENTS.get(current_stage, []):
        return {"status": "pending", "restart_count": 0}

    return {"status": "idle", "restart_count": 0}


def calculate_progress(state: Dict[str, Any]) -> float:
    """计算进度百分比"""
    current_stage = state.get("current_stage", "INIT")

    try:
        current_idx = STAGE_ORDER.index(current_stage)
        total_stages = len(STAGE_ORDER)
        return round((current_idx / (total_stages - 1)) * 100, 1)
    except ValueError:
        return 0.0


def get_progress_bar(progress: float, width: int = 20) -> str:
    """生成分隔符进度条"""
    filled = int(width * progress / 100)
    empty = width - filled
    return "█" * filled + "░" * empty


# ============ Dashboard 渲染 ============

def render_dashboard(project_name: str):
    """渲染 Dashboard"""
    state = get_project_state(project_name)

    if not state:
        print(f"❌ 项目 '{project_name}' 不存在")
        return

    current_stage = state.get("current_stage", "INIT")
    current_stage_name = STAGE_NAMES.get(current_stage, current_stage)
    progress = calculate_progress(state)
    progress_bar = get_progress_bar(progress)

    # Agent 状态
    active_agents = state.get("active_agents", {})
    pending_approvals = [p for p in state.get("pending_approvals", []) if not p.get("approved")]
    blockers = [b for b in state.get("blockers", []) if not b.get("resolved")]
    artifacts = state.get("artifacts", [])

    # 检查 Agent 健康状态
    agent_health = {}
    for agent_id in AGENTS.keys():
        agent_status = get_agent_status(state, agent_id)
        agent_health[agent_id] = agent_status

    # 构建输出
    lines = []

    # Header
    lines.append("┌" + "─" * 68 + "┐")
    project_status = "🏃 运行中" if current_stage not in ["DONE", "INIT"] else ("🎉 完成" if current_stage == "DONE" else "⏸️ 等待")
    lines.append(f"│  📁 {project_name:<50} [{project_status}] │")
    lines.append("├" + "─" * 68 + "┤")

    # 当前阶段和进度
    lines.append(f"│  📍 当前阶段: {current_stage_name:<47} │")
    lines.append(f"│  进度: {progress_bar} {progress:5.1f}%{' ' * (30 - len(progress_bar))}│")
    lines.append("│" + " " * 68 + "│")

    # Agent 状态表格
    lines.append("│  👥 Agent 状态" + " " * 54 + "│")
    lines.append("│  ┌──────────┬────────┬────────┐" + " " * 20 + "│")
    lines.append("│  │ Agent    │ 状态   │ 重启   │" + " " * 20 + "│")
    lines.append("│  ├──────────┼────────┼────────┤" + " " * 20 + "│")

    for agent_id, info in AGENTS.items():
        status_info = agent_health.get(agent_id, {})
        status = status_info.get("status", "idle")

        if status == "running":
            status_text = "🔄 运行"
            status_icon = "🔄"
        elif status == "completed":
            status_text = "✅ 完成"
            status_icon = "✅"
        elif status == "pending":
            status_text = "⏳ 等待"
            status_icon = "⏳"
        else:
            status_text = "⚪ 空闲"
            status_icon = "⚪"

        restart_count = status_info.get("restart_count", 0)
        restart_text = str(restart_count) if restart_count > 0 else "0"

        lines.append(f"│  │ {info['icon']} {info['name']:<7} │ {status_text:<7} │ {restart_text:<7} │" + " " * 20 + "│")

    lines.append("│  └──────────┴────────┴────────┘" + " " * 20 + "│")
    lines.append("│" + " " * 68 + "│")

    # 产出物
    if artifacts:
        lines.append(f"│  📦 产出物 ({len(artifacts)})" + " " * 50 + "│")
        for i, artifact in enumerate(artifacts[:5]):
            name = artifact.get("name", "unknown")
            lines.append(f"│    ├── {name:<60}│")
        if len(artifacts) > 5:
            lines.append(f"│    └── ... 还有 {len(artifacts) - 5} 个" + " " * 44 + "│")
    else:
        lines.append(f"│  📦 产出物 (0)" + " " * 54 + "│")

    lines.append("│" + " " * 68 + "│")

    # 待审批
    if pending_approvals:
        lines.append(f"│  ⏳ 待审批 ({len(pending_approvals)})" + " " * 48 + "│")
        for p in pending_approvals:
            from_s = STAGE_NAMES.get(p.get("from_stage", ""), p.get("from_stage", ""))
            to_s = STAGE_NAMES.get(p.get("to_stage", ""), p.get("to_stage", ""))
            lines.append(f"│    └── {from_s} → {to_s:<46}│")
    else:
        lines.append(f"│  ⏳ 待审批 (0)" + " " * 54 + "│")

    lines.append("│" + " " * 68 + "│")

    # 阻塞
    if blockers:
        lines.append(f"│  ⚠️  阻塞 ({len(blockers)})" + " " * 53 + "│")
        for b in blockers[:3]:
            blocker_text = b.get("blocker", "")[:50]
            lines.append(f"│    └── {blocker_text:<59}│")
    else:
        lines.append(f"│  ⚠️  阻塞 (0)" + " " * 54 + "│")

    # Footer
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("├" + "─" * 68 + "┤")
    lines.append(f"│  更新: {now}          [刷新: {REFRESH_INTERVAL}秒后]  │")
    lines.append("└" + "─" * 68 + "┘")

    return "\n".join(lines)


# ============ CLI ============

def cmd_view(args):
    """查看 Dashboard"""
    project_name = args.project

    if not args.live:
        # 单次输出
        result = render_dashboard(project_name)
        print(result)
        return

    # 实时刷新模式
    print(f"\n🎛️  Dashboard - {project_name}")
    print("按 Ctrl+C 退出\n")

    try:
        while True:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')

            result = render_dashboard(project_name)
            print(result)

            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard 已退出")


def cmd_list(args):
    """列出所有项目"""
    if not ORCHESTRATOR_BASE_DIR.exists():
        print("❌ 没有找到任何项目")
        return

    projects = [d.name for d in ORCHESTRATOR_BASE_DIR.iterdir() if d.is_dir()]

    if not projects:
        print("❌ 没有找到任何项目")
        return

    print(f"\n📁 项目列表 ({len(projects)} 个)")
    print("=" * 50)

    for project_name in sorted(projects):
        state = get_project_state(project_name)
        if state:
            current_stage = state.get("current_stage", "INIT")
            stage_name = STAGE_NAMES.get(current_stage, current_stage)
            progress = calculate_progress(state)
            active = len(state.get("active_agents", {}))

            status_icon = "🏃" if current_stage not in ["DONE", "INIT"] else ("🎉" if current_stage == "DONE" else "⏸️")
            print(f"{status_icon} {project_name:<30} {stage_name:<15} {progress:5.1f}% 活跃: {active}")
        else:
            print(f"⚠️  {project_name} (无状态文件)")

    print()


def cmd_summary(args):
    """项目摘要"""
    state = get_project_state(args.project)

    if not state:
        print(f"❌ 项目 '{args.project}' 不存在")
        return

    current_stage = state.get("current_stage", "INIT")
    progress = calculate_progress(state)
    description = state.get("description", "无")
    created_at = state.get("created_at", "")[:10]
    updated_at = state.get("updated_at", "")[:10]

    print(f"""
📊 项目摘要: {args.project}
{'=' * 50}

📝 描述: {description}
📅 创建: {created_at}
🔄 更新: {updated_at}
📍 阶段: {STAGE_NAMES.get(current_stage, current_stage)}
📈 进度: {progress}%

👥 Agent:
""")

    for agent_id, info in AGENTS.items():
        status_info = get_agent_status(state, agent_id)
        status = status_info.get("status", "idle")

        if status == "running":
            print(f"   {info['color']} {info['name']}: 🔄 运行中")
        elif status == "completed":
            print(f"   {info['color']} {info['name']}: ✅ 已完成")
        elif status == "pending":
            print(f"   {info['color']} {info['name']}: ⏳ 待启动")
        else:
            print(f"   {info['color']} {info['name']}: ⚪ 空闲")

    print(f"""
📦 产出物: {len(state.get('artifacts', []))} 个
⏳ 待审批: {len([p for p in state.get('pending_approvals', []) if not p.get('approved')])} 个
⚠️  阻塞: {len([b for b in state.get('blockers', []) if not b.get('resolved')])} 个
""")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dashboard - 项目可视化面板")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # view
    p_view = subparsers.add_parser("view", help="查看 Dashboard")
    p_view.add_argument("project", help="项目名称")
    p_view.add_argument("--live", "-l", action="store_true", help="实时刷新")
    p_view.set_defaults(func=cmd_view)

    # list
    p_list = subparsers.add_parser("list", help="列出所有项目")
    p_list.set_defaults(func=cmd_list)

    # summary
    p_summary = subparsers.add_parser("summary", help="项目摘要")
    p_summary.add_argument("project", help="项目名称")
    p_summary.set_defaults(func=cmd_summary)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)
