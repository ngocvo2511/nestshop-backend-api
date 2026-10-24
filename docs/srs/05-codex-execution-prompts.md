# Prompt triển khai E-commerce Backend API bằng Codex

Ngày soạn: 2026-11-02. Baseline: SRS v0.9, quyết định MVP và implementation plan hiện tại. Đây là hướng dẫn triển khai, không phải bằng chứng tính năng đã hoàn thành.

## 1. Nhận xét và cách sử dụng

Plan đủ tốt để bắt đầu: phạm vi P0 rõ, milestone có cổng nghiệm thu, test được đưa vào từng tính năng và các yêu cầu transaction/concurrency được mô tả cụ thể. Chưa có application code; repository hiện có tài liệu thiết kế, README và cấu hình Git.

Các điều chỉnh nên áp dụng khi triển khai:

- Xem 15 ngày là ước lượng effort ban đầu. Re-estimate sau M1/M2; không bỏ kiểm chứng transaction hay Sandbox để giữ lịch.
- Chốt sơ bộ money representation, shipping, token transport và chính sách lỗi trước migration ở phần 2. Phần 3 hoàn thiện API design. Tránh map entity xong mới phát hiện hợp đồng API không phù hợp.
- `.gitignore` đang có `/docs/`, và `git ls-files` hiện chỉ có `.gitattributes`, `.gitignore`, `README.md`. Cần xử lý việc version-control tài liệu để clean clone có requirements và acceptance evidence; chỉ đưa tài liệu đã rà soát vào Git.
- Làm rõ quyền sau đổi role: thiết kế hiện dùng access JWT stateless, nên role claim có thể cũ đến khi token hết hạn. Ghi rõ hành vi này và role của token mới; không tự thêm token-version/session lookup vào mọi request.
- Common response envelope phải có ngoại lệ cho IPN theo hợp đồng provider, file/image, và response 204 không có body. Tránh interceptor/filter làm hỏng acknowledgement hoặc ghi query callback vào log.
- Race tests cần nhiều connection/transaction thật và cách phối hợp có kiểm soát; Promise.all trên repository mock hoặc sleep ngẫu nhiên không chứng minh được locking đúng.

Thực hiện lần lượt 01–15. Mỗi phần tương ứng một mục ngày trong plan, không bắt buộc hoàn thành trong đúng một ngày. Copy một prompt vào Codex trong repo này. Mỗi prompt yêu cầu đọc quy tắc chung ở mục 2 nên có thể dùng cả trong chat mới, miễn file này vẫn có trong workspace.

Không chuyển milestone khi gate bắt buộc chưa có bằng chứng. Có thể tiếp tục việc độc lập nếu một dependency bên ngoài bị chặn, nhưng phải ghi rõ gate nào còn mở. Không cần triển khai ứng dụng khi chỉ đang đọc bộ prompt này.

## 2. Quy tắc chung cho mọi prompt

