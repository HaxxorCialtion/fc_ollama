from tool_manager import ToolManager


def main():
    tm = ToolManager()

    print("🚀 升级多角色并发TTS工具...")

    # **支持多角色同时播放的高性能TTS函数**
    concurrent_tts_code = '''def advanced_character_tts(text: str, character: str = "纳西妲") -> str:
    """高性能流水线角色TTS（支持多角色并发播放）

    特性：
    - 智能文本分片（按标点符号）
    - 第一片段串行处理（最快首token）
    - 其余片段并行处理（利用TTS服务并发能力）
    - 流水线播放（一边合成一边播放）
    - **多角色并发播放**（使用pygame.Sound而非music）
    - 独立音频通道管理
    - 严格播放顺序保证

    Args:
        text: 要转换为语音的文本
        character: 角色名称

    Returns:
        str: 执行结果
    """
    import requests
    import os
    import tempfile
    import threading
    import time
    import queue
    import re
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import pygame
    import uuid

    # 全局管理器（支持多实例）
    class ConcurrentTTSManager:
        def __init__(self, instance_id: str):
            self.instance_id = instance_id
            self.segments = []
            self.audio_queue = queue.Queue()
            self.playing = False
            self.stop_flag = False
            self.temp_files = []
            self.sound_objects = []  # 存储Sound对象以防止垃圾回收

        def cleanup(self):
            """清理临时文件和音频资源"""
            # 停止所有音频
            for sound_obj in self.sound_objects:
                try:
                    sound_obj.stop()
                except:
                    pass

            # 清理临时文件
            for temp_file in self.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass

    # 创建唯一实例ID
    instance_id = f"{character}_{uuid.uuid4().hex[:8]}"
    manager = ConcurrentTTSManager(instance_id)

    # 检查角色音频文件
    audio_path = f"./wavs/{character}.wav"
    alt_paths = [f"./wavs/[{character}].wav", f"./wavs/{character}音色.wav"]
    for path in [audio_path] + alt_paths:
        if os.path.exists(path):
            audio_path = path
            break
    else:
        return f"❌ {character}不在场"

    def smart_text_segmentation(text: str) -> list:
        """智能文本分片"""
        # 按中英文标点符号分割
        separators = r'[。！？；：,.!?;:]'
        segments = re.split(f'({separators})', text)

        # 重新组合保留标点
        result = []
        current_segment = ""
        for part in segments:
            if part.strip():
                current_segment += part
                if re.match(separators, part) or len(current_segment) > 80:
                    if current_segment.strip():
                        result.append(current_segment.strip())
                        current_segment = ""

        if current_segment.strip():
            result.append(current_segment.strip())

        # 合并过短的片段
        final_result = []
        temp_segment = ""
        for segment in result:
            temp_segment += segment
            if len(temp_segment) >= 25 or segment == result[-1]:
                final_result.append(temp_segment)
                temp_segment = ""

        return final_result if final_result else [text]

    def synthesize_segment(segment_text: str, segment_id: int) -> dict:
        """合成单个文本片段"""
        try:
            url = "http://127.0.0.1:11996/tts_url"
            data = {
                "text": segment_text,
                "audio_paths": [audio_path]
            }

            start_time = time.time()
            response = requests.post(url, json=data, timeout=25)

            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}

            # 保存临时文件
            with tempfile.NamedTemporaryFile(suffix=f'_{instance_id}_seg_{segment_id}.wav', delete=False) as f:
                f.write(response.content)
                temp_file = f.name

            manager.temp_files.append(temp_file)

            synthesis_time = time.time() - start_time
            return {
                "success": True,
                "segment_id": segment_id,
                "file_path": temp_file,
                "synthesis_time": synthesis_time,
                "text_preview": segment_text[:20] + "..." if len(segment_text) > 20 else segment_text
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def priority_synthesis_worker():
        """优先级合成工作线程"""
        try:
            segments = manager.segments
            if not segments:
                return

            print(f"📄 {character}文本分片: {len(segments)}段")

            # 第一段：串行处理（首token优化）
            print(f"⚡ {character}优先合成首段...")
            first_result = synthesize_segment(segments[0], 0)

            if first_result["success"]:
                manager.audio_queue.put((0, first_result))
                print(f"✅ {character}首段完成: {first_result['synthesis_time']:.2f}s")
            else:
                print(f"❌ {character}首段失败: {first_result['error']}")
                return

            # 其余段：并行处理（并发数=3）
            if len(segments) > 1:
                print(f"🚄 {character}并行合成剩余{len(segments)-1}段...")

                with ThreadPoolExecutor(max_workers=3) as executor:
                    # 提交并行任务
                    future_to_id = {
                        executor.submit(synthesize_segment, segments[i], i): i
                        for i in range(1, len(segments))
                    }

                    # 收集结果
                    for future in as_completed(future_to_id):
                        if manager.stop_flag:
                            break

                        segment_id = future_to_id[future]
                        result = future.result()

                        if result["success"]:
                            manager.audio_queue.put((segment_id, result))
                            print(f"✅ {character}段{segment_id}: {result['synthesis_time']:.2f}s")
                        else:
                            print(f"❌ {character}段{segment_id}: {result['error']}")

            # 标记合成完成
            manager.audio_queue.put((999999, {"finished": True}))

        except Exception as e:
            print(f"❌ {character}合成线程异常: {e}")

    def concurrent_player():
        """并发播放工作线程（支持多角色同时播放）"""
        try:
            # 初始化pygame mixer（如果还没初始化）
            if not pygame.mixer.get_init():
                pygame.mixer.quit()  # 确保完全重置
                time.sleep(0.05)
                # 增加同时播放的音频数量
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.set_num_channels(16)  # 支持最多16个同时播放的音频
                time.sleep(0.05)

            manager.playing = True
            next_segment_id = 0
            ready_segments = {}  # 缓存乱序到达的片段

            print(f"🔊 {character}开始播放...")

            while manager.playing and not manager.stop_flag:
                try:
                    # 获取合成完成的音频（超时2秒）
                    segment_id, result = manager.audio_queue.get(timeout=2)

                    # 检查结束标记
                    if result.get("finished"):
                        break

                    if not result["success"]:
                        continue

                    # 缓存乱序到达的片段
                    ready_segments[segment_id] = result

                    # 按顺序播放
                    while next_segment_id in ready_segments:
                        segment_result = ready_segments.pop(next_segment_id)

                        try:
                            # **关键修改：使用Sound对象而不是music**
                            sound = pygame.mixer.Sound(segment_result["file_path"])
                            manager.sound_objects.append(sound)

                            # 播放音频（不会打断其他角色）
                            channel = sound.play()

                            if channel:
                                print(f"🎵 {character}播放段{next_segment_id}: {segment_result['text_preview']}")

                                # 等待此段播放完成（但不影响其他角色）
                                while channel.get_busy() and not manager.stop_flag:
                                    time.sleep(0.08)
                            else:
                                print(f"⚠️ {character}段{next_segment_id}播放失败：没有可用音频通道")

                            next_segment_id += 1

                        except Exception as e:
                            print(f"❌ {character}播放段{next_segment_id}失败: {e}")
                            next_segment_id += 1
                            continue

                except queue.Empty:
                    # 超时检查
                    if not ready_segments and next_segment_id >= len(manager.segments):
                        break
                    continue

                except Exception as e:
                    print(f"❌ {character}播放线程异常: {e}")
                    break

            manager.playing = False
            print(f"🏁 {character}播放完成")

        except Exception as e:
            print(f"❌ {character}播放器异常: {e}")
            manager.playing = False

    def delayed_cleanup():
        """延迟清理工作线程"""
        time.sleep(3)  # 等待播放完成
        while manager.playing:
            time.sleep(0.5)
        time.sleep(1)  # 额外等待
        manager.cleanup()
        print(f"🗑️ {character}临时文件已清理")

    # 主处理逻辑
    try:
        if not text.strip():
            return "文本为空"

        # **重要修改：不再停止其他角色的播放**
        # 文本分片
        manager.segments = smart_text_segmentation(text)

        print(f"📝 {character}准备朗读: {text[:40]}{'...' if len(text) > 40 else ''}")

        # 启动合成线程
        synthesis_thread = threading.Thread(target=priority_synthesis_worker, daemon=False)
        synthesis_thread.start()

        # 立即启动播放线程
        player_thread = threading.Thread(target=concurrent_player, daemon=False)
        player_thread.start()

        # 启动清理线程
        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()

        # 给系统启动时间
        time.sleep(0.08)

        return f"🚀 {character}并发播放启动: {len(manager.segments)}段文本 [实例:{instance_id[:8]}]"

    except Exception as e:
        manager.cleanup()
        return f"❌ {character}播放失败: {str(e)[:80]}..."'''

    # **全局停止函数（停止所有TTS）**
    stop_all_tts_code = '''def stop_all_advanced_tts() -> str:
    """停止所有高性能TTS播放"""
    try:
        import pygame

        if pygame.mixer.get_init():
            # 停止所有声音
            pygame.mixer.stop()
            print("🛑 已停止所有TTS播放")
            return "已停止所有流水线TTS播放"

        return "无播放中的TTS"

    except Exception as e:
        return f"停止失败: {str(e)}"'''

    # 删除旧工具
    old_tools = [
        "advanced_character_tts", "stop_advanced_tts",
        "simple_character_tts", "simple_tts_stop"
    ]

    for tool in old_tools:
        try:
            tm.delete_tool(tool, save=False)
            print(f"🗑️ 清理: {tool}")
        except:
            pass

    # 新工具配置
    tools = [
        ({
             "type": "function",
             "function": {
                 "name": "advanced_character_tts",
                 "description": "高性能多角色并发TTS。支持多个角色同时说话，不会互相打断。使用流水线处理，首段优化响应，其余段并行合成。",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "text": {
                             "type": "string",
                             "description": "要转换为语音的文本内容，支持任意长度"
                         },
                         "character": {
                             "type": "string",
                             "description": "角色名称，如纳西妲、甘雨、萝莎莉亚、水月、莉莉娅等",
                             "default": "纳西妲"
                         }
                     },
                     "required": ["text"]
                 }
             }
         }, concurrent_tts_code),

        ({
             "type": "function",
             "function": {
                 "name": "stop_all_advanced_tts",
                 "description": "停止所有正在播放的TTS音频",
                 "parameters": {
                     "type": "object",
                     "properties": {},
                     "required": []
                 }
             }
         }, stop_all_tts_code)
    ]

    # 添加工具
    success_count = 0
    for tool_config, code in tools:
        try:
            if tm.add_tool(tool_config, code):
                success_count += 1
                print(f"✅ {tool_config['function']['name']} 添加成功")
            else:
                print(f"❌ {tool_config['function']['name']} 添加失败")
        except Exception as e:
            print(f"❌ {tool_config['function']['name']} 错误: {e}")

    if success_count >= 1:
        print("🚀 多角色并发TTS系统部署成功！")
        print("\n🎯 新增特性:")
        print(" 🎭 多角色并发：支持同时播放多个角色的语音")
        print(" 🎵 独立音频通道：使用pygame.Sound而非music")
        print(" 🔄 流水线保持：保留首token优化和并发合成")
        print(" 📐 播放顺序：每个角色内部保证播放顺序")
        print(" 🛡️ 互不干扰：角色间播放互相独立")
        print(" 🆔 实例标识：每次调用创建唯一实例ID")

        print("\n📊 性能优势:")
        print(" • 多角色场景：完美支持对话、合唱等场景")
        print(" • 音频通道：最多支持16个同时播放的音频")
        print(" • 资源隔离：每个角色独立管理临时文件")
        print(" • 内存优化：播放完成后自动清理资源")

        print("\n🔧 使用场景:")
        print(" 1️⃣ 多角色对话（萝莎莉亚与莉莉娅对话）")
        print(" 2️⃣ 群组讨论（多个角色同时发言）")
        print(" 3️⃣ 背景音效（一个角色说话，另一个角色背景音）")
        print(" 4️⃣ 故事叙述（旁白+角色对话同时进行）")

        print(f"\n🎮 pygame配置: 16音频通道，22050Hz采样率")

    else:
        print(f"⚠️ 部署失败: {success_count}/{len(tools)}")

    tm.print_summary()


if __name__ == "__main__":
    main()
