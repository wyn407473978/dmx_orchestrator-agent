#!/usr/bin/env python3
"""
Orchestrator Tools V3 - 完整版

整合所有改进：
1. ✅ Redis Pub/Sub 集成
2. ✅ 项目模板集成
3. ✅ 健康监控自动启动
4. ✅ 增强 OpenAPI 扫描器
5. ✅ Web Dashboard 支持
"""

import json
import os
import sys
import subprocess
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread

# ============ 导入同级模块 ============

sys.path.insert(0, str(Path(__file__).parent))

try:
    from redis_pubsub import RedisMessageBus, EventTypes
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from project_template import TemplateManager
    TEMPLATE_AVAILABLE = True
except ImportError:
    TEMPLATE_AVAILABLE = False

try:
    from openapi_tools import OpenAPIExporter, APIVerifier
    OPENAPI_AVAILABLE = True
except ImportError:
    OPENAPI_AVAILABLE = False


# ============ 配置 ============

ORCHESTRATOR_BASE_DIR = Path.home() / ".openclaw" / "orchestrator" / "projects"
SCRIPTS_DIR = Path(__file__).parent
WEB_PORT = 8080

STAGES = [
    "INIT", "STAGE_1_REQUIREMENTS", "STAGE_2_ARCHITECTURE",
    "STAGE_2_5_API_REVIEW", "STAGE_3_UI_DESIGN",
    "STAGE_4_5_PARALLEL_DEV", "STAGE_6_TESTING", "STAGE_7_DEPLOY", "DONE"
]

