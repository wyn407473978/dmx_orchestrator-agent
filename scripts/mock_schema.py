#!/usr/bin/env python3
"""
Mock Schema - 标准化 Mock 数据格式

功能：
1. 定义标准 Mock Schema 格式
2. 从 OpenAPI 自动生成 Mock 数据
3. 支持多种数据类型和生成规则
4. 生成 Mock Server 代码

Mock Schema 格式：
{
  "field_name": {
    "type": "string|number|boolean|array|object",
    "mock": {
      "rule": "规则类型",
      "params": {...}
    },
    "required": true,
    "description": "字段描述"
  }
}
"""

import json
import random
import string
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


# ============ Mock 规则定义 ============

class MockRules:
    """Mock 数据生成规则"""

    @staticmethod
    def random_string(length: int = 10, prefix: str = "") -> str:
        """随机字符串"""
        chars = string.ascii_letters + string.digits
        result = ''.join(random.choice(chars) for _ in range(length))
        return prefix + result

    @staticmethod
    def random_int(min_val: int = 1, max_val: int = 1000) -> int:
        """随机整数"""
        return random.randint(min_val, max_val)

    @staticmethod
    def random_float(min_val: float = 0.0, max_val: float = 1000.0, decimals: int = 2) -> float:
        """随机浮点数"""
        return round(random.uniform(min_val, max_val), decimals)

    @staticmethod
    def random_choice(choices: List[Any]) -> Any:
        """随机选择"""
        return random.choice(choices)

    @staticmethod
    def random_bool(prob_true: float = 0.5) -> bool:
        """随机布尔"""
        return random.random() < prob_true

    @staticmethod
    def random_email() -> str:
        """随机邮箱"""
        names = ["john", "jane", "alex", "smith", "tom", "lucy"]
        domains = ["gmail.com", "qq.com", "163.com", "outlook.com"]
        return f"{random.choice(names)}{MockRules.random_int(1, 99)}@{random.choice(domains)}"

    @staticmethod
    def random_phone() -> str:
        """随机手机号"""
        prefixes = ["130", "131", "132", "133", "135", "136", "137", "138", "139", "150", "151", "152", "186", "187", "188"]
        return prefixes[random.randint(0, len(prefixes)-1)] + "".join([str(random.randint(0, 9)) for _ in range(8)])

    @staticmethod
    def random_date(start_year: int = 2020, end_year: int = 2026) -> str:
        """随机日期"""
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        delta = end - start
        random_days = random.randint(0, delta.days)
        return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")

    @staticmethod
    def random_datetime(start_year: int = 2020, end_year: int = 2026) -> str:
        """随机日期时间"""
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31, 23, 59, 59)
        delta = end - start
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return (start + timedelta(seconds=random_seconds)).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def random_url() -> str:
        """随机 URL"""
        domains = ["example.com", "test.com", "api.com", "demo.com"]
        paths = ["users", "products", "orders", "api/v1", "data"]
        return f"https://{random.choice(domains)}/{random.choice(paths)}/{MockRules.random_int(1, 100)}"

    @staticmethod
    def random_ip() -> str:
        """随机 IP"""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"

    @staticmethod
    def random_uuid() -> str:
        """随机 UUID"""
        return f"{MockRules.random_string(8)}-{MockRules.random_string(4)}-{MockRules.random_string(4)}-{MockRules.random_string(4)}-{MockRules.random_string(12)}"

    @staticmethod
    def random_name() -> str:
        """随机姓名"""
        first_names = ["张", "李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"]
        second_names = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "军", "洋", "勇", "艳", "杰", "涛", "明", "超", "秀兰", "桂英", "丹"]
        return random.choice(first_names) + random.choice(second_names)

    @staticmethod
    def random_paragraph(sentences: int = 3) -> str:
        """随机段落"""
        words = ["这个", "那个", "一个", "现在", "然后", "所以", "因为", "如果", "虽然", "但是", "公司", "项目", "用户", "产品", "系统", "开发", "测试", "上线", "运营", "数据"]
        return "".join(random.choice(words) for _ in range(sentences * 10))

    @staticmethod
    def random_image(width: int = 200, height: int = 200) -> str:
        """随机图片 URL"""
        return f"https://picsum.photos/{width}/{height}?random={MockRules.random_int(1, 1000)}"

    @staticmethod
    def increment(start: int = 1) -> int:
        """递增（需要外部计数器）"""
        return start


