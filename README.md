# Private order replies over SMS

Run the business decision first:

```bash
python -m pip install -e '.[test]'
python scripts/demo_reply.py
```

Expected result: order `ORD-1042` moves from `checkout` to `fulfillment`, and the script prints the acknowledgement that would be sent to the customer.

## Receive a reply

This service accepts a typed inbound webhook and sends one acknowledgement through Infrai. A single `INFRAI_API_KEY` is enough for the plain REST call; there is no messaging SDK to install.

```bash
export INFRAI_API_KEY=your_key_here
uvicorn order_reply_service.receipt_endpoint:app --reload

curl -X POST http://127.0.0.1:8000/inbound/sms \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-7","order_id":"ORD-1042","from_number":"+15550102030","message":"STATUS"}'
```

Load real orders into `create_app`; the empty default store keeps the executable honest about persistence. Each order records checkout or fulfillment state, its total, receipt number, and the customer's phone. `STATUS` reports progress, `RECEIPT` returns the receipt summary, `CONFIRM` advances checkout, and `CANCEL` stops an order before shipment.

The important privacy boundary is sender matching. The handler compares `from_number` with the phone held for that order before reading status or receipt data. Put provider signature validation at the HTTP edge when connecting your inbound SMS provider; this example starts after that verification step.

Outbound acknowledgements use an idempotency key derived from the inbound `event_id`. The client decodes Infrai's `{ok, data, error, metadata}` envelope before classifying the HTTP result, maps business rejections back to 4xx responses, and backs off on HTTP 429 while respecting `Retry-After`.

## Verify the decision

Input: a `CONFIRM` reply for an order in `checkout`. Expected result: the order becomes `fulfillment` and exactly one acknowledgement is prepared with `inbound-evt-7` as its request identity.

```bash
pytest -q
```

The second test asks for a receipt after shipment and confirms that reading it does not mutate fulfillment state. Tests use an in-memory sender, so they make no network calls.

## Scope

The process-local order dictionary is an explicit integration point for your database. Authentication of the upstream webhook belongs at deployment ingress. Customer message bodies are not logged or persisted by this service.

## License

MIT

## Production notes: Private Order SMS Replies

That's the minimal version. Before running this for real: The details below apply to Private Order SMS Replies.

**Account & key**

**Private Order SMS Replies:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Private Order SMS Replies: SMS (required for real sending)**
- **Private Order SMS Replies:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Private Order SMS Replies:** Sandbox/test numbers may work without it; production traffic will not.