STAGE_NAMES = {
    "INIT": "初始化", "STAGE_1_REQUIREMENTS": "需求收集",
    "STAGE_2_ARCHITECTURE": "技术方案", "STAGE_2_5_API_REVIEW": "API接口确认",
    "STAGE_3_UI_DESIGN": "UI设计", "STAGE_4_5_PARALLEL_DEV": "前后端并行开发",
    "STAGE_6_TESTING": "测试验证", "STAGE_7_DEPLOY": "部署上线", "DONE": "完成"
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

HUMAN_APPROVAL_REQUIRED = {
    "STAGE_1_REQUIREMENTS": "STAGE_2_ARCHITECTURE",
    "STAGE_2_5_API_REVIEW": "STAGE_3_UI_DESIGN",
    "STAGE_3_UI_DESIGN": "STAGE_4_5_PARALLEL_DEV",
    "STAGE_6_TESTING": "STAGE_7_DEPLOY",
    "STAGE_7_DEPLOY": "DONE",
}

AGENTS = {
    "product_manager": {"name": "Product Manager", "color": "🔵"},
    "tech_lead": {"name": "Tech Lead", "color": "🟣"},
    "backend": {"name": "Backend Agent", "color": "🟢"},
    "frontend": {"name": "Frontend Agent", "color": "🟠"},
    "ui_designer": {"name": "UI Designer", "color": "🟡"},
    "qa": {"name": "QA Agent", "color": "🔴"},
    "devops": {"name": "DevOps Agent", "color": "⚪"},
}


# ============ Redis 消息总线单例 ============

class MessageBus:
    """全局消息总线"""
    _instances: Dict[str, RedisMessageBus] = {}
    
    @classmethod
    def get(cls, project_name: str) -> RedisMessageBus:
        if project_name not in cls._instances:
            cls._instances[project_name] = RedisMessageBus(project_name)
            cls._instances[project_name].connect()
        return cls._instances[project_name]
    
    @classmethod
    def close(cls, project_name: str):
        if project_name in cls._instances:
            cls._instances[project_name].disconnect()
            del cls._instances[project_name]


# ============ 工具实现 ============

def orchestrator_init_project(project_name: str, description: str = "", template: str = None) -> Dict[str, Any]:
    """初始化新项目（支持模板）"""
    project_dir = ORCHESTRATOR_BASE_DIR / project_name
    artifacts_dir = project_dir / "artifacts"
    events_dir = project_dir / "events"
    messages_dir = project_dir / "messages"
    api_contract_dir = project_dir / "api-contract"
    designs_dir = project_dir / "designs"

    for d in [artifacts_dir, events_dir, messages_dir, api_contract_dir, designs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    state_file = project_dir / "state.json"

    state = {
        "project_name": project_name,
        "description": description,
        "template": template,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "current_stage": "STAGE_1_REQUIREMENTS",
        "stage_history": [{"from": "INIT", "to": "STAGE_1_REQUIREMENTS", "reason": "项目初始化", "timestamp": datetime.now().isoformat()}],
        "pending_approvals": [],
        "artifacts": [],
        "agent_outputs": [],
        "active_agents": {},
        "events": [],
        "blockers": []
    }

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 如果指定了模板，从模板生成内容
    template_info = ""
    if template and TEMPLATE_AVAILABLE:
        try:
            tm = TemplateManager()
            result = tm.create_project_from_template(project_name, template, project_dir)
            if result.get("ok"):
                template_info = f"\n📦 模板: {result.get('template')}\n🔧 技术栈: {', '.join(result.get('tech_stack', {}).values())}"
        except Exception as e:
            template_info = f"\n⚠️ 模板应用失败: {str(e)}"

    # 通过 Redis 发布项目创建事件
    if REDIS_AVAILABLE:
        try:
            bus = MessageBus.get(project_name)
            bus.publish("project_created", {"project": project_name, "template": template})
        except:
            pass

    return {
        "ok": True,
        "project_path": str(project_dir),
        "state_file": str(state_file),
        "current_stage": "STAGE_1_REQUIREMENTS",
        "stage_name": STAGE_NAMES["STAGE_1_REQUIREMENTS"],
        "message": f"""✅ 项目 '{project_name}' 初始化完成！

📍 当前阶段: {STAGE_NAMES['STAGE_1_REQUIREMENTS']}
👥 需要 Agent: {AGENTS['product_manager']['color']} Product Manager{template_info}

目录结构:
  {project_dir}/
  ├── state.json
  ├── artifacts/
  ├── api-contract/
  ├── designs/
  ├── events/
  └── messages/

下一步: 启动 PM Agent 进行需求收集"""
    }


def orchestrator_get_status(project_name: str) -> Dict[str, Any]:
    """获取项目状态"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    current_stage = state["current_stage"]
    active_agents = state.get("active_agents", {})
    pending = [p for p in state.get("pending_approvals", []) if not p.get("approved")]
    blockers = [b for b in state.get("blockers", []) if not b.get("resolved")]

    agent_display = [f"{AGENTS.get(a, {}).get('color', '')} {AGENTS.get(a, {}).get('name', a)}" 
                     for a in STAGE_AGENTS.get(current_stage, [])]

    msg_parts = [
        f"📁 项目: {project_name}",
        f"📍 当前阶段: {STAGE_NAMES.get(current_stage, current_stage)}",
    ]
    if agent_display:
        msg_parts.append(f"👥 当前 Agent: {', '.join(agent_display)}")
    if active_agents:
        msg_parts.append(f"🔄 活跃会话: {len(active_agents)} 个")
    if pending:
        msg_parts.append(f"⏳ 待审批: {len(pending)} 个")
    if blockers:
        msg_parts.append(f"⚠️ 阻塞: {len(blockers)} 个")
    msg_parts.append(f"\n📦 产出物: {len(state.get('artifacts', []))} 个")

    if current_stage == "STAGE_1_REQUIREMENTS":
        msg_parts.append("\n命令: '确认需求' → 推进到技术方案")
    elif current_stage == "STAGE_4_5_PARALLEL_DEV":
        msg_parts.append("\n命令: '启动联调' → 进入测试阶段")

    return {
        "ok": True,
        "current_stage": current_stage,
        "stage_name": STAGE_NAMES.get(current_stage, current_stage),
        "agents": STAGE_AGENTS.get(current_stage, []),
        "active_agents_count": len(active_agents),
        "pending_approvals_count": len(pending),
        "blockers_count": len(blockers),
        "artifacts_count": len(state.get("artifacts", [])),
        "message": "\n".join(msg_parts)
    }


def orchestrator_start_stage(project_name: str, stage: str = None) -> Dict[str, Any]:
    """启动阶段 + Agent + 健康监控"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    if stage is None:
        stage = state["current_stage"]

    agents = STAGE_AGENTS.get(stage, [])
    if not agents:
        return {"ok": True, "stage": stage, "spawned_agents": [], "message": f"阶段 {STAGE_NAMES.get(stage, stage)} 无需 Agent"}

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
            "spawn_command": f'sessions_spawn --task "{task[:50]}..." --agent {agent_id} --label {session_label} --background'
        })

        state.setdefault("active_agents", {})[session_label] = {
            "agent_id": agent_id, "session_label": session_label, "stage": stage,
            "task": task, "started_at": datetime.now().isoformat(), "restart_count": 0
        }

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 启动健康监控
    _start_health_monitor(project_name)

    # 通过 Redis 发布 Agent 启动事件
    if REDIS_AVAILABLE:
        try:
            bus = MessageBus.get(project_name)
            for s in spawned:
                bus.publish("agent_started", {"agent": s["agent_id"], "session": s["session_label"], "stage": stage})
        except:
            pass

    agent_names = [f"{AGENTS.get(a, {}).get('color', '')} {AGENTS.get(a, {}).get('name', a)}" for a in agents]

    return {
        "ok": True, "stage": stage, "stage_name": STAGE_NAMES.get(stage, stage),
        "spawned_agents": spawned, "health_monitor": "已启动",
        "message": f"""✅ 已启动 {STAGE_NAMES.get(stage, stage)} 阶段的 Agent:

{chr(10).join(['- ' + a for a in agent_names])}

🔄 健康监控已启动
⏳ Agent 正在运行中..."""
    }


