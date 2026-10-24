# VNPay PAY verification — Day 1

Checked **2026-11-02**. Documentation investigation only; no merchant credentials, provider calls, signed URLs or Sandbox receipts were used. This file is not payment acceptance evidence.

## Official findings

[PAY integration](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html) specifies:

| Topic | Documented contract |
|---|---|
| Merchant/API | Merchant-issued eight-character `vnp_TmnCode`; PAY `2.1.0`; Sandbox endpoint `https://sandbox.vnpayment.vn/paymentv2/vpcpay.html`. Actual merchant assignment remains unverified. |
| Amount | Integer VND multiplied by 100; `vnp_Amount` has 1–12 digits. |
| Time | Create/expire dates use GMT+7, `yyyyMMddHHmmss`; explicit `vnp_ExpireDate`. |
| Result | Verify checksum first; compare persisted reference/amount and current state. Successful result requires applicable response/status fields `00`. |
| IPN acknowledgement | HTTP 200 JSON with `RspCode` and `Message`: `00` accepted, `02` already confirmed, `01` unknown order, `04` amount mismatch, `97` checksum failure, `99` other error. These describe merchant processing, not payment success. |
| Retry | `00`/`02` stop retries; `01`/`04`/`97`/`99` or timeout trigger retries; documented maximum ten calls, five-minute intervals. |

[Hash migration and Node.js samples](https://sandbox.vnpayment.vn/apis/docs/chuyen-doi-thuat-toan/changeTypeHash.html) recommend API 2.1.0/HMAC-SHA512. Samples sort keys, encode values with `encodeURIComponent`, replace `%20` with `+`, serialize without a second encoding pass, and HMAC the UTF-8 signing string to hex. Callback examples remove `vnp_SecureHash` and `vnp_SecureHashType` before signing. Do not copy deprecated MD5/SHA256 examples or their buffer construction. Exact parser/encoding compatibility still needs fixtures and Sandbox verification.

## Project decisions and unresolved questions

These are engineering policies from [approved decisions](../srs/decisions-2026-10-29.md), not provider guarantees:

- Keep integer decimal strings at API boundaries and BigInt for calculations. Before signing, check `amountVnd * 100n` fits the provider's documented digit limit. This implies at most `9999999999` whole VND under that limit; confirm merchant-specific transaction limits in Sandbox. Never convert money through Number.
- Use `Asia/Ho_Chi_Minh` explicitly, independent of the host timezone; persist UTC instants. Test dates across midnight and after lock waits.
- Browser return never settles an order. A future IPN handler must validate signature, merchant, reference, currency/applicable fields, amount and order eligibility, then commit before acknowledging. Keep provider JSON outside the common response envelope.
- A 20-minute attempt target is not proof that VNPay cannot settle later. No universal URL reuse/finality guarantee was established by this investigation. Keep an unresolved attempt PENDING and reject replacement with conflict; do not release stock merely because an attempt's local target elapsed.
- Order reservation expiry is a separate approved 60-minute policy. Late callbacks on terminal orders remain reconciliation evidence and do not reactivate the order. No refund/query subsystem is added.
- Mapping late/conflicting callbacks to terminal acknowledgements needs a documented Day 12 decision and Sandbox evidence. Do not acknowledge a rolled-back update as accepted.

## Configure locally when access is available

1. Obtain the assigned Sandbox merchant code, hash secret and supported PAY version from your VNPay merchant contact/portal. No account was created by Day 1. Do not paste credentials into chat.
2. In ignored local `.env`, set `VNPAY_MODE=sandbox`, `VNPAY_API_VERSION=2.1.0`, `VNPAY_TMN_CODE`, `VNPAY_HASH_SECRET`, `VNPAY_RETURN_URL` and `VNPAY_IPN_URL`. Use actual issued credentials, not public demo values. Restart after changing config.
3. For the scaffold leave mode `unconfigured` and all four merchant/callback variables blank. Partial configuration is rejected; no fake secret is substituted. Sandbox mode validates configuration only: Day 1 has no payment routes, signing or settlement handlers.
4. Future intended routes are `/api/v1/payments/vnpay/return` and `/api/v1/payments/vnpay/ipn`; they currently return 404. Confirm routes/contracts during Day 3/11/12 before registering an IPN URL. Return may use HTTP loopback for local browser work; IPN config requires HTTPS. URL syntax validation does not establish provider reachability or domain approval.
5. An IPN server cannot reach this computer's `localhost`. Supply an explicitly arranged, merchant-approved reachable HTTPS test endpoint and register it in VNPay's merchant configuration. Do not open a public tunnel or expose an unfinished callback. This task did neither.
6. Keep access/proxy logs from capturing callback query strings; keep secrets, signed URLs and raw callbacks outside Git. Store only redacted, reviewed results in `docs/testing/`.

## Sandbox blockers / evidence checklist

All entries below remain **OPEN**; local mocks cannot close them.

- Assigned merchant credentials, active PAY 2.1.0/HMAC-SHA512 configuration, allowed return domain and transaction limits.
- Implemented callback handler and approved reachable IPN endpoint; real delivery and acknowledgement retry behavior.
- Golden signing fixtures and provider round trips: spaces, `+`, `%`, punctuation, Unicode, URL values, empty/optional fields, duplicate query keys and malformed encodings. Reject ambiguous inputs; preserve bytes consistently.
- Success/failure/status combinations, altered signature/reference/merchant/amount, duplicate/concurrent delivery, lost acknowledgement and transaction rollback.
- Reopen the same signed URL before expiry, concurrently and after payment/expiry; observe whether it can settle again. Use unique attempt references, never generate a replacement merely to bypass a pending constraint.
- Begin payment just before deadline, delay bank/browser/IPN completion past it, retry callbacks after attempt/order expiry and restart the API. Establish a defensible provider finality boundary before enabling automatic attempt terminalization/replacement.

Evidence must record test date, redacted scenario/reference identifiers, expected/observed result, database state after commit, acknowledgement and source of the verified rule. No signed URL, raw callback, personal data or credential belongs in the evidence. Payment acceptance remains blocked until the mandatory checks above are resolved.
