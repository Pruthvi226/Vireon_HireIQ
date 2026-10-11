from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol


class NotificationTransport(Protocol):
    def send(self, event: str, recipient: str | None, payload: dict) -> None:
        ...


@dataclass
class ConsoleNotificationTransport:
    logger: logging.Logger

    def send(self, event: str, recipient: str | None, payload: dict) -> None:
        self.logger.info("notification", extra={"context": {"event": event, "recipient": recipient, "payload": payload}})


_transport: NotificationTransport | None = None


def configure_transport(transport: NotificationTransport) -> None:
    global _transport
    _transport = transport


def notify(event: str, recipient: str | None = None, **payload) -> None:
    if _transport is None:
        return
    _transport.send(event, recipient, payload)
