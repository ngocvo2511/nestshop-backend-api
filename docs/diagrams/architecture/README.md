# E-commerce Backend API architecture

[architecture.dsl](architecture.dsl) describes the **required architecture**, not an implemented or deployed system. It is a standalone Structurizr DSL workspace based on [SRS v0.9, dated 2026-10-29](../../srs/01-project-overview-srs.md), the [sequence inventory and consistency findings](../sequence/README.md), and all 32 current sequence sources. A proposed [Database Design](../../database/database-design.md) and ERD now exist; detailed API Design remains planned. The unrelated hotel examples in the sequence examples directory are not project requirements.

## Views

| Key | Purpose |
|---|---|
| `SystemContext` | Shows Guest, Customer, Staff and Admin interactions with the API, customer browser payment initiation, VNPay's server IPN and optional outbound SMTP. |
| `Containers` | Opens the API boundary to show one NestJS backend application, PostgreSQL and local product-image storage, plus the same users and external integrations. |
| `BackendComponents` | Component Diagram (P0): Auth, Users, Products, Inventory, Orders, Payments, ExpirationScheduler and Health, with key collaborations and database, image storage and inbound VNPay IPN dependencies. |
| `BackendOptionalComponents` | Separately shows the three optional P1 areas (Categories, Cart, Notifications/Email) and their PostgreSQL/SMTP dependencies, keeping the core view readable. |

Container descriptions are deliberately short. Module responsibilities appear in the component views and the table below. All components share the same backend deployment and process; internal arrows express logical collaboration, not network calls or mandated class/method boundaries. Human interactions remain in the context/container views to avoid repeating role-to-module arrows. Shared JWT/RBAC/ownership checks, Swagger and detailed business-event flows are documented here and in the sequence set rather than drawn as arrows to every component. Health is included without invented database/provider dependencies.

The P0 component view uses single module names instead of combined functional labels such as `Users / Profile / Roles` or `Orders / Staff Fulfillment`; those responsibilities remain in descriptions. `ExpirationScheduler` follows the existing sequence participant name. These are proposed architectural module boundaries, not a claim that corresponding source classes/modules have been implemented. The title is `Backend Application - Component Diagram (P0)`; the stable view key remains `BackendComponents`.

VNPay is a top-level software system outside both `shop` and `backend`. The P0 component view uses explicit left-to-right spacing (`autoLayout lr 500 250`) and a compact external-system box to reduce overlap with the enclosing system/container boundaries. It remains connected only to Payments through the documented inbound IPN relationship at this level.

The backend is a **single deployable modular monolith**. PostgreSQL is separate infrastructure; file storage represents a mounted directory/volume, not an executable service or third application process. The container boundary expresses system ownership, not identical deployment lifecycles. Docker Compose provides local development/reviewer setup with the backend, database and named upload volume. No frontend implementation, worker, broker, gateway, cache or cloud storage is assumed.

## Logical modules inside the backend

These names group documented responsibilities; they do not prescribe an implemented NestJS module layout or separate deployment units.

| Priority | Logical area | Responsibility and evidence |
|---|---|---|
| P0 | Auth | JWT access authentication, hashed refresh sessions, rotation, replay handling and revocation; SEQ-01–04. |
| P0 | Users | Separate profile read/update, password change, dedicated Admin role operations and atomic role audit; SEQ-05–07, 14, 32. |
| P0 | Products | Catalog browsing and Admin changes, Multer validation, local upload/reference and orphan cleanup; SEQ-08–12. |
| P0 | Inventory | Transactional reservation/release and audited Admin stock adjustment; SEQ-13, 15, 18, 26. |
| P0 | Orders | Server-priced checkout with inline shipping snapshots, own history, pending-order cancellation, staff queue/details and permitted fulfillment transitions; SEQ-15–21. Staff responsibilities belong to order handling, not a separate service. |
| P0 | Payments | Locally signed VNPay URL, verified idempotent IPN, non-authoritative browser return and read-only Admin reconciliation; SEQ-22–24, 27. |
| P0 | ExpirationScheduler | Startup recovery and periodic attempt/order scans in the backend process; SEQ-25–26. |
| P0 | Health | Lightweight public health check; SEQ-28. |
| P1, optional | Categories / Cart | Category CRUD/public browsing and customer-owned cart convenience; direct checkout does not require either; SEQ-29–30. |
| P1, optional | Notifications / Email | Durable notification events in PostgreSQL, post-commit SMTP delivery and bounded in-process recovery/retry; SEQ-31. |

Swagger/OpenAPI documents the backend API; JWT/RBAC/ownership guards and TypeORM are in-process capabilities. Jest is development/test tooling, with the SRS requiring at least 70% coverage and critical PostgreSQL concurrency/transaction tests. Neither Swagger, Jest nor Docker Compose is an additional application container.