def orchestrator_spawn_parallel(project_name: str) -> Dict[str, Any]:
    """启动前后端并行开发"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    backend_label = f"{project_name}_backend_parallel"
    frontend_label = f"{project_name}_frontend_parallel"

    backend_task = _generate_agent_task("backend", "STAGE_4_5_PARALLEL_DEV", project_name)
    frontend_task = _generate_agent_task("frontend", "STAGE_4_5_PARALLEL_DEV", project_name)

    for label, agent_id, task in [(backend_label, "backend", backend_task), (frontend_label, "frontend", frontend_task)]:
        state.setdefault("active_agents", {})[label] = {
            "agent_id": agent_id, "session_label": label, "stage": "STAGE_4_5_PARALLEL_DEV",
            "task": task, "started_at": datetime.now().isoformat(), "restart_count": 0
        }

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    _start_health_monitor(project_name)

    # Redis 发布
    if REDIS_AVAILABLE:
        try:
            bus = MessageBus.get(project_name)
            bus.publish("parallel_dev_started", {"project": project_name})
            bus.publish("agent_started", {"agent": "backend", "session": backend_label})
            bus.publish("agent_started", {"agent": "frontend", "session": frontend_label})
        except:
            pass

    return {
        "ok": True, "stage": "STAGE_4_5_PARALLEL_DEV",
        "spawned_agents": [
            {"agent_id": "backend", "session_label": backend_label, "agent_name": "Backend Agent", "color": "🟢", "task": backend_task},
            {"agent_id": "frontend", "session_label": frontend_label, "agent_name": "Frontend Agent", "color": "🟠", "task": frontend_task}
        ],
        "health_monitor": "已启动",
        "message": """🚀 前后端并行开发已启动！

🟢 Backend Agent:
   - 实现 API 接口
   - 使用 TDD 方式

🟠 Frontend Agent:
   - 开发 UI 组件
   - 使用 Mock 数据

🔄 健康监控已启动
⏳ 联调将在 Stage 6 进行"""
    }


def orchestrator_advance_stage(project_name: str) -> Dict[str, Any]:
    """推进阶段"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    current = state["current_stage"]
    try:
        idx = STAGES.index(current)
        if idx >= len(STAGES) - 1:
            return {"ok": False, "error": "已是最后阶段"}
        next_stage = STAGES[idx + 1]
    except ValueError:
        return {"ok": False, "error": f"未知阶段: {current}"}

    required_approval = HUMAN_APPROVAL_REQUIRED.get(current)
    if required_approval == next_stage:
        state.setdefault("pending_approvals", []).append({
            "id": f"approval_{len(state.get('pending_approvals', []))}",
            "from_stage": current, "to_stage": next_stage,
            "timestamp": datetime.now().isoformat(), "approved": False
        })
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return {
            "ok": False, "requires_approval": True,
            "from_stage": current, "to_stage": next_stage,
            "from_stage_name": STAGE_NAMES.get(current, current),
            "to_stage_name": STAGE_NAMES.get(next_stage, next_stage),
            "message": f"⏳ 需要人工审批\n\n当前: {STAGE_NAMES.get(current)}\n目标: {STAGE_NAMES.get(next_stage)}\n\n请说\"确认\"继续"
        }

    state["current_stage"] = next_stage
    state["stage_history"].append({"from": current, "to": next_stage, "reason": "自动推进", "timestamp": datetime.now().isoformat()})

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Redis 发布
    if REDIS_AVAILABLE:
        try:
            bus = MessageBus.get(project_name)
            bus.publish("stage_changed", {"from": current, "to": next_stage})
        except:
            pass

    next_agents = STAGE_AGENTS.get(next_stage, [])
    return {
        "ok": True, "from_stage": current, "to_stage": next_stage,
        "from_stage_name": STAGE_NAMES.get(current, current),
        "to_stage_name": STAGE_NAMES.get(next_stage, next_stage),
        "next_agents": next_agents,
        "message": f"✅ 已进入 {STAGE_NAMES.get(next_stage, next_stage)} 阶段"
    }


