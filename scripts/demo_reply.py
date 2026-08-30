from order_reply_service.order_workflow import Order, OrderStage, handle_reply


order = Order("ORD-1042", "+15550102030", OrderStage.CHECKOUT, 4299, "RCPT-1042")
decision = handle_reply(order, "+15550102030", "CONFIRM")
print({"order_id": decision.order_id, "stage": decision.stage, "reply": decision.reply})
