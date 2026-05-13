import uuid
import uuid6
import random
import string
import time
from typing import Optional, Dict, Union, List, Any
from datetime import datetime, timezone

# UUID constants from the uuid module for variant comparison
VARIANT_NCS = uuid.RESERVED_NCS
VARIANT_RFC_4122 = uuid.RFC_4122
VARIANT_MICROSOFT = uuid.RESERVED_MICROSOFT
VARIANT_FUTURE = uuid.RESERVED_FUTURE

def _generate_random_mac_int() -> int:
    """Generates a random 48-bit integer for use as a MAC address, with multicast bit set."""
    return random.getrandbits(48) | (1 << 40)

def _format_mac_int_to_str(mac_int: Optional[int]) -> Optional[str]:
    """Formats a 48-bit integer MAC address to a hex string."""
    if mac_int is None:
        return None
    return f"{mac_int:012x}"

def _parse_mac_str_to_int(mac_str: Optional[str]) -> Optional[int]:
    """Parses a MAC address string (e.g., '00:1B:44:11:3A:B7' or '001B44113AB7') to an integer."""
    if not mac_str:
        return None
    cleaned_mac = mac_str.replace(":", "").replace("-", "")
    if len(cleaned_mac) != 12:
        raise ValueError("Invalid MAC address string format. Must be 12 hex characters.")
    try:
        return int(cleaned_mac, 16)
    except ValueError:
        raise ValueError("Invalid MAC address string format. Contains non-hex characters.")

def _generate_random_name(length: int = 16) -> str:
    """Generates a random string for use as a name in V3/V5 UUIDs."""
    return ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=length))

def generate_uuid_str(
    version: int = 4,
    name_str: Optional[str] = None,
    namespace_str: Optional[str] = None,
    node_mac_str: Optional[str] = None
) -> str:
    """Generates a single UUID string based on the specified version and parameters."""
    
    node_int = _parse_mac_str_to_int(node_mac_str) if node_mac_str else None

    if version == 1:
        return str(uuid.uuid1(node=node_int if node_int is not None else _generate_random_mac_int()))
    elif version == 3:
        current_namespace = uuid.UUID(namespace_str) if namespace_str else uuid.uuid4()
        current_name = name_str if name_str is not None else _generate_random_name()
        return str(uuid.uuid3(current_namespace, current_name))
    elif version == 4:
        return str(uuid.uuid4())
    elif version == 5:
        current_namespace = uuid.UUID(namespace_str) if namespace_str else uuid.uuid4()
        current_name = name_str if name_str is not None else _generate_random_name()
        return str(uuid.uuid5(current_namespace, current_name))
    elif version == 6:
        return str(uuid6.uuid6(node=node_int if node_int is not None else _generate_random_mac_int()))
    elif version == 7:
        return str(uuid6.uuid7())
    elif version == 8:
        return str(uuid6.uuid8())
    else:
        raise ValueError(f"Unsupported UUID version: {version}. Supported versions are 1, 3, 4, 5, 6, 7, 8.")

