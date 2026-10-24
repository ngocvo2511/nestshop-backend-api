# E-commerce API contract — P0 v1

Updated 2026-11-08. Baseline: SRS v0.9, approved MVP decisions, database design and SEQ-01–28/32. **Implemented through Day8: M2 health/accounts/catalog/images/manual-inventory plus CUSTOMER POST /orders checkout/reservation.** JWT/roles guards enforce verified claims; owner IDs come only from JWT sub. Order reads/cancellation/fulfillment, payment and expiration routes remain contracts for later days and return404. Provider signing/encoding/finality still requires the [Sandbox verification](../integrations/vnpay-verification.md).

## 1. Common HTTP contract

Base path: `/api/v1`. UTF-8 JSON; property names camelCase. Resource/actor IDs are UUID v4 strings, normalized to lowercase before lookup/duplicate checks. Timestamps are UTC ISO-8601 strings (for example `2026-11-03T03:00:00.000Z`). Request bodies for JSON operations are objects; Content-Type is `application/json`. JSON body limit is 64 KiB with maximum nesting depth 16; `__proto__`, `constructor` and `prototype` input keys are rejected before transformation instead of silently dropped. Multipart is used only on the image-upload route, with its own 5 MiB file cap. GET operations have no request body. Only listed body/query fields are accepted; unknown/protected fields cause 400, including nested objects. There is no silent field stripping, boolean/string coercion or general implicit conversion.

Success, including created resources, uses the route's actual HTTP status and:

```json
{"success":true,"data":{"status":"ok"},"meta":{"correlationId":"27357da2-c7d9-4db9-8015-dffbe1145396"}}
```

Errors use the actual HTTP status and a value-free public message:

```json
{"success":false,"error":{"status":400,"code":"VALIDATION_FAILED","message":"Request validation failed","details":[{"field":"shipping.recipientPhone","rules":["matches"]} ]},"meta":{"correlationId":"27357da2-c7d9-4db9-8015-dffbe1145396"}}
```

Validation details contain only bounded field paths and rule names (maximum 20 entries, eight levels of nesting); never values, object targets, SQL or stack traces. Custom domain errors use the catalog in `src/common/http/api-error.ts`; ordinary framework errors receive generic catalog messages, never arbitrary exception text. Unknown errors become 500 `INTERNAL_ERROR`. `data` is always present on success (null for an otherwise empty JSON result).

`X-Correlation-ID`: accept one UUID v4 (36 characters), normalize to lowercase; generate a new UUID when missing, malformed, oversized or repeated. Echo it on every HTTP response and in JSON meta. It is tracing metadata, never identity/authorization. JSON request-completion logs contain only timestamp, level, event, correlationId, bounded method, status and durationMs. Request paths/URLs/queries, bodies, Authorization, cookies, tokens, signed URLs and raw errors are omitted. Startup logs have explicit safe events; an invalid environment may identify only its configuration key. Proxy/access log configuration must uphold the same redaction policy.

### Response exceptions

- **204:** empty body, no envelope/content payload. Correlation header is still present.
- **Files/images:** `StreamableFile`/`@ResponseMode('file')` preserves content and MIME, without JSON wrapping. Before streaming, missing/invalid files use the normal safe JSON error envelope; once headers are sent an error only terminates the stream.
- **Provider IPN:** `@ResponseMode('provider')` preserves HTTP 200 plain `{RspCode,Message}`. The global boundary is recorded before parsing, route guards and validation so their failures cannot produce an API envelope. Unexpected failures produce 200 `99` retry acknowledgement, never `00`. Expected provider results must be returned as acknowledgements by the future adapter, not thrown as ordinary API errors. No production payment route exists on Day 3.
- Swagger UI/spec are framework documents at `/api/docs` and `/api/docs-json`, outside the JSON envelope. The spec advertises health and implemented account/catalog endpoints, plus common schemas/Bearer security. Public product reads have no Bearer requirement; product mutations require an ADMIN access claim. Complete business endpoint Swagger is added with each feature.

## 2. Validation and numeric representations

Body integers must already be JSON numbers with `Number.isInteger` semantics and within bounds; strings such as `"1"`, fractions, NaN/Infinity, null and unsafe numbers are rejected. JSON NaN/Infinity literals are malformed JSON. Booleans must already be JSON booleans, never `"false"`/0/1. No `@Type(() => Number/Boolean)` or global implicit conversion is allowed for body fields.

