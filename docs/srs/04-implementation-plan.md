# E-commerce Backend API — Implementation Plan

- Prepared: 2 November 2026
- Baseline: SRS v0.9 and the MVP decisions approved on 29 October 2026
- Status: Days 1–3 verified; M1 foundation gate passed. Sandbox access/payment acceptance remains open. See [implementation progress](implementation-progress.md) for actual evidence. Day 4 onward remains planned.

## 1. Objective and scope

Deliver the mandatory P0 NestJS backend as a modular monolith using TypeScript, TypeORM and PostgreSQL. The plan targets **15 working days (approximately three weeks)** for one developer, subject to experience and VNPay Sandbox access. Day numbers represent effort estimates, not committed calendar dates. Resolve integration blockers early and update this plan when actual effort differs.

P0 includes authentication, profile/password operations, RBAC and ownership, public catalog and Admin product/image operations, audited role/stock changes, direct checkout, order history and fulfillment, VNPay Sandbox payments, expiration jobs, health, Swagger, Docker Compose and required testing/documentation.

P1 categories, carts, email and advanced reports/filters remain deferred until P0 acceptance. Checkout works without a cart or saved address. Production payments, refunds, Redis, brokers and microservices remain outside scope.

## 2. Inputs and implementation rules

- [SRS and acceptance criteria](01-project-overview-srs.md).
- [Approved MVP policies](decisions-2026-10-29.md).
- [Architecture and module responsibilities](../diagrams/architecture/README.md).
- [Database design](../database/database-design.md), [SQL baseline](../database/schema.sql) and [DBML](../database/database.dbml).
- [32 sequence diagrams and requirement mappings](../diagrams/sequence/README.md).

The existing SQL is a design artifact, not an applied migration. Review its constraints and translate them into reproducible TypeORM migrations; do not execute it blindly against an existing database. Disable schema synchronization outside disposable experiments.

Use feature modules: Auth, Users, Products, Inventory, Orders, Payments, ExpirationScheduler and Health. Shared configuration, guards, validation, errors and response handling remain in-process infrastructure. Keep transaction boundaries in domain operations; repositories participating in one operation use the same transaction manager.

Money is integer VND. Define a consistent decimal-string/BigInt API and calculation policy before implementing checkout. Reject fractional, unsafe, overflowing and out-of-range values before database casting. Access JWTs remain stateless until expiry; do not add per-request session lookups or token-version infrastructure.

## 3. Milestones and completion gates

| Milestone | Target | Deliverables | Completion gate |
|---|---|---|---|
| M1 — Runnable foundation | Days 1–3 | NestJS scaffold, configuration, Compose, migrations, seed, health, common API behavior and preliminary contracts | A clean environment can start the API/database, apply migrations and run a smoke test. |
| M2 — Accounts and catalog | Days 4–7 | Auth/session lifecycle, RBAC, ownership, profiles, role audit, catalog, uploads and audited inventory adjustment | Auth/ownership/audit and catalog/upload tests pass; no secret fields leak. |
| M3 — Stock-safe orders | Days 8–10 | Transactional checkout, customer order reads/cancellation, Staff queue/details/transitions/history | Real PostgreSQL tests prove no overselling, partial checkout or double stock release. |
| M4 — Payments and expiration | Days 11–13 | Signed URL initiation/reuse/conflict, verified IPN, return, reconciliation and startup/periodic expiration | One-pending/one-success constraints and callback/cancellation/expiry races pass; Sandbox behavior is verified or explicitly blocks payment acceptance. |
| M5 — Accepted P0 delivery | Days 14–15 | Complete tests, coverage, performance measurement, Swagger, README, clean Compose verification and demo | All P0 acceptance criteria have evidence; documented limitations are explicit. |

Dependencies: M1 → M2 → M3 → M4 → M5. Start the provider investigation on Day 1 rather than waiting for M4. Write tests alongside each feature; Days 14–15 consolidate evidence and repair defects.

## 4. Detailed execution schedule

### Day 1 — Bootstrap and integration access

- [x] Initialize the NestJS application at the repository root while preserving `docs/`, the root README and Git configuration; generate in a temporary folder if scaffolding would overwrite them.
- [x] Select supported Node.js/package versions at implementation time; prepare a commit-ready lockfile and document the runtime version (no automatic commit).
- [x] Configure lint, formatting, build, Jest and scripts for unit/integration tests and coverage. The integration command explicitly reports unavailable setup; no integration pass is claimed.
- [x] Introduce validated environment configuration and a secret-free `.env.example`.
- [ ] Request/configure VNPay Sandbox merchant credentials and an accessible test IPN callback URL. Keep credentials and signed payment URLs out of Git/logs.
- [x] Begin provider verification: merchant/API version, signature/encoding, amount conversion, result/acknowledgement mapping, URL reuse and safe expiry/finality. [Documentation findings](../integrations/vnpay-verification.md) are recorded; Sandbox verification is still open.