1. Đọc `AGENTS.md` áp dụng nếu có, trạng thái Git và code hiện tại trước khi sửa. Không overwrite/revert thay đổi của người dùng. Không scaffold lại dự án đã có. Không tự commit, push, deploy hoặc thay đổi remote.
2. Đọc `docs/srs/04-implementation-plan.md`, SRS hiện tại và `docs/srs/decisions-2026-10-29.md`. Đọc thêm database design/schema, architecture và sequence liên quan đến phần đang làm. SRS/quyết định hiện hành là baseline nghiệp vụ; DDL là thiết kế đề xuất. Không âm thầm sửa policy để khớp code. Tự chốt lựa chọn kỹ thuật nhỏ và ghi lại; chỉ hỏi khi có mâu thuẫn nghiệp vụ quan trọng chưa thể giải quyết từ tài liệu.
3. Triển khai trực tiếp phần được giao, bao gồm migration nếu cần, validation, authorization, tests và tài liệu liên quan. Giữ modular monolith NestJS/TypeORM/PostgreSQL; không thêm P1, Redis, broker, microservices, address book, refund hay production payment.
4. VND dùng chuỗi thập phân nguyên ở biên API, PostgreSQL bigint và BigInt khi tính toán; không serialize BigInt trực tiếp thành JSON hoặc dùng Number cho money. Chốt giới hạn rõ ràng, kiểm tra input trước ép kiểu, kiểm tra overflow cả line total, order total và provider amount. Stock/quantity theo integer range của DB. Không lấy amount/role/stock từ client làm thẩm quyền ngoài input được phép.
5. Giữ transaction manager chung cho toàn bộ một nghiệp vụ. Theo protocol trong database design: auth khóa user trước token; mutation của existing order khóa order → payments theo ID → products theo ID nếu cần. Checkout khóa products theo ID. Đọc lại trạng thái/deadline sau khóa; dùng thời gian hiện tại phù hợp sau khi chờ lock.
6. Dùng PostgreSQL thật cho constraint, rollback và contention tests, trên DB disposable riêng. Không reset DB không xác định. Phối hợp concurrency tests bằng connection độc lập và synchronization có kiểm soát; kiểm tra cả kết quả request và trạng thái DB sau commit. Không dùng SQLite/mock để thay bằng chứng này.
7. Không hardcode/commit/in/log secrets, password, refresh/access token, signed payment URL hoặc raw sensitive callback. `.env.example` chỉ có tên biến và giá trị mẫu an toàn. Không yêu cầu người dùng dán secret vào chat; hướng dẫn cấu hình cục bộ nếu thiếu.
8. Kiểm tra phiên bản/runtime và tài liệu chính thức hiện hành khi chọn package hoặc triển khai VNPay; ghi phiên bản, URL nguồn và ngày kiểm tra. Fixture/mocks và Sandbox evidence là hai loại kiểm chứng khác nhau. Thiếu credentials/Docker/network: hoàn thành việc độc lập, ghi chính xác check chưa chạy và lý do; không báo pass bằng suy đoán.
9. Viết test có ý nghĩa cùng tính năng; chạy lint/build và checks liên quan. Không tạo test chỉ lặp lại implementation hoặc hạ threshold/exclude source để đạt coverage. Không đưa placeholder/TODO vào luồng bắt buộc rồi đánh dấu hoàn thành.
10. Duy trì `docs/srs/implementation-progress.md`: phạm vi đã làm, file chính, lệnh kiểm tra và kết quả thực tế, gate còn mở, quyết định kỹ thuật và bước kế tiếp. Duy trì `docs/testing/acceptance-matrix.md` theo FR → implementation → test/evidence → trạng thái khi bắt đầu có tính năng. Chỉ tick checklist plan khi đủ bằng chứng.
11. Kết thúc bằng tóm tắt ngắn bằng tiếng Việt: thay đổi, checks đã chạy và kết quả, phần chưa kiểm chứng/lý do, gate đạt/chưa đạt. Dừng ở phần được giao, không tự triển khai phần kế tiếp.

## 3. Các prompt triển khai

### Prompt 01 — Scaffold và khảo sát tích hợp (Day 1)

