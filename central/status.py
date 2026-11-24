"""Management feed for a display: connect, read STATE lines, reconnect."""
from __future__ import annotations
import asyncio
from core.management import MANAGEMENT_PORT, parse_state
from core.protocol import ProtocolError


async def follow(host: str, on_state, retry_s: float = 1.0, timeout_s: float = 3.0):
    """Feed on_state(seq, state); publish only valid snapshots and reconnect."""
    if retry_s <= 0 or timeout_s <= 0:
        raise ValueError("timeouts must be positive")
    while True:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, MANAGEMENT_PORT), timeout=timeout_s)
            try:
                while True:
                    line = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
                    if not line:
                        raise ConnectionError("management EOF")
                    sequence, state = parse_state(line)
                    on_state(sequence, state)
            finally:
                writer.close()
                await writer.wait_closed()
        except (OSError, ConnectionError, asyncio.TimeoutError, ProtocolError):
            await asyncio.sleep(retry_s)
