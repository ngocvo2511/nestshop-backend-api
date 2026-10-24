# Project Overview and Software Requirements Specification

## 1. Document information

| Field | Value |
|---|---|
| Project | E-commerce Backend API |
| Version | 0.9 |
| Status | Requirements baseline — MVP policy decisions approved; integration verification pending |
| Date | 2026-10-29 |
| Purpose | Define a feasible, testable 2–3-week backend MVP and its implementation boundaries. |
| Related artifact | Diagram inventory: [../diagrams/README.md](../diagrams/README.md) |

MVP policy decisions were approved by the project owner on 2026-10-29; see [decision record](decisions-2026-10-29.md). This is a requirements document, not evidence that an integration has been implemented. “Proposed” identifies a decision requiring confirmation; all other MUST statements are requirements.

## 2. Overview and architecture

The system is a NestJS REST API for an online shop. Guests discover products; customers manage an account and orders, enter shipping details at checkout, and initiate payments; staff fulfill orders; administrators manage catalog, inventory, users, and roles. The API is a **modular monolith** implemented with TypeScript, TypeORM, and PostgreSQL.

Required technology: NestJS, TypeScript, TypeORM, PostgreSQL, JWT access and refresh tokens, bcrypt (or equivalent), class-validator/class-transformer, Multer, Swagger/OpenAPI, Jest, Docker Compose, and VNPay Sandbox. Email is deferred from the mandatory MVP; future P1 email, if selected, uses SMTP through Nodemailer or equivalent. The application MUST NOT introduce microservices, Redis, RabbitMQ, or a broker merely for this MVP.

External dependencies are VNPay Sandbox and an SMTP provider. They are systems, not authenticated human users. A clean Docker Compose setup, Swagger, README/environment documentation, consistent responses, Conventional Commits, and at least 70% Jest unit-test coverage are delivery requirements.

## 3. Scope and priority

| Priority | Scope |
|---|---|
| **P0 — mandatory** | Authentication with refresh-token rotation/replay response; secure RBAC; product list/detail/create/update, search/filter/sort/offset pagination and image upload; direct order submission/history; separate profile viewing/updating and inline checkout shipping details; server price calculation and transactional inventory reservation/release; a basic staff order queue and status history; distinct order/payment states; minimal automated unpaid-order expiration; VNPay Sandbox payment URL and verified idempotent IPN handling; Swagger; Docker Compose; README/environment documentation; consistent API responses; Conventional Commits; at least 70% Jest coverage. |
| **P1 — important if time permits** | SMTP/Nodemailer configuration and all email notifications; `notification_deliveries` persistence, event deduplication/delivery status/retry handling, and email tests; cart/cart items; category CRUD; advanced staff filters/reporting; advanced status-history filtering; additional integration tests beyond the required P0 concurrency/transaction suite. |
| **P2 — out of scope** | Production payment processing, refunds, social login, microservices, brokers, Redis caching, complex promotions/loyalty, recommendations, carrier integration, split shipments, multi-warehouse inventory, and advanced analytics. |

If a P0 item proves larger than expected, the team MUST document a smaller compliant implementation and remaining risk; it MUST NOT be silently removed. A health-check endpoint is a P0 supporting feature. Categories and carts are P1; checkout MUST work without a cart.

## 4. Actors and authorization

| Actor | Permitted capabilities | Explicit restrictions |
|---|---|---|
| Guest | Browse active products/categories, search/filter/sort/paginate, see product detail, register, log in. | No protected data or mutations. |
| Customer | Guest capabilities; own profile/password; own cart if P1; submit orders with recipient and shipping details; initiate payment for own eligible order; see own orders, payment state, and status history. | Cannot access another customer’s profile, cart, orders (including their shipping details), or payments; cannot manage catalog/roles. |
| Staff | View order queues and fulfillment-relevant order, payment, address, and history information; make permitted fulfillment transitions. | Cannot manage admin accounts/roles, set prices/inventory, or mark payment successful. |
| Admin | Manage products/categories, inventory, user accounts/roles, orders, and inspect payment attempts/reconciliation information within business rules. | Public registration MUST NOT create ADMIN; cannot manually mark a payment successful, alter provider results to settle an order, or bypass VNPay verification; refunds remain out of scope. |
| VNPay Sandbox / SMTP | Process signed payment callbacks / deliver outbound email. | External dependency; no human API authorization role. |

Every protected route MUST authenticate an access token and enforce role and, where relevant, record ownership server-side. UI hiding is never authorization. Ordinary profile updates MUST NOT change user ID, role, account status, email verification/status, password hash, or refresh-token data.

## 5. Functional requirements

Each acceptance criterion is independently testable. “MUST” maps to P0 unless stated otherwise.

### 5.1 Authentication and authorization

