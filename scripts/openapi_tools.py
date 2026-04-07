#!/usr/bin/env python3
"""
API Tools - API 文档自动生成与验证

功能：
1. 从代码自动提取 API 路由生成 OpenAPI 文档
2. 验证 API 文档的完整性和正确性
3. 生成 Mock 数据
4. 检查前后端接口一致性
"""

import json
import re
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# ============ 配置 ============

DEFAULT_API_VERSION = "v1"
DEFAULT_BASE_PATH = "/api"


# ============ OpenAPI 生成 ============

class OpenAPIExporter:
    """OpenAPI 文档生成器"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_dir = Path.home() / ".openclaw" / "orchestrator" / "projects" / project_name
        self.api_contract_dir = self.project_dir / "api-contract"

    def scan_routes(self, routes_dir: Path) -> List[Dict[str, Any]]:
        """扫描代码中的路由定义"""
        routes = []

        if not routes_dir.exists():
            return routes

        # 支持的路由文件模式
        patterns = ["*.go", "*.py", "*.js", "*.ts"]

        for pattern in patterns:
            for file_path in routes_dir.rglob(pattern):
                if file_path.name in ["route.go", "router.go", "routes.go", "api.py", "routes.js", "routes.ts"]:
                    routes.extend(self._parse_route_file(file_path))

        return routes

    def _parse_route_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """解析路由文件（增强版）"""
        routes = []
        content = file_path.read_text(encoding='utf-8')

        # === Go Gin 路由模式 ===
        # router.HandleFunc("/users", handler).Methods("GET", "POST")
        go_pattern = r'(?:router|Route|HandleFunc|Mux)\s*[.(]\s*"([^"]+)"\s*,\s*(\w+)\s*\)(?:\.Methods\s*\(\s*"([A-Z]+)"\s*(?:,\s*"([A-Z]+)")*\s*\))?'

        for match in re.finditer(go_pattern, content):
            path = match.group(1)
            handler = match.group(2)
            methods = [m for m in [match.group(3), match.group(4)] if m]
            
            if not methods:
                methods = ["GET"]
            
            for method in methods:
                routes.append({
                    "path": path,
                    "method": method.upper(),
                    "handler": handler,
                    "source_file": str(file_path)
                })

        # === Go Gorilla Mux 路由模式 ===
        # mux.Methods("GET", "POST").Path("/users").HandlerFunc(handler)
        gorilla_pattern = r'\.Path\s*\(\s*"([^"]+)"\s*\)\s*\.HandlerFunc\s*\(\s*(\w+)\s*\)\s*\.Methods\s*\(\s*"([A-Z]+)"\s*(?:,\s*"([A-Z]+)")*'
        
        for match in re.finditer(gorilla_pattern, content):
            path = match.group(1)
            handler = match.group(2)
            methods = [m for m in [match.group(3), match.group(4)] if m] or ["GET"]
            
            for method in methods:
                routes.append({
                    "path": path,
                    "method": method.upper(),
                    "handler": handler,
                    "source_file": str(file_path)
                })

        # === Python FastAPI 装饰器模式 ===
        # @app.get("/users")
        # @router.post("/users")
        fastapi_pattern = r'@(\w+)\.(get|post|put|patch|delete|options|head)\s*\(\s*"([^"]+)"\s*\)'
        
        for match in re.finditer(fastapi_pattern, content):
            decorator = match.group(1)
            method = match.group(2).upper()
            path = match.group(3)
            
            routes.append({
                "path": path,
                "method": method,
                "handler": f"{decorator}_handler",
                "source_file": str(file_path)
            })

        # === Python Flask 路由模式 ===
        # @app.route('/users', methods=['GET', 'POST'])
        flask_pattern = r'@app\.route\s*\(\s*"([^"]+)"\s*(?:,\s*methods\s*=\s*\[(?:"([A-Z]+)"(?:,\s*)?)*\])?'
        
        for match in re.finditer(flask_pattern, content):
            path = match.group(1)
            method = match.group(2) or "GET"
            
            routes.append({
                "path": path,
                "method": method.upper(),
                "handler": "flask_handler",
                "source_file": str(file_path)
            })

        # === Express.js 路由模式 ===
        # router.get('/users', handler)
        # app.post('/users', handler)
        express_pattern = r'(?:router|app)\.(\w+)\s*\(\s*["\'](/[^"\']+)["\']\s*,\s*(\w+)\s*\)'
        
        for match in re.finditer(express_pattern, content):
            method = match.group(1).upper()
            path = match.group(2)
            handler = match.group(3)
            
            routes.append({
                "path": path,
                "method": method,
                "handler": handler,
                "source_file": str(file_path)
            })

        # === Next.js App Router 模式 ===
        # export async function GET(request: Request) {}
        # route.ts or route.js
        if file_path.name in ['route.ts', 'route.js', 'route.tsx', 'route.jsx']:
            nextjs_pattern = r'export\s+async\s+function\s+(\w+)\s*\('
            for match in re.finditer(nextjs_pattern, content):
                method = match.group(1).upper()
                routes.append({
                    "path": "/",
                    "method": method,
                    "handler": "nextjs_route_handler",
                    "source_file": str(file_path)
                })

        return routes

        return routes

    def generate_openapi(self, routes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成 OpenAPI 文档"""
        paths = {}

        for route in routes:
            path = route["path"]
            method = route["method"].lower()

            if path not in paths:
                paths[path] = {}

            paths[path][method] = {
                "summary": f"{method.upper()} {path}",
                "operationId": f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}",
                "parameters": self._extract_params(path),
                "responses": {
                    "200": {
                        "description": "Successful response"
                    },
                    "400": {
                        "description": "Bad request"
                    },
                    "401": {
                        "description": "Unauthorized"
                    },
                    "404": {
                        "description": "Not found"
                    },
                    "500": {
                        "description": "Internal server error"
                    }
                }
            }

        openapi_doc = {
            "openapi": "3.0.0",
            "info": {
                "title": self.project_name,
                "version": "1.0.0",
                "description": f"API documentation for {self.project_name}"
            },
            "servers": [
                {
                    "url": f"http://localhost:8000{DEFAULT_BASE_PATH}",
                    "description": "Development server"
                }
            ],
            "paths": paths,
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            }
        }

        return openapi_doc

    def _extract_params(self, path: str) -> List[Dict[str, Any]]:
        """从路径提取参数"""
        params = []
        # 匹配 {param} 格式
        param_pattern = r'\{([^}]+)\}'

        for match in re.finditer(param_pattern, path):
            param_name = match.group(1)
            params.append({
                "name": param_name,
                "in": "path",
                "required": True,
                "schema": {
                    "type": "string"
                }
            })

        return params

    def save_openapi(self, openapi_doc: Dict[str, Any], output_file: Path = None):
        """保存 OpenAPI 文档"""
        self.api_contract_dir.mkdir(parents=True, exist_ok=True)

        if output_file is None:
            output_file = self.api_contract_dir / "openapi.yaml"

        # 简单转换 JSON 为 YAML 格式（实际应该用 pyyaml）
        yaml_content = self._json_to_yaml(openapi_doc)
        output_file.write_text(yaml_content, encoding='utf-8')

        print(f"✅ OpenAPI 文档已生成: {output_file}")
        return str(output_file)

    def _json_to_yaml(self, obj, indent=0) -> str:
        """简单 JSON to YAML 转换"""
        lines = []
        prefix = "  " * indent

        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._json_to_yaml(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {json.dumps(value) if isinstance(value, str) else value}")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    first = True
                    for key, value in item.items():
                        if first:
                            lines.append(f"{prefix}- {key}: {json.dumps(value) if isinstance(value, str) else value}")
                            first = False
                        else:
                            lines.append(f"{prefix}  {key}: {json.dumps(value) if isinstance(value, str) else value}")
                else:
                    lines.append(f"{prefix}- {json.dumps(item) if isinstance(item, str) else item}")

        return "\n".join(lines)


# ============ API 验证 ============

class APIVerifier:
    """API 文档验证器"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_dir = Path.home() / ".openclaw" / "orchestrator" / "projects" / project_name
        self.api_contract_dir = self.project_dir / "api-contract"
        self.issues = []

    def load_openapi(self) -> Optional[Dict[str, Any]]:
        """加载 OpenAPI 文档"""
        openapi_file = self.api_contract_dir / "openapi.yaml"

        if not openapi_file.exists():
            openapi_file = self.api_contract_dir / "openapi.json"

        if not openapi_file.exists():
            return None

        content = openapi_file.read_text(encoding='utf-8')

        if openapi_file.suffix == ".yaml":
            # 简单 YAML 解析（实际应该用 pyyaml）
            return json.loads(self._yaml_to_json(content))
        else:
            return json.loads(content)

    def _yaml_to_json(self, yaml_str: str) -> str:
        """简单 YAML to JSON 转换"""
        # 这里做最简单的转换，实际应该用 pyyaml
        lines = []
        in_list = False

        for line in yaml_str.split('\n'):
            stripped = line.strip()

            if not stripped or stripped.startswith('#'):
                continue

            if ':' in stripped:
                key, value = stripped.split(':', 1)
                value = value.strip()

                if value.startswith('"') or value.startswith("'"):
                    # 字符串值，保持 JSON 格式
                    lines.append(f'"{key.strip()}": {value}')
                elif value == '' or value == '|' or value == '>':
                    # 对象开始
                    lines.append(f'"{key.strip()}": {{')
                    in_list = False
                elif value.startswith('-'):
                    # 列表项
                    if not in_list:
                        lines.append(f'"{key.strip()}": [')
                        in_list = True
                    lines.append(f'  {value}')
                elif in_list and not stripped.startswith('-'):
                    in_list = False
                    lines.append(']')
                    lines.append(f'"{key.strip()}": {value if value != "" else "null"}')
                else:
                    lines.append(f'"{key.strip()}": {value if value != "" else "null"}')

        # 简化处理，返回 JSON
        json_str = '{' + ','.join(lines) + '}'
        return json_str

    def verify(self) -> Dict[str, Any]:
        """执行验证"""
        self.issues = []
        openapi_doc = self.load_openapi()

        if not openapi_doc:
            return {
                "ok": False,
                "error": "OpenAPI 文档不存在",
                "issues": []
            }

        # 验证必需字段
        self._verify_required_fields(openapi_doc)

        # 验证 paths
        if "paths" in openapi_doc:
            for path, methods in openapi_doc["paths"].items():
                self._verify_path(path, methods)

        # 验证 schemas
        if "components" in openapi_doc and "schemas" in openapi_doc["components"]:
            self._verify_schemas(openapi_doc["components"]["schemas"])

        return {
            "ok": len(self.issues) == 0,
            "total_checks": len(openapi_doc.get("paths", {})),
            "issues": self.issues
        }

    def _verify_required_fields(self, doc: Dict[str, Any]):
        """验证必需字段"""
        required = ["openapi", "info", "paths"]
        for field in required:
            if field not in doc:
                self.issues.append({
                    "type": "missing_field",
                    "message": f"缺少必需字段: {field}"
                })

    def _verify_path(self, path: str, methods: Dict[str, Any]):
        """验证单个路径"""
        valid_methods = ["get", "post", "put", "patch", "delete", "options", "head"]

        for method, spec in methods.items():
            if method.lower() not in valid_methods:
                self.issues.append({
                    "type": "invalid_method",
                    "path": path,
                    "method": method,
                    "message": f"无效的 HTTP 方法: {method}"
                })

            # 检查是否有 summary
            if "summary" not in spec and "operationId" not in spec:
                self.issues.append({
                    "type": "missing_documentation",
                    "path": path,
                    "method": method,
                    "message": f"路径 {path} {method.upper()} 缺少 summary 或 operationId"
                })

            # 检查 responses
            if "responses" not in spec:
                self.issues.append({
                    "type": "missing_responses",
                    "path": path,
                    "method": method,
                    "message": f"路径 {path} {method.upper()} 缺少 responses 定义"
                })

    def _verify_schemas(self, schemas: Dict[str, Any]):
        """验证 Schema 定义"""
        for schema_name, schema in schemas.items():
            if "type" not in schema and "properties" not in schema:
                self.issues.append({
                    "type": "invalid_schema",
                    "schema": schema_name,
                    "message": f"Schema {schema_name} 缺少 type 或 properties"
                })


# ============ Mock 生成 ============

class MockGenerator:
    """Mock 数据生成器"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_dir = Path.home() / ".openclaw" / "orchestrator" / "projects" / project_name
        self.api_contract_dir = self.project_dir / "api-contract"
        self.mocks_dir = self.api_contract_dir / "mocks"

    def generate_mocks(self, openapi_doc: Dict[str, Any]) -> Dict[str, Any]:
        """根据 OpenAPI 生成 Mock 数据"""
        mocks = {}

        if "paths" not in openapi_doc:
            return mocks

        for path, methods in openapi_doc["paths"].items():
            for method, spec in methods.items():
                key = f"{method.upper()} {path}"
                mocks[key] = self._generate_response_mock(spec)

        return mocks

    def _generate_response_mock(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """为单个 endpoint 生成 Mock"""
        mock = {
            "status": 200,
            "headers": {
                "Content-Type": "application/json"
            }
        }

        # 从 schema 生成 mock data
        if "responses" in spec:
            resp_200 = spec["responses"].get("200", {})
            if "content" in resp_200:
                content = resp_200["content"]
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    mock["body"] = self._generate_from_schema(schema)

        return mock

    def _generate_from_schema(self, schema: Dict[str, Any]) -> Any:
        """根据 schema 生成数据"""
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            result = {}
            for prop_name, prop_schema in schema.get("properties", {}).items():
                result[prop_name] = self._generate_from_schema(prop_schema)
            return result
        elif schema_type == "array":
            item_schema = schema.get("items", {})
            return [self._generate_from_schema(item_schema)]
        elif schema_type == "string":
            if "enum" in schema:
                return schema["enum"][0]
            return "string"
        elif schema_type == "integer" or schema_type == "number":
            return 0
        elif schema_type == "boolean":
            return True
        else:
            return None

    def save_mocks(self, mocks: Dict[str, Any]):
        """保存 Mock 数据"""
        self.mocks_dir.mkdir(parents=True, exist_ok=True)

        output_file = self.mocks_dir / "api-mocks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(mocks, f, ensure_ascii=False, indent=2)

        print(f"✅ Mock 数据已生成: {output_file}")
        return str(output_file)


# ============ CLI ============

def cmd_generate(args):
    """生成 OpenAPI 文档"""
    exporter = OpenAPIExporter(args.project)

    if args.routes_dir:
        routes_dir = Path(args.routes_dir)
    else:
        routes_dir = Path.home() / "projects" / args.project / "backend"

    print(f"🔍 扫描路由目录: {routes_dir}")
    routes = exporter.scan_routes(routes_dir)
    print(f"📋 发现 {len(routes)} 个路由")

    if routes:
        openapi_doc = exporter.generate_openapi(routes)
        output_file = exporter.save_openapi(openapi_doc)
        print(f"✅ OpenAPI 文档已保存: {output_file}")
    else:
        print("⚠️ 未发现路由，请手动创建 OpenAPI 文档")


def cmd_verify(args):
    """验证 API 文档"""
    verifier = APIVerifier(args.project)
    result = verifier.verify()

    print(f"\n{'='*50}")
    print(f"API 验证结果: {'✅ 通过' if result['ok'] else '❌ 失败'}")
    print(f"{'='*50}")

    if result.get("total_checks"):
        print(f"检查接口数: {result['total_checks']}")

    if result.get("issues"):
        print(f"\n发现 {len(result['issues'])} 个问题:\n")
        for i, issue in enumerate(result["issues"], 1):
            print(f"{i}. [{issue['type']}] {issue['message']}")
            if "path" in issue:
                print(f"   路径: {issue['path']} {issue.get('method', '').upper()}")
    else:
        print("\n🎉 没有发现问题！")

    return result


def cmd_mock(args):
    """生成 Mock 数据"""
    verifier = APIVerifier(args.project)
    openapi_doc = verifier.load_openapi()

    if not openapi_doc:
        print("❌ OpenAPI 文档不存在，请先运行 generate 命令")
        return

    generator = MockGenerator(args.project)
    mocks = generator.generate_mocks(openapi_doc)
    output_file = generator.save_mocks(mocks)
    print(f"\n📦 共生成 {len(mocks)} 个 Mock endpoint")


def main():
    parser = argparse.ArgumentParser(description="API Tools - OpenAPI 生成与验证")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate
    p_gen = subparsers.add_parser("generate", help="生成 OpenAPI 文档")
    p_gen.add_argument("project", help="项目名称")
    p_gen.add_argument("--routes-dir", "-r", help="路由代码目录")

    # verify
    p_ver = subparsers.add_parser("verify", help="验证 API 文档")
    p_ver.add_argument("project", help="项目名称")

    # mock
    p_mock = subparsers.add_parser("mock", help="生成 Mock 数据")
    p_mock.add_argument("project", help="项目名称")

    args = parser.parse_args()

    commands = {
        "generate": cmd_generate,
        "verify": cmd_verify,
        "mock": cmd_mock,
    }

    if args.command is None:
        parser.print_help()
    else:
        commands[args.command](args)


if __name__ == "__main__":
    import argparse
    main()
