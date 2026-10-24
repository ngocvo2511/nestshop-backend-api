# ERD — E-commerce Backend

## Tạo ERD từ code trên web

Mở [PlantUML Web Server](https://www.plantuml.com/plantuml/uml/), dán toàn bộ [conceptual-erd.puml](conceptual-erd.puml), rồi chọn Submit. Có thể xuất SVG hoặc PNG. Mã dùng `@startchen` theo [tài liệu Chen ERD chính thức](https://plantuml.com/er-diagram), không khai báo column/thuộc tính. Đã kiểm tra cú pháp bằng PlantUML cục bộ với `-checkonly` thành công.

Trong nguồn PlantUML này, `(min,max)` cạnh thực thể là số lần **một đối tượng của thực thể đó tham gia quan hệ**: `USER -(0,N)- PLACES` nghĩa là một user có thể đặt 0 đến nhiều order; `PLACES -(1,1)- ORDER` nghĩa là mỗi order có đúng một user. Đây là cách ghi khoảng tham gia, khác cách đặt nhãn tỉ lệ `1:N` trên hình khái niệm bên dưới.

## ERD khái niệm (ký pháp Chen)

Thể hiện **10 thực thể và 12 quan hệ** trong phạm vi P0. Hình chữ nhật là thực thể; hình thoi là quan hệ nghiệp vụ. Nhãn ở hai đầu là số lượng tối thiểu/tối đa: `1`, `0..1`, `0..N`, `1..N`. Bản khái niệm tập trung vào quan hệ, lược bỏ thuộc tính để dễ đọc.

![ERD khái niệm](conceptual-erd.png)

- [SVG phóng to không vỡ nét](conceptual-erd.svg)
- [Ảnh PNG](conceptual-erd.png)
- [Mã nguồn Graphviz](conceptual-erd.dot)

## ERD logic (Crow’s Foot)

Hiển thị các thuộc tính nghiệp vụ chính, PK/FK/UK và quan hệ. Dấu `?` sau tên thuộc tính biểu thị trường cho phép NULL; `line_total_vnd` là cột được PostgreSQL tính tự động. Bản này chọn lọc thuộc tính để dễ đọc; toàn bộ 97 cột và ràng buộc nằm trong DBML/SQL.

![ERD logic](erd.png)

- [SVG phóng to không vỡ nét](erd.svg)
- [Ảnh PNG](erd.png)
- [Mã nguồn Mermaid](erd.mmd)
- [Mã nguồn Graphviz](erd.dot)

Các nhánh `orders → order_items` và `orders → order_status_history` phải có tối thiểu một bản ghi con theo quy tắc nghiệp vụ và transaction; chỉ riêng FK không bảo đảm số lượng tối thiểu này. Tác nhân lịch sử có thể NULL cho SYSTEM; callback không xác định được giao dịch có thể không liên kết payment. Mỗi order có nhiều payment attempts nhưng tối đa một PENDING và một SUCCESS, được bảo vệ bằng partial unique indexes trong SQL.

## Thiết kế đầy đủ

- [Phân tích, quyết định và quy tắc transaction](database-design.md)
- [DBML để mở tại dbdiagram.io](database.dbml)
- [PostgreSQL DDL tham khảo](schema.sql)

Hai ERD sử dụng cùng 10 thực thể và 12 liên kết FK của schema hiện tại; không thêm thực thể P1 hay thay đổi schema. Đã dựng thành công SVG/PNG bằng Graphviz và xem kiểm tra cả hai ảnh. ERD logic cũng có nguồn Mermaid; nguồn Mermaid chưa được chạy qua renderer riêng.

Tái tạo hình:

```powershell
dot -Tsvg docs/database/conceptual-erd.dot -o docs/database/conceptual-erd.svg
dot -Tpng:gd docs/database/conceptual-erd.dot -o docs/database/conceptual-erd.png
dot -Tsvg docs/database/erd.dot -o docs/database/erd.svg
dot -Tpng:gd docs/database/erd.dot -o docs/database/erd.png
```
