from typing import Any



def list_available_music() -> str:
    """查看音乐目录"""
    import os
    import glob

    music_dir = "./musics"
    if not os.path.exists(music_dir):
        return ""

    all_files = []
    for ext in ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'mp4', 'wma']:
        all_files.extend(glob.glob(os.path.join(music_dir, f"*.{ext}")))
        all_files.extend(glob.glob(os.path.join(music_dir, f"*.{ext.upper()}")))

    if not all_files:
        return ""

    filenames = [os.path.basename(f) for f in sorted(set(all_files))]
    print(f"找到 {len(filenames)} 首音乐:")
    for i, name in enumerate(filenames, 1):
        print(f"{i}. {name}")

    return ",".join([os.path.splitext(f)[0] for f in filenames])






def stop_current_music() -> str:
    """停止pygame音乐播放"""
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            return "已停止"
        return "无播放中音乐"
    except ImportError:
        return "pygame未安装"
    except Exception as e:
        return f"停止失败: {str(e)}"

def play_specific_music(music_name: str) -> str:
    """修复时序问题的pygame播放"""
    import os
    import glob
    import difflib
    import threading
    import time

    music_dir = "./musics"
    if not os.path.exists(music_dir):
        return "目录不存在"

    all_files = []
    for ext in ['mp3', 'wav', 'ogg']:
        all_files.extend(glob.glob(os.path.join(music_dir, f"*.{ext}")))
        all_files.extend(glob.glob(os.path.join(music_dir, f"*.{ext.upper()}")))

    if not all_files:
        return "无音乐文件"

    target_file = None
    basenames = [os.path.splitext(os.path.basename(f))[0] for f in all_files]

    for i, name in enumerate(basenames):
        if music_name.lower() in name.lower():
            target_file = all_files[i]
            break

    if not target_file:
        matches = difflib.get_close_matches(music_name, basenames, n=1, cutoff=0.3)
        if matches:
            idx = basenames.index(matches[0])
            target_file = all_files[idx]

    if not target_file:
        return "未找到匹配"

    filename = os.path.basename(target_file)

    def play_with_timing_fix():
        try:
            import pygame

            # 确保pygame完全重置
            pygame.mixer.quit()
            time.sleep(0.1)  # 给系统时间释放音频设备

            # 初始化pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=2048)
            time.sleep(0.1)  # 给初始化时间

            # 加载和播放
            pygame.mixer.music.load(target_file)
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play()

            print(f"pygame播放: {filename}")

            # **关键修复：等待播放真正开始**
            max_wait = 20  # 最多等待2秒
            wait_count = 0
            while not pygame.mixer.music.get_busy() and wait_count < max_wait:
                time.sleep(0.1)
                wait_count += 1

            if pygame.mixer.music.get_busy():
                print(f"✅ 播放已开始: {filename}")
            else:
                print(f"⚠️ 播放可能未成功启动: {filename}")

        except ImportError:
            print("pygame未安装")
        except Exception as e:
            print(f"播放失败: {e}")

    # **关键修复：使用非daemon线程，并立即开始执行**
    play_thread = threading.Thread(target=play_with_timing_fix, daemon=False)
    play_thread.start()

    # **立即给线程执行时间**
    time.sleep(0.2)

    return f"播放 {filename}"