# ============ 标准字段类型 ============

class StandardFields:
    """标准字段定义"""

    # 用户相关
    USER_ID = {"type": "integer", "mock": {"rule": "increment"}, "description": "用户ID"}
    USERNAME = {"type": "string", "mock": {"rule": "name"}, "description": "用户名"}
    EMAIL = {"type": "string", "mock": {"rule": "email"}, "description": "邮箱"}
    PHONE = {"type": "string", "mock": {"rule": "phone"}, "description": "手机号"}
    PASSWORD = {"type": "string", "mock": {"rule": "fixed", "value": "******"}, "description": "密码"}
    AVATAR = {"type": "string", "mock": {"rule": "image"}, "description": "头像"}
    NICKNAME = {"type": "string", "mock": {"rule": "name"}, "description": "昵称"}
    REAL_NAME = {"type": "string", "mock": {"rule": "name"}, "description": "真实姓名"}
    GENDER = {"type": "string", "mock": {"rule": "choice", "choices": ["male", "female", "unknown"]}, "description": "性别"}
    BIRTHDAY = {"type": "string", "mock": {"rule": "date"}, "description": "生日"}
    STATUS = {"type": "string", "mock": {"rule": "choice", "choices": ["active", "inactive", "banned"]}, "description": "状态"}
    CREATED_AT = {"type": "string", "mock": {"rule": "datetime"}, "description": "创建时间"}
    UPDATED_AT = {"type": "string", "mock": {"rule": "datetime"}, "description": "更新时间"}

    # 分页相关
    PAGE = {"type": "integer", "mock": {"rule": "increment"}, "description": "页码"}
    PAGE_SIZE = {"type": "integer", "mock": {"rule": "fixed", "value": 20}, "description": "每页数量"}
    TOTAL = {"type": "integer", "mock": {"rule": "random_int", "min": 0, "max": 1000}, "description": "总数"}
    TOTAL_PAGES = {"type": "integer", "mock": {"rule": "random_int", "min": 1, "max": 100}, "description": "总页数"}

    # 通用
    ID = {"type": "integer", "mock": {"rule": "increment"}, "description": "ID"}
    UUID = {"type": "string", "mock": {"rule": "uuid"}, "description": "UUID"}
    NAME = {"type": "string", "mock": {"rule": "name"}, "description": "名称"}
    TITLE = {"type": "string", "mock": {"rule": "paragraph"}, "description": "标题"}
    DESCRIPTION = {"type": "string", "mock": {"rule": "paragraph", "sentences": 2}, "description": "描述"}
    CONTENT = {"type": "string", "mock": {"rule": "paragraph", "sentences": 5}, "description": "内容"}
    PRICE = {"type": "number", "mock": {"rule": "random_float", "min": 0.01, "max": 999.99}, "description": "价格"}
    QUANTITY = {"type": "integer", "mock": {"rule": "random_int", "min": 1, "max": 100}, "description": "数量"}
    AMOUNT = {"type": "number", "mock": {"rule": "random_float", "min": 0, "max": 10000}, "description": "金额"}
    URL = {"type": "string", "mock": {"rule": "url"}, "description": "链接"}
    IMAGE = {"type": "string", "mock": {"rule": "image"}, "description": "图片"}
    IP = {"type": "string", "mock": {"rule": "ip"}, "description": "IP 地址"}
    REMARK = {"type": "string", "mock": {"rule": "paragraph", "sentences": 1}, "description": "备注"}


# ============ Mock Schema 生成器 ============

