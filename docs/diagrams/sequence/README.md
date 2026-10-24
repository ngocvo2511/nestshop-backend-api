# E-commerce backend sequence diagrams

Source: [SRS v0.9, 2026-10-29](../../srs/01-project-overview-srs.md), especially sections 4–6, 8–10; [existing planned artifact inventory](../README.md). These are requirements models, not evidence of implemented endpoints. The workspace contains documentation and a proposed database design/ERD under `docs/database/`; it contains no application implementation or detailed API contract. The SRS and parent inventory reflect the current inline-checkout shipping scope.

## Inventory and modeling decisions

This inventory was prepared from the SRS before `.puml` generation. Numbering is local to this sequence set. FR identifiers are authoritative: several section-8 UC rows group multiple independent functions and do not assign an individual UC number to each. No new SRS IDs are invented.

Independently meaningful functions are split, including product list/detail/create/update, checkout/history/detail/cancellation, staff queue/detail/transition, payment initiation/IPN/browser return, and attempt/order expiry. Profile viewing and updating are separate diagrams with separate service methods. Viewing role assignments and changing a role are separate diagrams and service methods. P1 category CRUD and P1 cart management follow the SRS's grouped definitions. Shipping details are entered and stored during checkout; there is no separate address-management diagram. UC-PAY-003 duplicate callback is an IPN alternative rather than a redundant second diagram. History viewing belongs with the relevant customer/staff order detail; inventory release belongs with cancellation/expiry.

All protected flows verify access JWT signature/type/expiry, role and ownership where applicable (FR-USER-001–003). They use safe common responses and DTO allowlisting (FR-API-001–002); these apply across the set even where not repeated in the mapping column. IPN uses provider verification, refresh/logout use supplied refresh credentials, and public routes do not acquire invented bearer requirements. PostgreSQL interactions use TypeORM. No physical columns or undisclosed tables are asserted. No exact HTTP paths/error codes or VNPay field/encoding details are invented.

### Controller, service and activation notation

The revised diagrams follow the controller/service interaction style in the three reference diagrams under [examples](examples/). The references belong to a different frontend/microservice project; their frontend pages, gRPC, RabbitMQ, OTP and unrelated services are not copied into this architecture. The example files are unchanged.

- Each HTTP flow shows the actor calling a named NestJS controller, the controller calling a named domain service, and that service accessing PostgreSQL where relevant. Guard lifelines show access-token verification and role authorization for protected operations. Ownership checks remain in domain operations against persisted records.
- Controller/service **class and method names are proposed design names**, because no application source exists in this workspace. They name logical components within one NestJS process, not remote services or implemented contracts.
- The two expiration diagrams show application startup/timer → `ExpirationScheduler` → `PaymentsService` / `OrdersService`. They do not add an HTTP controller to a scheduled operation. The optional P1 email flow shows the originating `BusinessService` and `NotificationService`; `BusinessService` denotes whichever domain service performs the selected business transition, not a new generic runtime component.
- There is one PostgreSQL database, accessed using TypeORM. The database participant lists the actual SRS entities involved in that diagram; these are tables in the same database, not separate databases. The P1 email diagram's “business records” means the relevant existing users/order/payment/history records associated with its originating event.
- Explicit `activate` / `deactivate` pairs now include the user or external trigger, controllers, services, guards, database, local storage and SMTP. The caller's bar covers the request through its response. Services return to controllers before controllers respond to the caller; no domain service is called after failed controller-level authorization. Shared activations close after their enclosing alternative fragment so the bars remain visible across all alternatives.
- Each completed alternative contains its own concrete success or error response through the caller chain. Responses are not combined into a generic result after `alt`. Internal per-candidate branches in scheduler/recovery loops continue the scan and return the scan result when the loop finishes. Outcome labels describe the intended meaning, not finalized HTTP status codes or exact API message contracts.
- The artificial `Prepare result` self-calls are removed. Processing and response labels use short natural descriptions, such as `Generate access token and refresh token`, instead of detailed explanations. Function invocations retain method names and parameters; important canonical state names remain where needed. Transaction lifecycle messages and generic database-failure alternatives are omitted from this business view. Detailed policies and assumptions remain in this README and the SRS.
- In SEQ-01, `AuthController` calls `AuthService`, which delegates normalized-email lookup and customer creation to `UsersService`. `UsersService` queries PostgreSQL before account creation; the unique email constraint still handles concurrent registrations that pass the initial lookup. The initial lookup provides a clear duplicate-email path but cannot replace database uniqueness. In SEQ-07, `UsersService` delegates refresh-family revocation to `AuthService` using the same password-change transaction. These are local calls inside the modular monolith.
- Decorative `box` and `group` containers and all inline notes, including SRS/FR labels, have been removed. Traceability and unresolved decisions remain in this README. Standard UML `alt`, `opt` and `loop` fragments remain to represent alternatives, optional work and iteration. Messages are automatically numbered.

