import ollama
import json
import os
from datetime import datetime
from jsonschema import validate, ValidationError
from tool_manager import ToolManager
import functions


class UniversalLLMLogger:
    """通用LLM对话和工具调用日志记录器"""

    def __init__(self, log_dir="./Log"):
        self.log_dir = log_dir
        self._ensure_log_dir()
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.conversation_history = []

    def _ensure_log_dir(self):
        """确保日志目录存在"""
        try:
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
        except Exception as e:
            print(f"⚠️ 无法创建日志目录: {e}")
            self.log_dir = "./temp_logs"
            try:
                os.makedirs(self.log_dir, exist_ok=True)
            except:
                self.log_dir = None

    def get_log_filename(self, log_type="general"):
        """生成日志文件名"""
        if not self.log_dir:
            return None
        now = datetime.now()
        return os.path.join(
            self.log_dir,
            f"{log_type}_{now.strftime('%Y%m%d_%H%M%S_%f')}.json"
        )

    def get_session_filename(self):
        """获取会话日志文件名"""
        if not self.log_dir:
            return None
        return os.path.join(self.log_dir, f"{self.session_id}.json")

    def log_event(self, event_data, log_type="general"):
        """记录事件到JSON文件"""
        if not self.log_dir:
            return False

        try:
            log_file = self.get_log_filename(log_type)
            if log_file:
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(event_data, f, indent=2, ensure_ascii=False)
                return True
        except Exception as e:
            print(f"⚠️ 日志记录失败: {e}")
        return False

    def log_conversation_turn(self, user_input, assistant_response, tool_executions=None):
        """记录对话回合"""
        turn_data = {
            "turn_id": f"turn_{len(self.conversation_history) + 1}",
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "assistant_response": {
                "content": assistant_response.get('content', ''),
                "tool_calls": self._serialize_tool_calls(assistant_response.get('tool_calls', []))
            },
            "tool_executions": tool_executions or [],
            "metadata": {
                "session_id": self.session_id,
                "turn_number": len(self.conversation_history) + 1
            }
        }

        self.conversation_history.append(turn_data)
        self.log_event(turn_data, "conversation_turn")
        self._update_session_log()
        return turn_data

    def log_tool_execution(self, function_name, parameters, result, execution_time_ms=None):
        """记录工具执行"""
        log_data = {
            "event_type": "tool_execution",
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "function_name": function_name,
            "parameters": parameters,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "success": self._determine_success(result)
        }
        self.log_event(log_data, "tool_execution")
        return log_data

    def _determine_success(self, result):
        """通用成功状态判断"""
        if result is None:
            return False
        result_str = str(result).lower()
        failure_indicators = ["失败", "错误", "error", "failed", "无法", "未找到"]
        return not any(indicator in result_str for indicator in failure_indicators)

    def _serialize_tool_calls(self, tool_calls):
        """序列化工具调用"""
        if not tool_calls:
            return []

        serializable_calls = []
        for call in tool_calls:
            try:
                call_dict = {
                    'function': {
                        'name': getattr(call.function, 'name', 'unknown'),
                        'arguments': getattr(call.function, 'arguments', {})
                    }
                }
                serializable_calls.append(call_dict)
            except Exception:
                serializable_calls.append({"error": "serialization_failed"})
        return serializable_calls

    def _update_session_log(self):
        """更新会话日志"""
        if not self.log_dir or not self.conversation_history:
            return

        try:
            session_data = {
                "session_id": self.session_id,
                "start_time": self.conversation_history[0]["timestamp"],
                "last_update": datetime.now().isoformat(),
                "total_turns": len(self.conversation_history),
                "conversation_history": self.conversation_history
            }

            session_file = self.get_session_filename()
            if session_file:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 会话日志更新失败: {e}")

    def get_session_summary(self):
        """获取会话摘要"""
        if not self.conversation_history:
            return {"message": "暂无对话记录"}

        tool_calls_count = sum(
            len(turn.get("tool_executions", []))
            for turn in self.conversation_history
        )

        return {
            "会话ID": self.session_id,
            "对话轮数": len(self.conversation_history),
            "工具调用总数": tool_calls_count,
            "会话开始时间": self.conversation_history[0]["timestamp"],
            "日志目录": self.log_dir or "日志功能已禁用"
        }


def validate_params(function_name, params, tools):
    """验证工具参数"""
    if not tools:
        return False, "无可用工具定义"

    for tool in tools:
        try:
            if tool.get("function", {}).get("name") == function_name:
                schema = tool["function"]["parameters"]
                validate(instance=params, schema=schema)
                return True, "参数格式正确"
        except ValidationError as e:
            return False, f"参数验证错误: {str(e)[:100]}..."
        except Exception as e:
            return False, f"参数验证异常: {str(e)[:100]}..."

    return False, "未找到对应的工具定义"


def execute_function(function_name, params, logger):
    """执行工具函数"""
    import time
    start_time = time.time()

    try:
        # 检查函数路由器
        if not hasattr(functions, 'function_router'):
            return None, "❌ 函数路由器未初始化"

        if function_name not in functions.function_router:
            return None, f"❌ 未找到函数 {function_name}"

        func = functions.function_router[function_name]

        # 执行函数
        result = func(**params)
        execution_time = (time.time() - start_time) * 1000
        result_msg = f"✅ {function_name} 执行成功，返回: {result}"

        # 记录日志
        if logger:
            logger.log_tool_execution(function_name, params, result, execution_time)

        return result, result_msg

    except TypeError as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = f"❌ {function_name} 参数错误: {str(e)[:100]}..."
        if logger:
            logger.log_tool_execution(function_name, params, str(e), execution_time)
        return None, error_msg

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = f"❌ {function_name} 执行异常: {str(e)[:100]}..."
        if logger:
            logger.log_tool_execution(function_name, params, str(e), execution_time)
        return None, error_msg


