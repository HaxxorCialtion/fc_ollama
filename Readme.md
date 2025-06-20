# LLM 工具调用测试与管理系统

一个用于测试和管理大语言模型（LLM）工具调用能力的完整解决方案，支持参数验证、性能监控和动态工具管理。

## 🚀 项目特性

- **模块化设计**：函数定义与工具配置完全分离
- **参数验证**：实时验证LLM传入参数的格式和合理性
- **性能监控**：统计API调用耗时和工具使用情况
- **动态管理**：支持工具的增删改查操作
- **一致性检查**：验证函数定义与工具配置的一致性
- **可视化输出**：详细的控制台输出和统计信息

## 📁 项目结构
```
fc_ollama/
├── README.md # 项目说明文档
├── main.py # 主程序入口
├── tool_manager.py # 工具管理核心模块
├── functions.py # 函数定义模块
├── tools.json # 工具配置文件
```

## 🛠️ 核心组件

### 1. 函数定义模块 (`functions.py`)
- 包含所有可调用的函数实现
- 提供函数路由映射
- 支持类型注解和文档字符串

### 2. 工具配置 (`tools.json`)
- JSON格式的工具定义
- 符合OpenAI Function Calling标准
- 包含参数schema和验证规则

### 3. 工具管理器 (`tool_manager.py`)
- 统一的工具管理接口
- 支持CRUD操作
- 提供一致性验证功能

### 4. 主程序 (`main.py`)
- API调用测试入口
- 参数验证和性能统计
- 结果可视化输出

## 🔧 安装依赖
```bash
pip install zhipuai jsonschema
```

## 📖 使用指南

### 基本使用
```python
from tool_manager import ToolManager

# 初始化工具管理器
tm = ToolManager()

# 查看所有工具
tm.print_summary()

# 获取工具定义
tools = tm.get_tools()
```

### 添加新工具

```python
new_tool = {
    "type": "function",
    "function": {
        "name": "new_function",
        "description": "新功能描述",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1"}
            },
            "required": ["param1"]
        }
    }
}

tm.add_tool(new_tool)
```


### 运行测试
```bash
python main.py
```

## 📊 功能演示

系统会输出详细的测试结果：
```
🚀 第 1 次调用 API：
⏱️ 耗时: 120.50 ms
🔧 使用工具数量: 5
✅ 函数 play_music 参数验证: 参数格式正确
📋 参数详情: {"song_name": "晴天", "artist": "周杰伦"}
✅ 函数 turn_on_lamp 参数验证: 参数格式正确
📋 参数详情: {"location": "卧室"}
```

## 🎯 应用场景

- **LLM能力评估**：测试模型的工具调用准确性
- **API性能监控**：统计调用耗时和成功率
- **工具开发调试**：验证工具定义的正确性
- **自动化测试**：批量测试不同场景下的表现

## 🔮 未来规划

- [ ] 支持更多LLM API接口
- [ ] 添加Web界面管理工具
- [ ] 集成测试报告生成
- [ ] 支持工具调用链路追踪
- [ ] 添加性能基准测试

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！
