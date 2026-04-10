"""Encode CAN signal from DBC file to bytes."""
import argparse
import sys
from typing import Any, Dict, List

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


def encode_can_signal(dbc_path: str, signal_name: str, physical_value: float) -> Dict[str, Any]:
    """Encode a signal with physical value to CAN message bytes.

    Args:
        dbc_path: Path to the DBC file
        signal_name: Name of the signal (e.g., 'FDC_PTG_inner_SW_2')
        physical_value: Physical value to encode (e.g., 1 for push)

    Returns:
        Dictionary with frame_id, message_name, and data (list of bytes)

    Raises:
        SignalNotFoundError: Signal not found in DBC file
        AmbiguousSignalError: Signal exists in multiple messages
        ValueOutOfRangeError: Physical value exceeds signal's min/max range
        NotImplementedError: Multiplexed signals not supported
    """
    db = cantools.database.load_file(dbc_path)

    matching_messages = []
    target_signal = None

    for message in db.messages:
        for signal in message.signals:
            if signal.name == signal_name:
                matching_messages.append(message)
                target_signal = signal
                break

    if not matching_messages:
        raise SignalNotFoundError(f"Signal '{signal_name}' not found in DBC file")

    if len(matching_messages) > 1:
        msg_names = [m.name for m in matching_messages]
        raise AmbiguousSignalError(
            f"Signal '{signal_name}' found in multiple messages: {msg_names}"
        )

    message = matching_messages[0]

    if target_signal.multiplexer_signal is not None:
        raise NotImplementedError("Multiplexed signals not supported")

    if target_signal.minimum is not None and physical_value < target_signal.minimum:
        raise ValueOutOfRangeError(
            f"Value {physical_value} below minimum {target_signal.minimum} for signal '{signal_name}'"
        )

    if target_signal.maximum is not None and physical_value > target_signal.maximum:
        raise ValueOutOfRangeError(
            f"Value {physical_value} above maximum {target_signal.maximum} for signal '{signal_name}'"
        )

    encode_data = {}
    for sig in message.signals:
        if sig.name == signal_name:
            encode_data[sig.name] = physical_value
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Encode a CAN signal from DBC file to bytes'
    )
    parser.add_argument('--dbc', '-d', required=True, help='Path to DBC file')
    parser.add_argument('--signal', '-s', required=True, help='Signal name')
    parser.add_argument('--value', '-v', required=True, type=float, help='Physical value')
    parser.add_argument('--format', '-f', choices=['decimal', 'hex'], default='decimal',
                        help='Output format (default: decimal)')

    args = parser.parse_args()

    try:
        result = encode_can_signal(args.dbc, args.signal, args.value)

        if args.format == 'hex':
            data_output = '[' + ', '.join(f'0x{b:02X}' for b in result['data']) + ']'
        else:
            data_output = '[' + ', '.join(str(b) for b in result['data']) + ']'

        print(f"Frame ID: 0x{result['frame_id']:X}, Message: {result['message_name']}, Data: {data_output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