**Output:** runnable scaffold and a documented integration checklist with unresolved technical questions.

### Day 2 — PostgreSQL, migrations and development environment

- [x] Create Docker Compose for the API and PostgreSQL, database readiness handling and persistent database/upload volumes.
- [x] Map the ten P0 entities from the proposed database design; create migrations for tables, foreign keys, checks, generated values and partial unique indexes.
- [x] Verify migration up/down behavior in a disposable database and initialize from an empty database.
- [x] Add a repeatable development seed. Create the initial Admin through a controlled seed/setup command with external configuration, never public registration or hardcoded credentials.
- [x] Add a separate disposable PostgreSQL test setup with no production credentials.

**Output:** reproducible schema and development/test setup. An empty checkout can migrate and seed successfully.

### Day 3 — API foundation and contracts

- [x] Set up `/api/v1`, DTO transformation/allowlisting, safe exception mapping and common success/error envelopes.
- [x] Write `02-api-design.md` beside this plan, specifying routes, roles/ownership, pagination, filters, shipping inputs, bigint representation, expected errors and upload behavior.
- [x] Define token transport/logout behavior and protected-field reject/ignore behavior explicitly.
- [x] Add Swagger/OpenAPI security and schema foundations, lightweight public health, structured logging and correlation IDs.
- [x] Specify the lock acquisition order and shared transaction conventions for refresh, checkout, payment and expiration flows.

**Requirements:** FR-API-001–003, FR-HEALTH-001 and foundations for all protected routes.

### Day 4 — Registration, login and refresh lifecycle

- [x] Implement normalized unique email, secure password hashing and CUSTOMER-only public registration.
- [x] Implement active-account login with generic invalid-credential errors and configurable access/refresh lifetimes.
- [x] Store refresh hashes, family, status, expiry and consumption/revocation metadata.
- [x] Implement atomic single-winner rotation and consumed-token replay detection with family revocation.
- [x] Test duplicate registration, inactive/invalid login, expired tokens, concurrent rotation and consumed-token replay against the relevant persistence rules.

**Requirements:** FR-AUTH-001–003, FR-AUTH-005, FR-USER-001.

### Day 5 — Authorization, profile, logout and role audit

- [x] Implement JWT authentication and role guards, and domain-level ownership checks.
- [x] Implement idempotent family logout, separate own-profile read/update and password change with atomic revocation of all refresh families.
- [x] Distinguish logout/password-change revocation from rotation replay; document access-JWT validity until expiry.
- [x] Add dedicated Admin role listing/change operations with atomic role-change audit.
- [x] Test unauthorized roles, foreign access, protected-field mass assignment, password verification and audit rollback. Verify public registration/profile cannot grant Admin.

**Requirements:** FR-AUTH-004–005, FR-USER-001–004, FR-PROFILE-001–003; SEQ-01–07, 14, 32 collectively cover the account scope.

### Day 6 — Product catalog

- [x] Implement active-only public product list/detail, allowlisted search/filter/sort and validated offset pagination with deterministic tie-breaking.
- [x] Add Admin product creation with positive integer-VND price and initial nonnegative integer stock.
- [x] Add allowlisted product updates that cannot directly modify stock.
- [x] Test inactive/missing product visibility, query bounds, deterministic ordering, monetary validation and role/mass-assignment rejection.

**Requirements:** FR-PROD-001–005; SEQ-08–11.

### Day 7 — Images and audited stock adjustment

- [x] Implement Admin-only Multer uploads for configured JPEG/PNG/WebP up to 5 MiB, server-generated filenames and safe path handling.
- [x] Store relative references, serve images safely and attempt orphan cleanup if database persistence fails. Log cleanup failures without host-path/secret disclosure to clients.
- [x] Implement signed integer stock deltas with required reason, transaction/locking, nonnegative-result checks and atomic inventory audit.
- [x] Test invalid/oversize files, missing files, failed storage/database writes, cleanup and stock-adjustment audit/rollback.

**Requirements:** FR-UPLOAD-001, FR-INVENTORY-001–002; SEQ-12–13.

### Day 8 — Transactional checkout