def generate_uuids(
    version: int = 4,
    count: int = 1,
    name: Optional[str] = None,
    namespace: Optional[str] = None,
    node: Optional[str] = None
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Generates one or more UUIDs of the specified version.
    """
    results = []
    for _ in range(count):
        generated_uuid_str = generate_uuid_str(version, name, namespace, node)
        results.append({"uuid": generated_uuid_str, "version_generated": version})

    if count == 1:
        return results[0]
    return results


def decode_uuid_string(uuid_str: str) -> Dict[str, Any]:
    """Decodes a UUID string and returns its components."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
    except ValueError:
        raise ValueError(f"Invalid UUID string: {uuid_str}")

    # Version and semantics descriptions
    version_descriptions = {
        1: "Version 1 (time-based)",
        3: "Version 3 (name-based, MD5)",
        4: "Version 4 (random data based)",
        5: "Version 5 (name-based, SHA-1)",
        6: "Version 6 (reordered time-based)",
        7: "Version 7 (Unix Epoch time-based)",
        8: "Version 8 (custom, application-specific)",
    }
    semantics_descriptions = {
        1: "Time-based with MAC address and clock sequence.",
        3: "Generated from a namespace and a name using MD5 hash.",
        4: "Generated from random or pseudo-random numbers.",
        5: "Generated from a namespace and a name using SHA-1 hash.",
        6: "Time-based (reordered for better DB indexing) with MAC address and clock sequence.",
        7: "Time-based (Unix Epoch) with random data.",
        8: "Custom data format, specific to the application that generated it.",

    }

    decoded_info: Dict[str, Any] = {
        "uuid_string": str(uuid_obj),
        "version": uuid_obj.version,
        "version_details": version_descriptions.get(uuid_obj.version, "Unknown version"),
        "integer_value": str(uuid_obj.int),
        "contents_hex": ':'.join(f'{b:02X}' for b in uuid_obj.bytes),
        "contents_semantics": semantics_descriptions.get(uuid_obj.version, "Unknown semantics."),

    }

    if uuid_obj.variant == VARIANT_NCS:
        decoded_info["variant"] = "Reserved NCS (compatibility)"
    elif uuid_obj.variant == VARIANT_RFC_4122:
        decoded_info["variant"] = "RFC 4122 (DCE 1.1)"
    elif uuid_obj.variant == VARIANT_MICROSOFT:
        decoded_info["variant"] = "Reserved Microsoft (compatibility)"
    elif uuid_obj.variant == VARIANT_FUTURE:
        decoded_info["variant"] = "Reserved for future definition"
    else:
        decoded_info["variant"] = "Unknown"

    # Time-based components (V1, V6, V7)
    if uuid_obj.version in [1, 6, 7]:
        # Timestamp is 100-nanosecond intervals since 1582-10-15 00:00:00 UTC
        # Convert to Unix timestamp (seconds since 1970-01-01 UTC)
        # UUID epoch is 0x01b21dd213814000 (100-ns intervals from 1582 to 1970)
        unix_timestamp_ns_intervals = uuid_obj.time - 0x01b21dd213814000
        # Convert 100-ns intervals to seconds
        unix_timestamp_seconds = unix_timestamp_ns_intervals / 10_000_000.0
        
        try:
            dt_object = datetime.fromtimestamp(unix_timestamp_seconds, tz=timezone.utc)
            decoded_info["time_iso"] = dt_object.isoformat(timespec='microseconds')
        except OverflowError: # Handle potential timestamp out of range for datetime
             decoded_info["time_iso"] = "Timestamp out of standard range"

        decoded_info["timestamp_value_100ns"] = uuid_obj.time

    # Node and Clock Sequence (V1, V6)
    if uuid_obj.version in [1, 6]:
        decoded_info["node_mac"] = _format_mac_int_to_str(uuid_obj.node)
        decoded_info["clock_sequence"] = uuid_obj.clock_seq

    # Fields (common to most UUIDs)
    decoded_info["fields"] = {
        "time_low": hex(uuid_obj.time_low),
        "time_mid": hex(uuid_obj.time_mid),
        "time_hi_version": hex(uuid_obj.time_hi_version),
        "clock_seq_hi_variant": hex(uuid_obj.clock_seq_hi_variant),
        "clock_seq_low": hex(uuid_obj.clock_seq_low),
        "node": hex(uuid_obj.node) if uuid_obj.node is not None else None,
    }
    
    # For V7, the timestamp is a Unix Epoch timestamp in milliseconds.
    # The uuid.UUID.time attribute for V7 is constructed differently internally
    # but the above conversion from 100-ns intervals should still work if
    # the library correctly populates `uuid_obj.time` for V7 based on its structure.
    # Python's uuid.uuid7() (3.8+) directly embeds Unix epoch time.
    # If we need more precise V7 decoding, we'd parse its specific bit layout.
    # For now, relying on uuid_obj.time and its version is a good start.

    return decoded_info