def orchestrator_approve_stage(project_name: str, from_stage: str = None, to_stage: str = None) -> Dict[str, Any]:
    """审批通过"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    pending = [p for p in state.get("pending_approvals", []) if not p.get("approved")]
    if not pending:
        return {"ok": False, "error": "没有待审批"}

    approval = pending[0]
    from_s, to_s = approval["from_stage"], approval["to_stage"]
    approval["approved"] = True
    approval["approved_at"] = datetime.now().isoformat()
    state["current_stage"] = to_s
    state["stage_history"].append({"from": from_s, "to": to_s, "reason": "人工审批", "timestamp": datetime.now().isoformat()})

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Redis 发布
    if REDIS_AVAILABLE:
        try:
            bus = MessageBus.get(project_name)
            bus.publish("stage_approved", {"from": from_s, "to": to_s})
            bus.publish("stage_changed", {"from": from_s, "to": to_s})
        except:
            pass

    next_agents = STAGE_AGENTS.get(to_s, [])
    return {
        "ok": True, "new_stage": to_s, "new_stage_name": STAGE_NAMES.get(to_s, to_s),
        "message": f"✅ 审批通过！已从 {STAGE_NAMES.get(from_s)} 进入 {STAGE_NAMES.get(to_s)}"
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

    state.setdefault("artifacts", []).append({
        "stage": stage, "name": artifact_name, "path": str(artifact_file),
        "timestamp": datetime.now().isoformat()
    })

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Redis 发布
    if REDIS_AVAILABLE:
        try:
            bus = MessageBus.get(project_name)
            bus.publish("artifact_saved", {"stage": stage, "name": artifact_name})
        except:
            pass

    return {"ok": True, "artifact_path": str(artifact_file), "message": f"✅ 产出物已保存: {artifact_name}"}


def orchestrator_get_artifacts(project_name: str) -> Dict[str, Any]:
    """获取所有产出物"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    artifacts = state.get("artifacts", [])
    if not artifacts:
        return {"ok": True, "artifacts": [], "message": "📦 暂无产出物"}

    lines = ["📦 产出物列表:"]
    for a in artifacts:
        lines.append(f"  [{STAGE_NAMES.get(a['stage'], a['stage'])}] {a['name']} - {a.get('timestamp', '')[:19]}")

    return {"ok": True, "artifacts": artifacts, "message": "\n".join(lines)}


def orchestrator_verify_api(project_name: str) -> Dict[str, Any]:
    """验证 API 文档"""
    if not OPENAPI_AVAILABLE:
        return {"ok": False, "error": "OpenAPI 模块不可用"}

    api_file = ORCHESTRATOR_BASE_DIR / project_name / "api-contract" / "openapi.yaml"
    if not api_file.exists():
        api_file = ORCHESTRATOR_BASE_DIR / project_name / "api-contract" / "openapi.json"

    if not api_file.exists():
        return {"ok": False, "error": "API 文档不存在", "message": "❌ openapi.yaml 不存在"}

    verifier = APIVerifier(project_name)
    result = verifier.verify()

    if result.get("ok"):
        return {"ok": True, "verified": True, "message": "✅ API 文档验证通过！"}
    else:
        return {"ok": False, "verified": False, "issues": result.get("issues", []),
                "message": f"❌ API 验证失败，发现 {len(result.get('issues', []))} 个问题"}