## Use in Structurizr Playground

1. Open [Structurizr Playground](https://playground.structurizr.com/).
2. Open `architecture.dsl` locally and copy its **entire contents**, including the `workspace` wrapper.
3. Replace the sample DSL in the Playground editor with that text and run its render action.
4. Select `SystemContext`, `Containers`, `BackendComponents` or `BackendOptionalComponents` in the diagram selector. All views use automatic left-to-right layout. Start with `Containers` for runtime structure, then use the component views for internal responsibilities.

Pasting the complete file requires no includes, plugins, themes, credentials or other project files. DSL constructs/styles were reviewed against the [official language reference](https://docs.structurizr.com/dsl/language).

## Assumptions, inconsistencies and limitations

- **Source precedence:** current SRS v0.9 and current sequence files govern. Older address-book/default-address change-log entries are superseded: checkout stores inline shipping details on each order. No address module is modeled.
- **P1 scope:** SMTP is shown as an explicitly optional external dependency to document the conditional integration, not to claim email is approved or mandatory. Its element and relationships have the `Optional` style. Categories, cart and notifications remain optional logical areas inside the backend; P0 starts without SMTP or notification-event persistence. Optional data, if selected, uses the existing PostgreSQL database.
- **Payment boundary:** the backend constructs and returns signed URLs locally (SEQ-22); the customer browser opens VNPay. Accordingly, there is no invented backend-to-VNPay payment-initiation HTTP call. The direct provider/backend relationship is inbound IPN. The customer-to-backend relationship includes browser return, which never settles payment; only an applicable verified successful IPN may settle. Customers are used as the browser interaction abstraction, with no frontend technology/container assumed.
- **Approved expiry policies:** SRS v0.9 approves the configurable 20-minute attempt target subject to safe provider/integration rules. SEQ-25 keeps an attempt pending when provider finality is unresolved. No provider-query service is invented. Attempt expiry alone keeps the order pending and stock reserved. The separate configurable 60-minute order reservation policy and in-process startup/periodic scheduler are approved; terminal order expiry expires remaining attempts and releases stock exactly once. Late callbacks are recorded for reconciliation and do not reactivate orders. Scheduler scan interval is an implementation configuration detail.
- **Other unresolved contracts:** official VNPay signature/encoding, amount conversion, response codes, URL validity/reuse and timeout semantics remain implementation verification work. Finer Staff permissions, general user-account mutations beyond dedicated role assignment, and P1 email event/retry/lease policies are not fully specified. This diagram adds no provider internals, refund flow or manual settlement override.
- **Storage representation:** the configurable upload directory (example `uploads/products`) is persisted with a Docker named volume. PostgreSQL stores generated relative paths/metadata, not image bytes. Read-only static image serving is a documented MVP option; no separate file server is introduced.
- **Inventory plan discrepancy:** the parent diagram inventory says all artifacts are PlantUML and lists `system-architecture.puml` as planned. This task explicitly requires Structurizr at `architecture/architecture.dsl`; that older planned path is not evidence of an existing architecture diagram. Existing inventory and SRS files have been left intact.

## Validation

Reviewed the model against SRS sections 2–7 and 9 and the current sequence set: one backend application, internal scheduler, documented storage, role boundaries, browser/IPN distinction and optional P1 integration. Reviewed all identifiers/relationship endpoints, unique view keys, balanced blocks, tags, styles and view scopes. Implied relationships are disabled so explicit context relationships cannot acquire misleading container-level labels.

After the readability revision, the model contains 11 components nested inside the single backend container (8 P0 and 3 optional P1). Static checks cover element/relationship references, component membership and the four unique view keys. Component views explicitly include their elements to keep P1 scope separate and avoid pulling in all users and unrelated dependencies.

On **2026-10-29**, the complete workspace was successfully parsed/rendered in the live Structurizr Playground (displayed version v2026.10.01). All four view keys appeared in its selector. The P0 Component Diagram was visually inspected: VNPay is entirely outside the E-commerce Backend API boundary, with space between its box and the boundary. The rendered DSL was compared with the saved `architecture.dsl` and matched after ignoring blank lines and line indentation. The other three views were not individually visually inspected during this revision.

No local CLI validator was used. No application code was created or changed and no application tests were run; this workspace contains documentation only.

## Approved policy baseline — 2026-10-29

See [SRS v0.9 decisions](../../srs/decisions-2026-10-29.md). The 60-minute reservation/scheduler and shared STAFF fulfillment permissions are approved. The 20-minute attempt target retains a safe-provider-expiry verification gate; pending URL reuse requires established validity, otherwise conflict. Email stays deferred to P1. These decisions do not change C4 topology; the three existing PNG exports remain applicable. Earlier discussion of approval-dependent order expiry is superseded by this record. The database design now exists under `docs/database/`.
