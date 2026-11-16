# Nguồn và giới hạn bằng chứng

Thông tin dưới đây được đối chiếu ngày **16/11/2026 (UTC+7)** từ các trang liên kết và tệp trong repo. Đây là ghi nhận khả năng truy vết, không phải thẩm định độc lập toàn bộ dữ liệu hoặc thuật toán.

## Nguồn công khai

| Nguồn | Tác giả, thời gian, nơi đăng | Bằng chứng và mức sử dụng |
| --- | --- | --- |
| [Đường Xô Viết Nghệ Tĩnh ở quận Bình Thạnh ùn ứ 615 lần trong 9 tháng](https://tuoitre.vn/duong-xo-viet-nghe-tinh-o-quan-binh-thanh-un-u-615-lan-trong-9-thang-2024102110025915.htm) | Châu Tuấn; 21/10/2024, 10:23 GMT+7; Tuổi Trẻ Online | Đã đọc trang gốc, khớp tác giả và ngày đăng. Bài dẫn số liệu Sở GTVT TP.HCM và ghi nhận hiện trường; hỗ trợ bối cảnh ùn tắc đoạn Bạch Đằng–Đài Liệt Sĩ. Chưa đối chiếu báo cáo gốc của Sở; không xác thực tốc độ mô phỏng. |
| [Bản đồ 28 điểm nghẽn giao thông TP.HCM và lộ trình tháo gỡ](https://znews.vn/ban-do-28-diem-nghen-giao-thong-tphcm-va-lo-trinh-thao-go-post1692028.html) | Phan Anh – Xuân Sang; 06/11/2026, 09:16 GMT+7; Znews | Đã đọc trang gốc, có tác giả, thời gian và khu vực Hàng Xanh. Là nguồn báo chí thứ cấp, hữu ích cho bối cảnh địa bàn; chưa đối chiếu hồ sơ gốc của cơ quan quản lý. |
| [“Ma trận” kẹt xe ở ngã tư Hàng Xanh giờ tan tầm](https://dantri.com.vn/thoi-su/ma-tran-ket-xe-o-nga-tu-hang-xanh-gio-tan-tam-20241025090505064.htm) | An Huy; **28/10/2024, 12:05** theo trang bài; Dân trí | Đã đọc bài gốc có ghi nhận hiện trường, ảnh và phỏng vấn. Hỗ trợ mô tả ùn tắc Ung Văn Khiêm–Nguyễn Gia Trí; chưa xác thực độc lập lời kể hoặc quy đổi thành tốc độ cố định. Ngày trong URL khác ngày trên bài; dùng ngày hiển thị. |
| [A Simple and Fast Bi-Objective Search Algorithm](https://doi.org/10.1609/icaps.v30i1.6655) | Carlos Hernández Ulloa, William Yeoh, Jorge A. Baier, Han Zhang, Luis Suazo, Sven Koenig; 2020; ICAPS, tập 30, tr. 143–151 | [Hồ sơ nghiên cứu của Universidad San Sebastián](https://researchers.uss.cl/en/publications/a-simple-and-fast-bi-objective-search-algorithm-2/) cung cấp tác giả, nơi xuất bản và DOI. Nguồn học thuật phù hợp về BOA*. Trang nhà xuất bản chặn truy cập tự động; chưa thẩm định lại toàn văn hoặc chứng minh bản triển khai tương đương thuật toán gốc. |
| [OpenStreetMap: Copyright and License](https://www.openstreetmap.org/copyright/en) | OpenStreetMap contributors / OpenStreetMap Foundation; trang hiện hành, không ghi ngày xuất bản trong nội dung đọc được | Đã đọc nguồn chính thức về ghi công và ODbL. Đáng tin cho thông tin cấp phép; không tự chứng minh độ chính xác từng cạnh trong bộ thử nghiệm. |

Các bài báo có tên tác giả trên trang của chính tòa soạn, nên có thể truy vết nội dung. Lần kiểm tra này không xác minh độc lập danh tính hoặc chuyên môn giao thông của từng tác giả. Không nguồn báo chí nào ở trên chứng minh toàn bộ tốc độ, độ trễ và bề rộng hẻm trong mô hình đã được đo hoặc xác thực.

## Dữ liệu trong repo

- `data_test/edges_clean.csv` và `nodes_clean.csv` là bản mạng đường được cung cấp, khớp bản nhúng ở thời điểm kiểm tra. Bộ này chưa có ngày trích xuất OSM, truy vấn trích xuất, tên người xử lý hoặc quy trình làm sạch đầy đủ; không suy ra chúng từ ngày commit.
- `data_test/cap_od.csv` giữ mã mới, mã gốc và nút đầu–cuối của 10 OD; lệnh kiểm tra đối chiếu trực tiếp với notebook.
- `cau_hinh/toc_do_gia_dinh_chuan.json` ghi phiên bản **2.3**, ngày cập nhật **15/11/2026**. Đây là metadata tự khai báo, không phải bằng chứng đo thực địa. Tốc độ, độ trễ và phạt hẻm cụt là tham số mô phỏng.
- SHA-256 trong notebook kiểm tra tính toàn vẹn dữ liệu nhúng. Khớp CSV/JSON chỉ xác nhận tính nhất quán nội bộ, không xác nhận nguồn gốc hoặc độ chính xác địa lý.
- CSV kết quả được tính bằng chính notebook; không phải đáp án độc lập hoặc dữ liệu khảo sát. Mốc ngoài đồ thị và mốc chưa kiểm chứng vẫn giữ trạng thái đó.