```text
Hãy thực hiện phần Day 1 của docs/srs/04-implementation-plan.md tại repo hiện tại. Đọc và áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md trước khi làm.

Mục tiêu: tạo NestJS scaffold chạy được, giữ nguyên tài liệu và nội dung README có ích.
- Kiểm tra trạng thái repo; chọn Node LTS, package manager và package versions tương thích qua tài liệu chính thức; ghi runtime, commit-ready lockfile, scripts dev/start/build/lint/format/test/test:cov/test:integration. Không chạy integration giả khi chưa có test setup.
- Cấu hình TypeScript, Jest, lint/format và validated environment. Tách cấu hình app/DB/JWT/upload/expiry/VNPay; phát hiện cấu hình sai, không âm thầm fallback fake secret. Không bắt buộc VNPay secrets cho smoke test nền tảng; ghi rõ chế độ chưa cấu hình và đóng an toàn chức năng thanh toán.
- Rà việc /docs/ đang bị ignore. Điều chỉnh để các tài liệu yêu cầu/thiết kế và evidence an toàn có thể được version-control; giữ ignore cho generated/temp/sensitive artifacts. Không stage toàn bộ docs một cách mù quáng.
- Tra cứu tài liệu VNPay chính thức và tạo docs/integrations/vnpay-verification.md: merchant/API version, signing/encoding, amount, timezone, callback acknowledgement, URL reuse, expiry/finality; phân biệt điều đã có nguồn và điều cần Sandbox. Hướng dẫn cấu hình credentials/IPN URL cục bộ, không tự tạo tài khoản hoặc public tunnel.
- Tạo implementation-progress theo quy tắc chung và cập nhật README/.env.example cho phần đã hoạt động.

Nghiệm thu: dependency install, lint, build, scaffold smoke test chạy được; không mất tài liệu; danh sách blocker Sandbox rõ ràng. Chưa triển khai auth/catalog/orders.
```

### Prompt 02 — Hợp đồng dữ liệu sơ bộ, PostgreSQL và migration (Day 2)

```text
Thực hiện Day 2 theo implementation plan. Đọc và áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; kiểm tra kết quả phần 01 trước khi thay đổi.

- Trước map entity, tạo bản nháp docs/srs/02-api-design.md chốt money decimal-string/BigInt, shipping fields khớp schema, duplicate product IDs bị reject, stock/quantity bounds và token transport. Dùng Bearer cho access token; chọn rõ cách truyền refresh/logout và ghi lý do, không trộn nhiều transport ngoài nhu cầu MVP. Để phần 03 hoàn thiện routes/contracts.
- Tạo Dockerfile/Compose API + PostgreSQL với readiness, persistent DB/upload volumes, env separation và setup test DB disposable riêng. Không ghi đè DB/volume đang có.
- Review và map đúng 10 P0 entities của docs/database/database-design.md. Viết TypeORM migrations cho toàn bộ tables/FK/check/generated line total/partial unique indexes; synchronize=false. Không thực thi schema.sql như migration vào DB hiện có.
- Entity mapping của generated column phải không insert/update giá trị tự tính. Giữ bigint chính xác, UUID do ứng dụng sinh, FK RESTRICT và các ràng buộc one-live-refresh/one-pending/one-success.
- Viết seed repeatable; initial Admin chỉ từ setup command có external config, không hardcode credential hoặc public registration. Seed lại không reset password/role/dữ liệu hiện hữu ngoài hành vi được ghi rõ.
- Kiểm chứng migrate up từ DB trống, down/up trên DB disposable, seed hai lần và constraints quan trọng. Ghi scripts/README đủ để người khác chạy lại.

Nghiệm thu: Compose build/start, migrate, seed và DB integration smoke test có kết quả thật. Nếu Docker chưa dùng được, hoàn thiện code và ghi gate DB chưa đạt, không thay bằng SQLite.
```

### Prompt 03 — API foundation và contracts (Day 3 / gate M1)

```text
Thực hiện Day 3 và đánh giá M1. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc contracts nháp và code hiện tại.

- Hoàn thiện docs/srs/02-api-design.md cho tất cả P0 routes: method/path, role/ownership, request/response, pagination/filter/sort allowlist, shipping, decimal-string money, token/logout transport, upload, status/error codes, ví dụ payload và policy duplicate/repeated actions.
- Chọn reject unknown/protected DTO fields một cách nhất quán; kiểm soát transform để chuỗi sai, số thập phân, NaN/Infinity hoặc giá trị ngoài range không lọt qua ép kiểu. Ghi role claim có thể cũ tới access-JWT expiry và token mới lấy role hiện tại; không thêm per-request session lookup.
- Implement /api/v1, validation, safe errors, success envelope, structured logging và correlation IDs có giới hạn/validation. Không log Authorization, cookies/token, query callback hoặc payment URL.
- Thiết kế ngoại lệ rõ cho provider IPN acknowledgement, image/file response và 204 không body. Không để global response/exception handling làm hỏng protocol VNPay.
- Thêm Swagger nền tảng và lightweight public health không lộ secrets/DB internals; ghi lock/transaction conventions theo database design. Không triển khai payment handler tại phần này.
- Test validation/envelopes/errors/health và smoke app + PostgreSQL; kiểm tra môi trường sạch có thể start, migrate, seed theo README.

Nghiệm thu: M1 chỉ đạt nếu startup + migrations + smoke có evidence. API design phải đủ rõ để các module sau không tự đoán hợp đồng.
```