For query offset/limit only, explicitly transform canonical unsigned decimal strings matching `0|[1-9][0-9]{0,6}` after bounding length; then validate integer/range. Reject whitespace, signs, leading zeroes, exponent notation, decimals, arrays, repeated keys and bracket/object query syntax. Query parsing is simple; every query DTO has an explicit allowlist.

- Positive VND values are **decimal strings** matching `[1-9][0-9]{0,18}`, at most `9223372036854775807`. Reject JSON numbers, zero/negative/fractional/leading-zero/whitespace/exponent strings and overflow before casting. PostgreSQL bigint stays TypeScript string (`parseInt8=false`); use BigInt internally, `.toString()` before JSON/SQL, never Number for money. Check line multiplication and cumulative order sum for overflow before writes. Generated SQL multiplication is a second safeguard.
- `minPriceVnd`/`maxPriceVnd` use the same positive-string validation, with min <= max when both provided. They are not query integers and are never converted to Number.
- VNPay conversion uses persisted amount * `100n`, checks provider digit limits before signing (currently documented 12 digits implies <= `9999999999` whole VND), and applies any stricter verified merchant limit. Catalog/order bounds remain bigint-wide; an unpayable amount must fail initiation with `MONEY_LIMIT_EXCEEDED`, not silently truncate.
- `initialStock`, returned `stockAvailable`: integers `0..2147483647`. Item `quantity`: integer `1..2147483647`, additionally limited by locked available stock. Manual `quantityDelta`: `-2147483648..2147483647`, excluding 0; compute the result in BigInt, require `0..2147483647` before writing.
- Checkout `items`: 1–100 entries with UUID productId and quantity. Reject duplicate product IDs after UUID normalization; no aggregation or cart requirement. Client totals/prices/stock/status/role are protected fields. All prices and amounts come from current locked server data.

Shared implementation: `PaginationQueryDto`, `UuidParamDto`, `IsVndAmount`, `ShippingDto` and `EmptyBodyPipe` for explicitly empty/no-body operations. Future DTOs must use class types, explicit nested `@Type`/`@ValidateNested`/`@IsDefined`, and the same global validation policy. Optional nullable fields allow null only where stated; an empty PATCH is 400 `EMPTY_UPDATE`. Required fields never accept null. All provided human text is trimmed, nonblank, bounded in Unicode characters and rejects control characters; passwords/tokens are never trimmed or case-normalized.

## 3. Token, identity and role contract

Access JWT transport is only `Authorization: Bearer <accessToken>`; no cookies/query alternative. JWT validation checks signature, algorithm, issuer/audience, token type and expiry before using sub/role; use HS256 only and payload `{sub,role,tokenType:"access",iss,aud,iat,exp}`. Issuer/audience are validated server configuration (`JWT_ISSUER=nestshop-api`, `JWT_AUDIENCE=nestshop-clients` by default), never request inputs. There is no mutable session/token-version claim. Roles: CUSTOMER, STAFF, ADMIN. Access claims remain stateless until expiry after role/password/logout changes; **new tokens read the current role**. No token version or per-request session lookup is introduced.

Login/refresh return `TokenPair`: `{user:UserPublic,accessToken,tokenType:"Bearer",expiresIn,refreshToken,refreshExpiresAt}`. `expiresIn` is integer seconds from configured access lifetime; refresh expiry is an ISO timestamp. Refresh is opaque 32 random bytes encoded as unpadded base64url (43 characters); store only its SHA-256 hash plus family/lifecycle metadata. Refresh/logout accept only JSON `{refreshToken}` with that exact shape/format, without requiring an access JWT. A token holder may revoke the supplied family; no user/family ID can be submitted. No cookies, header fallback or query transport. Token responses and payment-initiation responses use `Cache-Control: no-store`. Browser persistent token storage is not prescribed by this backend-only API.

Registration creates an active CUSTOMER and returns `UserPublic`, **without automatic login/session creation**, following SEQ-01; the Day 2 draft's phrase about registration returning tokens is corrected here. Call login to obtain the first token pair. Refresh consumes before creating its successor in one transaction. A consumed-token replay revokes the entire family and commits that revocation before returning 401 `REFRESH_REPLAY`; a concurrent loser may therefore revoke the winner's successor. No grace window. LOGOUT/PASSWORD_CHANGE revocation is ordinary invalid-token rejection, not a new replay event.

Email: trim, lowercase, valid email, maximum 254 characters; never allow role/isActive/passwordHash from public input. Passwords: 12–128 Unicode characters, no control characters or surrounding whitespace; secure salted hashing compatible with the existing self-describing scrypt setup format. Current passwords use the same no-normalization policy. No field reveals hashes, refresh rows/family IDs or credentials.