class MockSchemaGenerator:
    """Mock Schema 生成器"""

    def __init__(self):
        self.rules = MockRules()
        self.counters: Dict[str, int] = {}  # 用于 increment 规则

    def generate_from_schema(self, schema: Dict[str, Any]) -> Any:
        """从 Schema 生成 Mock 数据"""
        # 检测 schema 类型
        schema_type = schema.get("type", None)
        
        # 如果没有 type，检查是否是简单 dict（字段名 -> schema 的映射）
        if schema_type is None:
            # 检查是否是 dict of dicts（每个 value 都有 type）
            if isinstance(schema, dict) and len(schema) > 0:
                first_value = next(iter(schema.values()))
                if isinstance(first_value, dict) and "type" in first_value:
                    # 这是简单 object 格式
                    schema_type = "object"
                else:
                    schema_type = "string"
            else:
                schema_type = "string"

        if schema_type == "object":
            return self._generate_object(schema)
        elif schema_type == "array":
            return self._generate_array(schema)
        elif schema_type == "string":
            return self._generate_string(schema)
        elif schema_type in ("integer", "number"):
            return self._generate_number(schema)
        elif schema_type == "boolean":
            return self._generate_boolean(schema)
        else:
            return None

    def _generate_object(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """生成对象"""
        result = {}
        
        # 支持两种格式：
        # 1. OpenAPI 格式: {"type": "object", "properties": {"id": {...}}}
        # 2. 简单 dict 格式: {"id": {...}, "username": {...}}
        properties = schema.get("properties", schema)
        
        # 如果 properties 不是 dict（比如是 list），尝试直接用 schema
        if not isinstance(properties, dict):
            properties = schema

        for field_name, field_schema in properties.items():
            if isinstance(field_schema, dict):
                result[field_name] = self.generate_from_schema(field_schema)
            else:
                result[field_name] = field_schema

        return result

    def _generate_array(self, schema: Dict[str, Any]) -> List[Any]:
        """生成数组"""
        items = schema.get("items", {})
        length = schema.get("minItems", 1) if schema.get("minItems") else random.randint(1, 5)
        return [self.generate_from_schema(items) for _ in range(length)]

    def _generate_string(self, schema: Dict[str, Any]) -> str:
        """生成字符串"""
        mock_config = schema.get("mock", {})
        rule = mock_config.get("rule", "random_string")

        if rule == "fixed":
            return mock_config.get("value", "")
        elif rule == "name":
            return self.rules.random_name()
        elif rule == "email":
            return self.rules.random_email()
        elif rule == "phone":
            return self.rules.random_phone()
        elif rule == "date":
            return self.rules.random_date()
        elif rule == "datetime":
            return self.rules.random_datetime()
        elif rule == "url":
            return self.rules.random_url()
        elif rule == "image":
            return self.rules.random_image()
        elif rule == "uuid":
            return self.rules.random_uuid()
        elif rule == "ip":
            return self.rules.random_ip()
        elif rule == "paragraph":
            return self.rules.random_paragraph(mock_config.get("sentences", 3))
        elif rule == "choice":
            return self.rules.random_choice(mock_config.get("choices", []))
        elif rule == "increment":
            field_id = mock_config.get("field", "default")
            if field_id not in self.counters:
                self.counters[field_id] = mock_config.get("start", 1)
            else:
                self.counters[field_id] += 1
            return self.counters[field_id]
        else:
            return self.rules.random_string(mock_config.get("length", 10))

    def _generate_number(self, schema: Dict[str, Any]) -> float:
        """生成数字"""
        mock_config = schema.get("mock", {})
        rule = mock_config.get("rule", "random_int")

        if rule == "fixed":
            return mock_config.get("value", 0)
        elif rule == "random_int":
            return self.rules.random_int(
                mock_config.get("min", 1),
                mock_config.get("max", 1000)
            )
        elif rule == "random_float":
            return self.rules.random_float(
                mock_config.get("min", 0.0),
                mock_config.get("max", 1000.0),
                mock_config.get("decimals", 2)
            )
        elif rule == "increment":
            field_id = mock_config.get("field", "default")
            if field_id not in self.counters:
                self.counters[field_id] = mock_config.get("start", 1)
            else:
                self.counters[field_id] += 1
            return self.counters[field_id]
        else:
            return self.rules.random_int()

    def _generate_boolean(self, schema: Dict[str, Any]) -> bool:
        """生成布尔值"""
        mock_config = schema.get("mock", {})
        rule = mock_config.get("rule", "random_bool")

        if rule == "fixed":
            return mock_config.get("value", False)
        elif rule == "random_bool":
            return self.rules.random_bool(mock_config.get("prob_true", 0.5))
        else:
            return self.rules.random_bool()


# ============ 预定义 Mock Schema ============

class MockSchemas:
    """预定义的 Mock Schema"""

    @staticmethod
    def user() -> Dict[str, Any]:
        """用户 Schema"""
        return {
            "id": StandardFields.USER_ID.copy(),
            "username": StandardFields.USERNAME.copy(),
            "email": StandardFields.EMAIL.copy(),
            "phone": StandardFields.PHONE.copy(),
            "nickname": StandardFields.NICKNAME.copy(),
            "avatar": StandardFields.AVATAR.copy(),
            "gender": StandardFields.GENDER.copy(),
            "status": StandardFields.STATUS.copy(),
            "created_at": StandardFields.CREATED_AT.copy(),
            "updated_at": StandardFields.UPDATED_AT.copy()
        }

    @staticmethod
    def pagination(items_schema: Dict[str, Any] = None) -> Dict[str, Any]:
        """分页 Schema"""
        schema = {
            "page": StandardFields.PAGE.copy(),
            "page_size": StandardFields.PAGE_SIZE.copy(),
            "total": StandardFields.TOTAL.copy(),
            "total_pages": StandardFields.TOTAL_PAGES.copy(),
        }
        if items_schema:
            schema["items"] = {"type": "array", "items": items_schema}
        return schema

    @staticmethod
    def product() -> Dict[str, Any]:
        """商品 Schema"""
        return {
            "id": StandardFields.ID.copy(),
            "name": StandardFields.NAME.copy(),
            "description": StandardFields.DESCRIPTION.copy(),
            "price": StandardFields.PRICE.copy(),
            "stock": StandardFields.QUANTITY.copy(),
            "image": StandardFields.IMAGE.copy(),
            "status": StandardFields.STATUS.copy(),
            "created_at": StandardFields.CREATED_AT.copy()
        }

    @staticmethod
    def order() -> Dict[str, Any]:
        """订单 Schema"""
        return {
            "id": StandardFields.UUID.copy(),
            "user_id": StandardFields.USER_ID.copy(),
            "total_amount": StandardFields.AMOUNT.copy(),
            "status": {"type": "string", "mock": {"rule": "choice", "choices": ["pending", "paid", "shipped", "completed", "cancelled"]}},
            "created_at": StandardFields.CREATED_AT.copy(),
            "paid_at": {"type": "string", "mock": {"rule": "datetime"}, "description": "支付时间", "nullable": True}
        }

    @staticmethod
    def article() -> Dict[str, Any]:
        """文章 Schema"""
        return {
            "id": StandardFields.ID.copy(),
            "title": StandardFields.TITLE.copy(),
            "content": StandardFields.CONTENT.copy(),
            "author": StandardFields.USERNAME.copy(),
            "cover_image": StandardFields.IMAGE.copy(),
            "status": StandardFields.STATUS.copy(),
            "views": {"type": "integer", "mock": {"rule": "random_int", "min": 0, "max": 10000}},
            "created_at": StandardFields.CREATED_AT.copy(),
            "updated_at": StandardFields.UPDATED_AT.copy()
        }


# ============ Mock 数据生成器 ============

class MockDataGenerator:
    """Mock 数据生成器"""

    def __init__(self):
        self.schema_generator = MockSchemaGenerator()
        self.schemas = MockSchemas()

    def generate(self, schema: Dict[str, Any], count: int = 1) -> Any:
        """生成 Mock 数据"""
        self.schema_generator.counters.clear()  # 重置计数器

        if count == 1:
            return self.schema_generator.generate_from_schema(schema)
        else:
            return [self.schema_generator.generate_from_schema(schema) for _ in range(count)]

    def generate_user(self, count: int = 1) -> Any:
        """生成用户数据"""
        return self.generate(self.schemas.user(), count)

    def generate_product(self, count: int = 1) -> Any:
        """生成商品数据"""
        return self.generate(self.schemas.product(), count)

    def generate_order(self, count: int = 1) -> Any:
        """生成订单数据"""
        return self.generate(self.schemas.order(), count)

    def generate_article(self, count: int = 1) -> Any:
        """生成文章数据"""
        return self.generate(self.schemas.article(), count)

    def generate_paginated_users(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """生成分页用户数据"""
        self.schema_generator.counters.clear()
        users = self.generate(self.schemas.user(), page_size)
        return {
            "page": page,
            "page_size": page_size,
            "total": random.randint(100, 1000),
            "total_pages": random.randint(5, 50),
            "items": users
        }


# ============ CLI ============

def cmd_user(args):
    """生成用户 Mock 数据"""
    generator = MockDataGenerator()
    count = args.count
    data = generator.generate_user(count)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def cmd_product(args):
    """生成商品 Mock 数据"""
    generator = MockDataGenerator()
    count = args.count
    data = generator.generate_product(count)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def cmd_order(args):
    """生成订单 Mock 数据"""
    generator = MockDataGenerator()
    count = args.count
    data = generator.generate_order(count)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def cmd_paginated(args):
    """生成分页 Mock 数据"""
    generator = MockDataGenerator()
    data = generator.generate_paginated_users(args.page, args.page_size)
    print(json.dumps(data, ensure_ascii=False, indent=2))

def cmd_schema(args):
    """输出标准 Schema"""
    schemas = MockSchemas()
    if args.type == "user":
        schema = schemas.user()
    elif args.type == "product":
        schema = schemas.product()
    elif args.type == "order":
        schema = schemas.order()
    elif args.type == "article":
        schema = schemas.article()
    elif args.type == "pagination":
        schema = schemas.pagination()
    else:
        schema = {}
    print(json.dumps(schema, ensure_ascii=False, indent=2))

def cmd_generate(args):
    """从 OpenAPI 生成 Mock 数据"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from openapi_tools import OpenAPIExporter

    exporter = OpenAPIExporter(args.project)
    openapi_file = Path.home() / ".openclaw" / "orchestrator" / "projects" / args.project / "api-contract" / "openapi.yaml"

    if not openapi_file.exists():
        print(f"❌ OpenAPI 文件不存在: {openapi_file}")
        return

    content = json.loads(openapi_file.read_text())
    generator = MockDataGenerator()
    generator.schema_generator.counters.clear()

    mocks = {}
    for path, methods in content.get("paths", {}).items():
        for method, spec in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                # 生成 Mock 响应
                resp_200 = spec.get("responses", {}).get("200", {})
                content_spec = resp_200.get("content", {}).get("application/json", {}).get("schema", {})

                if content_spec:
                    mocks[f"{method.upper()} {path}"] = generator.schema_generator.generate_from_schema(content_spec)

    print(json.dumps(mocks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock Schema - Mock 数据生成")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # user
    p_user = subparsers.add_parser("user", help="生成用户 Mock")
    p_user.add_argument("--count", "-n", type=int, default=1, help="数量")
    p_user.set_defaults(func=cmd_user)

    # product
    p_product = subparsers.add_parser("product", help="生成商品 Mock")
    p_product.add_argument("--count", "-n", type=int, default=1, help="数量")
    p_product.set_defaults(func=cmd_product)

    # order
    p_order = subparsers.add_parser("order", help="生成订单 Mock")
    p_order.add_argument("--count", "-n", type=int, default=1, help="数量")
    p_order.set_defaults(func=cmd_order)

    # paginated
    p_page = subparsers.add_parser("paginated", help="生成分页 Mock")
    p_page.add_argument("--page", "-p", type=int, default=1, help="页码")
    p_page.add_argument("--page-size", "-s", type=int, default=20, help="每页数量")
    p_page.set_defaults(func=cmd_paginated)

    # schema
    p_schema = subparsers.add_parser("schema", help="输出标准 Schema")
    p_schema.add_argument("type", choices=["user", "product", "order", "article", "pagination"], help="Schema 类型")
    p_schema.set_defaults(func=cmd_schema)

    # generate
    p_gen = subparsers.add_parser("generate", help="从 OpenAPI 生成 Mock")
    p_gen.add_argument("project", help="项目名称")
    p_gen.set_defaults(func=cmd_generate)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)
