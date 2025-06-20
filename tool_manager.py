import json
import inspect
import ast
import re
from typing import Dict, List, Any, Optional, Callable


class ToolManager:
    def __init__(self, tools_file: str = "tools.json", functions_file: str = "functions.py", functions_module=None):
        """
        初始化工具管理器

        Args:
            tools_file: tools配置文件路径
            functions_file: functions.py文件路径
            functions_module: 函数模块，如果为None则尝试导入functions模块
        """
        self.tools_file = tools_file
        self.functions_file = functions_file
        self.tools = self._load_tools()

        if functions_module is None:
            try:
                import functions
                self.functions_module = functions
            except ImportError:
                print("警告: 无法导入functions模块")
                self.functions_module = None
        else:
            self.functions_module = functions_module

    def _load_tools(self) -> List[Dict]:
        """从JSON文件加载工具定义"""
        try:
            with open(self.tools_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"工具配置文件 {self.tools_file} 不存在，创建空配置")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return []

    def _save_tools(self) -> bool:
        """保存工具定义到JSON文件"""
        try:
            with open(self.tools_file, 'w', encoding='utf-8') as f:
                json.dump(self.tools, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存JSON失败: {e}")
            return False

    def _read_functions_file(self) -> str:
        """读取functions.py文件内容"""
        try:
            with open(self.functions_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"函数文件 {self.functions_file} 不存在")
            return ""
        except Exception as e:
            print(f"读取函数文件失败: {e}")
            return ""

    def _write_functions_file(self, content: str) -> bool:
        """写入functions.py文件内容"""
        try:
            with open(self.functions_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"写入函数文件失败: {e}")
            return False

    def _add_function_to_file(self, function_name: str, function_code: str) -> bool:
        """将函数添加到functions.py文件中"""
        content = self._read_functions_file()
        if not content:
            # 如果文件不存在或为空，创建基础结构
            content = """from typing import Any

# 路由映射
function_router = {
}
"""

        # 检查函数是否已存在
        if f"def {function_name}(" in content:
            print(f"错误: 函数 {function_name} 已存在于文件中")
            return False

        # 在文件末尾添加函数（在function_router之前）
        router_pattern = r'(# 路由映射\s*\nfunction_router\s*=\s*{[^}]*})'

        if re.search(router_pattern, content, re.MULTILINE | re.DOTALL):
            # 在路由映射之前插入函数
            new_content = re.sub(
                router_pattern,
                f'{function_code}\n\n\\1',
                content,
                flags=re.MULTILINE | re.DOTALL
            )

            # 更新路由映射
            new_content = self._update_function_router(new_content, function_name, add=True)
        else:
            # 如果没有找到路由映射，直接添加到末尾
            new_content = content + f"\n\n{function_code}\n"
            new_content += f"\n# 路由映射\nfunction_router = {{\n    \"{function_name}\": {function_name},\n}}\n"

        return self._write_functions_file(new_content)

    def _remove_function_from_file(self, function_name: str) -> bool:
        """从functions.py文件中删除函数"""
        content = self._read_functions_file()
        if not content:
            return False

        # 检查函数是否存在
        if f"def {function_name}(" not in content:
            print(f"警告: 函数 {function_name} 不存在于文件中")
            return False

        # 删除函数定义（包括文档字符串）
        function_pattern = rf'def {function_name}\([^)]*\)[^:]*:.*?(?=\ndef|\nclass|\n# 路由映射|\Z)'
        new_content = re.sub(function_pattern, '', content, flags=re.DOTALL)

        # 更新路由映射
        new_content = self._update_function_router(new_content, function_name, add=False)

        return self._write_functions_file(new_content)

    def _update_function_router(self, content: str, function_name: str, add: bool = True) -> str:
        """更新function_router字典"""
        router_pattern = r'(function_router\s*=\s*{)([^}]*)(})'

        def update_router(match):
            start, router_content, end = match.groups()

            # 解析现有的路由映射
            lines = [line.strip() for line in router_content.split('\n') if line.strip()]
            entries = []

            for line in lines:
                if ':' in line and not line.startswith('#'):
                    # 提取键名
                    key_match = re.search(r'"([^"]+)":', line)
                    if key_match:
                        key = key_match.group(1)
                        if key != function_name:  # 保留其他函数
                            entries.append(f'    "{key}": {key},')

            # 如果是添加操作，添加新函数
            if add:
                entries.append(f'    "{function_name}": {function_name},')

            # 重新构建路由映射
            if entries:
                new_router_content = '\n' + '\n'.join(entries) + '\n'
            else:
                new_router_content = ''

            return start + new_router_content + end

        return re.sub(router_pattern, update_router, content, flags=re.DOTALL)

    def get_tools(self) -> List[Dict]:
        """获取所有工具定义"""
        return self.tools.copy()

    def get_function_names(self) -> List[str]:
        """获取所有函数名"""
        return [tool['function']['name'] for tool in self.tools]

    def get_tool_by_name(self, function_name: str) -> Optional[Dict]:
        """根据函数名获取工具定义"""
        for tool in self.tools:
            if tool['function']['name'] == function_name:
                return tool.copy()
        return None

    def add_tool(self, tool: Dict, function_code: str = None, save: bool = True) -> bool:
        """
        添加新工具定义和对应的函数

        Args:
            tool: 工具定义字典
            function_code: 函数代码字符串
            save: 是否立即保存到文件
        """
        function_name = tool.get('function', {}).get('name')
        if not function_name:
            print("错误: 工具定义缺少函数名")
            return False

        # 检查JSON中是否已存在
        if self.get_tool_by_name(function_name):
            print(f"错误: 工具 {function_name} 已存在于配置中")
            return False

        # 检查functions.py中是否已存在
        content = self._read_functions_file()
        if f"def {function_name}(" in content:
            print(f"错误: 函数 {function_name} 已存在于代码中")
            return False

        # 如果提供了函数代码，添加到functions.py
        if function_code:
            if not self._add_function_to_file(function_name, function_code):
                return False

        # 添加到工具配置
        self.tools.append(tool)

        if save:
            success = self._save_tools()
            if not success and function_code:
                # 如果保存JSON失败，回滚函数文件的更改
                self._remove_function_from_file(function_name)
            return success

        return True

    def delete_tool(self, function_name: str, save: bool = True) -> bool:
        """
        删除指定函数的工具定义和对应的函数

        Args:
            function_name: 要删除的函数名
            save: 是否立即保存到文件
        """
        # 检查工具是否存在
        if not self.get_tool_by_name(function_name):
            print(f"错误: 工具 {function_name} 不存在于配置中")
            return False

        # 从JSON配置中删除
        original_length = len(self.tools)
        self.tools = [tool for tool in self.tools if tool['function']['name'] != function_name]

        if len(self.tools) == original_length:
            print(f"警告: 未找到工具 {function_name}")
            return False

        # 从functions.py中删除函数
        function_removed = self._remove_function_from_file(function_name)

        if save:
            json_saved = self._save_tools()
            if not json_saved:
                print("JSON保存失败，但函数已从代码中删除")
                return False

            if not function_removed:
                print("函数删除失败，但工具配置已更新")

            return json_saved

        return True

    def modify_tool(self, function_name: str, new_tool: Dict, new_function_code: str = None, save: bool = True) -> bool:
        """
        修改指定函数的工具定义和函数代码

        Args:
            function_name: 要修改的函数名
            new_tool: 新的工具定义
            new_function_code: 新的函数代码
            save: 是否立即保存到文件
        """
        # 检查工具是否存在
        if not self.get_tool_by_name(function_name):
            print(f"错误: 工具 {function_name} 不存在")
            return False

        # 更新工具定义
        for i, tool in enumerate(self.tools):
            if tool['function']['name'] == function_name:
                self.tools[i] = new_tool
                break

        # 如果提供了新的函数代码，更新函数
        if new_function_code:
            # 先删除旧函数，再添加新函数
            self._remove_function_from_file(function_name)
            new_function_name = new_tool.get('function', {}).get('name', function_name)
            self._add_function_to_file(new_function_name, new_function_code)

        if save:
            return self._save_tools()
        return True

    def get_function_info(self, function_name: str) -> Optional[Dict]:
        """获取函数的详细信息，包括源码和签名"""
        if not self.functions_module:
            print("错误: 函数模块未加载")
            return None

        if not hasattr(self.functions_module, function_name):
            print(f"错误: 函数 {function_name} 在模块中不存在")
            return None

        func = getattr(self.functions_module, function_name)

        try:
            signature = inspect.signature(func)
            source = inspect.getsource(func)
            docstring = inspect.getdoc(func)

            return {
                "name": function_name,
                "signature": str(signature),
                "docstring": docstring,
                "source": source,
                "tool_definition": self.get_tool_by_name(function_name)
            }
        except Exception as e:
            print(f"获取函数信息失败: {e}")
            return None

    def list_all_functions(self) -> Dict[str, Any]:
        """列出所有函数的基本信息"""
        if not self.functions_module:
            return {}

        result = {}
        for func_name in self.get_function_names():
            info = self.get_function_info(func_name)
            if info:
                result[func_name] = {
                    "signature": info["signature"],
                    "docstring": info["docstring"],
                    "has_tool_definition": info["tool_definition"] is not None
                }
        return result

    def validate_consistency(self) -> Dict[str, List[str]]:
        """验证工具定义与函数模块的一致性"""
        issues = {
            "missing_functions": [],  # 工具定义存在但函数不存在
            "missing_tools": [],  # 函数存在但工具定义不存在
            "signature_mismatches": []  # 签名不匹配
        }

        if not self.functions_module:
            return issues

        # 检查工具定义对应的函数是否存在
        for tool in self.tools:
            func_name = tool['function']['name']
            if not hasattr(self.functions_module, func_name):
                issues["missing_functions"].append(func_name)

        # 检查函数是否都有对应的工具定义
        if hasattr(self.functions_module, 'function_router'):
            for func_name in self.functions_module.function_router.keys():
                if not self.get_tool_by_name(func_name):
                    issues["missing_tools"].append(func_name)

        return issues

    def print_summary(self):
        """打印工具管理器的摘要信息"""
        print("=" * 50)
        print("🔧 工具管理器摘要")
        print("=" * 50)
        print(f"📁 配置文件: {self.tools_file}")
        print(f"📄 函数文件: {self.functions_file}")
        print(f"🛠️ 工具数量: {len(self.tools)}")
        print(f"📦 函数模块: {'已加载' if self.functions_module else '未加载'}")

        if self.tools:
            print("\n📋 已注册的工具:")
            for i, tool in enumerate(self.tools, 1):
                func_name = tool['function']['name']
                description = tool['function']['description']
                print(f"  {i}. {func_name} - {description}")

        # 验证一致性
        issues = self.validate_consistency()
        if any(issues.values()):
            print("\n⚠️ 发现的问题:")
            for issue_type, items in issues.items():
                if items:
                    print(f"  {issue_type}: {', '.join(items)}")
        else:
            print("\n✅ 工具定义与函数模块一致")


if __name__ == "__main__":
    # 示例用法
    tm = ToolManager()

    # 打印摘要
    tm.print_summary()

    # 获取所有函数信息
    print("\n" + "=" * 50)
    print("📚 函数详细信息")
    print("=" * 50)

    functions_info = tm.list_all_functions()
    for func_name, info in functions_info.items():
        print(f"\n🔹 {func_name}")
        print(f"   签名: {info['signature']}")
        print(f"   描述: {info['docstring']}")
        print(f"   工具定义: {'✅' if info['has_tool_definition'] else '❌'}")

    # 添加新工具示例
    print("\n" + "=" * 50)
    print("🆕 添加新工具示例")
    print("=" * 50)

    new_tool = {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "unit": {"type": "string", "description": "温度单位", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["city"]
            }
        }
    }

    new_function_code = '''def get_weather(city: str, unit: str = "celsius") -> int:
    """获取指定城市的天气信息"""
    print(f"获取{city}的天气，温度单位：{unit}")
    return 6'''

    # if tm.add_tool(new_tool, new_function_code):
    #     print("✅ 新工具和函数添加成功")
    # else:
    #     print("❌ 新工具和函数添加失败")

    # 删除刚添加的工具
    if tm.delete_tool("get_weather"):
        print("✅ 工具和函数删除成功")
    else:
        print("❌ 工具和函数删除失败")
