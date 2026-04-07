#!/usr/bin/env python3
"""
Redis Pub/Sub - Agent 实时消息推送

功能：
1. Agent 之间通过 Redis 频道实时通信
2. 事件发布/订阅机制
3. 替代文件轮询，毫秒级延迟

依赖：
   pip3 install redis
"""

import json
import threading
import time
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from pathlib import Path

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# ============ 配置 ============

DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0


# ============ Redis 消息总线 ============

class RedisMessageBus:
    """Redis 消息总线"""

    def __init__(self, project_name: str, host: str = DEFAULT_REDIS_HOST, 
                 port: int = DEFAULT_REDIS_PORT, db: int = DEFAULT_REDIS_DB):
        self.project_name = project_name
        self.channel_prefix = f"orchestrator:{project_name}"
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None
        self.pubsub = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.listener_thread: Optional[threading.Thread] = None
        self.running = False

    def connect(self) -> bool:
        """连接到 Redis"""
        if not REDIS_AVAILABLE:
            print("[RedisMessageBus] ⚠️ redis 模块未安装，使用降级方案")
            return False

        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            print(f"[RedisMessageBus] ✅ 已连接到 Redis {self.host}:{self.port}")
            return True
        except redis.ConnectionError as e:
            print(f"[RedisMessageBus] ❌ Redis 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self.running = False
        if self.pubsub:
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()
        print("[RedisMessageBus] ⏹️ 已断开连接")

    def _get_channel(self, event_type: str) -> str:
        """获取频道名称"""
        return f"{self.channel_prefix}:{event_type}"

    def publish(self, event_type: str, data: Dict[str, Any]) -> bool:
        """发布消息到频道"""
        message = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "source": "orchestrator"
        }

        if self.redis_client:
            try:
                channel = self._get_channel(event_type)
                self.redis_client.publish(channel, json.dumps(message, ensure_ascii=False))
                print(f"[RedisMessageBus] 📤 发布 {event_type} → {channel}")
                return True
            except Exception as e:
                print(f"[RedisMessageBus] ❌ 发布失败: {e}")
                return False
        else:
            # 降级：写入文件
            self._publish_to_file(event_type, message)
            return False

    def subscribe(self, event_type: str, callback: Callable[[Dict], None]):
        """订阅频道"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        print(f"[RedisMessageBus] 📥 订阅 {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)

    def start_listening(self):
        """开始监听（启动后台线程）"""
        if not self.redis_client:
            print("[RedisMessageBus] ⚠️ Redis 未连接，跳过监听")
            return

        self.running = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        print("[RedisMessageBus] 🎧 开始监听消息")

    def _listen_loop(self):
        """监听循环"""
        self.pubsub = self.redis_client.pubsub()

        # 订阅所有事件频道
        channels = [self._get_channel(e) for e in self.subscribers.keys()]
        self.pubsub.subscribe(*channels)

        for message in self.pubsub.listen():
            if not self.running:
                break

            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    event_type = data.get("event_type", "")
                    
                    if event_type in self.subscribers:
                        for callback in self.subscribers[event_type]:
                            try:
                                callback(data)
                            except Exception as e:
                                print(f"[RedisMessageBus] ❌ 回调异常: {e}")
                except json.JSONDecodeError:
                    pass

    def _publish_to_file(self, event_type: str, message: Dict):
        """降级方案：写入文件"""
        project_dir = Path.home() / ".openclaw" / "orchestrator" / "projects" / self.project_name
        events_dir = project_dir / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        event_file = events_dir / f"{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(event_file, 'w', encoding='utf-8') as f:
            json.dump(message, f, ensure_ascii=False, indent=2)


# ============ 事件类型定义 ============

class EventTypes:
    """事件类型常量"""

    # 项目事件
    PROJECT_INIT = "project_init"
    STAGE_CHANGED = "stage_changed"
    APPROVAL_NEEDED = "approval_needed"

    # Agent 事件
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_HEARTBEAT = "agent_heartbeat"

    # API 事件
    API_DOC_READY = "api_doc_ready"
    API_CHANGED = "api_changed"
    API_VERIFIED = "api_verified"

    # UI 事件
    UI_SPEC_READY = "ui_spec_ready"
    PEN_FILE_GENERATED = "pen_file_generated"

    # 开发事件
    BACKEND_API_READY = "backend_api_ready"
    FRONTEND_MOCK_DONE = "frontend_mock_done"
    INTEGRATION_DONE = "integration_done"

    # 测试事件
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    BUG_FOUND = "bug_found"

    # 部署事件
    DEPLOY_STARTED = "deploy_started"
    DEPLOY_COMPLETED = "deploy_completed"
    DEPLOY_FAILED = "deploy_failed"


# ============ 事件消息格式 ============

def create_event(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """创建事件消息"""
    return {
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }


def create_agent_event(agent_id: str, session_label: str, status: str, 
                       message: str = "", extra: Dict = None) -> Dict[str, Any]:
    """创建 Agent 事件"""
    return create_event(status, {
        "agent_id": agent_id,
        "session_label": session_label,
        "message": message,
        "extra": extra or {}
    })


def create_stage_event(from_stage: str, to_stage: str, reason: str = "") -> Dict[str, Any]:
    """创建阶段变更事件"""
    return create_event(EventTypes.STAGE_CHANGED, {
        "from_stage": from_stage,
        "to_stage": to_stage,
        "reason": reason
    })


def create_api_event(api_name: str, status: str, endpoints: List[str] = None) -> Dict[str, Any]:
    """创建 API 事件"""
    return create_event(status, {
        "api_name": api_name,
        "endpoints": endpoints or []
    })


# ============ 使用示例 ============

def example_usage():
    """使用示例"""
    bus = RedisMessageBus("my-project")

    # 连接 Redis
    if bus.connect():
        # 定义回调函数
        def on_api_ready(data):
            print(f"收到 API 就绪通知: {data}")

        def on_stage_changed(data):
            print(f"阶段变更: {data['from_stage']} → {data['to_stage']}")

        # 订阅事件
        bus.subscribe(EventTypes.API_DOC_READY, on_api_ready)
        bus.subscribe(EventTypes.STAGE_CHANGED, on_stage_changed)

        # 开始监听
        bus.start_listening()

        # 发布事件
        bus.publish(EventTypes.API_DOC_READY, {
            "api_name": "User API",
            "endpoints": ["/api/v1/users", "/api/v1/users/{id}"]
        })

        # 保持运行
        time.sleep(10)

        # 停止
        bus.disconnect()


# ============ CLI ============

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Redis Pub/Sub - Agent 消息推送")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # publish
    p_pub = subparsers.add_parser("publish", help="发布消息")
    p_pub.add_argument("project", help="项目名称")
    p_pub.add_argument("event_type", help="事件类型")
    p_pub.add_argument("--data", "-d", default="{}", help="JSON 数据")

    # subscribe
    p_sub = subparsers.add_parser("subscribe", help="订阅消息")
    p_sub.add_argument("project", help="项目名称")
    p_sub.add_argument("event_type", help="事件类型")

    # status
    p_status = subparsers.add_parser("status", help="查看连接状态")
    p_status.add_argument("project", help="项目名称")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    bus = RedisMessageBus(args.project)

    if args.command == "status":
        if bus.connect():
            print("✅ Redis 连接正常")
            bus.disconnect()
        else:
            print("❌ Redis 连接失败")

    elif args.command == "publish":
        data = json.loads(args.data)
        if bus.connect():
            bus.publish(args.event_type, data)
            bus.disconnect()

    elif args.command == "subscribe":
        def print_message(data):
            print(f"收到消息: {json.dumps(data, ensure_ascii=False, indent=2)}")

        if bus.connect():
            bus.subscribe(args.event_type, print_message)
            bus.start_listening()
            print(f"📥 监听 {args.event_type}，按 Ctrl+C 退出...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                bus.disconnect()