| Diagrams | Entry component | Domain service |
|---|---|---|
| SEQ-01 | `AuthController` | `AuthService → UsersService` |
| SEQ-02 | `AuthController` | `AuthService` |
| SEQ-03 | `AuthController` | `AuthService` |
| SEQ-04 | `AuthController` | `AuthService` |
| SEQ-05 | `UsersController` | `UsersService` |
| SEQ-06 | `UsersController` | `UsersService` |
| SEQ-07 | `UsersController` | `UsersService → AuthService` |
| SEQ-08 | `ProductsController` | `ProductsService` |
| SEQ-09 | `ProductsController` | `ProductsService` |
| SEQ-10 | `ProductsController` | `ProductsService` |
| SEQ-11 | `ProductsController` | `ProductsService` |
| SEQ-12 | `ProductsController` | `ProductImagesService` |
| SEQ-13 | `InventoryController` | `InventoryService` |
| SEQ-14 | `UsersController` | `RolesService` |
| SEQ-15 | `OrdersController` | `OrdersService` |
| SEQ-16 | `OrdersController` | `OrdersService` |
| SEQ-17 | `OrdersController` | `OrdersService` |
| SEQ-18 | `OrdersController` | `OrdersService` |
| SEQ-19 | `StaffOrdersController` | `OrdersService` |
| SEQ-20 | `StaffOrdersController` | `OrdersService` |
| SEQ-21 | `StaffOrdersController` | `OrdersService` |
| SEQ-22 | `PaymentsController` | `PaymentsService` |
| SEQ-23 | `PaymentsController` | `PaymentsService` |
| SEQ-24 | `PaymentsController` | `PaymentsService` |
| SEQ-25 | `ExpirationScheduler` | `PaymentsService` |
| SEQ-26 | `ExpirationScheduler` | `OrdersService` |
| SEQ-27 | `PaymentsController` | `PaymentsService` |
| SEQ-28 | `HealthController` | `HealthService` |
| SEQ-29 | `CategoriesController` | `CategoriesService` |
| SEQ-30 | `CartsController` | `CartsService` |
| SEQ-31 | `Originating business service / recovery trigger` | `NotificationService` |
| SEQ-32 | `UsersController` | `RolesService` |

P1 diagrams document optional capabilities without selecting them for implementation. SEQ-31 includes notification-event creation atomically with the originating business change; this conditional P1 overlay applies to the relevant P0 flows only if email is selected. P0 has no email dependency.

### Transaction detail retained in the design

These diagrams focus on business interactions. Starting, committing and rolling back database transactions, along with generic persistence errors, belong to implementation design and tests rather than repeated sequence fragments. Business alternatives remain explicit: duplicate email, invalid credentials, ownership/role rejection, insufficient stock, invalid state transitions, pending-attempt conflict, duplicate/late/mismatched IPNs and safe expiry eligibility. Upload orphan cleanup and an email accepted by SMTP but not recorded as sent remain explicit because they have specific recovery consequences.

The SRS transaction rules still apply. Refresh rotation and family revocation are atomic; password change and refresh-family revocation succeed together. Checkout creates the order, snapshots and history with the stock reservation as one operation. Stock/role changes include their audit records. IPN settlement, fulfillment, cancellation and order expiry include the required history and inventory effects in the same transaction, with cancellation/IPN/expiry races serialized. Failed writes retain no partial business effects. P1 business state and its unique notification event persist together, and delivery starts only after they commit. The diagrams describe these coupled effects briefly rather than showing transaction commands or an extra database-failure branch for each operation.

