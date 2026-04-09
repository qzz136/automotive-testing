import socket
import struct
import time
from typing import Tuple, Optional

# 智能小车控制器配置
SMART_CAR_IP = "192.168.1.1"
SMART_CAR_PORT = 2001
DEFAULT_TIMEOUT = 20  # 秒


def _create_socket(timeout: int = DEFAULT_TIMEOUT) -> socket.socket:
    """创建TCP套接字并设置超时"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    return sock


def send_switch_value(
    switch_value: int,
    keytime_ms: int,
    server_ip: str = SMART_CAR_IP,
    port: int = SMART_CAR_PORT,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[bool, str]:
    """
    向智能小车发送开关控制指令

    实现与C++版本send_switch_value相同的功能：
    - 连接到智能小车TCP服务器
    - 发送5字节消息: {0xFF, 0x05, switch_value, keytime/20, 0xFF}
    - 接收响应并验证第一个字节是否为0xFF

    Args:
        switch_value: 开关值 (0-255)
        keytime_ms: 按键持续时间，单位毫秒 (会被除以20)
        server_ip: 智能小车IP地址
        port: 智能小车端口号
        timeout: 连接和接收超时时间，单位秒

    Returns:
        Tuple[bool, str]: (是否成功, 状态信息)

    Raises:
        Exception: 连接失败、发送失败、接收超时等错误
    """
    sock: Optional[socket.socket] = None
    try:
        # 创建套接字
        sock = _create_socket(timeout)

        # 连接到服务器
        try:
            sock.connect((server_ip, port))
        except socket.timeout:
            return False, f"连接超时: {server_ip}:{port}"
        except Exception as e:
            return False, f"连接失败: {e}"

        # 构造发送的字节数组: {0xFF, 0x05, switch_value, keytime/20, 0xFF}
        message = bytes([
            0xFF,
            0x05,
            switch_value & 0xFF,
            (keytime_ms // 20) & 0xFF,
            0xFF,
        ])

        # 发送数据
        try:
            sock.sendall(message)
        except Exception as e:
            return False, f"发送失败: {e}"

        # 接收响应 (期望5字节)
        try:
            received_data = sock.recv(5)
        except socket.timeout:
            return False, "接收响应超时"
        except Exception as e:
            return False, f"接收失败: {e}"

        if len(received_data) == 0:
            return False, "连接已关闭，未收到响应"

        # 验证响应: 第一个字节应为0xFF
        if received_data[0] == 0xFF:
            return True, f"成功: 发送值={switch_value}, 持续时间={keytime_ms}ms"
        else:
            return (
                False,
                f"响应格式错误: 期望0xFF，收到0x{received_data[0]:02X}"
            )

    except Exception as e:
        return False, f"未知错误: {e}"
    finally:
        if sock:
            sock.close()


def send_switch_value_alltime(
    switch_value: int,
    enable_disable: int,
    server_ip: str = SMART_CAR_IP,
    port: int = SMART_CAR_PORT,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[bool, str]:
    """
    向智能小车发送持续开关控制指令

    发送消息格式: {0xFF, 0x07, switch_value, enable_disable, 0xFF}

    Args:
        switch_value: 开关值 (0-255)
        enable_disable: 启用/禁用标志 (0-255)
        server_ip: 智能小车IP地址
        port: 智能小车端口号
        timeout: 超时时间

    Returns:
        Tuple[bool, str]: (是否成功, 状态信息)
    """
    sock: Optional[socket.socket] = None
    try:
        sock = _create_socket(timeout)

        try:
            sock.connect((server_ip, port))
        except socket.timeout:
            return False, f"连接超时: {server_ip}:{port}"
        except Exception as e:
            return False, f"连接失败: {e}"

        # 构造消息: {0xFF, 0x07, switch_value, enable_disable, 0xFF}
        message = bytes([
            0xFF,
            0x07,
            switch_value & 0xFF,
            enable_disable & 0xFF,
            0xFF,
        ])

        try:
            sock.sendall(message)
        except Exception as e:
            return False, f"发送失败: {e}"

        try:
            received_data = sock.recv(5)
        except socket.timeout:
            return False, "接收响应超时"
        except Exception as e:
            return False, f"接收失败: {e}"

        if len(received_data) == 0:
            return False, "连接已关闭"

        if received_data[0] == 0xFF:
            return True, f"成功: switch={switch_value}, enable={enable_disable}"
        else:
            return (
                False,
                f"响应格式错误: 期望0xFF，收到0x{received_data[0]:02X}"
            )

    except Exception as e:
        return False, f"未知错误: {e}"
    finally:
        if sock:
            sock.close()


def send_zone_value(
    zone_value: int,
    server_ip: str = SMART_CAR_IP,
    port: int = SMART_CAR_PORT,
    timeout: int = 120,  # zone命令使用更长的超时
) -> Tuple[bool, str]:
    """
    向智能小车发送区域控制指令

    发送消息格式: {0xFF, 0x06, zone_value, 0x00, 0xFF}

    Args:
        zone_value: 区域值 (0-255)
        server_ip: 智能小车IP地址
        port: 智能小车端口号
        timeout: 超时时间(秒)，默认为120秒

    Returns:
        Tuple[bool, str]: (是否成功, 状态信息)
    """
    sock: Optional[socket.socket] = None
    try:
        sock = _create_socket(timeout)

        try:
            sock.connect((server_ip, port))
        except socket.timeout:
            return False, f"连接超时: {server_ip}:{port}"
        except Exception as e:
            return False, f"连接失败: {e}"

        # 构造消息: {0xFF, 0x06, zone_value, 0x00, 0xFF}
        message = bytes([0xFF, 0x06, zone_value & 0xFF, 0x00, 0xFF])

        try:
            sock.sendall(message)
        except Exception as e:
            return False, f"发送失败: {e}"

        try:
            received_data = sock.recv(5)
        except socket.timeout:
            return False, "接收响应超时"
        except Exception as e:
            return False, f"接收失败: {e}"

        if len(received_data) == 0:
            return False, "连接已关闭"

        if received_data[0] == 0xFF:
            return True, f"成功: zone={zone_value}"
        else:
            return (
                False,
                f"响应格式错误: 期望0xFF，收到0x{received_data[0]:02X}"
            )

    except Exception as e:
        return False, f"未知错误: {e}"
    finally:
        if sock:
            sock.close()
