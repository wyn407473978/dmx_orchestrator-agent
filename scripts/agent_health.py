#!/usr/bin/env python3
"""
Agent Health Monitor - Agent 健康检查与自动重试

功能：
1. 定期检查 Agent 状态
2. Agent 无响应时自动重试
3. 状态上报到 state.json
"""

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Thread, Event
import signal
import sys

# ============ 配置 ============

ORCHESTRATOR_BASE_DIR = Path.home() / ".openclaw" / "orchestrator" / "projects"
HEALTH_CHECK_INTERVAL = 30  # 秒
MAX_RESTART_COUNT = 3
HEALTH_TIMEOUT = 120  # 秒（Agent 多久没响应算超时）

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


# ============ 健康检查 ============

class AgentHealthMonitor:
    """Agent 健康监控器"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_dir = ORCHESTRATOR_BASE_DIR / project_name
        self.state_file = self.project_dir / "state.json"
        self.running = False
        self.monitor_thread: Optional[Thread] = None
        self.stop_event = Event()

    def load_state(self) -> Dict[str, Any]:
        """加载项目状态"""
        if not self.state_file.exists():
            return {}
        with open(self.state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_state(self, state: Dict[str, Any]):
        """保存项目状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def get_active_agents(self) -> List[Dict[str, Any]]:
        """获取当前活跃的 Agent"""
        state = self.load_state()
        # 从 agent_outputs 中获取正在运行的 Agent
        active = []
        for key, agent_info in state.get("agent_outputs", {}).items():
            if not agent_info.get("completed"):
                active.append(agent_info)
        return active

    def check_agent_health(self, agent_id: str, session_label: str) -> Dict[str, Any]:
        """检查单个 Agent 的健康状态"""
        try:
            # 使用 sessions_list 检查 session 状态
            result = subprocess.run(
                ["openclaw", "sessions", "list", "--label", session_label],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # session 存在，检查是否有新输出
                output = result.stdout.lower()
                if "active" in output or "running" in output:
                    return {
                        "status": "healthy",
                        "agent_id": agent_id,
                        "session_label": session_label,
                        "last_seen": datetime.now().isoformat()
                    }
                elif "idle" in output:
                    return {
                        "status": "idle",
                        "agent_id": agent_id,
                        "session_label": session_label,
                        "last_seen": datetime.now().isoformat()
                    }

            return {
                "status": "not_found",
                "agent_id": agent_id,
                "session_label": session_label,
                "error": "Session not found or not accessible"
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "agent_id": agent_id,
                "session_label": session_label,
                "error": "Health check timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "agent_id": agent_id,
                "session_label": session_label,
                "error": str(e)
            }

    def restart_agent(self, agent_id: str, session_label: str, task: str) -> Dict[str, Any]:
        """重启 Agent"""
        agent_info = AGENTS.get(agent_id, {})
        agent_name = agent_info.get("name", agent_id)

        print(f"[HealthMonitor] 🔄 重启 {agent_name}...")

        try:
            # 先尝试终止旧 session
            subprocess.run(
                ["openclaw", "sessions", "kill", "--label", session_label],
                capture_output=True,
                timeout=10
            )

            # 启动新 session
            result = subprocess.run(
                [
                    "openclaw", "sessions", "spawn",
                    "--task", task,
                    "--agent", agent_id.replace("_", "-"),
                    "--label", session_label,
                    "--background"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"[HealthMonitor] ✅ {agent_name} 重启成功")
                return {
                    "ok": True,
                    "agent_id": agent_id,
                    "new_session": session_label
                }
            else:
                print(f"[HealthMonitor] ❌ {agent_name} 重启失败: {result.stderr}")
                return {
                    "ok": False,
                    "agent_id": agent_id,
                    "error": result.stderr
                }

        except Exception as e:
            print(f"[HealthMonitor] ❌ {agent_name} 重启异常: {str(e)}")
            return {
                "ok": False,
                "agent_id": agent_id,
                "error": str(e)
            }

    def check_and_restart_dead_agents(self) -> Dict[str, Any]:
        """检查并重启挂掉的 Agent"""
        state = self.load_state()
        dead_agents = []
        restarted_agents = []

        for agent_key, agent_info in state.get("active_agents", {}).items():
            agent_id = agent_info.get("agent_id")
            session_label = agent_info.get("session_label")
            task = agent_info.get("task", "")
            restart_count = agent_info.get("restart_count", 0)

            # 检查健康状态
            health = self.check_agent_health(agent_id, session_label)

            if health["status"] in ["not_found", "timeout", "error"]:
                dead_agents.append({
                    "agent_id": agent_id,
                    "session_label": session_label,
                    "reason": health.get("error", "Unknown")
                })

                # 尝试重启
                if restart_count < MAX_RESTART_COUNT:
                    result = self.restart_agent(agent_id, session_label, task)
                    if result.get("ok"):
                        agent_info["restart_count"] = restart_count + 1
                        agent_info["last_restart"] = datetime.now().isoformat()
                        restarted_agents.append(agent_id)

        # 更新状态
        if dead_agents or restarted_agents:
            state["active_agents"] = state.get("active_agents", {})
            state["health_check"] = {
                "last_check": datetime.now().isoformat(),
                "dead_agents": dead_agents,
                "restarted_agents": restarted_agents
            }
            self.save_state(state)

        return {
            "checked_at": datetime.now().isoformat(),
            "dead_agents": dead_agents,
            "restarted_agents": restarted_agents
        }

    def register_agent(self, agent_id: str, session_label: str, task: str):
        """注册 Agent 到活跃列表"""
        state = self.load_state()

        if "active_agents" not in state:
            state["active_agents"] = {}

        state["active_agents"][session_label] = {
            "agent_id": agent_id,
            "session_label": session_label,
            "task": task,
            "registered_at": datetime.now().isoformat(),
            "restart_count": 0,
            "last_heartbeat": datetime.now().isoformat()
        }

        self.save_state(state)
        print(f"[HealthMonitor] ✅ 注册 Agent: {agent_id} ({session_label})")

    def unregister_agent(self, session_label: str):
        """从活跃列表移除 Agent"""
        state = self.load_state()

        if session_label in state.get("active_agents", {}):
            del state["active_agents"][session_label]
            self.save_state(state)
            print(f"[HealthMonitor] ✅ 移除 Agent: {session_label}")

    def start_monitoring(self):
        """开始监控"""
        self.running = True
        self.stop_event.clear()
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"[HealthMonitor] 🚀 开始监控项目: {self.project_name}")

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print(f"[HealthMonitor] ⏹️ 停止监控: {self.project_name}")

    def _monitor_loop(self):
        """监控循环"""
        while self.running and not self.stop_event.is_set():
            try:
                result = self.check_and_restart_dead_agents()

                if result["dead_agents"]:
                    print(f"[HealthMonitor] ⚠️ 发现 {len(result['dead_agents'])} 个无响应 Agent")
                    for a in result["dead_agents"]:
                        print(f"       - {a['agent_id']}: {a['reason']}")

                if result["restarted_agents"]:
                    print(f"[HealthMonitor] 🔄 已重启 {len(result['restarted_agents'])} 个 Agent")

            except Exception as e:
                print(f"[HealthMonitor] ❌ 监控异常: {str(e)}")

            # 等待下一次检查
            self.stop_event.wait(timeout=HEALTH_CHECK_INTERVAL)


# ============ CLI ============

def cmd_monitor(args):
    """启动监控"""
    monitor = AgentHealthMonitor(args.project)

    if args.action == "start":
        monitor.start_monitoring()
        try:
            # 主线程等待
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop_monitoring()
    elif args.action == "check":
        result = monitor.check_and_restart_dead_agents()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.action == "register":
        monitor.register_agent(args.agent, args.label, args.task)
    elif args.action == "unregister":
        monitor.unregister_agent(args.label)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent Health Monitor")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # monitor
    p_monitor = subparsers.add_parser("monitor", help="Agent 健康监控")
    p_monitor.add_argument("project", help="项目名称")
    p_monitor.add_argument("action", choices=["start", "check"], help="操作")
    p_monitor.set_defaults(func=cmd_monitor)

    # register
    p_reg = subparsers.add_parser("register", help="注册 Agent")
    p_reg.add_argument("project", help="项目名称")
    p_reg.add_argument("agent", help="Agent ID")
    p_reg.add_argument("label", help="Session Label")
    p_reg.add_argument("--task", "-t", default="", help="任务描述")
    p_reg.set_defaults(func=cmd_monitor)

    # unregister
    p_unreg = subparsers.add_parser("unregister", help="移除 Agent")
    p_unreg.add_argument("project", help="项目名称")
    p_unreg.add_argument("label", help="Session Label")
    p_unreg.set_defaults(func=cmd_monitor)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)
