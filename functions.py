from typing import Any

def play_music(song_name: str, artist: str) -> int:
    """播放指定的歌曲"""
    return 1

def turn_on_lamp(location: str) -> int:
    """打开指定位置的台灯"""
    return 2

def set_air_conditioner_temperature(room: str, temperature: float) -> int:
    """设置某个房间的空调温度"""
    return 3

def make_phone_call(phone_number: str, contact_name: str) -> int:
    """拨打电话给指定联系人"""
    return 4

def sing_song(song_name: str, style: str) -> int:
    """以指定风格演唱一首歌曲"""
    return 5


# 路由映射
function_router = {
    "play_music": play_music,
    "turn_on_lamp": turn_on_lamp,
    "set_air_conditioner_temperature": set_air_conditioner_temperature,
    "make_phone_call": make_phone_call,
    "sing_song": sing_song,
}