| ID / priority | Requirement and acceptance criteria |
|---|---|
| FR-AUTH-001 Register — MUST | With valid unique email/password, create an active CUSTOMER account using a secure password hash. Duplicate email is rejected; no plaintext password is persisted or returned. Public registration cannot select a role. |
| FR-AUTH-002 Login — MUST | An active user with valid credentials receives access and refresh tokens. Invalid credentials return a generic 401-style error that does not reveal which field failed. |
| FR-AUTH-003 Refresh token — MUST | A valid, unexpired, `ACTIVE` refresh token yields a new access token and replacement refresh token. Rotation atomically marks the old token consumed and stores the replacement, so only one concurrent request can rotate a given token. Reuse of a token consumed by successful rotation is replay: reject it and revoke its whole family, requiring login. Tests cover concurrent rotation and consumed-token replay. |
| FR-AUTH-004 Logout — MUST | Logout atomically revokes the supplied/current token family with revocation reason `LOGOUT`. A logout-revoked token is rejected on ordinary reuse but is not classified as a new replay event; repeated/concurrent logout or refresh has safe conditional behavior and does not restore a token. Already-issued stateless access JWTs may remain valid until configured expiry. |
| FR-AUTH-005 Session security — MUST | Access and refresh lifetimes are environment configured and differ. Access tokens are stateless JWTs with a short configurable lifetime; logout/password change revoke refresh sessions but do not immediately invalidate already-issued access tokens. Refresh tokens are stored as hashes with family/session, `ACTIVE`/`REVOKED`/`EXPIRED` representation, `consumed_at`, `revoked_at`, and revocation reason (or equivalent metadata). Password change atomically revokes all families, including the current one, with a distinct reason. Expired tokens are rejected without rotation. Tests cover replay, logout-revoked, password-change-revoked, expired, and concurrent refresh behavior; no grace period, multi-tab synchronization, token-version check, or per-request session lookup is provided. |
| FR-USER-001 Protected identity — MUST | Missing, invalid, or expired access tokens are rejected; role and identity are derived only from verified server token claims. |
| FR-USER-002 Role authorization — MUST | ADMIN-only catalog/user/role operations and STAFF fulfillment operations return 403 to unauthorized roles. |
| FR-USER-003 Ownership enforcement — MUST | Customer A cannot read or mutate Customer B’s profile, cart, order (including shipping details), payment initiation, or status history. |
| FR-USER-004 Role management — MUST | Only ADMIN can view/manage user account role assignments through dedicated allowlisted operations. The public registration/profile APIs cannot do so. Each successful change atomically persists a role-change audit record containing actor user ID, affected user ID, old role, new role, and timestamp; tests must verify both the changed role and audit record. |

### 5.2 Profile and password

| ID / priority | Requirement and acceptance criteria |
|---|---|
| FR-PROFILE-001 View profile — MUST | An authenticated user can view their own profile, including full name, phone number, and avatar URL if enabled. Profile viewing is a read-only operation, separate from updating a profile. Sensitive authentication data is not returned. |
| FR-PROFILE-002 Change password — MUST | The caller supplies current password plus a policy-valid replacement. Incorrect current password is rejected; successful change applies FR-AUTH-005 session revocation. |
| FR-PROFILE-003 Update profile — MUST | An authenticated user can update only their own allowlisted fields: full name, phone number, and avatar URL if enabled. Invalid phone/URL values and protected/mass-assigned fields are rejected or ignored consistently. Profile updates do not change shipping details already stored in an order. |

Shipping details are entered when placing an order under FR-ORDER-001 and stored directly in that order. A separate address book, address CRUD and default-address selection are out of scope.

### 5.3 Catalog, images, and inventory

| ID / priority | Requirement and acceptance criteria |
|---|---|
| FR-PROD-001 List/search/filter/sort — MUST | Guests/customers receive active products only. Allowlisted query parameters produce deterministic matching results. |
| FR-PROD-002 Offset pagination — MUST | Validated `offset`/`limit` are applied and the response includes items, offset, limit, and total. Invalid bounds fail validation. |
| FR-PROD-003 Product detail — MUST | An active product is returned; missing/inactive products do not disclose protected catalog data to public callers. |
| FR-PROD-004 Create product — MUST | ADMIN creates product with a positive integer VND price, initial non-negative integer stock, and active flag. Fractional, negative, binary-floating-point, or mass-assigned values are rejected. CUSTOMER/STAFF are forbidden. |
| FR-PROD-005 Update product — MUST | ADMIN updates allowlisted non-stock catalog fields. Direct stock modification is forbidden through general product update; every post-creation administrative stock change uses FR-INVENTORY-002. Invalid/mass-assigned fields do not persist. |
| FR-UPLOAD-001 Upload image — MUST | ADMIN uploads a product image through Multer. Only configured JPEG, PNG, or WebP files up to 5 MiB are accepted; unsafe names/types and oversize files are rejected. The API generates a non-guessable server-side filename, stores the relative image path in PostgreSQL, and returns a documented image URL/reference. If storage succeeds but the associated database operation fails, the API attempts to delete the orphaned file; a cleanup failure is safely logged with diagnostic context for manual cleanup. Failed validation or storage leaves no product-image reference; missing stored files return a safe not-found response. |
| FR-CAT-001 Category CRUD — P1 | ADMIN manages categories; active category browsing is public if categories are approved. |
| FR-INVENTORY-001 Inventory consistency — MUST | Product stock is never client-authoritative. System-managed checkout reservation, cancellation/expiry release, and transaction rollback use database transactions with row locks or conditional updates, so concurrent successful orders cannot oversell or make stock negative. |
| FR-INVENTORY-002 Admin stock adjustment — MUST | Only ADMIN may submit a documented signed integer quantity delta plus required reason; arbitrary stock-field mass assignment is forbidden. The transaction locks/conditionally updates the product, rejects a result below zero, and atomically persists an inventory-adjustment audit with product, actor ID, previous stock, new stock/delta, reason, and timestamp. Concurrent checkout/adjustment operations cannot lose updates or make stock negative. |

Inactive/out-of-stock products cannot be newly ordered. If a P1 cart contains a product whose price changed, became inactive, or lacks stock, checkout recalculates from current server data and rejects or adjusts only through an explicit response; cart values never reserve price or stock.

### 5.4 Orders and staff operations

