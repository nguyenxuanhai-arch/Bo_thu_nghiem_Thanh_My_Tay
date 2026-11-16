# Mã nguồn tham chiếu

Ba tệp trong thư mục này được giữ để đối chiếu với phần thuật toán đã tích hợp vào notebook chính. Chúng không được notebook chính nhập hoặc thực thi.

| Tệp | Đầu vào hoặc thư viện riêng |
| --- | --- |
| `dijkstra.py` | `Du_lieu_test.xlsx` với các sheet `OD_Pairs`, `Nodes`, `Directed_Edges`; pandas, NetworkX và bộ đọc Excel; CSV mốc và JSON kẹt xe |
| `yen_k_shortest_path.ipynb` | `Du_lieu_test.xlsx` với các sheet tương ứng; pandas và bộ đọc Excel |
| `boa_star.py` | File Excel và cấu hình theo tham số của script; openpyxl |

`Du_lieu_test.xlsx` không được cung cấp trong repo này. Các mã tham chiếu còn giữ lựa chọn OD riêng của bộ gốc, vì vậy chạy chúng không tự tái lập bộ 10 OD của notebook chính. `requirements.txt` ở thư mục gốc chỉ phục vụ notebook chính và lệnh kiểm tra.

Tác giả và ngày tạo của các bản mã tham chiếu chưa có metadata xác thực trong bộ tệp được cung cấp. Tài liệu BOA* được mã tham chiếu dẫn tới được ghi tại [SOURCES.md](../SOURCES.md); trích dẫn đó không xác thực riêng bản triển khai này.