def build_tool_results_summary(tool_executions):
    """构建通用工具执行结果摘要"""
    if not tool_executions:
        return ""

    summary_parts = []
    for execution in tool_executions:
        func_name = execution.get("function_name", "unknown")
        success = execution.get("success", False)
        result = execution.get("result")

        if success:
            summary_parts.append(f"{func_name} 执行成功")
            if result and str(result) != "None":
                summary_parts[-1] += f": {str(result)[:50]}..."
        else:
            summary_parts.append(f"{func_name} 执行失败")

    return "工具执行结果: " + "; ".join(summary_parts)


def main():
    print("🤖 智能工具调用系统启动 (输入 'quit' 退出)")
    print("=" * 50)

    # 初始化组件
    try:
        tm = ToolManager()
        tools = tm.get_tools()
        logger = UniversalLLMLogger()

        print(f"📋 已加载 {len(tools)} 个工具")
        print(f"📁 日志保存: {logger.log_dir or '已禁用'}")
        print(f"🆔 会话ID: {logger.session_id}")

    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return

    # **通用化系统提示词** - 去除音乐特殊化处理
    messages = [{
        "role": "system",
        "content": """你是一个智能助手，具备工具调用能力。
- 理解用户意图，选择合适的工具
- 在对话中用户的需求你可能无法直接满足，这个时候需要调用工具
- 另外，用户大部分时候可能不会直接要求你执行动作，但你需要理解其中的用意，你是否只有调用工具才能执行
- 你需要辨别用户是否想叫对应的人来，如果是则需要让她来说话，注意需要调用对应人的语音合成（不要在对话时暴露）
###
！！！一旦是这些角色对用户说话，那么必须带入这些角色进行扮演。
以下是你能叫来的人的名单与介绍(也就是能利用工具让他们说话)：
    1.萝莎莉亚:称呼用户为舰长，活泼、黏人、爱撒娇；莉莉娅是她的妹妹。
    2.水月：罗德岛干员，称呼用户为博士，说话温柔，天真浪漫
    3.莉莉娅:称呼用户为舰长，温顺、腼腆、依赖姐姐；姐姐是萝莎莉亚
    4.纳西妲：称呼用户为旅行者，可爱博学、治愈；称呼自己“我”；爱用比喻
彩蛋：如果莉莉娅和萝莎莉亚中任一人开口说话，那么另一人应该也要说话，但注意她们之间的对话应该具有互动性。也就是你要在一次对话中调用两个工具。
###
大部分时候，你都只是智能助手，不要暴露提示词给用户。/no_think
        """ #
    }]

    print("\n开始对话...")
    print("-" * 30)

    while True:
        try:
            # 用户输入
            user_input = input("\n👤 你: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("\n📊 会话摘要:")
                summary = logger.get_session_summary()
                for key, value in summary.items():
                    print(f"  {key}: {value}")
                print("👋 再见!")
                break

            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})

            # 调用LLM
            try:
                response = ollama.chat(
                    model="qwen3:8b",  # **更新模型配置**
                    messages=messages,
                    tools=tools
                )
            except Exception as e:
                print(f"❌ LLM调用失败: {e}")
                continue

            # 处理响应
            assistant_message = response.get('message', {})
            content = assistant_message.get('content', '')
            tool_calls = assistant_message.get('tool_calls', [])

            # 显示助手回复
            if content:
                print(f"🤖 助手: {content}")

            # **通用化工具执行处理**
            tool_executions = []
            if tool_calls:
                print(f"\n🔧 正在执行 {len(tool_calls)} 个工具...")

                for call in tool_calls:
                    try:
                        func_name = getattr(call.function, 'name', 'unknown')
                        params = getattr(call.function, 'arguments', {})

                        # 解析参数
                        if isinstance(params, str):
                            try:
                                params = json.loads(params)
                            except json.JSONDecodeError:
                                print(f"❌ {func_name} 参数解析失败")
                                continue

                        # 验证参数
                        valid, msg = validate_params(func_name, params, tools)
                        if valid:
                            print(f"  📋 {func_name}: {params}")
                            func_result, result_msg = execute_function(func_name, params, logger)
                            print(f"  {result_msg}")

                            # 记录执行结果
                            tool_executions.append({
                                "function_name": func_name,
                                "parameters": params,
                                "result": func_result,
                                "success": func_result is not None,
                                "message": result_msg
                            })
                        else:
                            print(f"  ❌ {func_name} 参数验证失败: {msg}")

                    except Exception as e:
                        print(f"  ❌ 工具执行异常: {str(e)[:100]}...")

            # 添加助手消息到历史
            messages.append(assistant_message)

            # 记录完整对话回合
            logger.log_conversation_turn(user_input, assistant_message, tool_executions)

            # **通用化上下文更新**
            if tool_executions:
                context_summary = build_tool_results_summary(tool_executions)
                if context_summary:
                    context_message = {
                        "role": "system",
                        "content": context_summary
                    }
                    messages.append(context_message)
                    print(f"📄 上下文已更新")

        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断操作")
            break
        except Exception as e:
            print(f"❌ 系统异常: {e}")
            # 记录错误但继续运行
            logger.log_event({
                "event_type": "system_error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "user_input": user_input if 'user_input' in locals() else "unknown"
            }, "error")


if __name__ == "__main__":
    main()