### Prompt 04 — Register, login và refresh rotation (Day 4)

```text
Thực hiện Day 4. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc FR-AUTH-001–003/005, FR-USER-001, database auth protocol và SEQ-01–03.

- Implement normalized unique email, secure password hashing/policy, CUSTOMER-only registration và login active account với generic credential errors; tuyệt đối không trả password hash/refresh hash.
- Phát hành JWT đúng signature/type/expiry với lifetimes từ env. Refresh token có entropy cao, lưu hash, family, status, expiry, consumed/revoked metadata theo schema.
- Login/refresh cùng khóa user trước token; recheck account/password/session dưới khóa. Rotation consume token cũ trước insert successor trong một transaction.
- Replay của consumed token phải revoke cả family, COMMIT revocation rồi mới trả rejection; tránh throw trong transaction khiến rollback mất revocation. Không coi token đã LOGOUT/PASSWORD_CHANGE revoke là replay mới.
- Unit/API tests và PostgreSQL tests: duplicate registration race, inactive/invalid login, expired/wrong token type, rotation thường, concurrent single-winner, consumed replay và family successor bị revoke. Ghi rõ concurrent loser có thể kích hoạt replay và revoke token của winner, theo baseline không có grace period.

Nghiệm thu: tests kiểm tra trạng thái family sau commit, không chỉ HTTP status; bổ sung FR-to-test matrix và Swagger phần auth đã làm. Chưa làm profile/role APIs.
```

### Prompt 05 — RBAC, profile, logout, password và role audit (Day 5)

```text
Thực hiện Day 5. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc SEQ-04–07/14/32 và requirements tương ứng.

- Implement JWT/roles guards, server-side ownership, own-profile GET/PATCH riêng; chỉ full name/phone được phép theo baseline, avatar chưa chọn thì không tự thêm.
- Implement idempotent logout revoke supplied/current refresh family với LOGOUT. Password change verify current password, cập nhật hash và revoke tất cả families với PASSWORD_CHANGE trong cùng user-locked transaction; login/refresh phải tham gia cùng protocol.
- Implement dedicated ADMIN role listing/change với allowlisted DTO và atomic role_change_audit. Ghi rõ role no-op xử lý thế nào, không ghi audit old=new trái constraint. Không thêm user deletion/deactivation APIs ngoài scope đã chốt.
- Test Guest/Customer/Staff/Admin, foreign-record access, register/profile mass assignment, secret-field leaks, wrong password, logout lặp/concurrent, password-change/login/refresh contention và role/audit rollback.
- Kiểm chứng access JWT đã phát hành vẫn theo stateless policy tới expiry; access token mới phản ánh role hiện tại. Không hứa immediate access revocation.

Nghiệm thu: account scope có API/DB evidence; update contracts/Swagger/matrix. M2 còn chờ catalog/upload/inventory.
```

### Prompt 06 — Product catalog (Day 6)