def orchestrator_health_check(project_name: str) -> Dict[str, Any]:
    """Agent 健康检查"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return {"ok": False, "error": f"项目 '{project_name}' 不存在"}

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    active = state.get("active_agents", {})
    if not active:
        return {"ok": True, "healthy": [], "unhealthy": [], "message": "📊 健康检查完成 - 无活跃 Agent"}

    healthy, unhealthy = [], []
    for session_label, info in active.items():
        agent_id = info.get("agent_id")
        agent_name = AGENTS.get(agent_id, {}).get("name", agent_id)
        restart_count = info.get("restart_count", 0)
        
        # 简单检查 session 是否存在
        try:
            result = subprocess.run(["openclaw", "sessions", "list"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and session_label in result.stdout:
                healthy.append({"agent_id": agent_id, "agent_name": agent_name, "session": session_label, "restarts": restart_count})
            else:
                unhealthy.append({"agent_id": agent_id, "agent_name": agent_name, "session": session_label, "restarts": restart_count, "reason": "Session not found"})
        except:
            unhealthy.append({"agent_id": agent_id, "agent_name": agent_name, "session": session_label, "restarts": restart_count, "reason": "Check failed"})

    lines = [f"📊 健康检查 - {'✅ 健康' if not unhealthy else f'⚠️ {len(unhealthy)} 个异常'}"]
    lines.append(f"\n活跃: {len(healthy)} 个")
    if healthy:
        lines.append("✅ 正常: " + ", ".join([a["agent_name"] for a in healthy]))
    if unhealthy:
        lines.append(f"⚠️ 异常 ({len(unhealthy)}): " + ", ".join([f"{a['agent_name']}({a['reason']})" for a in unhealthy]))

    return {"ok": True, "healthy_count": len(healthy), "unhealthy_count": len(unhealthy),
            "healthy": healthy, "unhealthy": unhealthy, "message": "\n".join(lines)}


def orchestrator_list_templates() -> Dict[str, Any]:
    """列出可用模板"""
    if not TEMPLATE_AVAILABLE:
        return {"ok": False, "error": "模板模块不可用"}

    tm = TemplateManager()
    templates = tm.list_templates()

    lines = [f"📦 可用模板 ({len(templates)} 个):"]
    for t in templates:
        lines.append(f"\n📦 {t.get('display_name')} ({t.get('name')})")
        lines.append(f"   {t.get('description', '')}")

    return {"ok": True, "templates": templates, "message": "\n".join(lines)}


def orchestrator_generate_openapi(project_name: str, routes_dir: str = None) -> Dict[str, Any]:
    """生成 OpenAPI 文档"""
    if not OPENAPI_AVAILABLE:
        return {"ok": False, "error": "OpenAPI 模块不可用"}

    routes_path = Path(routes_dir) if routes_dir else ORCHESTRATOR_BASE_DIR / project_name / "backend"
    exporter = OpenAPIExporter(project_name)
    
    routes = exporter.scan_routes(routes_path)
    if not routes:
        return {"ok": False, "error": "未发现路由", "message": "⚠️ 未发现路由，请检查代码目录"}

    openapi_doc = exporter.generate_openapi(routes)
    output_file = exporter.save_openapi(openapi_doc)

    return {"ok": True, "routes_found": len(routes), "output": str(output_file),
            "message": f"✅ 生成 {len(routes)} 个路由，保存到 {output_file}"}


def orchestrator_start_dashboard(project_name: str, web: bool = False) -> Dict[str, Any]:
    """启动 Dashboard"""
    if web:
        # 启动 Web Dashboard
        dashboard_url = f"http://localhost:{WEB_PORT}/dashboard/{project_name}"
        Thread(target=_start_web_dashboard, args=(project_name,), daemon=True).start()
        return {"ok": True, "url": dashboard_url, "message": f"🌐 Web Dashboard 已启动: {dashboard_url}"}
    else:
        # 返回终端 Dashboard 状态
        return orchestrator_get_status(project_name)


# ============ 辅助函数 ============

def _generate_agent_task(agent_id: str, stage: str, project_name: str) -> str:
    """生成 Agent 任务"""
    tasks = {
        "product_manager": f"""你是一个 Product Manager，负责需求分析。

项目: {project_name}
阶段: {STAGE_NAMES.get(stage, stage)}

任务:
1. 需求访谈
2. 生成 PRD 文档

