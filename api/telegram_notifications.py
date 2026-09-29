"""Telegram result sink for read-only market scan alerts."""

from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from api.scanner import ScanItem
from api.scan_scheduling import FileRunLock, ScanAlreadyRunningError


_BOT_TOKEN_PATTERN = re.compile(r"^[0-9]+:[A-Za-z0-9_-]+$")
_MAX_MESSAGE_LENGTH = 4000
_MAX_REASON_LENGTH = 240
_MAX_STATE_FILE_BYTES = 1_000_000


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram does not accept an alert.

    Messages intentionally omit the request URL and response body because both
    can contain credentials or provider-controlled content.
    """


class TelegramStateBusyError(RuntimeError):
    """Raised when another process is updating durable alert state."""


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str = field(repr=False)
    chat_id: str
    timeout_seconds: float = 10.0
    alert_state_file: str | None = None

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
        if self.alert_state_file is not None and (
            not isinstance(self.alert_state_file, str)
            or not self.alert_state_file.strip()
            or "\x00" in self.alert_state_file
        ):
            raise ValueError("alert_state_file has an invalid format")

    @classmethod
    def from_env(cls, environ=None):
        source = os.environ if environ is None else environ
        if not isinstance(source, Mapping):
            raise TypeError("environ must be a mapping")
        token = source.get("TELEGRAM_BOT_TOKEN")
        chat_id = source.get("TELEGRAM_CHAT_ID")
        if token is None or chat_id is None:
            raise ValueError("Telegram credentials are not configured")
        return cls(
            bot_token=token,
            chat_id=chat_id,
            alert_state_file=source.get("KIWOOM_ALERT_STATE_FILE"),
        )


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
        self._last_states = self._load_states(config.alert_state_file)

    def __call__(self, batch):
        items = self._validate_batch(batch)
        with self._locked_state():
            return self._send_and_record(items)

    def _send_and_record(self, items):
        passive_state_changed = False
        for item in items:
            if item.status == "NO_MATCH":
                fingerprint = self._state_fingerprint(item)
                if self._last_states.get(item.code) != fingerprint:
                    self._last_states[item.code] = fingerprint
                    passive_state_changed = True
        if passive_state_changed:
            self._persist_states()
        actionable = [
            item
            for item in items
            if item.status in {"MATCH", "ERROR"}
            and self._last_states.get(item.code) != self._state_fingerprint(item)
        ]
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
        for item in actionable:
            self._last_states[item.code] = self._state_fingerprint(item)
        self._persist_states()
        return True

    @contextmanager
    def _locked_state(self):
        state_file = self.config.alert_state_file
        if state_file is None:
            yield
            return
        lock = FileRunLock(f"{state_file}.lock")
        try:
            lock.acquire()
        except ScanAlreadyRunningError:
            raise TelegramStateBusyError(
                "alert state is being updated by another process"
            ) from None
        except RuntimeError:
            raise RuntimeError("alert state lock file could not be opened") from None
        try:
            self._last_states = self._load_states(state_file)
            yield
        finally:
            lock.release()

    @staticmethod
    def _state_fingerprint(item):
        return [
            item.status,
            item.reason,
            item.latest_date,
            item.latest_close,
            item.latest_volume,
        ]

    @classmethod
    def _load_states(cls, state_file):
        if state_file is None:
            return {}
        path = Path(state_file)
        try:
            if path.stat().st_size > _MAX_STATE_FILE_BYTES:
                raise ValueError("alert state file is too large")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except ValueError:
            raise ValueError("alert state file is invalid") from None
        except OSError:
            raise ValueError("alert state file could not be read") from None

        if (
            not isinstance(payload, Mapping)
            or payload.get("version") != 1
            or not isinstance(payload.get("states"), Mapping)
        ):
            raise ValueError("alert state file is invalid")
        states = dict(payload["states"])
        if any(
            not isinstance(code, str)
            or len(code) != 6
            or not code.isdigit()
            or not cls._valid_fingerprint(fingerprint)
            for code, fingerprint in states.items()
        ):
            raise ValueError("alert state file is invalid")
        return states

    @staticmethod
    def _valid_fingerprint(value):
        return (
            isinstance(value, list)
            and len(value) == 5
            and value[0] in {"MATCH", "NO_MATCH", "ERROR"}
            and isinstance(value[1], str)
            and bool(value[1].strip())
        )

    def _persist_states(self):
        if self.config.alert_state_file is None:
            return
        path = Path(self.config.alert_state_file)
        temporary_path = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(
                    {"version": 1, "states": self._last_states},
                    temporary,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
        except (OSError, TypeError, ValueError):
            raise RuntimeError("alert state file could not be written") from None
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

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