| ID / priority | Requirement and acceptance criteria |
|---|---|
| FR-ORDER-001 Submit order — MUST | CUSTOMER submits nonempty product IDs/quantities and inline shipping details containing recipient name, contact phone number, and delivery address. The server validates the supplied shipping details, reloads products, calculates integer-VND line total as snapshotted unit price × quantity and the server-side order total as the sum of validated lines, and stores the recipient/contact/address details directly in the order with product name/unit price/line-total snapshots. It creates the order directly as `PENDING_PAYMENT` and reserves inventory atomically. Client amounts are never authoritative. Missing/invalid shipping details, fractional/invalid/negative amount, bad item, insufficient stock, inactive product, or transaction failure creates no partial order/stock change. Checkout does not require a saved address or an address ID. Stored shipping details belong to that order and remain independent of later profile changes. |
| FR-ORDER-002 Order history — MUST | CUSTOMER receives only own orders, details, payment state, and status history with documented pagination/filtering. |
| FR-ORDER-003 Staff order queue — MUST | STAFF/ADMIN can list the minimal fulfillment queue by current order status and inspect necessary order, item, address, payment summary, and history data. Creation-date range, compound filters, exports, and reporting are P1. |
| FR-ORDER-004 Fulfillment transition — MUST | STAFF with authorization and ADMIN can make only permitted fulfillment transitions and cannot alter payment status. Invalid transition is rejected. |
| FR-ORDER-005 Status history — MUST | Each order-status change persists actor ID or `SYSTEM`, previous status, new status, timestamp, and optional safe note. Customer can view history for own order; STAFF/ADMIN can view it for eligible orders. Advanced history filtering is P1. |

### 5.5 Payment: VNPay Sandbox

| ID / priority | Requirement and acceptance criteria |
|---|---|
| FR-PAY-001 Create attempt/initiate payment — MUST | An authenticated owner may initiate payment only for an eligible `PENDING_PAYMENT` order. Creation is concurrency-safe: PostgreSQL locking/conditional updates plus a partial unique constraint/index allow at most one `PENDING` attempt per order. If a valid pending attempt already exists, the API returns/reuses its documented payment URL only while safely valid; otherwise it returns a documented conflict response and creates no new attempt. A new attempt may be created only after the prior attempt is genuinely `FAILED` or `EXPIRED` and the order remains eligible. The URL uses persisted integer-VND order total, never a client amount. Paid/cancelled/expired/foreign orders are rejected. Each attempt records an intended/configurable approximately 20-minute application expiry from creation, pending official VNPay Sandbox documentation and integration verification. |
| FR-PAY-002 Configured signed request — MUST | Merchant identifier, signing secret, return URL, IPN URL, locale/time zone, and sandbox/production environment settings are environment-configured. The API signs requests according to the current official VNPay specification; credentials are never hardcoded. |
| FR-PAY-003 Verified return/IPN — MUST | IPN processing verifies the official VNPay signature and validates provider order reference, amount, currency (`VND`), transaction data, and applicable result fields against persisted order/payment records. VNPay request/callback amount conversion and comparison follow the current official Sandbox specification; the SRS does not assume provider encoding or URL-expiry details. A browser return URL alone never confirms payment. A valid applicable successful server callback alone makes one attempt `SUCCESS` and its order `PAID`; invalid, duplicate, inapplicable, and late callbacks are safely recorded for reconciliation without an unauthorized state change. |
| FR-PAY-004 Idempotency and failures — MUST | Duplicate, delayed, invalid, failed, cancelled, or mismatched callbacks are safely recorded/handled without duplicate business effects. Callback settlement locks the target payment/order (or uses an equivalent conditional update) in one transaction. A terminal attempt cannot be marked terminal merely to bypass the one-pending-attempt invariant. Successful payment cannot be repeated or arbitrarily set by client/staff/admin. ADMIN may inspect payment/reconciliation records but cannot edit provider results or settlement state; any future manual annotation is auditable and non-settling. Persist safe transaction references, response/result codes, verified VND amount/currency, relevant transaction data, receive time, and reconciliation outcome. |
| FR-PAY-005 Expiry and inventory — MUST | Order creation reserves stock; verified success confirms the reservation. The P0 in-process scheduler performs startup recovery and periodic scans for (a) pending attempts whose intended configurable approximately 20-minute application expiry is due and (b) orders whose configurable 60-minute reservation expiry is due. Attempt expiry safely marks only that attempt `EXPIRED`; a still-eligible order remains `PENDING_PAYMENT` with reservation intact and may receive a replacement attempt. Order expiry atomically expires any remaining pending attempt(s), transitions the order `EXPIRED`, writes history, and releases stock exactly once. Repeated scans/restarts cannot release stock twice. |

One order MAY have multiple payment attempts; at most one verified successful attempt may settle it. Refunds and production processing are out of scope. Exact VNPay field names, canonical sort/encoding/signature algorithm, success codes, IPN response protocol, and timeout values MUST be verified against the official VNPay documentation during implementation; this SRS does not assert their current values.

### 5.6 Email notifications — P1

| ID / priority | Requirement and acceptance criteria |
|---|---|
| FR-EMAIL-001 Notification events — P1 | In the same database transaction as registration, order creation, verified payment-result, expiration, or selected fulfillment state change, create a durable notification-event record with a unique event key. After that transaction commits, attempt delivery from the persisted event if SMTP is configured. Core events are welcome, order confirmation, verified payment success/failure, and expiration/cancellation where customer notification is enabled. |
| FR-EMAIL-002 Safe delivery — P1 | Recipient comes from the validated account email, not an arbitrary request field. Templates include a subject, plain text or HTML body, and only necessary non-sensitive data; no credentials, token, card, or secret is sent/logged. |
| FR-EMAIL-003 Graceful failure/idempotency — P1 | SMTP host/port/user/password/from address/timeouts are environment-configured. An event record has `PENDING`, `SENDING`, `SENT`, and `FAILED` delivery status, attempt count, and safe error/timestamp fields. Its unique event key prevents duplicate event creation across callbacks/restarts. After restart, the application finds eligible `PENDING` events; stale `SENDING` events become eligible after a documented timeout/lease. Conditional updates claim one event at a time, and retries are bounded/configurable. Timeouts/provider errors do not roll back an accepted order or verified payment. Deduplication is at-least-once event processing, not exactly-once SMTP delivery: a crash after provider acceptance but before `SENT` is persisted can result in a repeat message. No broker or separate worker is required. |

