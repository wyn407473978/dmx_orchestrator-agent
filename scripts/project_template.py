#!/usr/bin/env python3
"""
Project Templates - 项目模板系统

功能：
1. 预定义项目模板（电商、博客、管理后台等）
2. 快速初始化项目结构
3. 自动配置技术栈和依赖

模板目录结构：
   ~/.openclaw/orchestrator/templates/
   ├── metadata.json              # 模板索引
   ├── ecommerce/
   │   ├── metadata.json         # 模板描述
   │   ├── tech-stack.yaml       # 技术栈
   │   ├── project-structure/    # 项目结构
   │   │   ├── backend/
   │   │   ├── frontend/
   │   │   └── docker/
   │   ├── openapi/            # API 规范
   │   └── scripts/
   │       └── init.sh
   └── ...
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


# ============ 配置 ============

TEMPLATES_DIR = Path.home() / ".openclaw" / "orchestrator" / "templates"
PROJECTS_DIR = Path.home() / ".openclaw" / "orchestrator" / "projects"


# ============ 内置模板定义 ============

BUILTIN_TEMPLATES = {
    "ecommerce": {
        "name": "ecommerce",
        "display_name": "电商后台",
        "description": "完整的电商后台管理系统，包含商品、订单、用户、支付等模块",
        "tech_stack": {
            "backend": "Go + Gin + GORM + PostgreSQL",
            "frontend": "React + TypeScript + Ant Design Pro",
            "cache": "Redis",
            "search": "Elasticsearch",
            "queue": "RabbitMQ",
            "docker": "docker-compose"
        },
        "features": [
            "商品管理（CRUD + 分类 + 标签 + SKU）",
            "订单管理（下单 + 支付 + 物流 + 售后）",
            "用户管理（注册 + 登录 + 权限 + 积分）",
            "库存管理（入库 + 出库 + 盘点）",
            "数据分析（报表 + 图表 + 导出）"
        ],
        "api_modules": [
            {"name": "user", "endpoints": ["/api/v1/users", "/api/v1/auth"]},
            {"name": "product", "endpoints": ["/api/v1/products", "/api/v1/categories"]},
            {"name": "order", "endpoints": ["/api/v1/orders", "/api/v1/payments"]},
            {"name": "inventory", "endpoints": ["/api/v1/inventory"]},
            {"name": "analytics", "endpoints": ["/api/v1/stats", "/api/v1/reports"]}
        ],
        "stages": {
            "parallel_dev": True,
            "api_review_required": True,
            "mock_data_required": True
        }
    },

    "blog": {
        "name": "blog",
        "display_name": "博客系统",
        "description": "支持多用户的博客系统，包含文章、评论、标签、搜索等功能",
        "tech_stack": {
            "backend": "Go + Gin + GORM + PostgreSQL",
            "frontend": "Next.js + TypeScript + TailwindCSS",
            "cache": "Redis",
            "search": "Elasticsearch"
        },
        "features": [
            "文章管理（Markdown + 富文本 + 草稿）",
            "评论系统（嵌套评论 + 点赞）",
            "用户系统（注册 + 登录 + 权限）",
            "标签系统（多标签 + 分类）",
            "搜索（全文搜索 + 标签搜索）"
        ],
        "api_modules": [
            {"name": "article", "endpoints": ["/api/v1/articles", "/api/v1/drafts"]},
            {"name": "comment", "endpoints": ["/api/v1/comments"]},
            {"name": "user", "endpoints": ["/api/v1/users", "/api/v1/auth"]},
            {"name": "tag", "endpoints": ["/api/v1/tags", "/api/v1/categories"]}
        ],
        "stages": {
            "parallel_dev": True,
            "api_review_required": True,
            "mock_data_required": True
        }
    },

    "dashboard": {
        "name": "dashboard",
        "display_name": "管理后台",
        "description": "通用管理后台模板，包含仪表盘、CRUD、表单、图表等",
        "tech_stack": {
            "backend": "Go + Gin + GORM + PostgreSQL",
            "frontend": "React + TypeScript + Ant Design",
            "cache": "Redis"
        },
        "features": [
            "仪表盘（统计卡片 + 图表）",
            "数据表格（分页 + 筛选 + 排序 + 导出）",
            "表单（单表 + 多步表单）",
            "用户权限（RBAC + 菜单权限）",
            "系统设置（配置管理）"
        ],
        "api_modules": [
            {"name": "dashboard", "endpoints": ["/api/v1/dashboard/stats"]},
            {"name": "crud", "endpoints": ["/api/v1/resources", "/api/v1/resources/{id}"]},
            {"name": "user", "endpoints": ["/api/v1/users"]},
            {"name": "role", "endpoints": ["/api/v1/roles", "/api/v1/permissions"]},
            {"name": "setting", "endpoints": ["/api/v1/settings"]}
        ],
        "stages": {
            "parallel_dev": True,
            "api_review_required": True,
            "mock_data_required": False
        }
    },

    "saas": {
        "name": "saas",
        "display_name": "SaaS 应用",
        "description": "多租户 SaaS 模板，支持租户隔离、订阅计费、使用量统计",
        "tech_stack": {
            "backend": "Go + Gin + GORM + PostgreSQL",
            "frontend": "React + TypeScript + TailwindCSS",
            "cache": "Redis",
            "queue": "RabbitMQ"
        },
        "features": [
            "多租户（租户隔离 + 租户管理）",
            "订阅计费（套餐 + 订阅 + 续费 + 升级）",
            "使用量统计（API 调用 + 存储 + 流量）",
            "团队管理（成员 + 邀请 + 角色）",
            "Webhooks（事件通知 + 回调）"
        ],
        "api_modules": [
            {"name": "tenant", "endpoints": ["/api/v1/tenants"]},
            {"name": "subscription", "endpoints": ["/api/v1/subscriptions", "/api/v1/plans"]},
            {"name": "usage", "endpoints": ["/api/v1/usage", "/api/v1/billing"]},
            {"name": "team", "endpoints": ["/api/v1/team", "/api/v1/invites"]},
            {"name": "webhook", "endpoints": ["/api/v1/webhooks"]}
        ],
        "stages": {
            "parallel_dev": True,
            "api_review_required": True,
            "mock_data_required": True
        }
    }
}


# ============ 模板管理器 ============

class TemplateManager:
    """模板管理器"""

    def __init__(self):
        self.templates_dir = TEMPLATES_DIR
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_builtin_templates()

    def _ensure_builtin_templates(self):
        """确保内置模板存在"""
        for template_id, template_data in BUILTIN_TEMPLATES.items():
            template_dir = self.templates_dir / template_id
            metadata_file = template_dir / "metadata.json"

            if not metadata_file.exists():
                template_dir.mkdir(parents=True, exist_ok=True)
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(template_data, f, ensure_ascii=False, indent=2)
                print(f"[TemplateManager] ✅ 创建内置模板: {template_id}")

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用模板"""
        templates = []

        for template_dir in self.templates_dir.iterdir():
            if template_dir.is_dir():
                metadata_file = template_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        templates.append(json.load(f))

        return templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板详情"""
        template_dir = self.templates_dir / template_id
        metadata_file = template_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate_openapi_from_template(self, template_id: str) -> Dict[str, Any]:
        """从模板生成 OpenAPI 规范"""
        template = self.get_template(template_id)
        if not template:
            return {}

        paths = {}
        components = {
            "schemas": {}
        }

        for module in template.get("api_modules", []):
            module_name = module["name"]

            for endpoint in module.get("endpoints", []):
                # GET list
                paths[endpoint] = {
                    "get": {
                        "summary": f"获取{module_name}列表",
                        "tags": [module_name],
                        "responses": {"200": {"description": "成功"}}
                    }
                }

                # POST create
                paths[endpoint] = paths.get(endpoint, {})
                paths[endpoint]["post"] = {
                    "summary": f"创建{module_name}",
                    "tags": [module_name],
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                    "responses": {"201": {"description": "创建成功"}}
                }

                # GET by id
                detail_endpoint = f"{endpoint}/{{id}}"
                paths[detail_endpoint] = {
                    "get": {
                        "summary": f"获取{module_name}详情",
                        "tags": [module_name],
                        "parameters": [{"name": "id", "in": "path", "required": True}],
                        "responses": {"200": {"description": "成功"}}
                    },
                    "put": {
                        "summary": f"更新{module_name}",
                        "tags": [module_name],
                        "parameters": [{"name": "id", "in": "path", "required": True}],
                        "responses": {"200": {"description": "成功"}}
                    },
                    "delete": {
                        "summary": f"删除{module_name}",
                        "tags": [module_name],
                        "parameters": [{"name": "id", "in": "path", "required": True}],
                        "responses": {"204": {"description": "删除成功"}}
                    }
                }

        return {
            "openapi": "3.0.0",
            "info": {
                "title": template.get("display_name", template_id),
                "version": "1.0.0"
            },
            "paths": paths,
            "components": components
        }

    def create_project_from_template(
        self,
        project_name: str,
        template_id: str,
        project_dir: Path = None
    ) -> Dict[str, Any]:
        """从模板创建项目"""
        template = self.get_template(template_id)
        if not template:
            return {"ok": False, "error": f"模板 '{template_id}' 不存在"}

        if project_dir is None:
            project_dir = PROJECTS_DIR / project_name

        # 创建项目目录
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (project_dir / "artifacts").mkdir(exist_ok=True)
        (project_dir / "api-contract").mkdir(exist_ok=True)
        (project_dir / "designs" / "pages").mkdir(parents=True, exist_ok=True)
        (project_dir / "events").mkdir(exist_ok=True)
        (project_dir / "messages").mkdir(exist_ok=True)
        (project_dir / "backend").mkdir(exist_ok=True)
        (project_dir / "frontend").mkdir(exist_ok=True)

        # 生成 OpenAPI 文档
        openapi = self.generate_openapi_from_template(template_id)
        openapi_file = project_dir / "api-contract" / "openapi.yaml"
        with open(openapi_file, 'w', encoding='utf-8') as f:
            json.dump(openapi, f, ensure_ascii=False, indent=2)

        # 保存模板信息
        template_info = {
            "project_name": project_name,
            "template_id": template_id,
            "template_name": template.get("display_name"),
            "created_at": datetime.now().isoformat(),
            "tech_stack": template.get("tech_stack", {}),
            "features": template.get("features", []),
            "api_modules": template.get("api_modules", [])
        }

        with open(project_dir / "template-info.json", 'w', encoding='utf-8') as f:
            json.dump(template_info, f, ensure_ascii=False, indent=2)

        return {
            "ok": True,
            "project_dir": str(project_dir),
            "template": template.get("display_name"),
            "tech_stack": template.get("tech_stack", {}),
            "api_modules": len(template.get("api_modules", [])),
            "message": f"""✅ 项目 '{project_name}' 创建成功！