```text
Thực hiện Day 6. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc FR-PROD-001–005 và SEQ-08–11.

- Implement public active-only product list/detail; missing/inactive có response an toàn nhất quán.
- Search/filter/sort theo API allowlist, parameterized queries, offset/limit có bounds và tie-break bằng ID. Response gồm items/offset/limit/total; total theo cùng filter.
- ADMIN create với positive integer VND dạng decimal string, initial nonnegative integer stock. Update chỉ catalog allowlist; stock và image path tùy ý không được mass-assign qua general PATCH.
- Test role, inactive visibility, filter/sort injection và unknown keys, pagination bounds/tie-break, money unsafe/fractional/overflow, create stock bounds và forbidden stock update.
- Unit/API tests và DB tests phù hợp; cập nhật Swagger/matrix. Không thêm category/cart/gallery hoặc benchmark claim chưa đo.

Nghiệm thu: catalog contracts hoạt động và tests pass; chưa đánh dấu M2 hoàn thành.
```

### Prompt 07 — Product image và audited inventory (Day 7 / gate M2)

```text
Thực hiện Day 7 và đánh giá M2. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc FR-UPLOAD-001, FR-INVENTORY-001–002, SEQ-12–13.

- ADMIN-only Multer upload JPEG/PNG/WebP tối đa 5 MiB. Kiểm tra nội dung file phù hợp kiểu cho phép thay vì chỉ tin filename/client MIME; generated filenames, canonical path containment, lưu relative reference, serve an toàn và missing-file 404.
- Ràng buộc mỗi product một image reference theo design. Chốt behavior khi replace và concurrency sao cho không xóa file còn được tham chiếu; scope tối thiểu, không gallery.
- Storage thành công nhưng DB lỗi phải attempt orphan cleanup. Cleanup lỗi chỉ log safe diagnostic context, không host path/secret trong client response; validation/storage lỗi không để DB reference sai.
- Implement ADMIN stock delta khác 0 + required reason, lock product, kiểm tra integer overflow/nonnegative result và atomic inventory_adjustment_audit. Không cho general product update bypass audit.
- Test spoofed/invalid/oversize files, missing file, storage/DB failures, orphan cleanup failure, path traversal; stock role/reason/range, audit rollback và adjustment contention trên PostgreSQL.

Nghiệm thu M2: account/auth/ownership/audit + catalog/upload/inventory checks đủ evidence, không lộ sensitive fields. Liệt kê gate còn thiếu nếu có.
```

### Prompt 08 — Transactional checkout (Day 8)

```text
Thực hiện Day 8. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc SEQ-15, FR-ORDER-001/005, FR-INVENTORY-001 và database checkout protocol.

- CUSTOMER checkout với nonempty distinct product IDs/positive integer quantities và inline recipient/phone/address đúng API design; giới hạn số items/quantities rõ ràng. Không cần cart/address ID.
- Lock products theo ID, reload active/price/stock, tính line/order totals chính xác từ server; reject thiếu stock/inactive/overflow trước persist sai.
- Một transaction tạo PENDING_PAYMENT order, immutable product/price/shipping snapshots, initial SYSTEM history và trừ available stock. Dùng cùng transaction manager cho mọi module tham gia; generated line total không bị insert/update trực tiếp.
- Persist reservation deadline cấu hình mặc định 60 phút. Không thêm payment initiation vào checkout.
- Test shipping/bad items/duplicate IDs/client amount manipulation, snapshot độc lập sau đổi profile/product, money overflow, rollback sau khi đã trừ một phần stock hoặc insert một phần records.
- PostgreSQL contention test last unit với connection độc lập: đúng một checkout thành công; không stock âm, không partial orders/history.

Nghiệm thu: test chứng minh atomicity và no overselling bằng DB state sau commit. Update contracts/Swagger/matrix.
```

### Prompt 09 — Own order history và cancellation (Day 9)