Email tests MUST mock delivery; real SMTP credentials are never required. P0 starts and functions without SMTP settings and has no dependency on notification events for order, payment, inventory, history, or API correctness.

### 5.7 State machines and transaction rules

All P0 state-changing operations below MUST use a PostgreSQL transaction. A transition writes the changed record and required history/audit fields atomically; a failed transaction rolls back all state and stock changes. P1 notification-event creation/delivery, when selected, follows section 5.6 and does not alter P0 transition correctness.

**Canonical enums and money policy.** These are the sole status values for detailed database/API/diagram design: Order: `PENDING_PAYMENT`, `PAID`, `PROCESSING`, `SHIPPED`, `COMPLETED`, `CANCELLED`, `EXPIRED`; payment attempt (`payments` row): `PENDING`, `SUCCESS`, `FAILED`, `EXPIRED`; refresh token representation: `ACTIVE`, `REVOKED`, `EXPIRED`; notification delivery (P1 only): `PENDING`, `SENDING`, `SENT`, `FAILED`. A `payments` row is one payment attempt, not an order-level payment state; an order may have multiple `FAILED` attempts but at most one `PENDING` and one `SUCCESS` attempt. There is no `NEW` order status. The MVP currency is VND only: persisted product prices, line totals, order totals, and payment amounts are integer VND, never binary floating point; shipping fees, taxes, discounts, promotions, and multi-currency are out of scope.

| State machine | Allowed transition | Trigger / preconditions | Atomic effects; rejected case |
|---|---|---|---|
| **Order** | `PENDING_PAYMENT` (initial) | Customer submits valid items and inline recipient/contact/address details, and locked/conditional stock decrement succeeds. | In one transaction create the order directly in `PENDING_PAYMENT`, items/address snapshots, initial `SYSTEM` history entry, and reservation. Any invalid address/item/stock/transaction failure creates no order or reservation. |
| **Order** | `PENDING_PAYMENT → PAID` | Verified successful callback for the current eligible payment attempt before expiry. | Lock order/payment; set order `PAID` and attempt `SUCCESS`, write history, and retain reservation. Duplicate/concurrent callbacks observe settled state and make no second change. |
| **Order** | `PAID → PROCESSING → SHIPPED → COMPLETED` | STAFF/ADMIN performs next permitted fulfillment transition. | Update order + history atomically. Staff cannot set payment fields. Backward/skipped/terminal transitions are rejected. |
| **Order** | `PENDING_PAYMENT → EXPIRED` | Startup recovery or periodic P0 scheduler finds the configurable 60-minute reservation/order expiry passed and payment/order are still pending. | In one transaction lock/conditionally update the order, expire remaining pending attempts, write history, and restore each reservation. Stock is restored only if the conditional `PENDING_PAYMENT → EXPIRED` update succeeds; zero affected rows means no stock change. Repeated scans do nothing. |
| **Order** | `PENDING_PAYMENT → CANCELLED` | Customer explicitly cancels before verified payment success and before expiry. | In one transaction lock/conditionally update the order, expire pending attempts, write history, and restore reservation. Stock is restored only if the conditional `PENDING_PAYMENT → CANCELLED` update succeeds; zero affected rows means no stock change. Paid/processing/shipped/completed orders cannot be cancelled in the MVP. |
| **Payment attempt** | `PENDING → FAILED` | Verified non-success provider result for that attempt while order remains pending. | Record provider result/timestamp; order remains `PENDING_PAYMENT`, reservation remains, and only then may the customer create another attempt. |
| **Payment attempt** | `PENDING → SUCCESS` | Signed IPN passes current official VNPay verification, references/amount match persisted attempt/order, and order is not expired/cancelled/paid. | Lock payment and order in a consistent order (or use equivalent conditional updates), then perform the `PENDING_PAYMENT → PAID` transaction. If cancellation or expiry acquired the lock and committed first, record the callback as late/non-settling and do not reactivate the order, alter stock, or settle payment. Client amount and browser return are never authoritative. |
| **Payment attempt** | `PENDING → EXPIRED` | The scheduler determines the attempt's intended/configurable approximately 20-minute application expiry is due under verified provider/integration rules, while the order remains eligible. | Mark only that attempt expired with a conditional update; order remains `PENDING_PAYMENT` and reservation remains. The customer may then create a replacement attempt if no other `PENDING` attempt exists. The application does not assume VNPay universally expires URLs at exactly 20 minutes. |
| **Payment attempt** | `PENDING → EXPIRED` | Associated order expires or customer cancellation commits first. | Mark all still-pending attempts expired in that same terminal-order transaction. A callback arriving later is recorded as late/non-settling; it MUST NOT reactivate the order, settle it, or change stock. It is flagged for admin reconciliation with the provider outside the automated workflow. |
| **Inventory reservation** | `NONE → RESERVED → CONSUMED` | Checkout succeeds, then payment succeeds. | Reservation is represented by the stock decrement associated with the pending order; success consumes it without another stock change. |
| **Inventory reservation** | `RESERVED → RELEASED` | Order expiry, permitted pre-payment cancellation, or checkout rollback. Attempt expiry alone does not release inventory. | In the same locked transaction, conditionally restore stock once and mark the order terminal. Repeated callbacks/scans cannot release twice. |