| ID / file | Business use case | SRS mapping | Main actor / trigger | Scope and important alternatives | Ambiguity |
|---|---|---|---|---|---|
| [SEQ-01](SEQ-01-register.puml) `SEQ-01-register.puml` · [SVG](rendered/SEQ-01-register.svg) | Register account | FR-AUTH-001; FR-API-001–002; UC-AUTH-001 | Guest | Register; validation and duplicate email | None beyond shared open decisions. |
| [SEQ-02](SEQ-02-login.puml) `SEQ-02-login.puml` · [SVG](rendered/SEQ-02-login.svg) | Login | FR-AUTH-002, FR-AUTH-005; UC-AUTH-002 | Guest | Login; inactive account or invalid credentials | None beyond shared open decisions. |
| [SEQ-03](SEQ-03-refresh-token.puml) `SEQ-03-refresh-token.puml` · [SVG](rendered/SEQ-03-refresh-token.svg) | Refresh token | FR-AUTH-003, FR-AUTH-005; UC-AUTH-003 | Token holder | Atomic rotation; replay and ordinary revocation | None beyond shared open decisions. |
| [SEQ-04](SEQ-04-logout.puml) `SEQ-04-logout.puml` · [SVG](rendered/SEQ-04-logout.svg) | Logout | FR-AUTH-004–005; UC-AUTH-004 | Token holder | Logout; repeat/concurrent revocation | Exact logout credential transport and response contract are deferred to API design. |
| [SEQ-05](SEQ-05-view-profile.puml) `SEQ-05-view-profile.puml` · [SVG](rendered/SEQ-05-view-profile.svg) | View own profile | FR-PROFILE-001; FR-USER-001, FR-USER-003; UC-PROFILE-001 | Customer | Read only the authenticated user's profile | Avatar enablement is not fixed. |
| [SEQ-06](SEQ-06-update-profile.puml) `SEQ-06-update-profile.puml` · [SVG](rendered/SEQ-06-update-profile.svg) | Update own profile | FR-PROFILE-003; FR-USER-001, FR-USER-003; UC-PROFILE-003 | Customer | Update allowlisted profile fields; reject invalid/protected input | Avatar enablement and reject-versus-ignore policy for protected fields are not fixed. |
| [SEQ-07](SEQ-07-change-password.puml) `SEQ-07-change-password.puml` · [SVG](rendered/SEQ-07-change-password.svg) | Change password | FR-PROFILE-002; FR-AUTH-005; UC-PROFILE-002 | Customer | Current-password verification; revoke all families | None beyond shared open decisions. |
| [SEQ-08](SEQ-08-view-product-list.puml) `SEQ-08-view-product-list.puml` · [SVG](rendered/SEQ-08-view-product-list.svg) | View product list | FR-PROD-001–002; FR-API-002; UC-PROD-001 | Guest / Customer | Search, filter, sort, offset pagination | None beyond shared open decisions. |
| [SEQ-09](SEQ-09-view-product-details.puml) `SEQ-09-view-product-details.puml` · [SVG](rendered/SEQ-09-view-product-details.svg) | View product details | FR-PROD-003; UC-PROD-001 | Guest / Customer | Public product detail; missing/inactive | None beyond shared open decisions. |
| [SEQ-10](SEQ-10-create-product.puml) `SEQ-10-create-product.puml` · [SVG](rendered/SEQ-10-create-product.svg) | Create product | FR-PROD-004; FR-USER-002; UC-PROD-002 | Admin | Initial stock and integer-VND validation | None beyond shared open decisions. |
| [SEQ-11](SEQ-11-update-product.puml) `SEQ-11-update-product.puml` · [SVG](rendered/SEQ-11-update-product.svg) | Update product | FR-PROD-005; FR-USER-002; UC-PROD-002 | Admin | Allowlisted catalog update; direct stock forbidden | None beyond shared open decisions. |
| [SEQ-12](SEQ-12-upload-product-image.puml) `SEQ-12-upload-product-image.puml` · [SVG](rendered/SEQ-12-upload-product-image.svg) | Upload product image | FR-UPLOAD-001; FR-USER-002; UC-UPLOAD-001 | Admin | Multer validation, local storage and orphan cleanup | None beyond shared open decisions. |
| [SEQ-13](SEQ-13-adjust-product-stock.puml) `SEQ-13-adjust-product-stock.puml` · [SVG](rendered/SEQ-13-adjust-product-stock.svg) | Adjust product stock | FR-INVENTORY-001–002; FR-USER-002; UC-ADMIN-002 | Admin | Reasoned signed delta; negative stock and contention | None beyond shared open decisions. |
| [SEQ-14](SEQ-14-view-user-roles.puml) `SEQ-14-view-user-roles.puml` · [SVG](rendered/SEQ-14-view-user-roles.svg) | View user roles | FR-USER-004 | Admin | Read role assignments without changing users | Exact listing/filter contract remains an API-design detail. |
| [SEQ-15](SEQ-15-create-order.puml) `SEQ-15-create-order.puml` · [SVG](rendered/SEQ-15-create-order.svg) | Create order | FR-ORDER-001, FR-ORDER-005; FR-INVENTORY-001; FR-PAY-005; UC-ORDER-001 | Customer | Validate inline recipient/phone/address; calculate server totals, snapshot shipping details and reserve stock | Exact shipping-field limits, duplicate product-ID handling and quantity bounds remain API-design details. |
| [SEQ-16](SEQ-16-view-own-order-list.puml) `SEQ-16-view-own-order-list.puml` · [SVG](rendered/SEQ-16-view-own-order-list.svg) | View own order list | FR-ORDER-002; FR-USER-003; UC-ORDER-002 | Customer | Paginated own orders with documented filtering | Order pagination/filter parameters and response details are deferred to API design. |
| [SEQ-17](SEQ-17-view-own-order-details.puml) `SEQ-17-view-own-order-details.puml` · [SVG](rendered/SEQ-17-view-own-order-details.svg) | View own order details | FR-ORDER-002, FR-ORDER-005; FR-USER-003; UC-ORDER-002 | Customer | Owned detail, snapshots, payment state, status history | None beyond shared open decisions. |
| [SEQ-18](SEQ-18-cancel-order.puml) `SEQ-18-cancel-order.puml` · [SVG](rendered/SEQ-18-cancel-order.svg) | Cancel order | FR-ORDER-002, FR-ORDER-005; FR-INVENTORY-001; FR-PAY-005; SRS 5.7; UC-ORDER-001–002 | Customer | Pre-payment cancellation; settlement/expiry races | None beyond shared open decisions. |
| [SEQ-19](SEQ-19-view-order-list.puml) `SEQ-19-view-order-list.puml` · [SVG](rendered/SEQ-19-view-order-list.svg) | View order list (Staff/Admin) | FR-ORDER-003; FR-USER-002; UC-STAFF-001 | Staff / Admin | Minimal status-based queue; advanced filters deferred | One shared STAFF fulfillment permission set is approved; exact pagination remains an API-design detail and advanced filters are P1. |
| [SEQ-20](SEQ-20-view-order-details.puml) `SEQ-20-view-order-details.puml` · [SVG](rendered/SEQ-20-view-order-details.svg) | View order details (Staff/Admin) | FR-ORDER-003, FR-ORDER-005; FR-USER-002; UC-STAFF-001 | Staff / Admin | Eligible detail and status history | One shared STAFF fulfillment permission set is approved; implementation must enforce eligible-order scope. |
| [SEQ-21](SEQ-21-update-order-status.puml) `SEQ-21-update-order-status.puml` · [SVG](rendered/SEQ-21-update-order-status.svg) | Update order status | FR-ORDER-004–005; FR-USER-002; SRS 5.7; UC-STAFF-001 | Staff / Admin | Next permitted transition; reject skipped/backward/payment edits | None beyond shared open decisions. |
| [SEQ-22](SEQ-22-initiate-payment.puml) `SEQ-22-initiate-payment.puml` · [SVG](rendered/SEQ-22-initiate-payment.svg) | Initiate VNPay payment | FR-PAY-001–002, FR-PAY-004; UC-PAY-001 | Customer | Eligible owned order; one pending attempt, URL reuse/conflict | Official signature/encoding, URL validity/reuse and provider timeout semantics require integration verification. |
| [SEQ-23](SEQ-23-handle-vnpay-ipn.puml) `SEQ-23-handle-vnpay-ipn.puml` · [SVG](rendered/SEQ-23-handle-vnpay-ipn.svg) | Handle VNPay IPN | FR-PAY-003–005; FR-ORDER-005; SRS 5.7; UC-PAY-002–003 | VNPay Sandbox | Signature/data validation; success/failure, duplicate, late and conflicting results | Exact provider fields/codes/acknowledgement and record layout remain deferred; invalid data cannot settle. |
| [SEQ-24](SEQ-24-handle-payment-return.puml) `SEQ-24-handle-payment-return.puml` · [SVG](rendered/SEQ-24-handle-payment-return.svg) | Handle payment return | FR-PAY-003; SRS 5.9 | Customer browser | Non-authoritative browser return; no settlement | SRS requires a return endpoint but leaves redirect, response and display contract unspecified. |
| [SEQ-25](SEQ-25-expire-payment-attempt.puml) `SEQ-25-expire-payment-attempt.puml` · [SVG](rendered/SEQ-25-expire-payment-attempt.svg) | Expire payment attempt | FR-PAY-005; SRS 5.7; UC-PAY-001 expiry support | In-process scheduler | Startup/periodic attempt scan; unresolved provider finality | SRS mandates local expiry but conditions it on unverified provider rules; no finality-resolution mechanism is specified. |
| [SEQ-26](SEQ-26-expire-order-release-stock.puml) `SEQ-26-expire-order-release-stock.puml` · [SVG](rendered/SEQ-26-expire-order-release-stock.svg) | Expire order and release stock | FR-PAY-005; FR-ORDER-005; FR-INVENTORY-001; UC-ORDER-003 | In-process scheduler | Startup/periodic 60-minute expiry; release once and serialize with IPN | 60-minute configurable reservation and the P0 scheduler were approved on 2026-10-29. Scan interval is not specified. |
| [SEQ-27](SEQ-27-view-payment-reconciliation.puml) `SEQ-27-view-payment-reconciliation.puml` · [SVG](rendered/SEQ-27-view-payment-reconciliation.svg) | View payment reconciliation | FR-PAY-004; SRS 4 | Admin | Read-only attempt/reconciliation inspection | Inspection API/filter details are not yet defined; manual provider-resolution procedure is outside automated scope. |
| [SEQ-28](SEQ-28-health-check.puml) `SEQ-28-health-check.puml` · [SVG](rendered/SEQ-28-health-check.svg) | Check API health | FR-HEALTH-001; FR-API-001 | Health-check caller | Public lightweight health; no secret exposure | None beyond shared open decisions. |
| [SEQ-29](SEQ-29-manage-categories.puml) `SEQ-29-manage-categories.puml` · [SVG](rendered/SEQ-29-manage-categories.svg) | Manage categories (P1) | FR-CAT-001; SRS 4 | Guest / Admin | Approved P1 public active browsing and admin CRUD | P1 selection, category fields, hierarchy and referenced-category deletion policy are not defined. |
| [SEQ-30](SEQ-30-manage-cart.puml) `SEQ-30-manage-cart.puml` · [SVG](rendered/SEQ-30-manage-cart.svg) | Manage cart (P1) | FR-CART-001; FR-USER-003; SRS 5.3 | Customer | Own cart/items only; no price or stock reservation | P1 selection, precise cart operations and changed-price reject/adjust response policy are not defined. |
| [SEQ-31](SEQ-31-send-email-notification.puml) `SEQ-31-send-email-notification.puml` · [SVG](rendered/SEQ-31-send-email-notification.svg) | Send email notification (P1) | FR-EMAIL-001–003; UC-EMAIL-001 | Business event / startup recovery | Durable event, post-commit SMTP, bounded retry and crash recovery | P1 selection, selected fulfillment events, retry bounds and lease duration require configuration/design decisions. |
| [SEQ-32](SEQ-32-update-user-role.puml) `SEQ-32-update-user-role.puml` · [SVG](rendered/SEQ-32-update-user-role.svg) | Update user role | FR-USER-004; UC-ADMIN-001 | Admin | Validate target and role; change assignment with atomic audit | General account-management mutations beyond role assignment remain unspecified. |

