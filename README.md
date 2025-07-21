# 本地智能助手系统
一个基于 Ollama和 index-TTS-vllm 的完全本地化LLM应用，利用LLM的functional calling能力的同时，便捷化修改tools。

## ✨ 项目特色

### 🎯 完全本地化
- 离线运行：无需任何联网 API，数据隐私完全可控  
- 本地 LLM：基于 Ollama 运行大语言模型  
- 本地 TTS：使用 [index-TTS-vllm](https://github.com/Ksuriuri/index-tts-vllm) 实现高质量语音合成  

### 🎭 多角色语音系统
- 角色丰富：可自定义N个角色  
- 并发播放：多个角色可同时说话，互不干扰  
- index-TTS-vllm强大的速度和并发能力
- 高性能：首 token 优化 + 流水线处理

### 🔧 动态工具管理
- 热插拔：运行时动态添加/删除工具功能  
- 代码生成：自动管理 Python 函数和 JSON 配置  
- 扩展性强：简单易用的工具开发框架，可根据需求自行快速开发工具。

## 🏗️ 系统架构
```
智能助手系统
├── main_ollama.py # 主程序入口
├── tool_manager.py # 工具管理框架
├── functions.py # 功能模块
├── tools.json # 工具配置文件
├── func_add.py # 工具添加器
├── tts_serve.py # TTS 性能测试，验证 TTS服务是否启动成功
└── Log/ # 日志目录
├── wavs/ # 角色音频文件
└── musics/ # 音乐文件
```
### 运行
- 修改工具函数时，参考tool_manager.py和func_add.py,建议对AI(如Claude)描述需求让AI先写，开发效率极大提升。
```bash
cd your_index_tts_vllm_directory 
VLLM_USE_V1=0 python api_server.py --model_dir /your/path/to/Index-TTS --port 11996
cd local_llm_fc
python main_ollama.py
```