Payment initiation only creates a new `PENDING` attempt for a non-expired `PENDING_PAYMENT` order when no pending attempt exists, and does not change inventory. Duplicate/concurrent initiation requests lock or conditionally update the order and rely on the database partial unique constraint: one request creates/returns the pending attempt; another returns the same safely reusable URL or documented business conflict response. An attempt may become terminal only on a verified provider result, its documented attempt-expiry policy, or terminal order transition—never to bypass this invariant. Attempt expiry does not release reserved inventory; only terminal order cancellation/60-minute expiry does. An order can have failed attempts but only one successful settlement. A verified IPN, customer cancellation, and order expiry transaction serialize on the same order/payment rows: the first transaction satisfying its conditional preconditions wins; later transactions observe the terminal/paid result and make no stock or settlement change. A late callback for an attempt already terminal is a non-settling reconciliation case: retain safe provider reference/result/receive time and outcome on the existing attempt or minimal related structure, but never reactivate the order or alter inventory. Unknown callbacks produce safe structured diagnostics with a correlation ID where possible. Invalid signatures/references/amounts are rejected without state or inventory changes. Signing secrets and unnecessarily sensitive raw provider payloads MUST NOT be logged.

### 5.8 Cart and common API behavior

| ID / priority | Requirement and acceptance criteria |
|---|---|
| FR-CART-001 Manage cart — P1 | CUSTOMER can manage only their own cart and cart items. Checkout remains server-priced and stock-validated. |
| FR-API-001 Responses/errors — MUST | All endpoints follow one documented success envelope and one error shape containing safe message, status, code, and actionable validation detail where appropriate. |
| FR-API-002 Validation — MUST | DTO transformation/allowlisting validates body/query/route inputs; unexpected writable fields cannot change persisted state. |
| FR-API-003 Swagger — MUST | Swagger documents every endpoint, role/security requirement, principal DTO/schema, query/filter, multipart behavior, and expected errors. |
| FR-HEALTH-001 Health check — MUST | An unauthenticated documented endpoint returns lightweight health without secrets. |

### 5.9 Minimum P0 endpoint inventory

The detailed API contract remains a planned artifact, but Swagger MUST include at least the following P0 route groups: public auth (`register`, `login`, `refresh`, `logout`); separate authenticated profile view/update and password operations; public product list/detail and ADMIN product/image management plus reasoned stock adjustment; CUSTOMER checkout with inline recipient/contact/address input, own order list/detail/history, cancellation while pending, and payment initiation; STAFF/ADMIN order queue/detail and permitted status transition; the public/provider payment return and IPN endpoints; and health. Repeated payment initiation returns the reusable pending-attempt URL or a documented conflict, never a second pending attempt. Payment IPN is authenticated by verified VNPay request data, not a bearer user token. Route-level roles and ownership checks follow sections 4 and 5.

## 6. Business rules and data model impact

| Entity | Priority | Ownership / purpose |
|---|---|---|
| `users` | P0 | Account identity, role, profile, account status. |
| `refresh_tokens` | P0 | User-owned hashed refresh sessions with token family, `ACTIVE`/`REVOKED`/`EXPIRED` representation, expiry, and consumption/revocation metadata. |
| `products` | P0 | Admin-managed integer-VND catalog price, active status, initial stock, and image reference; post-creation stock changes occur only through audited adjustment or system reservation/release flows. |
| `orders`, `order_items` | P0 | Customer-owned purchase record; items preserve product name, integer-VND unit-price/line-total, and quantity snapshots, while order preserves integer-VND total and the recipient name, contact phone, and delivery-address snapshot entered at checkout. |
| `payments` | P0 | One payment attempt per row, with provider/transaction references, integer-VND amount/currency, canonical attempt status, intended/configurable application expiry, result, received/reconciliation details, and timestamps. PostgreSQL partial unique constraints/indexes permit at most one `PENDING` and one `SUCCESS` attempt per order. |
| `notification_deliveries` | P1 | Durable, uniquely keyed notification-event record created with its business transaction; stores event type/key, recipient snapshot, payload/template reference, P1 delivery status, attempts, and safe outcome timestamps/details. It prevents duplicate event creation, not every possible duplicate SMTP message. |
| `order_status_history` | P0 | Immutable minimal record of fulfillment and system state transitions, actor, prior/new state, timestamp, and safe note. |
| `role_change_audit` | P0 | Immutable Admin role-change record with actor user ID, affected user ID, old role, new role, and timestamp. |
| `inventory_adjustment_audit` | P0 | Immutable Admin stock-adjustment audit with product, actor ID, previous stock, new stock/delta, required reason, and timestamp; inserted atomically with the adjustment. |
| `categories` | P1 | Admin-managed product taxonomy. |
| `carts`, `cart_items` | P1 | Customer-owned convenience state; not an authoritative reservation. |

Key rules: normalized user email is unique; passwords are only secure hashes; refresh-token rows retain `ACTIVE`/`REVOKED`/`EXPIRED` statuses and distinguish successful rotation consumption from ordinary revocation through metadata; public registration creates CUSTOMER only; prices/totals are server-calculated positive/non-negative integer VND values; checkout validates inline recipient/contact/address input and stores it directly in immutable order snapshots; and payment-attempt state is never inferred from order fulfillment state. PostgreSQL must enforce at most one pending and one successful attempt per order using partial unique indexes or equivalent constraints. Product creation may set initial stock, but later administrative stock changes use audited delta adjustment only; system reservation/release is separate. Admin role/stock updates and their respective audit insertions are one transaction. P1 notification event keys are unique where applicable. Physical columns, indexes, migration details, and exact constraints are deferred to Database Design/ERD.

