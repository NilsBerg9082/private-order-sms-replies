from dataclasses import dataclass
from enum import StrEnum
from hmac import compare_digest


class OrderStage(StrEnum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class Order:
    order_id: str
    customer_phone: str
    stage: OrderStage
    total_cents: int
    receipt_number: str


@dataclass(frozen=True)
class ReplyDecision:
    order_id: str
    stage: OrderStage
    reply: str
    changed: bool


def handle_reply(order: Order, from_number: str, message: str) -> ReplyDecision:
    """Apply one customer command and return the SMS acknowledgement."""
    if not compare_digest(order.customer_phone, from_number):
        raise PermissionError("sender does not match the order")

    command = message.strip().upper()
    previous = order.stage

    if command == "CONFIRM" and order.stage == OrderStage.CHECKOUT:
        order.stage = OrderStage.FULFILLMENT
        reply = f"Order {order.order_id} confirmed. We are preparing it now."
    elif command == "CANCEL" and order.stage in {
        OrderStage.CHECKOUT,
        OrderStage.FULFILLMENT,
    }:
        order.stage = OrderStage.CANCELLED
        reply = f"Order {order.order_id} is cancelled."
    elif command == "RECEIPT":
        amount = f"{order.total_cents / 100:.2f}"
        reply = f"Receipt {order.receipt_number}: order {order.order_id}, total ${amount}."
    elif command == "STATUS":
        reply = f"Order {order.order_id} status: {order.stage.value}."
    else:
        reply = "Reply STATUS, RECEIPT, CONFIRM, or CANCEL."

    return ReplyDecision(order.order_id, order.stage, reply, order.stage != previous)
