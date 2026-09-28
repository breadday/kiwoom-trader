"""Safe order-domain primitives for Kiwoom Trader.

This module deliberately does not import credentials, broker clients, or
network libraries.  It validates an order request and produces a deterministic
dry-run result.  Live order submission is fail-closed until a separately
approved live-trading adapter is designed and reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import count
import re
from typing import Any, Mapping


_STOCK_CODE = re.compile(r"^\d{6}$")


class OrderValidationError(ValueError):
    """Raised when an order request violates the local order contract."""


class LiveOrderDisabledError(RuntimeError):
    """Raised whenever code attempts to submit a live order."""


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    ACCEPTED = "accepted"


def _coerce_side(value: OrderSide | str) -> OrderSide:
    if isinstance(value, OrderSide):
        return value
    try:
        return OrderSide(str(value).upper())
    except ValueError as exc:
        raise OrderValidationError("side must be BUY or SELL") from exc


def _coerce_order_type(value: OrderType | str) -> OrderType:
    if isinstance(value, OrderType):
        return value
    try:
        return OrderType(str(value).upper())
    except ValueError as exc:
        raise OrderValidationError("order_type must be MARKET or LIMIT") from exc


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Validated order intent without any broker-side side effects."""

    code: str
    side: OrderSide | str
    quantity: int
    order_type: OrderType | str = OrderType.MARKET
    limit_price: int | None = None
    client_order_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not _STOCK_CODE.fullmatch(self.code):
            raise OrderValidationError("code must be a six-digit stock code")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity <= 0:
            raise OrderValidationError("quantity must be a positive integer")

        side = _coerce_side(self.side)
        order_type = _coerce_order_type(self.order_type)
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "order_type", order_type)

        if order_type is OrderType.LIMIT:
            if isinstance(self.limit_price, bool) or not isinstance(self.limit_price, int) or self.limit_price <= 0:
                raise OrderValidationError("limit_price must be a positive integer for LIMIT orders")
        elif self.limit_price is not None:
            raise OrderValidationError("limit_price is only valid for LIMIT orders")

        if self.client_order_id is not None:
            if not isinstance(self.client_order_id, str) or not self.client_order_id.strip():
                raise OrderValidationError("client_order_id must be a non-empty string when provided")


@dataclass(frozen=True, slots=True)
class OrderResult:
    """Result returned by the safe local executor."""

    order_id: str
    request: OrderRequest
    status: OrderStatus
    simulated: bool
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "code": self.request.code,
            "side": self.request.side.value,
            "quantity": self.request.quantity,
            "order_type": self.request.order_type.value,
            "limit_price": self.request.limit_price,
            "client_order_id": self.request.client_order_id,
            "status": self.status.value,
            "simulated": self.simulated,
            "message": self.message,
        }


class OrderExecutor:
    """Create safe dry-run results and reject live submission by default.

    ``transport`` is accepted only for dependency-injection tests and future
    adapter work.  It is never called by the current implementation.
    """

    def __init__(self, *, dry_run: bool = True, transport: object | None = None) -> None:
        if not isinstance(dry_run, bool):
            raise TypeError("dry_run must be a boolean")
        self.dry_run = dry_run
        self._transport = transport
        self._sequence = count(1)

    def submit(self, request: OrderRequest) -> OrderResult:
        if not isinstance(request, OrderRequest):
            raise TypeError("request must be an OrderRequest")
        if not self.dry_run:
            raise LiveOrderDisabledError(
                "live order submission is disabled; obtain explicit approval and add a reviewed adapter first"
            )

        order_id = request.client_order_id or f"dry-run-{next(self._sequence):06d}"
        return OrderResult(
            order_id=order_id,
            request=request,
            status=OrderStatus.ACCEPTED,
            simulated=True,
            message="dry-run only; no broker or account API was called",
        )

    def buy_market(self, code: str, quantity: int, *, client_order_id: str | None = None) -> OrderResult:
        return self.submit(OrderRequest(code, OrderSide.BUY, quantity, client_order_id=client_order_id))

    def sell_market(self, code: str, quantity: int, *, client_order_id: str | None = None) -> OrderResult:
        return self.submit(OrderRequest(code, OrderSide.SELL, quantity, client_order_id=client_order_id))


def validate_order(payload: Mapping[str, Any]) -> OrderRequest:
    """Build an :class:`OrderRequest` from an untrusted mapping."""

    if not isinstance(payload, Mapping):
        raise OrderValidationError("order payload must be a mapping")
    required = {"code", "side", "quantity"}
    missing = sorted(required.difference(payload))
    if missing:
        raise OrderValidationError(f"missing required fields: {', '.join(missing)}")
    return OrderRequest(
        code=payload["code"],
        side=payload["side"],
        quantity=payload["quantity"],
        order_type=payload.get("order_type", OrderType.MARKET),
        limit_price=payload.get("limit_price"),
        client_order_id=payload.get("client_order_id"),
    )


__all__ = [
    "LiveOrderDisabledError",
    "OrderExecutor",
    "OrderRequest",
    "OrderResult",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "OrderValidationError",
    "validate_order",
]
