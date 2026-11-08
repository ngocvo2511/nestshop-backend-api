# E-commerce Backend API

A NestJS modular monolith for accounts, catalog and stock-safe checkout, backed by TypeORM and PostgreSQL. VNPay Sandbox integration remains planned.

**Current status:** Day8 adds CUSTOMER `POST /api/v1/orders`:1–100 distinct products with positive integer quantities and inline shipping. It locks products by ID, uses current server prices and BigInt totals, and atomically reserves stock with immutable order/items and initial SYSTEM history. Reservation defaults60minutes through `ORDER_RESERVATION_SECONDS`; no cart/address ID or payment initiation. M2 account/catalog/image/manual-stock APIs remain implemented with safe file lifecycle and atomic audits. JWT claims remain stateless until expiry. Swagger and [contracts](docs/srs/02-api-design.md) document scope. Order reads/cancellation/fulfillment, payments and expiration remain future work; VNPay defaults to `unconfigured`. No category/cart/gallery or benchmark result is included.

## Local Node setup

Use **Node 24.22.2 LTS** (see `.nvmrc` / `.node-version`) and **npm 11.12.1**. `.npmrc` rejects unsupported runtime versions. Install that runtime with your preferred Node version manager; if the bundled npm differs, install `npm@11.12.1` locally in your development toolchain. Version choices and official references are recorded in [implementation progress](docs/srs/implementation-progress.md).

```powershell
node --version
npm --version
npm ci
Copy-Item .env.example .env
```

Edit ignored `.env` locally: set `DB_PASSWORD`, `JWT_ACCESS_SECRET` (at least 32 characters for JWT), and the target PostgreSQL host/port/user/database. Generate independent local values with `node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"`. Copying the example alone fails validation. Use a new dedicated database: the initial migration refuses a public schema with pre-existing application tables. App startup now opens the DB and requires migrations to be current; it never synchronizes or automatically migrates schema.

```powershell
npm run build
npm run migration:status
npm run migration:run
npm run seed
npm run dev
# Or start the compiled app:
npm start
```

Open `http://127.0.0.1:3000/api/v1/health` and Swagger at `http://127.0.0.1:3000/api/docs` (JSON spec `/api/docs-json`). The root `/` returns safe 404. Set `HOST`/`PORT` explicitly to change the listener; default binding is loopback. Startup rejects malformed numbers, unsupported modes, missing secrets, inconsistent lifetimes and partial VNPay configuration. Logs use JSON events; safe startup diagnostics can name an invalid configuration key without printing its value.

| Command | Behavior |
|---|---|
| `npm run lint` | ESLint with TypeScript type checks; no automatic edits. |
| `npm run format` / `npm run format:check` | Format/check application and tooling files; preserve existing docs. |
| `npm test` / `npm run test:cov` | Jest unit and HTTP account/foundation tests; scripts enable VM modules for Nest 12 ESM on Node 24.22.2. Coverage includes all application source. DB integration/Compose checks are separate; final delivery coverage gate remains open. |
| `npm run build` | Compile production source into `dist/`. |
| `npm run test:smoke` | Requires build first; isolated HTTP scaffold regression with `NODE_ENV=test, DB_ENABLED=false`. DB disabling is rejected outside test; this smoke is not DB readiness evidence. |
| `npm run test:integration` | Builds and runs Jest against fresh real PostgreSQL 18.6 in a random Compose project, generated credentials, loopback ephemeral port and tmpfs. Verifies migration down/up, mappings/constraints, generated values, rollback, seed/admin repeatability and actual compiled app + DB health/Swagger/errors. Also proves startup rejects pending migrations. Removes only that project; no external DB URL accepted. |
| `npm run verify:compose` | Builds/starts API + PostgreSQL, verifies migration/seed/admin commands and HTTP, recreates its own containers to verify DB/upload persistence, then removes only its own newly created volumes. Uses generated credentials and a random project/port. |
| `npm run migration:run` / `migration:status` | Run/show migrations using built source and local DB config. |
| `npm run migration:revert` | Drop the last migration's ten P0 tables; use only on a disposable database. Integration tests exercise down/up automatically. |
| `npm run seed` | Insert three fixed-ID demo products only if missing; preserve existing names, prices, stock/images and accounts. Forbidden in production mode. |
| `npm run admin:setup` | Explicit initial ADMIN creation from external credentials; never an automatic startup/public registration operation. |