```text
Thực hiện Day 9. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc SEQ-16–18 và database cancellation/expiry protocol.

- Own-order list/detail/history với documented pagination và safe payment summaries; không trả payment URL/sensitive provider data qua listing.
- Owner cancellation chỉ khi PENDING_PAYMENT và còn trong reservation deadline; recheck sau lock. Foreign access theo response policy đã chốt.
- Serialize order → payments theo ID → products theo ID. Một transaction conditional transition CANCELLED, expire pending attempts, restore stock theo immutable lines đúng một lần và ghi human-actor history.
- Xử lý repeated cancellation nhất quán theo contract, không release/history lần hai. Stock restoration overflow phải rollback và báo lỗi an toàn, không clip số lượng.
- Test foreign reads/mutations, paid/expired/overdue cancellation, repeated/concurrent cancellation và fault-injected rollback trên PostgreSQL. Tests có thể tạo attempt fixture trong DB; không dựng API payment giả.

Nghiệm thu: cancellation atomic/release-once và order ownership có evidence; race với IPN sẽ được bổ sung khi callback tồn tại ở phần 12.
```

### Prompt 10 — Staff fulfillment và order contention (Day 10 / gate M3)

```text
Thực hiện Day 10 và đánh giá M3. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc SEQ-19–21, FR-ORDER-003–005, FR-USER-002.

- STAFF/ADMIN shared queue/detail/history với minimal status filter và pagination theo contract; xác định eligible-order scope từ tài liệu/API design, không mở rộng dữ liệu tùy tiện.
- Chỉ PAID → PROCESSING → SHIPPED → COMPLETED; lock/recheck và history atomic. Không cho direct payment-state edit, skip/backward/terminal transition.
- Test unauthorized access, eligible scope, transition validation, repeated/concurrent transition, history attribution và rollback.
- Hoàn thiện PostgreSQL adjustment/checkout contention, multi-product locking, last-unit checkout, checkout rollback và cancellation release-once; kiểm tra no lost update, no negative stock, no orphan records.
- Tránh circular module dependencies bằng orchestration/transaction interfaces vừa đủ; không tạo generic repository framework chỉ để giải quyết phần này.

Nghiệm thu M3: stock-safe order lifecycle có evidence thực tế. Payment callbacks chưa tồn tại không được báo là đã kiểm chứng.
```

### Prompt 11 — VNPay adapter và initiation (Day 11)

```text
Thực hiện Day 11. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc SEQ-22, integration checklist và FR-PAY-001–002/004.

- Kiểm tra tài liệu VNPay chính thức hiện hành, selected merchant/API configuration; viết signing/encoding/amount/timezone fixtures có expected output độc lập. Ghi nguồn và assumptions; không lấy chính hàm đang test để tự tạo expected signature.
- Adapter tạo signed URL cục bộ với unique attempt reference và persisted order total, cấu hình merchant/secret/return/IPN/environment; không phát minh backend HTTP call để tạo URL nếu protocol không yêu cầu.
- Owner initiation cho PENDING_PAYMENT trước order deadline; lock order → payments, recheck và enforce partial unique one-pending index.
- Reuse pending URL chỉ theo validity predicate đã xác lập; nếu chưa chứng minh an toàn thì conflict, không tạo attempt thứ hai. New attempt chỉ sau genuinely FAILED/EXPIRED và order còn eligible; target deadline 20 phút không tự chứng minh provider finality.
- Signing/config failure rollback không để attempt dở dang. Signed URL chỉ xuất ở response được phép, không logs/listings.
- Test roles/ownership/order eligibility, signing errors, concurrent initiation, reuse/conflict, replacement sau genuine terminal attempt trên PostgreSQL. Run Sandbox checks nếu local credentials có sẵn; nếu thiếu, ghi rõ acceptance còn mở.

Nghiệm thu: deterministic adapter + DB invariants pass; phân biệt implemented với Sandbox-verified. Chưa báo M4 hoàn thành.
```

### Prompt 12 — IPN, browser return và reconciliation (Day 12)