**Chosen inventory strategy:** reserve (deduct available stock) in the order transaction at checkout, then release exactly once on pre-payment cancellation or order expiry; retain it on verified success. The approved P0 in-process scheduler scans once during startup recovery and at a documented periodic interval for pending attempts past their intended/configurable approximately **20-minute** application expiry and orders past the approved configurable **60-minute** reservation duration. Attempt expiry marks only the attempt terminal and retains reservation; order expiry locks/conditionally updates the order, atomically expires remaining pending attempts, writes history, and restores stock, so restarts and repeated scans cannot double-release. This single-instance MVP does not use a worker, broker, or distributed lock.

**Local uploads:** files are stored under a configured application directory such as `uploads/products`; PostgreSQL stores only the generated relative path and metadata needed by the product. Docker Compose mounts that directory as a named volume so files survive API-container recreation. Public product images may be served read-only from a documented static `/uploads` path in this MVP; upload/replace remains ADMIN-only. The application returns a safe missing-image/not-found result if a referenced file is absent and never exposes host paths.

**SMTP runtime policy — P1:** P0 starts and operates without SMTP credentials. If P1 email is selected, missing SMTP settings disable delivery with one safe configuration warning. Each event record commits atomically with its associated business state; after commit, the modular monolith attempts delivery from that record. On restart it scans eligible `PENDING` events; a `SENDING` event becomes eligible after the documented timeout/lease. Conditional status updates claim one event at a time and retries are bounded/configurable. Failure never reverses registration, order, payment, inventory, history, or API responses. The design cannot guarantee exactly-once SMTP delivery if the process crashes after provider acceptance but before `SENT` is stored.

## 7. API, security, and non-functional requirements

The proposed base path is `/api/v1`, resource names are plural, and REST methods use documented 200/201/204 and safe 4xx/5xx behavior. Bearer access tokens protect protected endpoints. Detailed endpoint schemas and error code map belong in planned API design.

| Area | Requirement and verification |
|---|---|
| Security | Verify JWT signature/type/expiry, role and ownership guards, bcrypt/equivalent hashes, DTO allowlisting, ORM parameterization, safe uploads, and secret-free responses/logs through review and automated tests. |
| Transaction integrity | Checkout, reservation/release, and Admin stock adjustment use transactions and appropriate locks/conditional updates. Test successful, insufficient-stock, rollback, adjustment, and concurrency-oriented cases. |
| Payment resilience | Persist and idempotently process callbacks; verify signed provider data and log safe diagnostics. Test duplicate, invalid, mismatch, success, late, and failure callbacks using fixtures/mocks. |
| Email resilience — P1 | If selected, business state and a unique notification event commit together; delivery happens after commit from the persisted event. Conditional status updates make retries safe, but SMTP is not exactly-once across a post-acceptance process crash. Failures do not undo business state. Test with a mock mailer. |
| Performance | Target p95 server-side duration under 500 ms for the documented local `GET /products?offset=0&limit=20&sort=name` scenario against 1,000 active seeded products, excluding client/network time. Measure server-side request duration across at least 30 sequential local requests and record the observed p95 in implementation/test documentation. This is a target to measure, not a benchmark claim. |
| Logging/errors | Use structured contextual logs without passwords, tokens, signing secrets, raw payment payloads containing sensitive data, SQL internals, or stack traces in responses. |
| Configuration | P0 database/JWT/VNPay/upload/expiry settings come from environment variables. P1 SMTP settings are documented only when email is selected. Sample env lists names only; secrets are uncommitted. Sandbox and production configuration remain distinct. |
| Maintainability/testability | Feature modules, DTOs, entities, guards, services, configuration, and tests have focused responsibilities. The project MUST expose `npm run test:cov`; it runs Jest and reports statement, branch, function, and line coverage at or above 70% for configured application source (`src/**` service, guard, controller, DTO-validation, and utility files), excluding generated/bootstrap-only files only through documented Jest configuration. Coverage does not prove correctness: critical auth replay/concurrency, ownership, role audit, checkout/stock contention and rollback, payment-initiation contention, duplicate/late callback, expiration race, scheduler, and inventory-adjustment tests remain required. P1 email tests apply only if P1 email is selected. |
| PostgreSQL integration tests | A small P0 Jest integration suite uses a real PostgreSQL instance through Docker Compose or equivalent reproducible setup, without production credentials or real VNPay transactions. It verifies final-stock checkout contention, single-winner refresh rotation, settlement/cancellation-or-expiry race, duplicate callbacks and one-success constraint, one-pending initiation constraint, checkout rollback, and adjustment/checkout race. |
| Documentation/reproducibility | Swagger is complete; README documents setup, commands, configuration, Docker Compose, migrations/init, and conventions. Verify from a clean checkout. |

## 8. Use cases

