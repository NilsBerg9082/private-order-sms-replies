from fastapi.testclient import TestClient

from order_reply_service.order_workflow import Order, OrderStage
from order_reply_service.receipt_endpoint import create_app


class RecordingSender:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, *, to: str, body: str, idempotency_key: str) -> dict:
        self.sent.append({"to": to, "body": body, "idempotency_key": idempotency_key})
        return {"message_id": "msg_test"}


def test_confirm_moves_checkout_to_fulfillment_and_acknowledges_once() -> None:
    sender = RecordingSender()
    order = Order("ORD-1042", "+15550102030", OrderStage.CHECKOUT, 4299, "RCPT-1042")
    client = TestClient(create_app({order.order_id: order}, sender))

    response = client.post(
        "/inbound/sms",
        json={
            "event_id": "evt-7",
            "order_id": "ORD-1042",
            "from_number": "+15550102030",
            "message": " confirm ",
        },
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "fulfillment"
    assert order.stage == OrderStage.FULFILLMENT
    assert sender.sent == [
        {
            "to": "+15550102030",
            "body": "Order ORD-1042 confirmed. We are preparing it now.",
            "idempotency_key": "inbound-evt-7",
        }
    ]


def test_receipt_does_not_change_fulfillment_state() -> None:
    sender = RecordingSender()
    order = Order("ORD-8", "+15550102030", OrderStage.SHIPPED, 1250, "RCPT-8")
    client = TestClient(create_app({order.order_id: order}, sender))

    response = client.post(
        "/inbound/sms",
        json={
            "event_id": "evt-8",
            "order_id": "ORD-8",
            "from_number": "+15550102030",
            "message": "RECEIPT",
        },
    )

    assert response.status_code == 200
    assert response.json()["changed"] is False
    assert "total $12.50" in response.json()["acknowledgement"]