## 4. Shipping and response models

`Shipping` input/output matches persisted order snapshot:

| Field | Column | Rules |
|---|---|---|
| recipientName | recipient_name | required nonblank text, <=200 |
| recipientPhone | recipient_phone | required string, optional leading + then 8–15 digits; <=32; no spaces/extensions |
| addressLine | address_line | required nonblank text, <=500 |
| ward | ward | optional/null text, <=150 |
| district | district | optional/null text, <=150 |
| provinceCity | province_city | required nonblank text, <=150 |
| postalCode | postal_code | optional/null text, <=20 |

Absent optional fields persist/return null; supplied blanks are rejected. Domestic delivery is the MVP assumption; no address book, carrier integration, administrative-code lookup or international shipping extension. Later profile/product edits never change order snapshots.

All object fields below are exhaustive; omitted nullable fields are returned as null, not raw entities. Lists return `data:{items:[Model],offset,limit,total}` with total for the same filters. No unbounded embedded lists except checkout items (max 100).

| Model | Fields |
|---|---|
| UserPublic | id, email, role, isActive, fullName:null/text<=200, phoneNumber:null/phone<=32, createdAt, updatedAt |
| RoleAssignment | id, email, role, isActive |
| Product | id, name, description:null/text, priceVnd:positive VND string, stockAvailable:integer, isActive:boolean, imageUrl:null/relative URL `/api/v1/products/:id/image`, createdAt, updatedAt |
| InventoryAdjustment | id, productId, actorUserId, previousStock, quantityDelta, newStock, reason, createdAt |
| PaymentSummary | id, provider:"VNPAY", providerReference, status, amountVnd:VND string, currency:"VND", createdAt, expiresAt, terminalAt:null/time |
| OrderSummary | id, status, totalVnd:VND string, createdAt, updatedAt, reservationExpiresAt, paymentSummary:{latestAttempt:PaymentSummary/null,successfulAttempt:PaymentSummary/null} |
| OrderItem | id, productId, productName, unitPriceVnd:VND string, quantity:integer, lineTotalVnd:VND string |
| OrderDetail | OrderSummary fields plus shipping:Shipping and items:OrderItem[]; Staff/Admin detail additionally includes customerId (UUID, no account credentials) |
| HistoryEntry | id, previousStatus:null/order status, newStatus, actorType:"SYSTEM"/"USER", actorUserId:null/UUID, note:null/text<=1000, createdAt |
| AdminPayment | PaymentSummary plus orderId, providerTransactionReference:null/string, responseCode:null/string, transactionStatusCode:null/string; no signed URL |
| PaymentReceipt | id, paymentId:null/UUID, correlationId, providerReference:null/string, providerTransactionReference:null/string, signatureVerified:boolean, reportedAmountVnd:null/positive VND string, reportedCurrency:null/bounded string, responseCode:null/bounded string, transactionStatusCode:null/bounded string, outcome, safeDetail:null/bounded diagnostic code, receivedAt |

Malformed/fractional/negative/overflowing reported money is NULL plus a safe diagnostic code; untrusted callback data is never echoed as raw payload. Admin receipt fields are normalized/bounded: provider references <=100 characters, result codes <=32, reported currency <=16, and safeDetail a diagnostic code of 1–64 ASCII letters/digits/underscores (never raw provider prose). Canonical states: orders `PENDING_PAYMENT|PAID|PROCESSING|SHIPPED|COMPLETED|CANCELLED|EXPIRED`; payments `PENDING|SUCCESS|FAILED|EXPIRED`; receipts `SETTLED|FAILED|DUPLICATE|INVALID|MISMATCH|UNKNOWN_REFERENCE|LATE|CONFLICT`. Actor SYSTEM means null user ID, not a fake user row.

## 5. P0 route inventory

Paths below are relative to `/api/v1`. No query/body is allowed unless listed. Any protected route may return 401/403; UUID/DTO/query errors are 400, absent/foreign records are 404, unexpected infrastructure failures are safe 500/503. These common errors apply to every row in addition to listed business outcomes. Authentication precedes ownership and business precondition checks. There are no generic user-update, user-delete, order-edit, payment-status mutation or manual settlement endpoints.

### Auth and users

Foundation route: **GET `/health`**, public, no body/query, 200 success envelope with `data:{"status":"ok"}` and `Cache-Control:no-store`. Unknown query fields return 400 VALIDATION_FAILED. It is process liveness only, with no secret/version/DB/provider internals. Swagger UI and spec are public GET `/api/docs` and `/api/docs-json` (absolute paths outside `/api/v1`), respectively HTML/assets and unwrapped OpenAPI JSON.

