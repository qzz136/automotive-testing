"""
机械臂控制模块 - 包含NFC刷卡和机械臂旋转功能

对应MPLibCode.cpp中的:
- NFCStrat: 机械臂NFC刷卡功能(带视频录制)
- MachineArm_Rotation: 机械臂旋转控制
"""

import urllib.request
import urllib.error
import cv2
import os
import time
from datetime import datetime
from typing import Tuple

# 机械臂服务器配置
MACHINE_ARM_IP = "192.168.2.1"
DEFAULT_TIMEOUT = 20  # 秒

# 视频录制配置
VIDEO_BASE_PATH = "D:/dkc_test_log/video"
VIDEO_FPS = 10
VIDEO_FRAMES = 40  # 录制40帧 @ 10fps = 4秒


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bool, str]:
    """
    发送HTTP GET请求

    Args:
        url: 完整的URL
        timeout: 超时时间(秒)

    Returns:
        Tuple[bool, str]: (是否成功, 状态信息)
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read().decode("utf-8")
            return True, content
    except urllib.error.URLError as e:
        return False, f"HTTP请求失败: {e}"
    except Exception as e:
        return False, f"未知错误: {e}"


def _create_folder_with_date(base_path: str) -> str:
    """
    创建以今日日期命名的文件夹

    Args:
        base_path: 基础路径

    Returns:
        str: 日期文件夹的完整路径
    """
    today = datetime.now().strftime("%Y%m%d")
    folder_path = os.path.join(base_path, today)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)

    return folder_path


def _trigger_nfc() -> Tuple[bool, str]:
    """
    触发NFC刷卡动作

    Returns:
        Tuple[bool, str]: (是否成功, 状态信息)
    """
    url = f"http://{MACHINE_ARM_IP}/command?NFCStart.txt&time=1708684897557"
    return _http_get(url)


def nfc_start(name: str = "nfc_test") -> Tuple[bool, str]:
    """
    机械臂NFC刷卡功能(带视频录制)

    对应MPLibCode.cpp中的NFCStrat函数。
    功能流程:
    1. 打开摄像头
    2. 创建以今日日期命名的文件夹
    3. 开始录制视频(40帧 @ 10fps = 4秒)
    4. 在第5帧时触发NFC刷卡
    5. 保存视频到 D:/dkc_test_log/video/YYYYMMDD/{name}_{timestamp}.avi

    Args:
        name: 测试名称标识(用于文件名)

    Returns:
        Tuple[bool, str]: (是否成功, 状态信息)
    """
    # 打开摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "摄像头无法打开"

    try:
        # 获取视频帧的宽度和高度
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 创建以今日日期命名的文件夹
        date_folder = _create_folder_with_date(VIDEO_BASE_PATH)

        # 获取当前时间用于文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 构建完整文件名: {name}_{timestamp}.avi
        filename = f"{name}_{timestamp}.avi"
        full_path = os.path.join(date_folder, filename)

        # 创建视频写入对象
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        video_writer = cv2.VideoWriter(full_path, fourcc, VIDEO_FPS, (frame_width, frame_height))

        if not video_writer.isOpened():
            return False, "视频写入对象创建失败"

        frame_count = 0
        success = True
        error_msg = ""

        # 开始录制视频
        while frame_count < VIDEO_FRAMES:
            ret, frame = cap.read()
            if not ret:
                error_msg = "帧捕获失败"
                success = False
                break

            # 在第5帧时触发NFC刷卡
            if frame_count == 5:
                nfc_success, nfc_msg = _trigger_nfc()
                if not nfc_success:
                    error_msg = f"NFC触发失败: {nfc_msg}"

            # 写入视频帧
            video_writer.write(frame)
            frame_count += 1

        # 释放资源
        video_writer.release()
        cap.release()
        cv2.destroyAllWindows()

        if success:
            return True, f"视频已保存: {full_path}"
        else:
            return False, error_msg

    except Exception as e:
        # 确保释放资源
        if 'cap' in locals():
            cap.release()
        if 'video_writer' in locals():
            video_writer.release()
        cv2.destroyAllWindows()
        return False, f"录制异常: {str(e)}"


def machine_arm_rotation(
    angle: int,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[bool, str]:
    """
    机械臂旋转控制

    控制机械臂旋转到指定角度(0-180度)。
    对应MPLibCode.cpp中的MachineArm_Rotation函数。

    Args:
        angle: 目标角度 (0-180)
        timeout: 超时时间(秒)

    Returns:
        Tuple[bool, str]: (是否成功, 状态信息)

    Raises:
        ValueError: 角度超出有效范围
    """
    if angle < 0 or angle > 180:
        return False, f"角度不在有效范围内(0-180): {angle}"

    url = f"http://{MACHINE_ARM_IP}/command?X{angle}"
    return _http_get(url, timeout)