模板: {template.get('display_name')}
技术栈: {', '.join(template.get('tech_stack', {}).values())}
API 模块: {len(template.get('api_modules', []))} 个

目录结构:
{project_dir}/
├── artifacts/          # 产出物
├── api-contract/      # API 文档 (已生成 openapi.yaml)
├── designs/          # UI 设计
├── events/           # 事件日志
├── messages/         # 消息队列
├── backend/         # 后端代码
└── frontend/        # 前端代码"""
        }


# ============ CLI ============

def cmd_list(args):
    """列出所有模板"""
    manager = TemplateManager()
    templates = manager.list_templates()

    print(f"\n{'='*60}")
    print(f"可用模板 ({len(templates)} 个)")
    print(f"{'='*60}\n")

    for t in templates:
        print(f"📦 {t.get('display_name')} ({t.get('name')})")
        print(f"   {t.get('description', '')}")
        print(f"   技术栈: {', '.join(t.get('tech_stack', {}).values())}")
        print()

    return templates


def cmd_info(args):
    """查看模板详情"""
    manager = TemplateManager()
    template = manager.get_template(args.template)

    if not template:
        print(f"❌ 模板 '{args.template}' 不存在")
        return

    print(f"\n{'='*60}")
    print(f"📦 {template.get('display_name')}")
    print(f"{'='*60}")
    print(f"\n描述: {template.get('description', '')}")
    print(f"\n技术栈:")
    for key, value in template.get('tech_stack', {}).items():
        print(f"   {key}: {value}")

    print(f"\n功能:")
    for feature in template.get('features', []):
        print(f"   - {feature}")

    print(f"\nAPI 模块 ({len(template.get('api_modules', []))} 个):")
    for module in template.get('api_modules', []):
        print(f"   [{module.get('name')}] {len(module.get('endpoints', []))} 个接口")

    return template