| Method/path | Role/ownership | Request | Success data / status | Additional outcomes |
|---|---|---|---|---|
| POST /auth/register | Guest/public | JSON `{email,password,fullName?,phoneNumber?}`; optional profile fields null allowed, same profile bounds | UserPublic / 201 | EMAIL_IN_USE 409; role/active/hash inputs 400 |
| POST /auth/login | Guest/public | JSON `{email,password}` | TokenPair / 200, no-store | INVALID_CREDENTIALS 401 for missing/inactive account or wrong password, generic message |
| POST /auth/refresh | Refresh-token holder | JSON `{refreshToken}` | replacement TokenPair / 200, no-store | INVALID_REFRESH_TOKEN or REFRESH_REPLAY 401; malformed body 400 |
| POST /auth/logout | Refresh-token holder; no access JWT needed | JSON `{refreshToken}` | 204, no body | Well-formed unknown/expired/already-revoked token also 204; preserve ordinary revocation classification; malformed token/body 400 |
| GET /users/me | Any authenticated role; sub only | none | UserPublic / 200 | Never accept an arbitrary userId |
| PATCH /users/me | Any authenticated role; sub only | JSON nonempty subset `{fullName?,phoneNumber?}`; both nullable to clear | UserPublic / 200 | EMPTY_UPDATE 400; email/role/active/password/avatar fields 400; avatar not selected |
| POST /users/me/password | Any authenticated role; sub only | JSON `{currentPassword,newPassword}`; different values required | 204, no body; all refresh families revoked atomically | INVALID_CURRENT_PASSWORD 400; same new password/invalid policy 400; repeat with old current password fails |
| GET /admin/users/roles | ADMIN | offset,limit; optional role enum; fixed createdAt desc,id desc | list RoleAssignment / 200 | Query allowlist only |
| PATCH /admin/users/:id/role | ADMIN; target UUID | JSON `{role:CUSTOMER|STAFF|ADMIN}` | `{user:RoleAssignment,changed:boolean,auditId:UUID/null}` / 200 | Existing same role => changed:false,auditId:null, no audit; absent target 404; no general user mutation |

A role change uses the verified Admin actor and atomically updates role/audit. No undeclared last-admin protection, immediate claim revocation or account-management policy is introduced.

Day5 behavior: role authority comes from the verified JWT claim, including a previously issued ADMIN JWT after demotion, until its configured expiry. There is no per-request role/session database check. Login/refresh use the current persisted role. Role no-op returns `changed:false,auditId:null`, preserves `updatedAt` and writes no audit. Self-demotion is allowed; there is no last-admin exception.

Own-account GET/PATCH/password routes have no arbitrary ID alternative. Unknown query/body/protected fields are rejected, including `userId`, email, role, active status, hashes, refresh data and avatar. GET is read-only. PATCH trims fullName/phoneNumber, permits null to clear, and rejects an empty update. These writes target only the verified sub; shipping snapshots are untouched.

Logout and password change lock the user before token rows in ascending ID. Logout via a consumed predecessor revokes its still-live family without classifying replay; unavailable/expired/already-revoked families return empty204 unchanged. Ordinary revocation metadata is retained: password change revokes every not-yet-ordinarily-revoked family with PASSWORD_CHANGE, while prior LOGOUT/PASSWORD_CHANGE reason/timestamp remain intact. Consumed evidence is preserved. Password-hash update and all required refresh revocations commit together, or all roll back. Access JWTs remain usable until expiry after either operation. All account responses use no-store;204 responses have no envelope/body.

### Catalog, files and inventory

| Method/path | Role/ownership | Request | Success data / status | Additional outcomes |
|---|---|---|---|---|
| GET /products | Public active-only, for all callers | offset,limit,q?,minPriceVnd?,maxPriceVnd?,sort? | list Product / 200 | Invalid ranges/filter/sort 400 |
| GET /products/:id | Public active-only | UUID id | Product / 200 | Missing/inactive both NOT_FOUND 404 |
| POST /products | ADMIN | JSON `{name,description?,priceVnd,initialStock,isActive?}`; name1..250, description null/text1..10000; isActive defaults true | Product / 201 | Money/integer/unknown fields 400 |
| PATCH /products/:id | ADMIN; target may be inactive | nonempty subset `{name?,description?,priceVnd?,isActive?}`; only description nullable | Product / 200 | Missing404; EMPTY_UPDATE400; stockAvailable/initialStock/imagePath/imageUrl 400. Repeating identical catalog values is safe and creates no inventory audit |
| POST /products/:id/image | ADMIN; target may be inactive | multipart, exactly one `file`, no other fields; content-inspected JPEG/PNG/WebP, <=configured cap<=5MiB | `{productId,imageUrl}` / 200 | Missing product404; missing/multiple/unexpected fields400; UPLOAD_INVALID_TYPE415; UPLOAD_TOO_LARGE413; storage/DB500 |
| GET /products/:id/image | Public active-only | UUID id | raw file/image, correct MIME / 200 | Missing/inactive product or missing stored file => safe404 JSON; no arbitrary path/name input |
| POST /products/:id/stock-adjustments | ADMIN | JSON `{quantityDelta,reason}`; signed nonzero integer; trimmed reason1..1000 | InventoryAdjustment / 201 | STOCK_RANGE_EXCEEDED409; invalid delta/reason400; missing404 |