```text
Thực hiện Day 12. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc SEQ-23–24/27, FR-PAY-003–004 và transaction protocol.

- Public IPN authenticates bằng provider signature, không human JWT. Xác minh canonicalization/signature, merchant/environment/reference/amount conversion/currency và applicable result/transaction fields theo spec thực tế. Reject malformed/duplicate ambiguous parameters an toàn; không giả định field provider không gửi luôn có mặt.
- Lock order → payments; recheck trạng thái và deadline sau lock. Accepted applicable success: payment SUCCESS + terminal metadata, order PAID + SYSTEM history + SETTLED receipt atomic; không trừ stock lần hai. Applicable failure giữ reservation theo policy.
- Persist bounded safe receipts cho invalid/unknown/mismatch/failed/duplicate/late/conflict; không raw payload/signature/secrets. Expected rejection không được rollback mất receipt; terminal attempt không bị overwrite canonical outcome bởi callback muộn.
- IPN acknowledgement đúng provider protocol, bypass common envelope khi cần; chỉ ACK durable handling sau commit. DB failure phải cho retry an toàn, không false-success ACK.
- Browser return chỉ đọc/hiển thị trạng thái an toàn, tuyệt đối không settle; giới hạn dữ liệu/order ownership theo contract. ADMIN reconciliation chỉ read-only, không manual-success/refund.
- Test signatures/encoding fixtures, mismatches, unknown/invalid, one-success constraint, duplicate/concurrent callbacks, terminal protection, receipt rollback/commit và cancellation-vs-settlement trên PostgreSQL. Assert order/payment/history/stock cuối cùng.

Nghiệm thu: verified settlement idempotent với evidence; Sandbox observations ghi riêng. Expiration race hoàn tất ở phần 13.
```

### Prompt 13 — Startup recovery và expiration (Day 13 / gate M4)

```text
Thực hiện Day 13 và đánh giá M4. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc SEQ-25–26 và approved expiry policies.

- In-process startup scan + configurable periodic scan, bounded batch size và tránh scan overlap trong một process; shutdown sạch. Candidate query không thay locked recheck. Ghi deployment scope single-instance, không thêm distributed infrastructure.
- Attempt due chỉ terminalize khi verified expiry/finality policy cho phép; giữ reservation. Chưa rõ finality thì giữ PENDING và conflict replacement, không expire chỉ vì elapsed 20 phút.
- Pending order quá reservation deadline: order → payments → products lock, recheck current deadline/status; conditional EXPIRED + remaining pending attempts EXPIRED + SYSTEM history + stock release-once trong cùng transaction.
- Reuse domain operations với cancellation/settlement, tránh copy logic release khác nhau. Một candidate lỗi không làm mất toàn bộ khả năng scan các order khác; safe logs đủ diagnostic.
- PostgreSQL tests: repeated/overlapping scans, startup recovery sau downtime, fault rollback, IPN-vs-expiry, cancellation-vs-expiry và adjustment-vs-release. Không double release/history/settlement.
- Hoàn thiện Sandbox evidence về callback, URL reuse, expiry/finality. Nếu chưa có evidence hoặc policy safe expiry chưa xác lập, ghi M4 payment acceptance chưa đạt; vẫn nghiệm thu riêng các thành phần đã chứng minh được.

Nghiệm thu M4: DB races/recovery pass và integration gate rõ ràng; mocks không thay Sandbox acceptance.
```

### Prompt 14 — Coverage, performance, security và CI (Day 14)

```text
Thực hiện Day 14. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đối chiếu required test evidence trong plan và acceptance matrix.

- Chạy unit/API/real-PostgreSQL suites; sửa lỗi auth replay, ownership, audit, inventory, payment/expiration trước. Không skip critical checks để pipeline xanh.
- npm run test:cov phải enforce >=70% riêng statement/branch/function/line trên configured src service/guard/controller/DTO-validation/utility scope theo SRS; chỉ exclusions bootstrap/generated có lý do. Thêm meaningful missing tests, không hạ threshold.
- Seed 1.000 active products trong môi trường benchmark riêng/reproducible. Đo server-side duration của ít nhất 30 sequential GET /api/v1/products?offset=0&limit=20&sort=name requests; ghi runtime, dataset, warmup, sample count, cách tính p95 và observed p95 so với target <500 ms. Client round-trip không được gọi là server-side duration.
- Review secret/PII leaks, DTO/mass assignment, SQL allowlist, upload content/path/cleanup, callback log redaction, environment/test DB separation. Sửa issue thực tế trong P0, không tự mở rộng sang compliance hay architecture mới.
- CI install từ lockfile, lint/build/unit/coverage và PostgreSQL service integration; không cần live VNPay/SMTP credentials. Env fixture chỉ synthetic test config.
- Lưu evidence thật trong docs/testing và update FR matrix/progress; ghi rõ check chưa chạy hoặc fail, môi trường và cách reproduce.

Nghiệm thu: coverage/performance/security/CI có kết quả tái lập; benchmark fail phải được sửa hoặc ghi gate chưa đạt, không thay số liệu.
```

