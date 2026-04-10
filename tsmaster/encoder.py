"""
CAN signal encoding from DBC file.
"""

from typing import Any, Dict, List, Union

import cantools


class SignalNotFoundError(Exception):
    """Raised when signal is not found in DBC file"""
    pass


class ValueOutOfRangeError(Exception):
    """Raised when physical value exceeds signal's min/max range"""
    pass


class AmbiguousSignalError(Exception):
    """Raised when signal name exists in multiple messages"""
    pass


class SignalsNotInSameMessageError(Exception):
    """Raised when signals belong to different messages"""
    pass


class DecodeError(Exception):
    """Raised when message decoding fails"""
    pass


def encode_can_signal(
    dbc_path: str,
    signal_values: Dict[str, float]
) -> Dict[str, Any]:
    """Encode signals with physical values to CAN message bytes.

    Args:
        dbc_path: Path to the DBC file
        signal_values: Dictionary of signal_name -> physical_value
                       Example: {'Dr_SeatSta': 1, 'ShiftGearPosn': 2}

    Returns:
        Dictionary with frame_id, message_name, and data (list of bytes)

    Raises:
        SignalNotFoundError: Signal not found in DBC file
        AmbiguousSignalError: Signal exists in multiple messages
        SignalsNotInSameMessageError: Signals belong to different messages
        ValueOutOfRangeError: Physical value exceeds signal's min/max range
        NotImplementedError: Multiplexed signals not supported
    """
    db = cantools.database.load_file(dbc_path)

    # Find the message that contains ALL provided signals
    signal_to_message_map: Dict[str, tuple] = {}  # signal_name -> (message, signal_obj)
    target_signal_names = set(signal_values.keys())

    for message in db.messages:
        for signal in message.signals:
            if signal.name in target_signal_names:
                signal_to_message_map[signal.name] = (message, signal)

    # Check all signals found
    for signal_name in signal_values.keys():
        if signal_name not in signal_to_message_map:
            raise SignalNotFoundError(f"Signal '{signal_name}' not found in DBC file")

    # Get all messages that contain the signals
    messages_involved = set(msg for msg, _ in signal_to_message_map.values())

    # Check all signals are in the same message
    if len(messages_involved) > 1:
        msg_info: List[str] = []
        for msg in messages_involved:
            sigs_in_msg = [s.name for s in msg.signals if s.name in target_signal_names]
            msg_info.append(f"{msg.name} (ID: 0x{msg.frame_id:X}) contains: {sigs_in_msg}")
        raise SignalsNotInSameMessageError(
            "Signals belong to different messages:\n" + "\n".join(msg_info)
        )

    # Get the single message containing all signals
    message = messages_involved.pop()

    # Validate all signals are not multiplexed and values are in range
    for signal_name, physical_value in signal_values.items():
        _, signal = signal_to_message_map[signal_name]

        if signal.multiplexer_signal is not None:
            raise NotImplementedError(
                f"Multiplexed signal '{signal_name}' not supported"
            )

        if signal.minimum is not None and physical_value < signal.minimum:
            raise ValueOutOfRangeError(
                f"Value {physical_value} below minimum {signal.minimum} for signal '{signal_name}'"
            )

        if signal.maximum is not None and physical_value > signal.maximum:
            raise ValueOutOfRangeError(
                f"Value {physical_value} above maximum {signal.maximum} for signal '{signal_name}'"
            )

    # Build encode_data with provided values and defaults for others
    encode_data: Dict[str, float] = {}
    for sig in message.signals:
        if sig.name in signal_values:
            encode_data[sig.name] = signal_values[sig.name]
        else:
            if sig.initial is not None:
                encode_data[sig.name] = sig.initial
            elif sig.minimum is not None:
                encode_data[sig.name] = sig.minimum
            else:
                encode_data[sig.name] = 0

    data = message.encode(encode_data)
    return {
        'frame_id': message.frame_id,
        'message_name': message.name,
        'data': list(data)
    }


def decode_can_signal(
    dbc_path: str,
    frame_id: Union[int, str],
    data: List[int]
) -> Dict[str, Any]:
    """Decode CAN message bytes to signal values using DBC file.

    Args:
        dbc_path: Path to the DBC file
        frame_id: Message frame ID (int or hex string like '0x100')
        data: Message data bytes (list of integers)

    Returns:
        Dictionary with frame_id, message_name, and signals (dict of signal->value)

    Raises:
        DecodeError: Message ID not found in DBC or decoding failed
    """
    import cantools

    # Import _parse_id from api module
    from tsmaster.api import _parse_id

    db = cantools.database.load_file(dbc_path)

    # Convert frame_id to int if string
    fid = _parse_id(frame_id) if isinstance(frame_id, str) else frame_id

    try:
        message = db.get_message_by_frame_id(fid)
    except KeyError:
        raise DecodeError(f"Message ID 0x{fid:X} not found in DBC file")

    try:
        decoded = message.decode(bytes(data))
    except Exception as e:
        raise DecodeError(f"Failed to decode message 0x{fid:X}: {e}")

    return {
        'frame_id': message.frame_id,
        'message_name': message.name,
        'signals': dict(decoded)
    }