Product list query: offset defaults0 (0..1000000), limit defaults20 (1..100). `q`: trimmed text1..100, case-insensitive literal substring of name/description; escape SQL wildcard characters, parameterize values. `sort`: `name|-name|priceVnd|-priceVnd|createdAt|-createdAt`, default `name`; prefix `-` means DESC. Tie-break by id in the same direction. Public callers cannot request inactive data via query/role. Total applies the same active/search/price filters.

Day6 implementation uses PostgreSQL ILIKE with explicit `!` escape, escaping literal `!`, `%` and `_` before binding the complete search parameter. Backslash and quotes remain literal parameter data. Money filters are inclusive canonical VND strings; compare min/max using BigInt, never Number. Sort identifiers/directions come only from a fixed server mapping, not SQL supplied by callers. Count uses the same predicates as items, including when offset is beyond the end; offset pages are not a cross-request snapshot guarantee. Active out-of-stock products remain browsable. Invalid UUIDs return400; well-formed missing/inactive IDs share safe404 for all roles, including Admin.

ADMIN create is a single atomic product insert with explicit initial stock and default active=true. General PATCH locks/reloads its target and writes only supplied catalog columns plus updatedAt; it never saves a stale stock/image value or emits an inventory-adjustment audit. Inactive targets may be edited/reactivated. Repeated catalog values are safe. Unknown/protected fields are rejected even when they equal stored values; only description is nullable. Raw imagePath never appears in Product responses. Images and audited stock changes use dedicated routes. No category/cart/gallery or performance claim is part of this delivery.

One image reference per product. Every accepted upload generates a new non-guessable filename; serialize reference replacement on the product, preserve the winner's reference, and delete superseded files only after commit and confirmed unreferenced. Retried uploads may replace the image; there is no gallery/idempotency-key API. If DB persistence fails, attempt orphan cleanup; cleanup failure logs a safe event/correlation rather than a host path and does not convert failure into success. Direct static serving by arbitrary filename is not part of P0.

Day7 specifics: Multer memory upload accepts exactly one `file` part and no text fields; guards run before parsing file bytes. UPLOAD_MAX_BYTES is enforced inclusively up to5242880 bytes, and can be lowered by env. Header signatures and full sharp decode/re-encode must agree on JPEG/PNG/WebP and client MIME; filename extension is never authority. Unsafe path/control characters in original filenames are rejected. To keep decoding bounded, single-frame images up to16 million pixels are accepted; corrupt/truncated/animated/unsupported files return415 UPLOAD_INVALID_TYPE. Both input and canonical output must fit the configured byte limit; oversized input/output return413 UPLOAD_TOO_LARGE. Canonical encoding strips metadata/trailing data.

The relative DB reference is only a server-generated lowercase UUIDv4 plus `.jpeg|.png|.webp` under the canonical configured UPLOAD_DIRECTORY, not a host path or nested client path. Read/delete reject non-generated references, traversal and symlink/junction entries. POST replacement can target inactive products; GET requires an active product and reads bounded bytes under a shared product lock before releasing the transaction. Binary responses have correct MIME, `nosniff`, `no-store` and no envelope; absent/unsafe/missing-file references give safe404 JSON. No arbitrary filename static route exists.

The file is written before a user-visible DB reference, with exclusive-create semantics. Reference replacement locks/reloads the product and commits before considering old-file deletion. Generated references are never reused or assigned by client input; a global DB reference check preserves any file still referenced by a product. Orphan cleanup also checks DB first so an ambiguous commit cannot cause deletion of a committed image. If DB reachability prevents establishing that a file is unreferenced, keep it and emit the safe cleanup event for manual reconciliation. Cleanup failures log only timestamp/level/event, product UUID, correlation UUID and bounded stage (`partial|orphan|superseded`), never host path, client filename, raw exception or credentials. Failure to remove an old file after successful replacement does not roll back the committed image reference.