### Prompt 15 — Clean setup, acceptance và bàn giao (Day 15 / gate M5)

```text
Thực hiện Day 15 và final P0 acceptance review. Áp dụng mục 2 của docs/srs/05-codex-execution-prompts.md; đọc toàn bộ milestone gates và acceptance matrix hiện tại.

- Review current diff/source để bảo đảm delivery không phụ thuộc ignored/untracked local assets. Dựng bản source sạch cô lập chỉ gồm file dự định bàn giao, không đọc local secrets/node_modules/dist/volumes; install, Compose build/start, migrate, seed và checks theo README. Không xóa runtime data của workspace. Nếu chưa thể kiểm chứng từ actual clean clone vì chưa commit, ghi chính xác giới hạn thay vì gọi source copy là clean clone.
- Hoàn thiện Swagger mọi P0 route: security/role/ownership, query, DTO/money string, errors, upload và provider acknowledgement exceptions. Hoàn thiện README/runtime/env/migration/seed/test/coverage/benchmark và known limitations.
- Tạo hướng dẫn demo reproducible: register/login, Admin catalog/stock audit, checkout concurrency, Sandbox payment confirmation, staff fulfillment, unpaid-order expiry và recovery; không chứa real secrets hoặc signed payment URL đã dùng.
- Hoàn thiện FR → code → test/evidence matrix; chỉ tick plan khi evidence có thật. Sửa defects P0 trong phạm vi, chạy lại checks bị ảnh hưởng.
- Update project overview/README/progress để phản ánh implementation thực tế. Không ghi P0 complete khi thiếu Sandbox acceptance, real-PostgreSQL checks, coverage hoặc clean setup evidence. Chỉ rõ gate nào đã đạt và phần nào còn chặn.
- Đề xuất focused Conventional Commit messages nếu hữu ích; không tự commit/push/deploy.

Nghiệm thu: báo cáo bàn giao ngắn bằng tiếng Việt với trạng thái M1–M5, lệnh chạy chính, evidence paths, unresolved blockers và kết luận P0 đạt/chưa đạt có căn cứ. Không tự triển khai P1.
```

## 4. Prompt sửa một gate chưa đạt

```text
Đọc mục 2 của docs/srs/05-codex-execution-prompts.md, implementation-progress và acceptance matrix hiện tại. Hãy xử lý các failure/blocker kỹ thuật còn mở của phần vừa triển khai trong phạm vi P0.

Tái hiện lỗi trước, xác định nguyên nhân và sửa tối thiểu nhưng đầy đủ. Thêm regression test khi cần, chạy lại checks liên quan và cập nhật evidence. Không đổi requirements, hạ coverage, skip concurrency tests hoặc dùng mock thay bằng chứng PostgreSQL/Sandbox. Nếu blocker đòi credentials hay môi trường bên ngoài, hoàn thành việc độc lập và ghi chính xác bước người dùng cần cấu hình cục bộ; không yêu cầu secret trong chat. Không tự làm phần tiếp theo, commit, push hay deploy.

Kết thúc: lỗi nào đã sửa, test nào chứng minh, gate đạt/chưa đạt và blocker còn lại.
```