| ID | Actor | Outcome / failure handling |
|---|---|---|
| UC-AUTH-001–004 | Guest/customer | Register, log in, refresh, and logout with generic invalid-credential handling and revocable refresh sessions; existing stateless access JWTs may remain valid until configured expiry after logout/password change. |
| UC-PROFILE-001 | Customer | View own profile without modifying it. |
| UC-PROFILE-002 | Customer | Change password after current-password verification; sessions revoke. |
| UC-PROFILE-003 | Customer | Update own allowlisted profile fields; protected fields are rejected/ignored. |
| UC-PROD-001–002 | Guest/Admin | Browse active catalog; ADMIN creates/updates validated catalog data and performs audited, non-negative stock adjustments. |
| UC-UPLOAD-001 | Admin | Upload allowed product image; type/size/role errors reject safely. |
| UC-ORDER-001–002 | Customer | Submit a server-priced stock-safe order with inline recipient/contact/address details saved into the order, view only own history, and cancel only while still pending payment. |
| UC-STAFF-001 | Staff/Admin | Inspect eligible orders and make a valid fulfillment transition; payment state cannot be changed. |
| UC-ADMIN-001 | Admin | Assign role through dedicated operation and atomically record actor, affected user, old/new role, and timestamp; public/profile flows cannot assign roles. |
| UC-ADMIN-002 | Admin | Submit a reasoned stock delta; lock product state, reject negative outcome, and atomically write inventory-adjustment audit. |
| UC-PAY-001 | Customer | Initiate/reuse one eligible pending VNPay attempt from persisted amount; after genuine attempt failure/expiry, start a replacement while order reservation remains valid. |
| UC-PAY-002 | VNPay Sandbox | Verify IPN, settle exactly once, and record result. |
| UC-PAY-003 | VNPay Sandbox | Duplicate callback returns safe idempotent handling with no repeated business effects. |
| UC-EMAIL-001 — P1 | System/SMTP | Commit unique notification event with the business state, then attempt delivery; SMTP failure is recorded and does not reverse business state. |
| UC-ORDER-003 | System | Periodically expire still-pending unpaid orders and release inventory exactly once. |

## 9. Approved policies and remaining implementation verification

| Item | Decision / mitigation |
|---|---|
| VNPay specification changes | Verify official Sandbox documentation before implementation; do not copy assumed field/signature details. |
| Order expiry | Approved 2026-10-29: configurable 60-minute reservation/order expiry with the minimal P0 in-process scheduler; release stock exactly once. A late success is reconciled manually, never automatically settled. |
| Attempt expiry | Approved 2026-10-29: configurable 20-minute target for application attempt expiry; it retains stock. Safe terminalization remains conditional on verified VNPay integration rules; elapsed local time alone is not proof of provider finality. It does not assert universal provider URL expiry. |
| Payment URL reuse | Approved 2026-10-29: reuse the existing pending-attempt URL only when safely valid; otherwise return a documented conflict without creating another pending attempt. Official documentation and Sandbox integration tests must establish the validity predicate. |
| Staff permissions | Approved 2026-10-29: all STAFF share one fulfillment permission set: eligible queue/detail/history reads and PAID → PROCESSING → SHIPPED → COMPLETED transitions. No price, stock, role, payment-success or reconciliation-edit permission. |
| Email availability | Approved 2026-10-29: defer email to P1; it is not selected for the mandatory MVP. P0 has no SMTP/runtime, persistence, or email-test dependency. Future P1 activation must define events/retry/lease settings; business commits remain valid on delivery failure. |
| SMTP delivery semantics — P1 | Notification events are durably deduplicated, but exactly-once provider delivery is not achievable without provider-side idempotency: a crash after provider acceptance may cause a repeat on recovery. |
| Paid cancellation | Paid/processing/shipped/completed orders are not cancellable in the MVP because refunds are out of scope. |
| Scope | Finish P0 traceability/acceptance first; defer categories/cart/advanced filtering/retries rather than weakening payment verification or authorization. |

## 10. Traceability matrix

| Requirement(s) | Verification approach | Priority |
|---|---|---|
| FR-AUTH-001–005, FR-USER-001–004 | Auth/service/guard tests for credentials, concurrent one-winner rotation, consumed-token replay family revocation, logout/password-change ordinary revocation, configured access-token expiry behavior, roles, ownership, session revocation, and atomic role-change audit persistence; Swagger/manual flow | P0 |
| FR-PROFILE-001–003 | DTO/service/controller tests for separate profile read/update, ownership, protected fields, and password verification | P0 |
| FR-PROD-001–005, FR-UPLOAD-001, FR-INVENTORY-001–002 | Catalog/upload tests for initial-stock-only product creation, forbidden direct stock update, VND integer validation, orphan-file cleanup, stock-adjustment role/reason/negative checks/audit; checkout transaction, rollback, and adjustment concurrency tests | P0 |
| FR-ORDER-001–005 | Tests for required/invalid inline recipient/contact/address input, order-local shipping snapshots independent of profile changes, VND line/order total and snapshots, foreign access, basic queue, status-history persistence, permitted/rejected transitions, pre-payment-only cancellation, and payment/order separation | P0 |
| FR-PAY-001–005 | Provider fixtures/mocks for initiation reuse/conflict, one-pending concurrent initiation, failed/attempt-expired-then-new attempt, 20-minute attempt expiry retaining reservation, 60-minute order expiry releasing once, VND amount mismatch, signature/amount/currency/reference checks, duplicate/concurrent/late/invalid/success IPNs, cancellation/order-expiry race serialization, startup recovery, and atomic release-on-expiry | P0 |
| FR-EMAIL-001–003 | Mock-mailer tests for in-transaction event creation, post-commit send, recipient source, durable event-key duplicate prevention across restart simulation, delivery status/retry eligibility, disabled SMTP, and timeout/failure behavior | P1 |
| FR-API-001–003, FR-HEALTH-001 | Exception/DTO tests, Swagger audit, health check, clean Compose verification | P0 |
| FR-CAT-001, FR-CART-001 | CRUD/ownership tests if selected | P1 |
| NFR coverage/docs/containerization | Jest report >=70%; lint/build; clean Docker Compose + README/env review | P0 |

## 11. Planned artifact references

The completed sequence set is indexed in [../diagrams/sequence/README.md](../diagrams/sequence/README.md). Other listed artifacts remain planned unless present; independently triggered use cases use separate PlantUML files.

