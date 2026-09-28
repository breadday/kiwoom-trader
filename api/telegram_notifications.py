"""Telegram result sink for read-only market scan alerts."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
import os
import re
from typing import Any

from api.scanner import ScanItem


_BOT_TOKEN_PATTERN = re.compile(r"^[0-9]+:[A-Za-z0-9_-]+$")
_MAX_MESSAGE_LENGTH = 4000
_MAX_REASON_LENGTH = 240


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram does not accept an alert.

    Messages intentionally omit the request URL and response body because both
    can contain credentials or provider-controlled content.
    """


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str = field(repr=False)
    chat_id: str
    timeout_seconds: float = 10.0

    def __post_init__(self):
        if not isinstance(self.bot_token, str) or not _BOT_TOKEN_PATTERN.fullmatch(
            self.bot_token
        ):
            raise ValueError("bot_token has an invalid format")
        if (
            not isinstance(self.chat_id, str)
            or not self.chat_id
            or len(self.chat_id) > 128
            or any(character.isspace() for character in self.chat_id)
        ):
            raise ValueError("chat_id has an invalid format")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")

    @classmethod
    def from_env(cls, environ=None):
        source = os.environ if environ is None else environ
        if not isinstance(source, Mapping):
            raise TypeError("environ must be a mapping")
        token = source.get("TELEGRAM_BOT_TOKEN")
        chat_id = source.get("TELEGRAM_CHAT_ID")
        if token is None or chat_id is None:
            raise ValueError("Telegram credentials are not configured")
        return cls(bot_token=token, chat_id=chat_id)


def _default_transport(url, **kwargs):
    import requests

    return requests.post(url, **kwargs)


class TelegramScanResultSink:
    """Send MATCH and ERROR scan results as a bounded plain-text alert."""

    def __init__(
        self,
        config: TelegramConfig,
        *,
        transport: Callable[..., Any] | None = None,
    ):
        if not isinstance(config, TelegramConfig):
            raise TypeError("config must be a TelegramConfig")
        if transport is not None and not callable(transport):
            raise TypeError("transport must be callable")
        self.config = config
        self._transport = _default_transport if transport is None else transport

    def __call__(self, batch):
        items = self._validate_batch(batch)
        actionable = [item for item in items if item.status in {"MATCH", "ERROR"}]
        if not actionable:
            return False

        message = self._format_message(actionable)
        endpoint = (
            f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        )
        try:
            response = self._transport(
                endpoint,
                json={"chat_id": self.config.chat_id, "text": message},
                timeout=float(self.config.timeout_seconds),
            )
        except Exception:
            raise TelegramDeliveryError("Telegram request failed") from None

        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int) or not 200 <= status_code < 300:
            raise TelegramDeliveryError("Telegram rejected the alert")
        try:
            payload = response.json()
        except Exception:
            raise TelegramDeliveryError("Telegram returned an invalid response") from None
        if not isinstance(payload, Mapping) or payload.get("ok") is not True:
            raise TelegramDeliveryError("Telegram rejected the alert")
        return True

    @staticmethod
    def _validate_batch(batch):
        if isinstance(batch, (str, bytes)) or not isinstance(batch, Sequence):
            raise TypeError("batch must be a sequence of ScanItem values")
        items = list(batch)
        for item in items:
            if not isinstance(item, ScanItem):
                raise TypeError("batch must contain only ScanItem values")
            if item.status not in {"MATCH", "NO_MATCH", "ERROR"}:
                raise ValueError("ScanItem has an unsupported status")
            if not isinstance(item.reason, str) or not item.reason.strip():
                raise ValueError("ScanItem reason must be non-empty")
            if not isinstance(item.matched, bool):
                raise ValueError("ScanItem matched must be boolean")
            if (item.status == "MATCH") is not item.matched:
                raise ValueError("ScanItem status and matched flag are inconsistent")
        return items

    @classmethod
    def _format_message(cls, actionable):
        match_count = sum(item.status == "MATCH" for item in actionable)
        error_count = sum(item.status == "ERROR" for item in actionable)
        lines = [
            "Kiwoom scan alert",
            f"MATCH {match_count} / ERROR {error_count}",
        ]
        omitted = 0
        for index, item in enumerate(actionable):
            line = cls._format_item(item)
            remaining = len(actionable) - index - 1
            omission_line = f"... {remaining} more omitted" if remaining else ""
            reserved = len(omission_line) + (1 if omission_line else 0)
            candidate = "\n".join([*lines, line])
            if len(candidate) + reserved > _MAX_MESSAGE_LENGTH:
                omitted = len(actionable) - index
                break
            lines.append(line)
        if omitted:
            omission_line = f"... {omitted} more omitted"
            while (
                len("\n".join([*lines, omission_line])) > _MAX_MESSAGE_LENGTH
                and len(lines) > 2
            ):
                lines.pop()
                omitted += 1
                omission_line = f"... {omitted} more omitted"
            lines.append(omission_line)
        return "\n".join(lines)

    @staticmethod
    def _format_item(item):
        reason = " ".join(item.reason.split())[:_MAX_REASON_LENGTH]
        fields = [f"[{item.status}] {item.code}"]
        if item.latest_date is not None:
            fields.append(str(item.latest_date))
        if item.latest_close is not None:
            fields.append(f"close {item.latest_close}")
        fields.append(reason)
        return " | ".join(fields)