## Unresolved decisions and consistency findings

1. **Attempt expiry/finality:** FR-PAY-005 calls for approximately 20-minute application expiry; section 5.7 conditions expiry on verified integration rules, while section 9 leaves provider behavior unverified. A local deadline alone does not establish provider finality. SEQ-25 explicitly retains the pending attempt when safe expiry is unresolved. Replacement is allowed only after genuine failure/expiry; this set invents no provider-query mechanism. The owner approved the 20-minute application target on 2026-10-29; provider finality and safe expiry remain integration-verification gates, not unresolved product choices.
2. **Order expiry:** model the requested configurable **60-minute** reservation policy separately from the intended configurable **approximately 20-minute** attempt deadline. Section 9 now records project-owner approval dated 2026-10-29. Safe terminal-order expiry follows the SRS even with unresolved external provider status: any later callback is recorded and never settles or changes stock automatically.
3. **VNPay contract:** signature algorithm, fields, encoding/canonicalization, amount conversion, success codes, IPN responses, URL validity and URL reuse require official Sandbox verification during implementation. This documentation task preserves those unknowns rather than introducing technical claims. Signed URL construction is local; only server IPN has a provider-to-backend interaction. Browser return has no settlement authority. No VNPay internal payment processing is modeled.
4. **Reconciliation:** invalid/late/conflicting callbacks are safely recorded, known references retain safe outcome details, and unknown callbacks use safe diagnostics. ADMIN inspection is read-only. Manual provider resolution is outside automated scope; no refund, annotation endpoint or settlement override is invented. Physical reconciliation persistence remains unspecified.
5. **Other deferred details:** allowlisted schema limits, exact endpoint contracts, logout credential transport, avatar enablement, profile reject/ignore behavior, order pagination/filtering, duplicate product-ID handling, scheduler interval and exact eligible-order query contracts are not settled. STAFF granularity is now one approved shared fulfillment set. General account-management operations beyond dedicated role assignments are mentioned in section 4 but lack sufficient acceptance criteria for additional diagrams.
6. **P1 policy:** category reference/deletion behavior, cart operation details and changed-price response policy, email activation/event selection/retry/lease settings require decisions. Email delivery failure never reverses accepted business changes; post-acceptance crashes can duplicate email.
7. **Existing diagram plan:** the parent inventory describes broad combined sequences and says all its artifacts are planned. This sequence set supersedes that granularity for this task only. The parent inventory links the current sequence set; its other artifact entries remain planned.

