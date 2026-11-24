"""Jetson entry point: build the controller and wire its inputs. Start it with bringup/zone_controller.sh."""
import argparse
import asyncio
import os
import sys

from core.zones import DEFAULT_SUBNET
from zone_controller import net
from zone_controller.controller import ZoneController, log


async def run(subnet: str) -> None:
    controller = ZoneController()
    servers = await net.listen(controller, subnet)
    loop = asyncio.get_running_loop()

    def on_stdin() -> None:  # Enter stands in for the ZONE SELECT button until GPIO is wired.
        # Raw read: buffered sys.stdin.readline() would hide Enters that arrive together.
        data = os.read(sys.stdin.fileno(), 4096)
        if not data:
            loop.remove_reader(sys.stdin)
        for _ in range(data.count(b"\n")):
            controller.select_next()

    loop.add_reader(sys.stdin, on_stdin)
    log(f"READY active_zone={controller.state.active_zone.value}")
    await asyncio.gather(*(server.serve_forever() for server in servers))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zone_controller")
    parser.add_argument("--subnet", default=DEFAULT_SUBNET,
                        help="first three octets of the zone addresses (127.0.0 for a local run)")
    args = parser.parse_args(argv)
    try:
        asyncio.run(run(args.subnet))
    except OSError as cause:
        print(f"cannot listen: {cause}. Is this the Jetson with its zone addresses? "
              "Start with bringup/zone_controller.sh", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
