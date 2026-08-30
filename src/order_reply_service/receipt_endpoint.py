from typing import Protocol

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_sms import InfraiError, InfraiSms
from .order_workflow import Order, OrderStage, ReplyDecision, handle_reply


class SmsSender(Protocol):
    def send(self, *, to: str, body: str, idempotency_key: str) -> dict:
        raise AssertionError("protocol method called directly")


class InboundReply(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    order_id: str = Field(min_length=1, max_length=50)
    from_number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    message: str = Field(min_length=1, max_length=160)


class ReplyResult(BaseModel):
    order_id: str
    stage: OrderStage
    changed: bool
    acknowledgement: str


def create_app(orders: dict[str, Order] | None = None, sender: SmsSender | None = None) -> FastAPI:
    app = FastAPI(title="Order reply service")
    order_store = orders if orders is not None else {}

    @app.post("/inbound/sms", response_model=ReplyResult)
    def inbound_sms(inbound: InboundReply) -> ReplyResult:
        order = order_store.get(inbound.order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="order not found")
        try:
            decision: ReplyDecision = handle_reply(order, inbound.from_number, inbound.message)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        active_sender = sender or InfraiSms()
        try:
            active_sender.send(
                to=inbound.from_number,
                body=decision.reply,
                idempotency_key=f"inbound-{inbound.event_id}",
            )
        except InfraiError as exc:
            caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=caller_status, detail=exc.detail) from exc
        except ConnectionError as exc:
            raise HTTPException(status_code=502, detail="SMS delivery unavailable") from exc

        return ReplyResult(
            order_id=decision.order_id,
            stage=decision.stage,
            changed=decision.changed,
            acknowledgement=decision.reply,
        )

    return app


app = create_app()