## Coverage and remaining work

All sufficiently specified P0 business functions are represented, including role-audit, stock-audit, browser return, cancellation, scheduler startup recovery, and health. FR-AUTH-001–005, FR-USER-001–004, FR-PROFILE-001–003, FR-PROD-001–005, FR-UPLOAD-001, FR-INVENTORY-001–002, FR-ORDER-001–005, FR-PAY-001–005 and FR-HEALTH-001 map to the inventory. Common FR-API-001–002 behavior is modeled throughout; diagrams do not establish implementation compliance.

No sufficiently defined SRS business use case is intentionally left without a diagram or an explicit alternative. UC-PAY-003 is covered within IPN processing. P1 FR-CAT-001, FR-CART-001 and FR-EMAIL-001–003 have high-level diagrams. P1 advanced staff reporting/exports/date/compound filters and advanced status-history filters remain **uncovered** because contracts are not sufficiently specified. They are not added to the P0 queue/detail flows.

P0 delivery/quality requirements are **not proven or replaced by sequence diagrams**: FR-API-003 complete Swagger, actual common-envelope/schema contracts, Docker Compose, README/environment/migrations, Conventional Commits, >=70% Jest coverage, real-PostgreSQL contention/race/rollback tests, secret handling review and the measured local performance target still require implementation and verification. P1 extra integration/email tests and SMTP configuration verification likewise remain implementation work. No dedicated diagrams are appropriate for these delivery checks.

