"""Durable one-shot state for strategy partial exits."""

from collections.abc import Mapping
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile

from .scan_scheduling import FileRunLock, ScanAlreadyRunningError


_MAX_STATE_FILE_BYTES = 1_000_000
_MAX_ENTRIES = 1_000
_VALID_STATUSES = {"pending", "filled"}


class PartialExitStateBusyError(RuntimeError):
    """Raised when another process is updating the partial-exit state."""


class PartialExitStateStore:
    """Track reserved and filled partial exits, optionally in an atomic JSON file."""

    def __init__(self, state_file=None):
        if state_file is None:
            self.path = None
        else:
            try:
                raw_path = os.fspath(state_file)
            except TypeError:
                raise TypeError("partial-exit state path must be path-like") from None
            if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
                raise ValueError("partial-exit state path has an invalid format")
            self.path = Path(raw_path)
        self.lock_path = None if self.path is None else Path(f"{self.path}.lock")
        self._entries = self._load()

    def contains(self, account_id, code, strategy_id):
        key = self._key(account_id, code, strategy_id)
        with self._locked():
            return key in self._entries

    def reserve(self, account_id, code, strategy_id):
        key = self._key(account_id, code, strategy_id)
        with self._locked():
            if key in self._entries:
                return False
            if len(self._entries) >= _MAX_ENTRIES:
                raise RuntimeError("partial-exit state has too many entries")
            self._update(key, "pending")
            return True

    def confirm(self, account_id, code, strategy_id):
        key = self._key(account_id, code, strategy_id)
        with self._locked():
            if key not in self._entries:
                raise RuntimeError("partial exit has no reservation")
            self._update(key, "filled")

    def release(self, account_id, code, strategy_id):
        key = self._key(account_id, code, strategy_id)
        with self._locked():
            if key not in self._entries:
                return False
            previous = dict(self._entries)
            del self._entries[key]
            try:
                self._persist()
            except Exception:
                self._entries = previous
                raise
            return True

    @contextmanager
    def _locked(self):
        if self.lock_path is None:
            yield
            return
        lock = FileRunLock(self.lock_path)
        try:
            lock.acquire()
        except ScanAlreadyRunningError:
            raise PartialExitStateBusyError(
                "partial-exit state is being updated by another process"
            ) from None
        except RuntimeError:
            raise RuntimeError(
                "partial-exit state lock could not be acquired"
            ) from None
        try:
            self._entries = self._load()
            yield
        finally:
            lock.release()

    def _update(self, key, status):
        previous = dict(self._entries)
        self._entries[key] = status
        try:
            self._persist()
        except Exception:
            self._entries = previous
            raise

    def _load(self):
        if self.path is None:
            return {}
        try:
            if self.path.stat().st_size > _MAX_STATE_FILE_BYTES:
                raise ValueError("partial-exit state file is too large")
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except ValueError:
            raise ValueError("partial-exit state file is invalid") from None
        except OSError:
            raise ValueError("partial-exit state file could not be read") from None

        if (
            not isinstance(payload, Mapping)
            or payload.get("version") != 1
            or not isinstance(payload.get("entries"), list)
            or len(payload["entries"]) > _MAX_ENTRIES
        ):
            raise ValueError("partial-exit state file is invalid")
        entries = {}
        for entry in payload["entries"]:
            if not isinstance(entry, Mapping) or set(entry) != {
                "account_id",
                "code",
                "strategy",
                "status",
            }:
                raise ValueError("partial-exit state file is invalid")
            try:
                key = self._key(
                    entry["account_id"],
                    entry["code"],
                    entry["strategy"],
                )
            except ValueError:
                raise ValueError("partial-exit state file is invalid") from None
            if (
                not isinstance(entry["status"], str)
                or entry["status"] not in _VALID_STATUSES
                or key in entries
            ):
                raise ValueError("partial-exit state file is invalid")
            entries[key] = entry["status"]
        return entries

    def _persist(self):
        if self.path is None:
            return
        temporary_path = None
        entries = [
            {
                "account_id": account_id,
                "code": code,
                "strategy": strategy_id,
                "status": status,
            }
            for (account_id, code, strategy_id), status in sorted(
                self._entries.items()
            )
        ]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(
                    {"version": 1, "entries": entries},
                    temporary,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
        except (OSError, TypeError, ValueError):
            raise RuntimeError(
                "partial-exit state file could not be written"
            ) from None
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _key(account_id, code, strategy_id):
        if (
            not isinstance(account_id, str)
            or not account_id.strip()
            or len(account_id) > 128
            or "\x00" in account_id
        ):
            raise ValueError("account_id has an invalid format")
        if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
            raise ValueError("code must be a six-digit string")
        if (
            not isinstance(strategy_id, str)
            or not strategy_id.strip()
            or len(strategy_id) > 64
            or "\x00" in strategy_id
        ):
            raise ValueError("strategy_id has an invalid format")
        return account_id, code, strategy_id