def cmd_create(args):
    """从模板创建项目"""
    manager = TemplateManager()
    project_dir = Path(args.output) if args.output else None

    result = manager.create_project_from_template(
        args.project,
        args.template,
        project_dir
    )

    if result.get('ok'):
        print(result.get('message', ''))
    else:
        print(f"❌ 创建失败: {result.get('error', '')}")

    return result


def cmd_generate_openapi(args):
    """生成 OpenAPI 文档"""
    manager = TemplateManager()
    openapi = manager.generate_openapi_from_template(args.template)

    if not openapi:
        print(f"❌ 模板 '{args.template}' 不存在")
        return

    output_file = Path(args.output) if args.output else Path.cwd() / "openapi.yaml"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(openapi, f, ensure_ascii=False, indent=2)

    print(f"✅ OpenAPI 文档已生成: {output_file}")
    print(f"   路径数: {len(openapi.get('paths', {}))}")

    return openapi


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Project Templates - 项目模板系统")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list
    p_list = subparsers.add_parser("list", help="列出所有模板")

    # info
    p_info = subparsers.add_parser("info", help="查看模板详情")
    p_info.add_argument("template", help="模板名称")

    # create
    p_create = subparsers.add_parser("create", help="从模板创建项目")
    p_create.add_argument("project", help="项目名称")
    p_create.add_argument("template", help="模板名称")
    p_create.add_argument("--output", "-o", help="项目目录")

    # generate-openapi
    p_gen = subparsers.add_parser("generate-openapi", help="生成 OpenAPI 文档")
    p_gen.add_argument("template", help="模板名称")
    p_gen.add_argument("--output", "-o", help="输出文件")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "info": cmd_info,
        "create": cmd_create,
        "generate-openapi": cmd_generate_openapi,
    }

    if args.command is None:
        parser.print_help()
    else:
        commands[args.command](args)