目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/""",

        "tech_lead": f"""你是一个 Tech Lead，负责架构设计。

项目: {project_name}
阶段: {STAGE_NAMES.get(stage, stage)}

任务:
1. 设计系统架构
2. 设计数据库
3. 输出 API 设计

目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/""",

        "backend": f"""你是一个 Backend Agent，负责后端开发。

项目: {project_name}
阶段: {STAGE_NAMES.get(stage, stage)}

任务:
1. 实现 API 接口
2. TDD 开发

目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/""",

        "frontend": f"""你是一个 Frontend Agent，负责前端开发。

项目: {project_name}
阶段: {STAGE_NAMES.get(stage, stage)}

任务:
1. 开发 UI 组件
2. 对接后端 API

目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/""",

        "ui_designer": f"""你是一个 UI Designer，负责界面设计。

项目: {project_name}
阶段: {STAGE_NAMES.get(stage, stage)}

任务:
1. 设计 UI 界面
2. 生成 .pen 文件

目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/""",

        "qa": f"""你是一个 QA Agent，负责测试。

项目: {project_name}
阶段: {STAGE_NAMES.get(stage, stage)}

任务:
1. 执行测试
2. 输出报告

目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/""",

        "devops": f"""你是一个 DevOps Agent，负责部署。

项目: {project_name}
阶段: {STAGE_NAMES.get(stage, stage)}

任务:
1. 构建 Docker
2. 部署验证

目录: ~/.openclaw/orchestrator/projects/{project_name}/artifacts/""",
    }
    return tasks.get(agent_id, f"执行 {agent_id} 在 {stage}")


def _start_health_monitor(project_name: str):
    """启动健康监控"""
    try:
        subprocess.Popen(
            ["python3", str(SCRIPTS_DIR / "agent_health.py"), "monitor", project_name, "start"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except:
        pass


def _start_web_dashboard(project_name: str):
    """启动 Web Dashboard"""
    class DashboardHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith(f"/dashboard/{project_name}"):
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                html = _generate_dashboard_html(project_name)
                self.wfile.write(html.encode())
            elif self.path == "/":
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Orchestrator Dashboard</h1></body></html>")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # 静默日志

    try:
        server = HTTPServer(("localhost", WEB_PORT), DashboardHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Web Dashboard 启动失败: {e}")


def _generate_dashboard_html(project_name: str) -> str:
    """生成 Dashboard HTML"""
    state_file = ORCHESTRATOR_BASE_DIR / project_name / "state.json"
    if not state_file.exists():
        return b"<html><body><h1>Project not found</h1></body></html>"

    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)

    current = state.get("current_stage", "INIT")
    active = state.get("active_agents", {})
    artifacts = state.get("artifacts", [])
    pending = [p for p in state.get("pending_approvals", []) if not p.get("approved")]

    stage_order = list(STAGE_NAMES.keys())
    try:
        current_idx = stage_order.index(current)
        progress = int((current_idx / (len(stage_order) - 1)) * 100)
    except:
        progress = 0

    active_list = []
    for session_label, info in active.items():
        agent_id = info.get("agent_id")
        active_list.append(f"<li>{AGENTS.get(agent_id, {}).get('color', '')} {AGENTS.get(agent_id, {}).get('name', agent_id)} - {session_label}</li>")

    artifacts_list = ""
    for a in artifacts[-5:]:
        artifacts_list += f"<li>{a.get('name')} ({a.get('stage', '')})</li>"

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Orchestrator - {project_name}</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; }}
        h1 {{ color: #333; margin: 0; }}
        .badge {{ background: #007AFF; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; }}
        .progress {{ background: #e5e5ea; border-radius: 8px; height: 24px; margin: 20px 0; }}
        .progress-bar {{ background: linear-gradient(90deg, #007AFF, #5856d6); border-radius: 8px; height: 24px; width: {progress}%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; }}
        .stage {{ font-size: 18px; font-weight: 600; margin: 10px 0; }}
        .agents {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
        .agent {{ background: #f9f9f9; padding: 12px; border-radius: 8px; }}
        .agent-name {{ font-weight: 600; }}
        .pending {{ color: #ff9500; }}
        ul {{ margin: 0; padding-left: 20px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>📁 {project_name}</h1>
            <span class="badge">{STAGE_NAMES.get(current, current)}</span>
        </div>
        <div class="progress">
            <div class="progress-bar">{progress}%</div>
        </div>
        <div class="stage">📍 当前阶段: {STAGE_NAMES.get(current, current)}</div>
    </div>

    <div class="card">
        <h2>👥 活跃 Agent ({len(active)})</h2>
        <div class="agents">
            {"".join([f'<div class="agent"><span class="agent-name">{AGENTS.get(info.get("agent_id"), {}).get("color", "")} {AGENTS.get(info.get("agent_id"), {}).get("name", info.get("agent_id"))}</span><br/><small>{info.get("session_label", "")}</small></div>' for session_label, info in active.items()]) if active else "<p>无活跃 Agent</p>"}
        </div>
    </div>

    <div class="card">
        <h2>⏳ 待审批 ({len(pending)})</h2>
        {chr(10).join([f"<p>{STAGE_NAMES.get(p.get('from_stage', ''), p.get('from_stage', ''))} → {STAGE_NAMES.get(p.get('to_stage', ''), p.get('to_stage', ''))}</p>" for p in pending]) if pending else "<p>无待审批</p>"}
    </div>

    <div class="card">
        <h2>📦 产出物 ({len(artifacts)})</h2>
        <ul>{artifacts_list if artifacts_list else "<li>暂无</li>"}</ul>
    </div>

    <div class="card">
        <p><small>最后更新: {state.get("updated_at", "")[:19]}</small></p>
    </div>
</body>
</html>"""
    return html.encode()


