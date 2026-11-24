"""One management state-push port. Explicit local bind; no silent discovery."""
from __future__ import annotations
import asyncio
from core.management import MANAGEMENT_PORT, state_line
from zone_controller.controller import ZoneController


class StatePublisher:
    def __init__(self, controller: ZoneController, interval: float = 1.0) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive")
        self.controller = controller
        self.interval = interval
        self.sequence = 0
        self.clients = set()
        self._server = None
        self._heartbeat = None

    def publish(self) -> None:
        self.sequence += 1
        data = state_line(self.controller.state, self.sequence)
        for writer in tuple(self.clients):
            if writer.is_closing():
                self.clients.discard(writer)
            else:
                try:
                    writer.write(data)
                except (ConnectionError, OSError):
                    self.clients.discard(writer)

    async def _on_client(self, reader, writer) -> None:
        self.clients.add(writer)
        writer.write(state_line(self.controller.state, self.sequence))
        try:
            await writer.drain()
            # Subscribers are read-only; consuming bytes lets us detect EOF.
            while await reader.read(1024):
                pass
        except (ConnectionError, OSError):
            pass
        finally:
            self.clients.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except (OSError, ConnectionError):
                pass

    async def _pulse(self):
        while True:
            await asyncio.sleep(self.interval)
            self.publish()

    async def start(self, address: str) -> None:
        self._server = await asyncio.start_server(self._on_client, address, MANAGEMENT_PORT)
        self._heartbeat = asyncio.create_task(self._pulse())

    async def close(self) -> None:
        if self._heartbeat is not None:
            self._heartbeat.cancel()
            try:
                await self._heartbeat
            except asyncio.CancelledError:
                pass
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        for writer in tuple(self.clients):
            writer.close()
