# SPDX-License-Identifier: MPL-2.0
"""Entry point of the daemon (``clockodo-plasma-daemon``)."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import signal
import sys

from dbus_fast import BusType, NameFlag, RequestNameReply
from dbus_fast.aio import MessageBus

from . import DBUS_NAME, DBUS_PATH, __version__
from .config import ConfigStore
from .dbus_interface import ClockodoInterface
from .logutil import setup_logging
from .notifications import DesktopNotifier, watch_screen_lock
from .poller import Poller
from .secret_store import SecretStore
from .service import Service

log = logging.getLogger("clockodo_plasma")


async def run() -> int:
    bus = await MessageBus(bus_type=BusType.SESSION).connect()
    service = Service(ConfigStore(), SecretStore(), notifier=DesktopNotifier(bus))
    interface = ClockodoInterface(service)
    bus.export(DBUS_PATH, interface)

    # Initialise before taking the name: D-Bus activation queues the caller's
    # first request until then, so it never sees a half-initialised state.
    await service.initialize()
    reply = await bus.request_name(DBUS_NAME, NameFlag.DO_NOT_QUEUE)
    if reply not in (RequestNameReply.PRIMARY_OWNER, RequestNameReply.ALREADY_OWNER):
        log.error("%s is already owned by another process, exiting", DBUS_NAME)
        bus.disconnect()
        return 1

    poller = Poller(service)
    poller.start()
    try:
        await watch_screen_lock(bus, service.on_screen_locked)
    except Exception as exc:
        log.warning("screen lock monitoring unavailable: %s", type(exc).__name__)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    disconnected = loop.create_task(bus.wait_for_disconnect())
    stopped = loop.create_task(stop.wait())
    log.info("clockodo-plasma %s running", __version__)
    await asyncio.wait({disconnected, stopped}, return_when=asyncio.FIRST_COMPLETED)

    log.info("shutting down")
    await poller.stop()
    await service.shutdown()
    for task in (disconnected, stopped):
        task.cancel()
    with contextlib.suppress(Exception):
        bus.disconnect()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="clockodo-plasma-daemon",
        description="Background daemon of the Clockodo Plasma widget.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    args = parser.parse_args(argv)
    setup_logging(args.debug)
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