- [x] Accept nonempty product IDs/quantities and inline recipient, phone and shipping details; validate limits and duplicate-product policy.
- [x] Reload and lock products in a consistent order, reject inactive/insufficient stock and calculate totals using server data.
- [x] Atomically create the PENDING_PAYMENT order, immutable item/shipping snapshots, initial SYSTEM history and stock reservation.
- [x] Persist the configurable reservation deadline, default 60 minutes. Checkout does not require a cart/address record.
- [x] Test shipping validation, server price authority, snapshot independence, overflow, rollback and concurrent purchases of the last available item.

**Requirements:** FR-ORDER-001, FR-ORDER-005, FR-INVENTORY-001, FR-PAY-005; SEQ-15.

### Day 9 — Customer order history and cancellation

- [ ] Implement own-order list/detail/history with documented pagination and payment summaries.
- [ ] Implement owner cancellation only while still eligible and pending payment.
- [ ] In one serialized transaction, expire pending attempts, write history and release stock only when the conditional cancellation transition succeeds.
- [ ] Test foreign reads/mutations, cancellation after payment/expiry, repeated cancellation, rollback and release-once behavior.

**Requirements:** FR-ORDER-002, FR-ORDER-005, FR-USER-003, FR-INVENTORY-001; SEQ-16–18.

### Day 10 — Staff fulfillment and order contention tests

- [ ] Implement the shared STAFF/ADMIN queue, eligible order detail and history reads.
- [ ] Permit only PAID → PROCESSING → SHIPPED → COMPLETED transitions, with atomic history.
- [ ] Deny skipped/backward/terminal transitions and payment-state edits.
- [ ] Complete real-PostgreSQL checkout/adjustment contention and checkout rollback tests.

**Requirements:** FR-ORDER-003–005, FR-USER-002; SEQ-19–21.

### Day 11 — VNPay adapter and payment initiation

- [ ] Turn the Day 1 documentation investigation into verified signature/encoding fixtures and configured Sandbox adapter behavior; run actual Sandbox checks when credentials are available.
- [ ] Initiate only for eligible owned pending orders, using persisted integer-VND totals and a unique attempt reference.
- [ ] Enforce at most one pending attempt with transaction/locking and a PostgreSQL partial unique index.
- [ ] Reuse an existing URL only when safely valid; otherwise return the documented conflict without creating a second pending attempt.
- [ ] Persist the configurable 20-minute target deadline. A new attempt requires a genuinely failed/expired predecessor and an eligible order.
- [ ] Test unauthorized/ineligible initiation, signing/configuration failure, concurrent initiation and failed/expired-then-replacement behavior.

**Requirements:** FR-PAY-001–002, FR-PAY-004; SEQ-22.

### Day 12 — Verified callbacks, browser return and reconciliation

- [ ] Verify provider signature and validate merchant/reference, amount/currency and applicable transaction/result fields against persisted data.
- [ ] Serialize settlement with cancellation/expiry; atomically set SUCCESS/PAID and write history without another stock decrement.
- [ ] Persist safe IPN receipts for accepted, failed, duplicate, invalid, unknown, late and conflicting cases; implement appropriate acknowledgements.
- [ ] Implement the non-settling browser-return boundary and read-only Admin reconciliation inspection.
- [ ] Test one-success constraints, repeated/concurrent callbacks, mismatches, unknown/late receipts and cancellation/settlement races with PostgreSQL.

**Requirements:** FR-PAY-003–004, FR-ORDER-005; SEQ-23–24, 27.

### Day 13 — Startup recovery and expiration

- [ ] Configure an in-process startup scan and periodic scan interval.
- [ ] Evaluate due attempts against verified safe expiry rules; attempt expiry retains order reservation. If finality is unresolved, keep PENDING and return conflict on replacement initiation.
- [ ] Atomically expire still-pending overdue orders, expire remaining pending attempts, record history and restore stock exactly once.
- [ ] Verify repeated scans, restart recovery, rollback and callback/expiry/cancellation races.
- [ ] Record Sandbox evidence for URL reuse/finality. Missing credentials or unresolved safe expiry blocks payment-integration acceptance; mocks alone cannot close that gate.

**Requirements:** FR-PAY-005, FR-INVENTORY-001, FR-ORDER-005; SEQ-25–26.

### Day 14 — Coverage, performance and security review