## Scope update

SRS v0.8 removes the address-book and default-address use cases. Their two source/render files and the former combined-profile source/render were removed. After the role-management split, the set has **32 sequential diagrams**: SEQ-05 views the profile using `getProfile(userId)`, SEQ-06 updates it using `updateProfile(userId, dto)`, SEQ-07 changes the password, and SEQ-15 is checkout. IDs SEQ-01–31 retain their current meanings. SEQ-14 now only views role assignments, and the separate role-assignment flow is appended as SEQ-32. Use filenames and this inventory for current links.

Checkout accepts recipient name, contact phone and delivery address directly. The server validates these fields, calculates prices from current product data, and saves shipping details as an order-local snapshot with items, history and stock reservation. It reads no saved-address record. Customer/staff order-detail flows read the stored shipping snapshot; later profile changes do not alter it. Profile-view and profile-update requirements are FR-PROFILE-001 and FR-PROFILE-003 respectively; FR-PROFILE-002 remains password change. The retired address requirements are recorded only in SRS change history.

## Purpose of the queried flows

- **SEQ-14 / SEQ-32:** ADMIN reads user role assignments in SEQ-14 and changes a selected user's role in SEQ-32. The methods are `getRoleAssignments(query)` and `assignRole(actorId, userId, role)`; only a successful role change writes an audit.
- **SEQ-19:** STAFF/ADMIN lists the fulfillment queue by order status to find orders requiring attention (FR-ORDER-003).
- **SEQ-20:** STAFF/ADMIN reads one eligible order's items, order-local shipping details, payment summary and history for fulfillment (FR-ORDER-003, FR-ORDER-005).
- **SEQ-21:** STAFF/ADMIN advances the next permitted fulfillment status and records history: `PAID → PROCESSING → SHIPPED → COMPLETED`. It cannot set payment success (FR-ORDER-004–005).
- **SEQ-24:** handles the browser returning from VNPay. This is a public/provider return boundary, not a frontend implementation. It can provide a safe return outcome but cannot settle payment; SEQ-23 is the verified server IPN that may settle the order (FR-PAY-003; SRS 5.9). Exact return presentation remains unspecified.
- **SEQ-25 / SEQ-26:** startup recovery and the in-process timer trigger these independently of user requests. Attempt expiry is approximately 20 minutes under verified provider rules and retains the order reservation; unresolved provider finality does not force an attempt expired. Order expiry is 60 minutes and releases stock once while expiring pending attempts. These are required business workflows (FR-PAY-005, UC-ORDER-003), so both remain in the complete sequence set. Scheduler implementation mechanics are not modeled.