| Artifact | Relative path |
|---|---|
| Diagram inventory | [../diagrams/README.md](../diagrams/README.md) |
| Use-case diagram | `../diagrams/use-case.puml` |
| Product browsing flow | `../diagrams/product-browsing-flow.puml` |
| Order submission flow | `../diagrams/order-submission-flow.puml` |
| Authentication/refresh sequence | `../diagrams/auth-token-refresh-sequence.puml` |
| Profile view sequence | `../diagrams/sequence/SEQ-05-view-profile.puml` |
| Profile update sequence | `../diagrams/sequence/SEQ-06-update-profile.puml` |
| VNPay initiation and IPN sequence | `../diagrams/vnpay-payment-ipn-sequence.puml` |
| Order/payment/inventory state machine | `../diagrams/order-payment-inventory-state-machine.puml` |
| Email notification sequence — P1 | `../diagrams/email-notification-sequence.puml` |
| Staff order-processing sequence | `../diagrams/staff-order-processing-sequence.puml` |
| System architecture | `../diagrams/system-architecture.puml` |
| Database ERD | `../diagrams/database-erd.puml` |
| API design | `02-api-design.md` |
| Database design | `03-database-design.md` |
| Implementation plan | `04-implementation-plan.md` |

## 12. Revision change log

| Version | Change | Rationale |
|---|---|---|
| 0.9 | Approved configurable 60-minute order reservation, a 20-minute attempt-expiry target subject to safe VNPay integration rules, safe-URL-reuse/otherwise-conflict policy, one shared STAFF fulfillment permission set, and deferral of email to P1. | Record project-owner decisions of 2026-10-29; technical verification is not implementation evidence. |
| 0.5 | Moved SMTP, notification events/delivery records, deduplication, retries, tests, and email diagram to P1. | Keep the mandatory 2–3-week payment/order MVP operational without SMTP credentials or email infrastructure. |
| 0.5 | Defined conditional cancellation/expiration stock release and one-winner IPN/cancellation/expiry serialization. | Prevent double release, late settlement, and duplicate business effects. |
| 0.5 | Added canonical order, payment-attempt, refresh-token, and P1 notification enum values. | Provide one source of truth for database, API, and diagram design. |
| 0.5 | Strengthened IPN validation, payment-attempt database integrity, refresh concurrency, and Jest coverage command/scope. | Make detailed design and testing requirements implementable and auditable. |
| 0.6 | Added one-pending-attempt invariant, PostgreSQL partial-unique constraint requirement, initiation API behavior, and late-callback reconciliation details. | Prevent concurrent duplicate payment initiation and unsafe settlement while preserving retry after genuine terminal attempts. |
| 0.6 | Standardized VND integer monetary rules and added audited Admin stock adjustment. | Remove monetary ambiguity and align the existing Admin inventory responsibility with atomic, testable controls. |
| 0.6 | Distinguished consumed-token replay from logout/password-change revocation; added PostgreSQL integration-test, upload-cleanup, address-default, email-recovery, and performance-verification requirements. | Close critical concurrency/recovery gaps before detailed database and API design. |
| 0.7 | Restricted post-creation administrative stock changes to audited delta adjustment; product creation alone accepts initial stock. | Prevent general product updates from bypassing inventory auditability. |
| 0.7 | Split intended configurable attempt expiry (approximately 20 minutes, pending VNPay verification) from the configurable 60-minute order reservation expiry. | Allow safe replacement attempts without releasing an eligible order’s reservation while retaining exactly-once release on order termination. |
| 0.7 | Clarified refresh-token metadata/status use, stateless access-JWT behavior, default-address deletion, and related tests/traceability. | Remove lifecycle ambiguity without expanding the MVP architecture or authorization scope. |
| 0.8 | Removed the separate address-book/default-address scope (retiring FR-ADDRESS-001–002 and UC-ADDRESS-001); checkout now validates inline recipient, phone and delivery-address input and stores it directly on each order. Split profile viewing (FR-PROFILE-001 / UC-PROFILE-001) from updating (FR-PROFILE-003 / UC-PROFILE-003), preserving password-change IDs. | Apply the requested simpler checkout scope and keep independently meaningful profile operations separate. Earlier address-related change-log entries describe superseded versions. |

## 13. Pre-design consistency checklist

| Check | Result |
|---|---|
| P0/P1 priorities | P0 contains no SMTP, event-record, or email-test dependency; all email scope is P1. |
| Canonical state enums | Defined in section 5.7; one pending and one successful payment attempt per order are required; `NEW` is not an order status. |
| Currency | VND-only integer snapshots/calculations apply to products, orders, payments, DTOs, APIs, logs, and tests; multi-currency/fees/taxes/discounts are excluded. |
| Entities and integrity | P0 supports orders, attempts, history, role/inventory audits, stock, and refresh family rules; `notification_deliveries` is P1. |
| API scope | P0 includes separate profile view/update, checkout with inline shipping details, auth, pending cancellation, payment initiation reuse/conflict, staff processing, IPN, and audited stock adjustment; there are no address-book/default-address or email endpoints. |
| Acceptance and traceability | P0 traces cover auth concurrency, checkout/adjustment contention and rollback, one-pending initiation, callback/expiration races, audit, real-PostgreSQL integration checks, and coverage; email trace is P1. |
| Sequence diagrams | 32 separate business-use-case diagrams are present under `docs/diagrams/sequence/`; optional email is marked P1. Other diagram/design artifacts remain planned. |
| Inventory update policy | Initial stock is set only at product creation; later Admin changes use audited deltas, while checkout/cancellation/order-expiry changes remain system-managed. |
| Expiry lifecycle | Attempt expiry retains a pending eligible order’s reservation; 60-minute order expiry releases it once and expires remaining attempts. |
| Authentication lifecycle | Refresh status remains `ACTIVE`/`REVOKED`/`EXPIRED`; consumption/revocation metadata distinguishes replay. Access JWTs remain stateless until configured expiry. |
