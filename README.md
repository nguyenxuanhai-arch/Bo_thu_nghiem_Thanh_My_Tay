# Bộ thử nghiệm mạng đường Thạnh Mỹ Tây

So sánh Dijkstra, Yen K-shortest paths và BOA* trên mạng đường gồm **509 cạnh, 458 nút và 10 cặp OD**. Notebook tự chứa dữ liệu và mã thực thi; các bảng kết quả được lưu sẵn để xem trực tiếp trên GitHub.

[Mở trên Google Colab](https://colab.research.google.com/github/nguyenxuanhai-arch/Bo_thu_nghiem_Thanh_My_Tay/blob/main/Thu_nghiem_Dijkstra_Yen_BOA_Thanh_My_Tay.ipynb) · [Xem notebook](Thu_nghiem_Dijkstra_Yen_BOA_Thanh_My_Tay.ipynb) · [Nguồn và giới hạn bằng chứng](SOURCES.md)

## Chạy thử

Trên Colab, mở liên kết ở trên rồi chọn **Runtime → Run all**. Nếu thiếu thư viện, chạy `%pip install pandas IPython` trong một ô riêng trước khi chạy notebook.

Trên máy cá nhân, dùng Python 3.10 trở lên, mở terminal tại thư mục repo:

```powershell
python -m pip install -r requirements.txt
python -m pip install jupyterlab
python -m jupyterlab Thu_nghiem_Dijkstra_Yen_BOA_Thanh_My_Tay.ipynb
```

Trong notebook, chọn **Run → Run All Cells**. Ô cuối ghi kết quả vào `ket_qua_thu_nghiem_Thanh_My_Tay/` bên dưới thư mục làm việc và in đường dẫn thực tế.

Mặc định chạy đủ 10 OD. Đặt `OD_CAN_CHAY = ["OD01", "OD04"]` ở mục 2 để chạy một phần; `YEN_K = 3` quy định số tuyến tối đa cho Yen. Chạy lại toàn bộ notebook sau khi đổi tham số. Chạy một phần sẽ ghi đè các CSV bằng kết quả của phần OD đã chọn.

## Cấu trúc

| Đường dẫn | Nội dung |
| --- | --- |
| `Thu_nghiem_Dijkstra_Yen_BOA_Thanh_My_Tay.ipynb` | Điểm chạy chính; dữ liệu nhúng, thuật toán, bảng và xuất kết quả |
| `data_test/` | Mạng đường và danh sách OD để đối chiếu |
| `cau_hinh/` | Mốc kẹt xe và cấu hình tốc độ giả định phiên bản 2.3 |
| `ket_qua_thu_nghiem_Thanh_My_Tay/` | Kết quả mẫu: 40 dòng so sánh, 60 dòng chi tiết và ba tệp cấu hình xuất lại |
| `ma_nguon_tham_chieu/` | Mã gốc để đối chiếu; xem [hướng dẫn riêng](ma_nguon_tham_chieu/README.md) |
| `scripts/verify_notebook.py` | Chạy các ô mã trong thư mục tạm và đối chiếu kết quả với bộ mẫu |

**Notebook đọc bản dữ liệu nhúng, không đọc lại `data_test/` hoặc `cau_hinh/`.** Chỉnh riêng các CSV/JSON sẽ không thay đổi kết quả Run All. Khi thay dữ liệu, cần đồng bộ cả bản nhúng và SHA-256 trong notebook.

## Các cặp OD

Các mã mới OD01–OD10 tương ứng mã gốc theo thứ tự **OD01, OD02, OD03, OD04, OD06, OD07, OD13, OD14, OD17, OD21**. Bảng notebook, `data_test/cap_od.csv` và CSV kết quả đều giữ mã gốc để đối chiếu.

## Cách đọc kết quả

- Dijkstra và Yen tối ưu tổng thời gian trên cung, trễ tại nút và phạt hẻm cụt.
- BOA* tìm tập Pareto theo thời gian và số lần rẽ. Bảng tổng hợp lấy tuyến ít rẽ nhất; nếu bằng số lần rẽ thì chọn tuyến nhanh hơn.
- Đường chính là tuyến nhanh nhất trên các cung `is_main`, dùng cùng mô hình chi phí.
- `so_sanh_ba_thuat_toan.csv` có 10 OD × 4 phương án, gồm cả đường chính. `chi_tiet_phuong_an.csv` giữ thêm các tuyến Yen và Pareto BOA*.

Thời gian là **kết quả mô phỏng**, chưa được hiệu chỉnh bằng đo thực địa. Kết quả trên mạng đường rút gọn không đại diện cho toàn bộ mạng đường hoặc giao thông hiện tại. Chi tiết tác giả, ngày đăng, nguồn và mức xác thực được ghi tại [SOURCES.md](SOURCES.md).

## Kiểm tra khả năng tái lập

Sau khi cài `requirements.txt`, chạy:

```powershell
python -X utf8 scripts/verify_notebook.py
```

Lệnh chạy tất cả ô mã theo thứ tự, dùng các kiểm tra sẵn có của notebook, đối chiếu dữ liệu/cấu hình nhúng, ánh xạ OD và cả năm tệp xuất mẫu. Các tệp thử nghiệm được tạo trong thư mục tạm, không ghi đè kết quả trong repo. Khớp kết quả chứng minh tính nhất quán của bộ hiện tại; chưa chứng minh độ chính xác thực địa hoặc tính đúng tổng quát của thuật toán.

## Ghi công dữ liệu

Dữ liệu mạng đường có nguồn OpenStreetMap: **© OpenStreetMap contributors**, theo [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/), xem [trang ghi công chính thức](https://www.openstreetmap.org/copyright/en). Repo chưa có giấy phép riêng cho mã nguồn.
