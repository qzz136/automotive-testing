"""
Example 2: CAN Signal Encoding
CAN信号编码示例

This example demonstrates how to encode CAN signals using a DBC file.
展示如何使用DBC文件将物理信号值编码为CAN报文字节。
"""

from tsmaster import encode_can_signal
from tsmaster.models import SignalInput


def encode_power_status():
    """
    Encode power status signal to CAN message.
    将电源状态信号编码为CAN报文。
    """
    # Define DBC file path
    # DBC文件路径
    dbc_path = "D31L_15.3_CAN4_DKC_20251204_Draft.dbc"
    
    # Define signals to encode
    # 要编码的信号列表
    signals = [
        SignalInput(signal="PwrSta", value=3),      # Power state: ON
        SignalInput(signal="Voltage", value=12.5),  # Battery voltage: 12.5V
    ]
    
    # Encode signals
    # 编码信号
    result = encode_can_signal(dbc_path, signals)
    
    return result


def encode_vehicle_control():
    """
    Encode vehicle control signals.
    编码车辆控制信号。
    """
    dbc_path = "vehicle.dbc"
    
    # Multiple signals in same message
    # 同一报文中的多个信号
    signals = [
        SignalInput(signal="VehicleSpeed", value=60.0),   # Speed: 60 km/h
        SignalInput(signal="GearPosition", value=3),      # Gear: D (Drive)
        SignalInput(signal="EngineRPM", value=2500),      # RPM: 2500
    ]
    
    result = encode_can_signal(dbc_path, signals)
    return result


def encode_door_lock():
    """
    Encode door lock control signal.
    编码门锁控制信号。
    """
    dbc_path = "body_control.dbc"
    
    # Single signal encoding
    # 单信号编码
    signals = [
        SignalInput(signal="DoorLockCmd", value=1),  # Lock command
    ]
    
    result = encode_can_signal(dbc_path, signals)
    return result


# Example usage
if __name__ == "__main__":
    # Example 1: Power status
    print("Example 1: Power Status Encoding")
    print("=" * 40)
    result = encode_power_status()
    print(result)
    
    # Example 2: Vehicle control
    print("\nExample 2: Vehicle Control Encoding")
    print("=" * 40)
    result = encode_vehicle_control()
    print(result)
    
    # Example 3: Door lock
    print("\nExample 3: Door Lock Encoding")
    print("=" * 40)
    result = encode_door_lock()
    print(result)
