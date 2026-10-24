# Diagram Inventory

All diagrams for the E-commerce Backend API will be maintained as separate PlantUML (`.puml`) files. The current **32 sequence diagrams** are listed in [sequence/README.md](sequence/README.md). The broader artifacts below remain planned unless explicitly marked present.

| Planned file | Purpose | Status |
|---|---|---|
| `use-case.puml` | Guest, Customer, Staff, Admin, VNPay Sandbox, and SMTP use cases and system boundary | Planned |
| `product-browsing-flow.puml` | Active-product browsing, search/filter/sort, pagination, and detail visibility | Planned |
| `order-submission-flow.puml` | Inline recipient/contact/address input, server prices, order snapshots and stock reservation | Planned |
| `auth-token-refresh-sequence.puml` | Registration, login, access/refresh issuance, rotation, logout, and revocation | Planned |
| `sequence/SEQ-05-view-profile.puml` | View own profile | Present |
| `sequence/SEQ-06-update-profile.puml` | Update own allowlisted profile fields | Present |
| `sequence/SEQ-07-change-password.puml` | Password verification and refresh-session revocation | Present |
| `vnpay-payment-ipn-sequence.puml` | Payment attempt, signed VNPay URL, return handling, verified IPN, idempotency, and settlement | Planned |
| `order-payment-inventory-state-machine.puml` | Allowed/rejected order, payment-attempt, and inventory-reservation transitions, including expiry and late callbacks | Planned |
| `email-notification-sequence.puml` | P1 event-triggered notification, SMTP success/failure, safe logging, and duplicate prevention | Planned (P1) |
| `staff-order-processing-sequence.puml` | Order queue/detail access, permitted fulfillment transition, and history record | Planned |
| `system-architecture.puml` | NestJS modular monolith, PostgreSQL, local upload storage, VNPay Sandbox, SMTP, and client boundaries | Planned |
| `database-erd.puml` | Conceptual/logical relationships among users, tokens, products, orders with inline shipping snapshots, payments, and optional P1 entities | Planned |

The future diagram task should keep payment status separate from order fulfillment status, represent verified/idempotent IPN handling, the P0 expiry scheduler, and label P1 capabilities clearly.
