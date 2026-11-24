"""TCP adapter: one listener per zone address. Bytes <-> core.protocol <-> ZoneController."""
from __future__ import annotations  # builtin generics in hints on Python 3.8

import asyncio
import functools

from core.protocol import MAX_LINE, PORT, ProtocolError, ack, error, parse_command
from core.zones import Signal, Zone, zone_address
from zone_controller.controller import ZoneController, log


async def listen(controller: ZoneController, subnet: str) -> list[asyncio.AbstractServer]:
    return [
        await asyncio.start_server(functools.partial(_serve_zone, controller, zone),
                                   zone_address(subnet, zone), PORT, limit=MAX_LINE)
        for zone in Zone
    ]


async def _serve_zone(controller: ZoneController, zone: Zone,
                      reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """One client connection on `zone`'s address. The address, not the payload, names the zone."""
    local_ip = writer.get_extra_info("sockname")[0]
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                command = parse_command(line)
            except ProtocolError as cause:
                writer.write(error(str(cause)))
            else:
                status, state = controller.request(zone, command.action, command.value)
                value = command.value.value if isinstance(command.value, Signal) else command.value
                log(f"COMMAND ip={local_ip} zone={zone.value} request_id={command.request_id} "
                    f"action={command.action.value} value={value} status={status.value} "
                    f"active={state.active_zone.value} signal={state.signal.value} "
                    f"brake={state.brake}")
                writer.write(ack(command.request_id, status, state))
            await writer.drain()
    except (ConnectionError, ValueError):  # ValueError: line longer than MAX_LINE
        pass
    finally:
        writer.close()
