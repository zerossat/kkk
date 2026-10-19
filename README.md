# Minecraft Paper/Spigot Diagnostics (Python)

Bộ kiểm tra chẩn đoán lưu lượng thấp dành cho máy chủ Minecraft Java Paper/Spigot mà bạn sở hữu hoặc được ủy quyền quản lý. Đây không phải công cụ DDoS/flood.

## Chức năng

- **TCP IPv4:** thử mở kết nối TCP tới port Minecraft và đo thời gian kết nối.
- **TCP IPv6:** thử kết nối TCP qua IPv6 nếu hostname có bản ghi AAAA hoặc bạn nhập IPv6 trực tiếp. IPv6 là phiên bản IP, không phải tầng OSI Layer 6.
- **Minecraft Status/Ping:** gửi truy vấn status chuẩn của Minecraft Java, ghi phiên bản, số người chơi và độ trễ phản hồi.
- **Bộ kiểm tra tổng hợp:** chạy lần lượt ba kiểm tra, giới hạn tối đa 20 lượt cho mỗi lần chạy.
- **CSV log:** kết quả được lưu ở `diagnostics.csv`.

## Yêu cầu

- Python 3.10 trở lên được khuyến nghị.
- Minecraft Java server Paper/Spigot; port mặc định `25565`.

## Chạy trên Windows

1. Cài Python từ https://www.python.org/downloads/ (đánh dấu tùy chọn thêm Python vào PATH).
2. Giải nén project.
3. Chạy `run_windows.bat`, hoặc chạy thủ công:

```powershell
py -m pip install -r requirements.txt
py mc_diag.py
```

## Chạy trên Linux

```bash
python3 -m pip install -r requirements.txt
python3 mc_diag.py
```

## Đọc kết quả

- `TCP/IPv4` hoặc `TCP/IPv6` thành công nhưng status ping lỗi: port có thể mở nhưng dịch vụ Minecraft không phản hồi status, hoặc bị proxy/firewall/chính sách mạng chặn.
- Cả TCP và status đều thất bại: kiểm tra IP/port, firewall, port forwarding, DNS và trạng thái tiến trình server.
- Không có IPv6: thường có nghĩa hostname không có bản ghi AAAA hoặc tuyến IPv6 không khả dụng; không có nghĩa server bị lỗi nếu bạn chỉ triển khai IPv4.
- So sánh độ trễ ở nhiều thời điểm; một lần kiểm tra không đủ để kết luận server có vấn đề.

Các lượt chạy bị giới hạn tối đa 20 và tối thiểu 1 giây nghỉ giữa lượt. Chỉ kiểm tra máy chủ thuộc quyền quản lý/được cho phép của bạn; với kiểm thử tải thực sự, hãy dùng staging và công cụ benchmark được giới hạn tốc độ, có giám sát tài nguyên.

## Xử lý kết quả `FAIL` / `SKIP`

- `SKIP` ở TCP/IPv6 khi nhập một IPv4 (ví dụ `180.93.103.30`) là bình thường: địa chỉ IPv4 không thể được kiểm tra bằng socket IPv6. Nếu server chỉ có IPv4 thì có thể bỏ qua kiểm tra này.
- `Connection refused` ở TCP/IPv4 hoặc Minecraft Status có nghĩa là kết nối tới IP/port đã bị từ chối. Hãy xác minh port công khai, server đang chạy, `server-port` trong `server.properties`, firewall của máy chủ/nhà cung cấp và cấu hình NAT/port-forwarding. Nếu dùng Velocity/BungeeCord, hãy kiểm tra port public của proxy.
- Trong `diagnostics.csv`, cột `success` ghi `yes`, `no` hoặc `skip`.