Manual adjustment is additive and **not idempotent**: a second accepted identical request makes a second audited change. Never automatically retry a successful adjustment after an ambiguous client timeout. Initial stock is create-only; all later manual changes use this route and atomic audit. Checkout/expiry reservations/releases are system transactions and do not create manual-adjustment audit rows.

Adjustment requires a JSON integer delta in -2147483648..2147483647 excluding0 and a trimmed safe nonblank reason<=1000 characters. A verified ADMIN actor is authoritative; actorId/stock replacement fields are forbidden. Inactive products may be adjusted. Lock/reload product, add delta in BigInt, reject a result outside0..2147483647 with409 STOCK_RANGE_EXCEEDED, then write stock/updatedAt and audit using one manager/transaction. Audit captures actor/product/previous/new/delta/reason/time; a failed audit rolls back stock. Image and catalog mutations use the same product row lock while changing only their own columns. Checkout/release contention is future Day8–13 evidence, not established by manual-adjustment tests alone.

### Customer and Staff orders

| Method/path | Role/ownership | Request | Success data / status | Additional outcomes |
|---|---|---|---|---|
| POST /orders | CUSTOMER; sub is owner | JSON `{items:[{productId,quantity}],shipping:Shipping}` | OrderDetail / 201, PENDING_PAYMENT | Duplicate/bad items or shipping400; INSUFFICIENT_STOCK409 includes unavailable/inactive products without partial writes; MONEY_LIMIT_EXCEEDED400 |
| GET /orders | CUSTOMER; own records only | offset,limit,status?,sort? | list OrderSummary / 200 | status any canonical order state; default all; sort createdAt or -createdAt, default -createdAt, matching id tie-break |
| GET /orders/:id | CUSTOMER; owner | UUID id | OrderDetail / 200 | Missing/foreign404 |
| GET /orders/:id/history | CUSTOMER; owner | UUID id; offset,limit | list HistoryEntry / 200; fixed createdAt asc,id asc | Missing/foreign404 |
| POST /orders/:id/cancel | CUSTOMER; owner | empty JSON object or no body | `{order:OrderSummary,changed:boolean}` / 200 | Already CANCELLED => changed:false, no repeated history/stock release; otherwise requires pending/before reservation deadline; paid/expired/other states409 ORDER_NOT_ELIGIBLE |
| POST /orders/:id/payment-attempts | CUSTOMER; owner | empty JSON object or no body; no amount | `{attempt:PaymentSummary,paymentUrl:string,reused:boolean}` / 201 new or 200 safely reused; no-store | PAYMENT_UNAVAILABLE503 if unconfigured; ORDER_NOT_ELIGIBLE409; PAYMENT_UNRESOLVED409; MONEY_LIMIT_EXCEEDED400; foreign404 |
| GET /staff/orders | STAFF/ADMIN shared fulfillment permission | offset,limit,status?; fixed createdAt asc,id asc | list OrderSummary / 200 | status one of PAID,PROCESSING,SHIPPED,COMPLETED, default PAID; PENDING_PAYMENT/CANCELLED/EXPIRED filter400 |
| GET /staff/orders/:id | STAFF/ADMIN; only fulfillment-eligible states above | UUID id | Staff OrderDetail / 200 | Missing/outside scope404 |
| GET /staff/orders/:id/history | STAFF/ADMIN; same eligibility | UUID id; offset,limit | list HistoryEntry / 200; fixed createdAt asc,id asc | Missing/outside scope404 |
| POST /staff/orders/:id/status | STAFF/ADMIN; eligible order | JSON `{status:PROCESSING|SHIPPED|COMPLETED,note?}`; note null/text1..1000 | OrderSummary / 200 | Only PAID→PROCESSING→SHIPPED→COMPLETED. Repeated same/skipped/backward/terminal transition409 INVALID_STATE_TRANSITION, no duplicate history; missing/outside scope404 |

Each accepted checkout creates a new order/reservation; no checkout idempotency-key or duplicate-submit merging is selected. Failed checkout rolls back every deduction/row. Snapshot shipping/product/price/quantities are immutable. Reservation deadline is createdAt+configured3600 seconds; attempt target createdAt+configured1200 seconds. These durations are independent, not a promise of provider finality. Attempt expiry alone retains reservation. Cancellation/order expiry releases exactly once only after winning the conditional pending transition.