## Docker Compose development

Docker must provide Linux containers and Compose v2.40+. Node/npm on the host are not required for this path. Copy `.env.compose.example` to ignored `.env.compose` and fill `COMPOSE_DB_PASSWORD` and `COMPOSE_JWT_ACCESS_SECRET` with independent generated local values. `COMPOSE_API_PORT` defaults to 3300. This file is separate from the host app's `.env`; neither is copied into the image. Compose intentionally starts without VNPay credentials.

```powershell
Copy-Item .env.compose.example .env.compose
# Fill the two blank secrets locally, then:
docker compose --env-file .env.compose build api
docker compose --env-file .env.compose up -d --wait
docker compose --env-file .env.compose exec -T api npm run migration:status
docker compose --env-file .env.compose exec -T api npm run seed
docker compose --env-file .env.compose ps
```

Open `http://127.0.0.1:3300/api/v1/health` and `http://127.0.0.1:3300/api/docs`. PostgreSQL is private to the Compose network; no host DB port is published. `postgres` must be healthy before the one-shot `migrate` service runs, and migration success gates API startup. The runtime runs as the `node` user. Project `nestshop-day2` owns named `postgres-data` and `uploads` volumes (resolved with the project prefix); no existing unrelated container or volume is used. Choose a different `-p <new-project>` if that name is already occupied. PostgreSQL 18 stores its persistent tree under `/var/lib/postgresql`; this is the mounted path.

`docker compose --env-file .env.compose down` stops this stack while retaining its data. Do not add `--volumes` to routine shutdown. The test/verification scripts use fresh random projects and clean up only resources they created. Changing the DB password in the env file does not rotate credentials in an existing PostgreSQL volume; keep existing credentials or perform a deliberate DB password rotation.

## Initial Admin setup

Set `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` in local process environment (or ignored `.env` for the host CLI). Password must contain 12–128 characters without surrounding whitespace/control characters; email is normalized to lowercase. Use your secure local secret-entry tooling, never command arguments or chat. On the host run `npm run admin:setup` after build/migration. In Compose, forward the two environment variable names:

```powershell
docker compose --env-file .env.compose run --rm --no-deps -e INITIAL_ADMIN_EMAIL -e INITIAL_ADMIN_PASSWORD api npm run admin:setup
```

Clear those setup variables afterward. Creation uses salted native scrypt (`N=131072,r=8,p=1`, 16-byte random salt, 64-byte key, 256 MiB memory ceiling). Rerunning for an existing Admin preserves its password, role, active flag and profile. If the email belongs to another role, setup fails without promotion or mutation. The product seed never creates users. Day4 registration, login and Admin setup share the same password helper and self-describing scrypt format/policy.

Keep `VNPAY_MODE=unconfigured` and the four merchant/callback fields blank for scaffold work. Read the [VNPay verification checklist](docs/integrations/vnpay-verification.md) before configuring Sandbox. A reachable, merchant-approved IPN endpoint and credentials remain external blockers; no account or public tunnel has been created.

## Documentation

The HTTP contract is `{success:true,data,meta:{correlationId}}` or `{success:false,error:{status,code,message,details?},meta:{correlationId}}`. Unknown/protected fields are rejected, including nested fields. JSON is capped at64KiB. ADMIN image upload accepts exactly one multipart `file`, no fields; `UPLOAD_MAX_BYTES` defaults5242880 and can be lowered. Set `UPLOAD_DIRECTORY` to a backend-owned persistent directory; generated UUID references are relative to it. Image GET returns raw bytes with safe MIME/nosniff/no-store, while missing images use the JSON404 envelope. Primitive implicit coercion is disabled; use class DTOs and explicit bounded query transforms.