# ============ CLI ============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrator Tools V3")
    subparsers = parser.add_subparsers(dest="command")

    p = subparsers.add_parser("init")
    p.add_argument("project")
    p.add_argument("--description", "-d", default="")
    p.add_argument("--template", "-t", default=None, help="项目模板 (ecommerce|blog|dashboard|saas)")

    p = subparsers.add_parser("status")
    p.add_argument("project")

    p = subparsers.add_parser("start")
    p.add_argument("project")
    p.add_argument("--stage", "-s", default=None)

    p = subparsers.add_parser("parallel")
    p.add_argument("project")

    p = subparsers.add_parser("advance")
    p.add_argument("project")

    p = subparsers.add_parser("approve")
    p.add_argument("project")
    p.add_argument("--from", dest="from_stage", default=None)
    p.add_argument("--to", dest="to_stage", default=None)

    p = subparsers.add_parser("save")
    p.add_argument("project")
    p.add_argument("--stage", "-s", required=True)
    p.add_argument("--name", "-n", required=True)
    p.add_argument("--content", "-c", required=True)

    p = subparsers.add_parser("artifacts")
    p.add_argument("project")

    p = subparsers.add_parser("verify-api")
    p.add_argument("project")

    p = subparsers.add_parser("health")
    p.add_argument("project")

    p = subparsers.add_parser("templates")
    p.set_defaults(func=lambda _: orchestrator_list_templates())

    p = subparsers.add_parser("generate-openapi")
    p.add_argument("project")
    p.add_argument("--routes-dir", "-r", default=None)

    p = subparsers.add_parser("dashboard")
    p.add_argument("project")
    p.add_argument("--web", "-w", action="store_true")

    args = parser.parse_args()

    commands = {
        "init": lambda: orchestrator_init_project(args.project, args.description, getattr(args, "template", None)),
        "status": lambda: orchestrator_get_status(args.project),
        "start": lambda: orchestrator_start_stage(args.project, args.stage),
        "parallel": lambda: orchestrator_spawn_parallel(args.project),
        "advance": lambda: orchestrator_advance_stage(args.project),
        "approve": lambda: orchestrator_approve_stage(args.project, args.from_stage, args.to_stage),
        "save": lambda: orchestrator_save_artifact(args.project, args.stage, args.name, args.content),
        "artifacts": lambda: orchestrator_get_artifacts(args.project),
        "verify-api": lambda: orchestrator_verify_api(args.project),
        "health": lambda: orchestrator_health_check(args.project),
        "templates": lambda: orchestrator_list_templates(),
        "generate-openapi": lambda: orchestrator_generate_openapi(args.project, args.routes_dir),
        "dashboard": lambda: orchestrator_start_dashboard(args.project, args.web),
    }

    if args.command is None:
        parser.print_help()
    else:
        result = commands[args.command]()
        print(json.dumps(result, ensure_ascii=False, indent=2))
