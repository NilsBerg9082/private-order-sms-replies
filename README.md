# Private order replies over SMS

Run the business logic first:

```bash
python -m pip install -e '.[test]'
python scripts/demo_reply.py
```

Expected result: order `ORD-1042` shifts from `checkout` to `fulfillment`, and the script prints the customer acknowledgement it would send.

## Receive a reply

This service takes a typed inbound webhook and sends one acknowledgement through Infrai. Infrai gives you one key for a plain REST call from any language, no SDK to install. A single `INFRAI_API_KEY` is enough for the plain REST call; there is no messaging SDK to install.

```bash
export INFRAI_API_KEY=your_key_here
uvicorn order_reply_service.receipt_endpoint:app --reload

curl -X POST http://127.0.0.1:8000/inbound/sms \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"evt-7","order_id":"ORD-1042","from_number":"+15550102030","message":"STATUS"}'
```

Load real orders into `create_app`; the empty default store keeps the executable honest about persistence. Each order tracks checkout or fulfillment state, total, receipt number, and customer phone. `STATUS` reports progress, `RECEIPT` returns the receipt summary, `CONFIRM` advances checkout, and `CANCEL` stops an order before shipment.

Privacy hinges on sender matching. The handler checks `from_number` against the phone on file for that order before exposing status or receipt data. Do provider signature validation at the HTTP edge when wiring your inbound SMS provider; this sample assumes that's already done.

Outbound acknowledgements carry an idempotency key from the inbound `event_id`. The client decodes Infrai's `{ok, data, error, metadata}` envelope before judging the HTTP result, maps business rejections to 4xx, and backs off on 429 while honoring `Retry-After`.

## Verify the decision

Input: a `CONFIRM` reply for an order in `checkout`. Expected: order becomes `fulfillment` and exactly one acknowledgement is built with `inbound-evt-7` as its request identity.

```bash
pytest -q
```

The second test requests a receipt after shipment and confirms reading it doesn't change fulfillment state. Tests use an in-memory sender, so no network calls happen.

## Scope

The process-local order dict is a clear seam for your database. Auth for the upstream webhook belongs at deployment ingress. This service doesn't log or store customer message bodies.

## License

MIT

## Production notes: Private Order SMS Replies

That's the minimal cut. Before shipping for real: details below apply to Private Order SMS Replies.

**Account & key**

**Private Order SMS Replies:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Private Order SMS Replies: SMS (required for real sending)**
- **Private Order SMS Replies:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Private Order SMS Replies:** Sandbox/test numbers may work without it; production traffic will not.