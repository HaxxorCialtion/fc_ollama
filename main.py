import ollama
import json
import time
from jsonschema import validate, ValidationError
from tool_manager import ToolManager
import functions
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class TokenUsage:
    """Token 使用统计数据类"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other):
        """支持 TokenUsage 对象相加"""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


class OllamaTokenTracker:
    """Ollama Token 追踪器"""

    def __init__(self):
        self.call_history: List[Dict[str, Any]] = []
        self.total_usage = TokenUsage()

    def chat_with_tracking(self, model: str, messages: List[Dict], tools: List[Dict] = None):
        """带 token 统计的聊天方法"""
        start_time = time.time()

        # 调用 Ollama API
        response = ollama.chat(
            model=model,
            messages=messages,
            tools=tools,
            options={
                "num_predict": -1,  # 允许完整响应
                "temperature": 0.7
            }
        )

        elapsed_time = (time.time() - start_time) * 1000

        # 提取 token 使用信息
        usage_info = response.get('usage', {})
        current_usage = TokenUsage(
            prompt_tokens=usage_info.get('prompt_tokens', 0),
            completion_tokens=usage_info.get('completion_tokens', 0),
            total_tokens=usage_info.get('total_tokens', 0)
        )

        # 如果 Ollama 没有返回 usage 信息，尝试估算
        if current_usage.total_tokens == 0:
            current_usage = self._estimate_tokens(messages, response, tools)

        # 记录调用历史
        call_record = {
            'timestamp': time.time(),
            'elapsed_time_ms': elapsed_time,
            'usage': current_usage,
            'tool_calls_count': len(response['message'].get('tool_calls', [])),
            'has_tools': tools is not None and len(tools) > 0
        }

        self.call_history.append(call_record)
        self.total_usage += current_usage

        return response, current_usage

    def _tool_calls_to_dict(self, tool_calls):
        """将 ToolCall 对象转换为可序列化的字典"""
        if not tool_calls:
            return []

        serializable_calls = []
        for call in tool_calls:
            try:
                # 尝试直接访问属性
                call_dict = {
                    'function': {
                        'name': call.function.name,
                        'arguments': call.function.arguments
                    }
                }
                # 如果有其他属性，也可以添加
                if hasattr(call, 'id'):
                    call_dict['id'] = call.id
                if hasattr(call, 'type'):
                    call_dict['type'] = call.type

                serializable_calls.append(call_dict)
            except Exception as e:
                # 如果无法访问属性，使用字符串表示
                serializable_calls.append(str(call))

        return serializable_calls

    def _estimate_tokens(self, messages: List[Dict], response: Dict, tools: List[Dict] = None) -> TokenUsage:
        """估算 token 使用量（当 Ollama 不提供精确统计时）"""
        # 简单的 token 估算：大约 4 个字符 = 1 个 token（英文），中文可能更少

        # 计算输入 tokens
        prompt_text = ""
        for msg in messages:
            prompt_text += msg.get('content', '')

        # 如果有工具定义，也要计算
        if tools:
            try:
                prompt_text += json.dumps(tools, ensure_ascii=False)
            except TypeError:
                # 如果工具定义无法序列化，使用字符串长度估算
                prompt_text += str(tools)

        # 计算输出 tokens
        completion_text = response['message'].get('content', '')

        # 处理 tool_calls - 修复序列化问题
        if response['message'].get('tool_calls'):
            try:
                # 将 ToolCall 对象转换为可序列化的字典
                serializable_calls = self._tool_calls_to_dict(response['message']['tool_calls'])
                completion_text += json.dumps(serializable_calls, ensure_ascii=False)
            except Exception as e:
                # 如果仍然无法序列化，使用字符串长度估算
                completion_text += str(response['message']['tool_calls'])

        # 估算（这是粗略估算，实际可能有差异）
        prompt_tokens = max(len(prompt_text) // 3, 1)  # 中文字符密度更高
        completion_tokens = max(len(completion_text) // 3, 1)

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        if not self.call_history:
            return {"message": "暂无调用记录"}

        # 计算各种统计指标
        total_calls = len(self.call_history)
        total_time = sum(record['elapsed_time_ms'] for record in self.call_history)
        tool_calls = sum(record['tool_calls_count'] for record in self.call_history)
        calls_with_tools = sum(1 for record in self.call_history if record['has_tools'])

        # Token 成本估算（假设价格，你可以根据实际情况调整）
        estimated_cost = self._calculate_cost(self.total_usage)

        return {
            "总调用次数": total_calls,
            "总耗时": f"{total_time:.2f} ms",
            "平均耗时": f"{total_time / total_calls:.2f} ms",
            "工具调用总数": tool_calls,
            "使用工具的调用次数": calls_with_tools,
            "Token统计": {
                "输入Token": self.total_usage.prompt_tokens,
                "输出Token": self.total_usage.completion_tokens,
                "总Token": self.total_usage.total_tokens
            },
            "估算成本": estimated_cost,
            "平均每次调用Token": f"{self.total_usage.total_tokens / total_calls:.1f}" if total_calls > 0 else 0
        }

    def _calculate_cost(self, usage: TokenUsage) -> str:
        """估算成本（本地部署通常免费，但可以估算云端等价成本）"""
        # 假设价格（仅供参考，实际使用时请根据具体服务商定价）
        input_price_per_1k = 0.001  # 每1K input tokens 的价格
        output_price_per_1k = 0.002  # 每1K output tokens 的价格

        input_cost = (usage.prompt_tokens / 1000) * input_price_per_1k
        output_cost = (usage.completion_tokens / 1000) * output_price_per_1k
        total_cost = input_cost + output_cost

        return f"${total_cost:.6f} (输入: ${input_cost:.6f}, 输出: ${output_cost:.6f})"

    def print_detailed_history(self):
        """打印详细的调用历史"""
        print("\n📊 详细调用历史:")
        print("=" * 80)

        for i, record in enumerate(self.call_history, 1):
            usage = record['usage']
            print(f"调用 #{i}:")
            print(f"  ⏱️  耗时: {record['elapsed_time_ms']:.2f} ms")
            print(f"  🔧 工具调用数: {record['tool_calls_count']}")
            print(
                f"  📝 Token使用: 输入={usage.prompt_tokens}, 输出={usage.completion_tokens}, 总计={usage.total_tokens}")
            print(f"  💰 单次成本: {self._calculate_cost(usage)}")
            print("-" * 40)


def validate_params(function_name, params, tools):
    """验证传入参数是否符合函数定义的格式和要求"""
    for tool in tools:
        if tool["function"]["name"] == function_name:
            schema = tool["function"]["parameters"]
            try:
                validate(instance=params, schema=schema)
                return True, "参数格式正确"
            except ValidationError as e:
                return False, f"参数格式错误: {e.message}"
    return False, "未找到对应的函数定义"


def main():
    # 初始化工具管理器和 Token 追踪器
    tm = ToolManager()
    tm.print_summary()

    tracker = OllamaTokenTracker()

    # 获取工具定义
    tools = tm.get_tools()

    messages = [
        {
            "role": "system",
            "content": "你是一个可以调用工具来执行任务的智能助手。根据用户的请求，自动调用合适的函数来完成任务。如果需要，可以一次调用多个函数。/no_think"
        },
        {
            "role": "user",
            "content": "我想听周杰伦的《晴天》，顺便把卧室的灯打开，空调调到26度，然后帮我给张三打个电话，最后来首说唱风格的《本草纲目》吧。/no_think"
        }
    ]

    print("🚀 开始进行多次 API 调用测试...")

    for i in range(5):
        print(f"\n🔄 第 {i + 1} 次调用:")

        try:
            # 使用带 token 统计的方法
            response, usage = tracker.chat_with_tracking(
                model="qwen2.5-coder:1.5b",
                messages=messages,
                tools=tools
            )

            # 获取工具调用信息
            tool_calls = response['message'].get('tool_calls', [])
            num_tools = len(tool_calls)

            print(f"⏱️ 耗时: {tracker.call_history[-1]['elapsed_time_ms']:.2f} ms")
            print(f"🔧 使用工具数量: {num_tools}")
            print(f"📊 Token使用: 输入={usage.prompt_tokens}, 输出={usage.completion_tokens}, 总计={usage.total_tokens}")

            # 验证每个函数调用的参数
            for call in tool_calls:
                func_name = call.function.name
                params = call.function.arguments

                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError:
                        print(f"❌ 函数 {func_name} 参数解析失败")
                        continue

                valid, msg = validate_params(func_name, params, tools)
                status_icon = "✅" if valid else "❌"
                print(f"{status_icon} 函数 {func_name} 参数验证: {msg}")

                if valid:
                    print(f"   📋 参数详情: {params}")

        except Exception as e:
            print(f"❌ 调用失败: {e}")
            continue

        print("-" * 50)

    # 打印统计汇总
    print("\n" + "=" * 60)
    print("📈 最终统计报告")
    print("=" * 60)

    stats = tracker.get_statistics()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")

    # 打印详细历史（可选）
    print("\n是否查看详细调用历史？(y/n): ", end="")
    try:
        if input().lower() == 'y':
            tracker.print_detailed_history()
    except:
        pass


if __name__ == "__main__":
    main()