Responses echo `X-Correlation-ID`; valid single UUID v4 headers are reused, others replaced. Request logs omit body, headers, paths/queries, signed URLs and raw exception messages. Health is lightweight process liveness, not a live DB/provider probe; startup separately requires DB connectivity/current migrations. Swagger advertises only implemented routes. `204`, files and future provider acknowledgements bypass JSON wrapping; unexpected provider failures map to retry code `99`. Those exceptions are tested with test-only controllers and do not create real payment endpoints.

Entities belong to their feature modules under `src/modules/{users,auth,products,inventory,orders,payments}/entities/`. Shared UUID persistence identity lives in `src/common/entities/uuid-entity.ts`. `src/database/` holds connection/bootstrap infrastructure, migrations, seeds and an explicit `entity-registry.ts` that registers module-owned entities with the shared DataSource. Feature code imports entities from their owning module rather than an infrastructure barrel. Business services/controllers will be added in their planned implementation days.

- [Implementation plan](docs/srs/04-implementation-plan.md): 15-working-day P0 schedule, deliverables, acceptance gates and test evidence.
- [Implementation progress](docs/srs/implementation-progress.md): actual checks, technical decisions and open gates.
- [P0 API contracts](docs/srs/02-api-design.md): complete planned routes, role/ownership, DTOs/models, filters/sorts, money/shipping/token transport, errors, repeat policies and provider exceptions.
- [VNPay verification](docs/integrations/vnpay-verification.md): official findings versus pending Sandbox evidence.
- [Requirements](docs/srs/01-project-overview-srs.md).
- [Approved MVP decisions](docs/srs/decisions-2026-10-29.md).
- [Architecture](docs/diagrams/architecture/README.md).
- [Sequence diagrams](docs/diagrams/sequence/README.md).
- [Database design](docs/database/database-design.md).
- [LaTeX overview sources](docs/latex/project-overview/README.md).
- [Submission PDF](<docs/latex/project-overview/Project_Overview_E-commerce Backend API.pdf>).

## Scope

P0 covers JWT/refresh sessions, role and ownership checks, profiles, catalog/images, audited stock and role changes, direct checkout with inline shipping details, fulfillment, VNPay Sandbox, expiration/recovery, health, Swagger, Docker Compose and testing. Categories, carts, email and advanced reporting are optional P1 extensions.

## Repository and contribution workflow

The public repository is [ngocvo2511/nestshop-backend-api](https://github.com/ngocvo2511/nestshop-backend-api). Clone it with:

```powershell
git clone https://github.com/ngocvo2511/nestshop-backend-api.git
cd nestshop-backend-api
```

Use `codex/<topic>` branches and Conventional Commit messages, for example `feat(auth): rotate refresh tokens atomically`. PR titles follow the same convention and descriptions use [the PR template](.github/pull_request_template.md). The initial PRs are stacked: documentation, backend API, then Docker runtime; review and merge in that order. See [the review and commit schedule](docs/review/2026-11-08-delivery.md) for dates, verification and remaining scope. Keep credentials in local configuration; `.gitignore` excludes local secrets, dependencies, runtime data and intermediate document exports.

Documentation source files under `docs/` are now eligible for version control, including reviewed Markdown evidence. Generated PDF/PNG/SVG/LaTeX exports, archives, temporary/raw/private evidence remain ignored and preserved locally. Review explicit file paths with `git status --untracked-files=all` and `git check-ignore -v <path>` before staging; do not bulk-stage `docs/`. The submission PDF above is an existing local export; a source-only clean clone must regenerate it using the LaTeX instructions.