def adjust_volume_percentage(percentage: float) -> str:
    """根据百分比调整当前音量（相对调整）

    Args:
        percentage: 音量调整百分比
                   - 100.0 = 保持当前音量不变
                   - 110.0 = 增加到当前音量的110%（增加10%）
                   - 80.0 = 减少到当前音量的80%（减少20%）
                   - 0.0 = 静音
                   - 200.0 = 增加到当前音量的200%（翻倍，但会被限制在100%以内）

    Returns:
        str: 调整结果描述
    """
    import subprocess
    import sys

    def get_current_volume():
        """获取当前系统音量（0-100）"""
        try:
            if sys.platform.startswith('win'):
                result = subprocess.run([
                    'powershell', '-Command', 
                    '[audio]::Volume'
                ], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    return int(float(result.stdout.strip()) * 100)
        except:
            pass
        return 50  # 默认音量

    def set_system_volume(volume_level):
        """设置系统音量（0-100）"""
        try:
            volume_level = max(0, min(100, volume_level))

            if sys.platform.startswith('win'):
                volume_decimal = volume_level / 100.0
                subprocess.run([
                    'powershell', '-Command', 
                    f'[Audio]::Volume = {volume_decimal}'
                ], shell=True, capture_output=True)

            return volume_level
        except Exception as e:
            print(f"设置系统音量失败: {e}")
            return None

    def set_pygame_volume(volume_level):
        """设置pygame音量（0-100）"""
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame_volume = volume_level / 100.0
                pygame.mixer.music.set_volume(pygame_volume)
                return True
        except:
            pass
        return False

    # 获取当前音量
    current_volume = get_current_volume()

    # 计算新音量（百分比调整）
    new_volume_raw = current_volume * (percentage / 100.0)

    # 应用音量上限和下限
    new_volume = max(0, min(100, int(new_volume_raw)))

    # 执行音量调整
    pygame_success = set_pygame_volume(new_volume)
    system_success = set_system_volume(new_volume)

    # 生成结果描述
    change = new_volume - current_volume
    if change > 0:
        action = f"增加 {change}%"
    elif change < 0:
        action = f"降低 {abs(change)}%"
    else:
        action = "保持不变"

    result_msg = f"音量调整: {current_volume}% → {new_volume}% ({action})"

    # 添加限制提示
    if new_volume_raw > 100:
        result_msg += f" [已限制在100%，原计算值为{new_volume_raw:.1f}%]"
    elif new_volume_raw < 0:
        result_msg += f" [已限制在0%，原计算值为{new_volume_raw:.1f}%]"

    # 添加控制反馈
    if pygame_success:
        result_msg += " (pygame✓)"
    if system_success is not None:
        result_msg += " (系统✓)"

    print(result_msg)
    return result_msg

def get_current_volume_status() -> str:
    """获取当前音量状态"""
    import subprocess
    import sys

    def get_system_volume():
        try:
            if sys.platform.startswith('win'):
                result = subprocess.run([
                    'powershell', '-Command', 
                    '[Audio]::Volume'
                ], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    return int(float(result.stdout.strip()) * 100)
        except:
            pass
        return None

    def get_pygame_volume():
        try:
            import pygame
            if pygame.mixer.get_init():
                volume = pygame.mixer.music.get_volume()
                return int(volume * 100)
        except:
            pass
        return None

    system_vol = get_system_volume()
    pygame_vol = get_pygame_volume()

    status_parts = []
    if system_vol is not None:
        status_parts.append(f"系统: {system_vol}%")
    if pygame_vol is not None:
        status_parts.append(f"pygame: {pygame_vol}%")

    if not status_parts:
        return "无法获取音量状态"

    result = "当前音量状态: " + ", ".join(status_parts)
    print(result)
    return result



def pipeline_tts_speak(text: str) -> str:
    """高性能流水线TTS语音合成

    特性：
    - 文本智能分片（按标点符号）
    - 第一片段零延迟合成（并发数=0）
    - 其他片段高并发合成（并发数=3）
    - 一边播放一边合成（流水线处理）
    - 严格保证播放顺序

    Args:
        text: 需要转换为语音的文本内容

    Returns:
        str: 执行结果描述
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

    # 全局状态管理
    class TTSPipelineManager:
        def __init__(self):
            self.segments = []
            self.audio_queue = queue.Queue()  # 音频文件队列
            self.synthesis_status = {}  # 合成状态跟踪
            self.playing = False
            self.stop_flag = False
            self.temp_files = []  # 临时文件列表

        def cleanup(self):
            """清理所有临时文件"""
            for temp_file in self.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass

    manager = TTSPipelineManager()

    def segment_text(text: str) -> list:
        """智能文本分片"""
        # 中英文标点符号分割
        separators = r'[。！？；：,.!?;:]'
        segments = re.split(f'({separators})', text)

        # 重新组合（保留标点）
        result = []
        current_segment = ""

        for i, part in enumerate(segments):
            if part.strip():
                current_segment += part
                # 如果是标点符号或者到达合理长度
                if re.match(separators, part) or len(current_segment) > 100:
                    if current_segment.strip():
                        result.append(current_segment.strip())
                        current_segment = ""

        # 处理最后一段
        if current_segment.strip():
            result.append(current_segment.strip())

        # 如果分片太短，合并相邻片段
        final_result = []
        temp_segment = ""

        for segment in result:
            temp_segment += segment
            if len(temp_segment) >= 30 or segment == result[-1]:
                final_result.append(temp_segment)
                temp_segment = ""

        return final_result if final_result else [text]

    def synthesize_audio(segment_text: str, segment_id: int, priority: int = 1) -> dict:
        """合成单个音频片段"""
        try:
            url = "http://127.0.0.1:11996/tts_url"
            data = {
                "text": segment_text,
                "audio_paths": ["./wavs/纳西妲.wav"],
            }

            start_time = time.time()
            response = requests.post(url, json=data, timeout=30)

            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(suffix=f'_seg_{segment_id}.wav', delete=False) as f:
                f.write(response.content)
                temp_file = f.name
                manager.temp_files.append(temp_file)

            synthesis_time = time.time() - start_time

            return {
                "success": True,
                "segment_id": segment_id,
                "file_path": temp_file,
                "synthesis_time": synthesis_time,
                "text": segment_text[:30] + "..." if len(segment_text) > 30 else segment_text
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def priority_synthesis_worker():
        """优先级合成工作线程"""
        try:
            segments = manager.segments
            if not segments:
                return

            print(f"📄 文本分片完成，共{len(segments)}段")

            # 第一段：零延迟合成（串行处理）
            print("🎯 开始优先合成首段...")
            first_result = synthesize_audio(segments[0], 0, priority=0)

            if first_result["success"]:
                manager.audio_queue.put((0, first_result))
                print(f"⚡ 首段合成完成: {first_result['synthesis_time']:.2f}s")
            else:
                print(f"❌ 首段合成失败: {first_result['error']}")
                return

            # 其他段：并发合成（并发数=3）
            if len(segments) > 1:
                print(f"🚄 开始并发合成剩余{len(segments)-1}段...")

                with ThreadPoolExecutor(max_workers=3) as executor:
                    # 提交其他段的合成任务
                    future_to_id = {
                        executor.submit(synthesize_audio, segments[i], i): i
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
                            print(f"✅ 段{segment_id}合成完成: {result['synthesis_time']:.2f}s")
                        else:
                            print(f"❌ 段{segment_id}合成失败: {result['error']}")

            # 标记合成完成
            manager.audio_queue.put((999999, {"success": False, "finished": True}))

        except Exception as e:
            print(f"❌ 合成工作线程异常: {e}")

    def sequential_player():
        """顺序播放工作线程"""
        try:
            # 初始化pygame（修复回车问题）
            pygame.mixer.quit()
            time.sleep(0.1)
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            time.sleep(0.1)

            manager.playing = True
            next_segment_id = 0
            ready_segments = {}  # 缓存乱序到达的片段

            while manager.playing and not manager.stop_flag:
                try:
                    # 获取合成完成的音频（超时3秒）
                    segment_id, result = manager.audio_queue.get(timeout=3)

                    # 检查是否结束标记
                    if result.get("finished"):
                        break

                    if not result["success"]:
                        continue

                    # 暂存乱序到达的片段
                    ready_segments[segment_id] = result

                    # 按顺序播放
                    while next_segment_id in ready_segments:
                        segment_result = ready_segments.pop(next_segment_id)

                        try:
                            # 播放音频
                            pygame.mixer.music.load(segment_result["file_path"])
                            pygame.mixer.music.set_volume(0.9)
                            pygame.mixer.music.play()

                            print(f"🔊 播放段{next_segment_id}: {segment_result['text']}")

                            # 等待播放开始
                            wait_count = 0
                            while not pygame.mixer.music.get_busy() and wait_count < 10:
                                time.sleep(0.05)
                                wait_count += 1

                            # 等待播放完成
                            while pygame.mixer.music.get_busy() and not manager.stop_flag:
                                time.sleep(0.1)

                            next_segment_id += 1

                        except Exception as e:
                            print(f"❌ 播放段{next_segment_id}失败: {e}")
                            next_segment_id += 1
                            continue

                except queue.Empty:
                    # 超时，检查是否还有待播放内容
                    if not ready_segments and next_segment_id >= len(manager.segments):
                        break
                    continue
                except Exception as e:
                    print(f"❌ 播放线程异常: {e}")
                    break

            manager.playing = False
            print("🏁 播放完成")

        except Exception as e:
            print(f"❌ 播放器异常: {e}")
            manager.playing = False

    def cleanup_worker():
        """延迟清理工作线程"""
        time.sleep(5)  # 等待播放完成后再清理
        while manager.playing:
            time.sleep(1)

        time.sleep(2)  # 额外等待时间
        manager.cleanup()
        print("🗑️ 临时文件已清理")

    # 主逻辑
    try:
        if not text.strip():
            return "文本内容为空"

        # 停止当前播放
        try:
            pygame.mixer.music.stop()
        except:
            pass

        # 文本分片
        manager.segments = segment_text(text)
        print(f"📝 准备播放: {text[:50]}{'...' if len(text) > 50 else ''}")
        print(f"🔪 分片策略: {len(manager.segments)}段")

        # 启动合成工作线程
        synthesis_thread = threading.Thread(target=priority_synthesis_worker, daemon=False)
        synthesis_thread.start()

        # 立即启动播放线程（无需等待）
        player_thread = threading.Thread(target=sequential_player, daemon=False)
        player_thread.start()

        # 启动清理线程
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

        # 给系统一点启动时间
        time.sleep(0.1)

        return f"🚀 流水线TTS启动: {len(manager.segments)}段文本，首段优先合成中..."

    except Exception as e:
        manager.cleanup()
        return f"❌ TTS启动失败: {str(e)[:100]}..."

def stop_pipeline_tts() -> str:
    """停止流水线TTS播放和合成"""
    try:
        import pygame

        # 停止pygame播放
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            print("🛑 TTS播放已停止")

        return "已停止流水线TTS播放"

    except Exception as e:
        return f"停止失败: {str(e)}"

def simple_character_tts(text: str, character: str = "纳西妲") -> str:
    """多角色TTS语音合成（简化版）

    Args:
        text: 需要转换为语音的文本内容
        character: 角色名称，对应./wavs/{character}.wav文件

    Returns:
        str: 执行结果描述
    """
    import requests
    import os
    import tempfile
    import threading
    import time
    import pygame

    # 验证角色音频文件
    audio_path = f"./wavs/{character}.wav"
    if not os.path.exists(audio_path):
        # 尝试带方括号的格式
        alt_path = f"./wavs/[{character}].wav"
        if os.path.exists(alt_path):
            audio_path = alt_path
        else:
            return f"角色'{character}'的音频文件不存在"

    def tts_and_play():
        temp_file = None
        try:
            # 调用TTS服务
            url = "http://127.0.0.1:11996/tts_url"
            data = {
                "text": text,
                "audio_paths": [audio_path]
            }

            response = requests.post(url, json=data, timeout=30)
            if response.status_code != 200:
                return f"TTS服务错误: {response.status_code}"

            # 保存临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(response.content)
                temp_file = f.name

            # 播放音频
            pygame.mixer.quit()
            time.sleep(0.1)
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            time.sleep(0.1)

            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.set_volume(0.9)
            pygame.mixer.music.play()

            # 等待播放完成后清理
            while pygame.mixer.music.get_busy():
                time.sleep(0.5)

            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

        except Exception as e:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
            print(f"TTS播放失败: {str(e)}")

    # 在新线程中执行
    play_thread = threading.Thread(target=tts_and_play, daemon=False)
    play_thread.start()
    time.sleep(0.2)

    return f"开始播放({character}音色): {text[:30]}..."














def advanced_character_tts(text: str, character: str = "纳西妲") -> str:
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
        return f"❌ {character}播放失败: {str(e)[:80]}..."

def stop_all_advanced_tts() -> str:
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
        return f"停止失败: {str(e)}"

# 路由映射
function_router = {
    "list_available_music": list_available_music,
    "stop_current_music": stop_current_music,
    "play_specific_music": play_specific_music,
    "adjust_volume_percentage": adjust_volume_percentage,
    "get_current_volume_status": get_current_volume_status,
    "pipeline_tts_speak": pipeline_tts_speak,
    "stop_pipeline_tts": stop_pipeline_tts,
    "simple_character_tts": simple_character_tts,
    "advanced_character_tts": advanced_character_tts,
    "stop_all_advanced_tts": stop_all_advanced_tts,
}