- [ ] Run unit and real-PostgreSQL integration suites; repair failures in auth concurrency, ownership, audits, stock and payment behavior first.
- [ ] Expose `npm run test:cov` and meet at least 70% statement, branch, function and line coverage over the required application source scope with documented exclusions.
- [ ] Seed 1,000 active products. Measure server-side duration for at least 30 sequential local product-list requests using the defined offset/limit/sort scenario; record observed p95 against the <500 ms target.
- [ ] Review logs/responses, DTO mass assignment, uploads, environment separation and secret handling.
- [ ] Add CI for dependency installation, lint/build, unit/coverage tests and PostgreSQL integration tests. Do not require real payment/SMTP credentials in CI.

**Output:** reproducible test/coverage/performance evidence; measured results are recorded only after execution.

### Day 15 — Clean setup and delivery

- [ ] Verify a clean clone can install, start Compose, migrate, seed and run checks using only documented setup.
- [ ] Complete Swagger for every P0 endpoint, schema, role, query, upload and expected error.
- [ ] Finish README/environment/migration instructions and the FR-to-test acceptance matrix.
- [ ] Demonstrate registration/login, product management, stock-safe checkout, payment confirmation, fulfillment and unpaid-order expiry.
- [ ] Review remaining defects and risks, including actual Sandbox evidence. Do not label P0 complete while a mandatory integration or transaction check is unresolved.
- [ ] Update the implementation status and project overview to match actual delivered behavior.

## 5. Required test evidence

| Area | Mandatory verification |
|---|---|
| Auth | Single-winner concurrent refresh; consumed-token replay revokes family; ordinary logout/password revocation; expiry and invalid credentials. |
| Authorization | Guest/Customer/Staff/Admin restrictions; own-record enforcement; profile/register cannot change role; atomic role audit. |
| Catalog/uploads | Active visibility, pagination validation, integer money, initial-stock-only creation, safe uploads and orphan cleanup. |
| Inventory/orders | Last-unit contention, no negative stock, checkout rollback, adjustment/checkout race, snapshots, transition history and release once. |
| Payments | Single pending and single success constraints, safe reuse/conflict, signature/amount/reference validation, duplicate/late callbacks and terminal-state protection. |
| Recovery | Startup scans, repeated scans and payment/cancellation/order-expiry serialization with no double release. |
| Delivery | Required coverage metrics, measured performance scenario, Swagger completeness and clean Compose setup. |

Use real PostgreSQL for concurrency and constraint checks. Use fixtures/mocks for repeatable provider behavior, alongside separate Sandbox integration evidence. SQLite or mocked repositories cannot establish PostgreSQL locking/index correctness.

## 6. Risks and adjustments

| Risk | Action / effect on plan |
|---|---|
| VNPay access, callback reachability or provider semantics unresolved | Investigate from Day 1. Continue independent modules, but leave payment acceptance open until verified. |
| Transaction/concurrency defects | Prioritize correction before adding P1; retain the integrity requirements even if the schedule moves. |
| Scope exceeds 15 working days | Re-estimate from evidence and document a smaller compliant P0 implementation; defer P1 first. |
| Secrets or nonreproducible local setup | Environment validation, secret-free examples, ignored local credentials and clean-clone verification. |
| Monolith assumes one runtime instance | Document the single-instance scheduler scope; do not claim distributed recovery/locking. |

## 7. Git and GitHub workflow

The repository starts with documentation and this plan. No application milestone is complete merely because the initial Git commit exists.

Use short feature branches such as `feat/auth`, `feat/catalog`, `feat/orders` and `feat/payments`. Commit focused changes with Conventional Commits, for example `feat(auth): implement refresh rotation` or `test(orders): verify last-unit contention`.

Before pushing a feature: review the staged diff, check for secrets, run the relevant checks and update affected documentation. Never commit real `.env` files, signing secrets, private keys, credentials, dependencies, upload volumes or database data.

Create an **empty GitHub repository** (without an extra README, license or `.gitignore`), then run from this project directory:

```powershell
git remote add origin <GITHUB_REPOSITORY_URL>
git push -u origin main
```

Replace the placeholder with the actual HTTPS or SSH repository URL. The remote is intentionally not guessed. GitHub authentication is handled through the user's Git credential manager or SSH configuration.

## 8. P0 completion checklist

- [ ] M1–M5 acceptance gates have evidence.
- [ ] All mandatory FRs map to implementation and verification.
- [ ] Required PostgreSQL contention, rollback and recovery checks pass.
- [ ] VNPay Sandbox behavior and safe attempt-expiry/reuse policy are verified.
- [ ] All four coverage metrics meet the required threshold.
- [ ] The performance scenario is measured and its outcome documented.
- [ ] Clean Compose setup, migration/seed and Swagger are reproducible.
- [ ] Secrets are absent from source control and logs.
- [ ] Remaining limitations are explicit; P1 features remain optional.