Day8 checkout implementation accepts1–100 distinct product UUIDv4 IDs, normalized lowercase before duplicate checking, and JSON integer quantity1..2147483647 additionally bounded by locked stock. Shipping is a required object; each item must be an object. Reject nested arrays, unknown/protected owner/price/total/status/deadline fields, cart/address IDs, and query transport. Inline shipping fields use section4 rules; optional missing ward/district/postalCode become null. CUSTOMER only; Guest401 and STAFF/ADMIN403. Owner comes only from verified sub.

Checkout locks individual product rows in ascending canonical UUID order regardless of request order. Reload active/stock/name/price under the locks; missing/inactive/insufficient stock share409 INSUFFICIENT_STOCK. BigInt line multiplication and cumulative sum must fit positive PostgreSQL bigint before any persistence; overflow400 MONEY_LIMIT_EXCEEDED. With one shared READ COMMITTED transaction manager: conditional stock deductions, insert PENDING_PAYMENT order with exact total/shipping snapshot, insert immutable product-name/unit-price/quantity lines, and insert one initial history row (previousStatus:null,newStatus:PENDING_PAYMENT,actorUserId:null meaning SYSTEM,note:null). The generated line_total_vnd is omitted from writes and read back from PostgreSQL. Product changes/profile edits do not mutate snapshots.

Creation/history timestamps use one database wall-clock instant captured after product locks; reservationExpiresAt is that instant plus ORDER_RESERVATION_SECONDS (default3600). The no-store OrderDetail response contains items sorted by productId ASC and a null paymentSummary; it exposes no customer credentials/internal token/session fields. Checkout does not create a payment attempt or manual inventory-adjustment audit. No saved cart/address, read-order API, cancellation or scheduler is introduced here. Durable effects are returned only after commit; any error rolls back every stock deduction and partial order/line/history.

Payment initiation locks and inspects existing attempts; reuse only a verified safely valid pending URL, otherwise conflict. Never expire an unresolved attempt just to create a replacement. Genuine failed/expired predecessors may allow a new attempt while the order remains eligible. Payment success never deducts stock a second time. Staff/Admin cannot mutate payment status.

### Provider and Admin reconciliation

| Method/path | Role/ownership | Request | Success / failure contract |
|---|---|---|---|
| GET /payments/vnpay/return | Public browser boundary; signature verification, no user JWT | bounded provider query | JSON200 `{reference,providerResponseCode,settlementAuthoritative:false}` for verified structured return; malformed/signature mismatch400 VALIDATION_FAILED. Does not settle or expose stored order/shipping/payment URL |
| GET /payments/vnpay/ipn | Provider boundary; merchant/signature/data verification, no user JWT | bounded provider query | HTTP200 plain `{RspCode,Message}` per table below; never standard envelope |
| GET /admin/payments | ADMIN, read-only | offset,limit,status?,orderId?,providerReference?; fixed createdAt desc,id desc | list AdminPayment / 200; status single payment enum, orderId UUID, providerReference exact bounded ASCII1..100; no substring/report filters |
| GET /admin/payments/:id | ADMIN, read-only | UUID payment id | AdminPayment / 200; missing404 |
| GET /admin/payments/:id/notifications | ADMIN, read-only | UUID payment id; offset,limit; fixed receivedAt asc,id asc | list PaymentReceipt / 200; missing payment404; duplicates remain distinct receipts |

Provider parsing is separate from ordinary DTO query conversion: preserve canonical signing bytes; reject duplicate/non-string/oversized/ambiguous keys and unsupported fields before trusting data. Expected field set includes vnp_TmnCode, vnp_TxnRef, vnp_Amount, vnp_ResponseCode, vnp_TransactionStatus, vnp_TransactionNo, vnp_PayDate, vnp_BankCode, vnp_BankTranNo, vnp_CardType, vnp_OrderInfo, vnp_SecureHash; optional vnp_SecureHashType and currency only if present in the verified merchant contract. Required/optional provider combinations and encoding fixtures must be verified in Day 11, not guessed from browser return. Stored attempt/merchant context must be VND; validate any provider currency if supplied. Never require a nonexistent callback currency field merely to compare VND.

IPN expected response selection (future adapter; Sandbox confirmation remains mandatory):

| Condition after verification/transaction | RspCode | Message |
|---|---|---|
| Applicable success/failure durably committed, or non-settling late/conflict receipt durably recorded | 00 | Handled |
| Exact already-processed result with no repeated effects | 02 | Already confirmed |
| Unknown reference / reference outside assigned merchant context | 01 | Unknown reference |
| Amount/currency mismatch | 04 | Amount mismatch |
| Invalid signature or noncanonical callback structure | 97 | Invalid signature |
| Processing/DB failure, guard/validation/parser exception, no durable handling | 99 | Processing error |