## Diagram naming

All diagram titles now use short action names such as `View product list`, `View order details` and `Update order status`. Filenames and inventory links match those names. Customer order views include “own”; staff order views include “Staff/Admin” in their titles. SEQ numbers and all interaction messages, conditions and activation statements are unchanged.

## Validation

Validated locally using PlantUML **1.2026.9** on 2026-10-28.

- After the title/filename cleanup, **32/32** sources passed local `-checkonly` syntax validation and rendered to SVG with exit code **0**. Each inventory row links the source and its current SVG.
- After splitting role management, all 32 sources were revalidated and rendered. Every source has one complete PlantUML block; sequential IDs, source/render counts and inventory links were checked. A branch-aware structural check passed for activation/deactivation and active message senders across every alternative and loop.
- The profile-view, profile-update and checkout PNG previews were visually inspected. The two role diagrams are checked separately after the latest split. They retain caller activation bars and branch-specific responses without generic transaction-management steps.
- Current diagrams contain no `getOrUpdateProfile`, saved-address lookup, address-management component or address-ID parameter. Retired source/render filenames and links were removed. The example files were left unchanged.
- Reviewed SRS v0.8 scope, actors, functional requirements, state-machine preconditions, entity inventory, API inventory and traceability against the updated checkout/profile flows. Address-related entries in the SRS revision history describe superseded versions only.

Reproduce from this directory with a local renderer:

```powershell
java -jar <path-to-plantuml.jar> -checkonly "*.puml"
java -jar <path-to-plantuml.jar> -tsvg -o rendered "*.puml"
```

No application tests were run: the workspace contains documentation only. The remaining design decisions and implementation verification obligations are listed above.

## Approved baseline update — 2026-10-29

SRS v0.9 and [the decision record](../../srs/decisions-2026-10-29.md) approve 60-minute order reservation, the configurable 20-minute attempt target with safe-expiry verification, URL reuse only when safely valid and conflict otherwise, shared STAFF fulfillment permissions, and email deferred to P1. SEQ-22 and SEQ-25 reflect these labels; other interaction structures remain applicable. Technical verification is still required before enabling replacement attempts. All 32 source files were re-rendered for the LaTeX overview; see its build manifest.
