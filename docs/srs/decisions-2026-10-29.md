# Approved MVP decisions — 2026-10-29

The project owner approved the following policies in the project-overview conversation. This updates SRS v0.9; it does not claim software implementation or live integration tests.

| Decision | Approved behavior |
|---|---|
| Order reservation | Configurable 60 minutes; startup recovery and periodic in-process scanning; conditional terminal transition releases stock exactly once. |
| Payment-attempt target | Configurable 20 minutes; expiry of an attempt retains order stock. Safe terminalization depends on verified integration rules. |
| Repeated initiation | Reuse a pending attempt's URL only when safely valid. Otherwise return a documented conflict; do not create another pending attempt. |
| STAFF permissions | One common fulfillment permission set: eligible queue/detail/history and PAID → PROCESSING → SHIPPED → COMPLETED; no catalog, inventory, role or payment-success mutation. |
| Email | Deferred to P1; not selected for mandatory MVP. SMTP, delivery tables and email tests are not P0 dependencies. |

## Technical evidence and implementation gates

Reviewed on 2026-10-29: [official VNPay PAY documentation](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html) and [official hash migration documentation](https://sandbox.vnpayment.vn/apis/docs/chuyen-doi-thuat-toan/changeTypeHash.html).

The PAY documentation specifies an explicit `vnp_ExpireDate` in GMT+7, integer amount encoding as VND multiplied by 100, and signature validation before processing callbacks. Its integration samples use HMAC-SHA512, sorted/encoded parameters, and JSON IPN acknowledgements. Successful settlement must check the applicable result fields, reference and amount against persisted records.

These documents do not establish universal 20-minute provider finality or guaranteed URL reuse. Those remain Sandbox integration checks. Until safe expiry is established, retain an unresolved pending attempt and return conflict; never expire an attempt merely to bypass the unique-pending constraint. Late callbacks remain non-settling reconciliation records. No provider-query subsystem or refund flow is introduced by this decision.

Encoding fixtures, selected merchant/API configuration, callback acknowledgement mapping, URL validity, and expiry/finality behavior must be tested before payment integration is accepted. Product policies above are approved; these are engineering verification obligations.