`00` means durable handling, not automatically successful settlement. Commit before acknowledgement. Late/terminal conflicts never reactivate an order or change stock; retain receipts for Admin inspection. Safe acknowledgement selection for late/conflicting cases is a project choice to confirm in Sandbox, not a proven provider finality guarantee. Global failure fallback is always `99`. No payment/query/refund/production handler, manual settlement API or reconciliation write API is introduced on Day 3.

## 6. Error/status catalog and repeated actions

Global errors: VALIDATION_FAILED400, BAD_REQUEST400, MALFORMED_JSON400, UNAUTHORIZED401, FORBIDDEN403, NOT_FOUND404, CONFLICT409, PAYLOAD_TOO_LARGE413, UNSUPPORTED_MEDIA_TYPE415, INTERNAL_ERROR500, SERVICE_UNAVAILABLE503. Domain codes used above are defined with fixed public messages/status in `api-error.ts`; do not pass arbitrary ORM/provider error strings as messages. P0 controllers must map known expected uniqueness/state conditions deliberately; unknown DB failures remain safe500 rather than exposing constraint names or inventing a business outcome. Bounded deadlock retries do not replay nontransactional provider effects.

| Action repeated | Contract |
|---|---|
| Register same normalized email | 409 EMAIL_IN_USE |
| Refresh consumed token | 401 REFRESH_REPLAY after committed family revocation |
| Logout well-formed unavailable token | 204; never restore or relabel ordinary revocation |
| Set same role | 200 changed:false, no audit |
| Same catalog PATCH | 200; no stock mutation |
| Upload again | Replace serialized single reference; no gallery |
| Stock adjustment / checkout | Each accepted call is a new operation; no automatic ambiguous retries |
| Cancel already-cancelled own order | 200 changed:false; release/history once |
| Repeat fulfillment target | 409; no history |
| Repeat payment initiation | 200 existing URL only if safely reusable, otherwise409; at most one pending |
| Duplicate/late IPN | Explicit durable acknowledgement with no repeated business effects |
| Scheduler retry/restart | Recheck under locks; stock release once, no order reactivation |

## 7. Examples

Registration (future; role is forbidden):

```json
{"email":"customer@example.invalid","password":"<12-to-128-character-local-password>","fullName":"Customer"}
```

Checkout (future; no client price/total/address ID):

```json
{"items":[{"productId":"10000000-0000-4000-8000-000000000001","quantity":2}],"shipping":{"recipientName":"Customer","recipientPhone":"+84901234567","addressLine":"Example delivery address","provinceCity":"Example city","ward":null,"district":null,"postalCode":null}}
```

Corresponding line shape: `{id,productId,productName:"Demo notebook",unitPriceVnd:"45000",quantity:2,lineTotalVnd:"90000"}`; order total `"90000"`, server calculated. `{"priceVnd":45000}`, `{"quantity":"2"}`, duplicate product IDs and extra `role`/`totalVnd` fields are invalid. Protected-field rejection applies even when the submitted value equals the server's value.

Queries: `GET /api/v1/products?offset=0&limit=20&sort=name&minPriceVnd=1000`; `GET /api/v1/orders?status=PENDING_PAYMENT&sort=-createdAt`. Unknown `sort=price;DROP...`, repeated `limit`, `limit=1e2`, fractional numbers and `isActive=true` public product filtering are 400.

## 8. Transaction and lock conventions

READ COMMITTED, one shared TypeORM transaction manager across a business operation. Auth: lock user before token rows sorted by ID; consume old refresh before successor insert. Password/login/refresh share the user lock. Existing-order mutation: order → payments by ascending ID → products by ascending ID when stock release is needed. Checkout: products in ascending ID order. Role/inventory mutations and their audit use the same transaction. Re-read status and wall-clock deadlines after waiting for locks (for example database clock_timestamp()), not stale transaction-start time. Conditional terminal transitions own stock release; repeated/losing operations make no second release/history/settlement. Keep immutable snapshots/audit/history and provider receipts, with no FK cascade deletion. Do not issue an acknowledgement or response claiming committed effects before commit; do not throw an expected HTTP rejection inside a transaction that must retain replay revocation or a reconciliation receipt.

M1 acceptance covers the working HTTP foundation plus startup/migration/seed/real PostgreSQL smoke evidence. Full feature Swagger, authorization/ownership, transaction contention, delivery coverage/performance and Sandbox behavior remain their implementation-day gates.
