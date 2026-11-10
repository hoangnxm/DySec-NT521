# Luật lần C: đo recall trên tập gói độc lớn (viết và commit TRƯỚC khi chạy lần C)

Lý do: lần A chỉ có 15 gói độc hợp lệ (khoảng tin cậy 55-93%), và luật loại mọi gói pip lỗi có thể loại oan các gói
mà setup.py đã chạy xong rồi mới lỗi. Lần C đo recall trên tập lớn hơn. PROTOCOL.md không bị sửa.

## Dữ liệu
- data/malicious-lapC.txt: 160 gói độc từ dataset/test.csv, mỗi họ tên một gói, không trùng họ với 40 gói lần A,
  seed 31 (data/select-malicious-lapC.py). Không chọn theo kết quả đo.
- Gói lành: dùng lại số đo lần B (33 gói hợp lệ). Lần C không đo lại gói lành.
- Ba model giữ nguyên (cùng file .pkl, sha256 in ra lúc đo): ngưỡng 0,5, không chỉnh gì.

## Gói tính vào recall (áp dụng chung cho cả ba model)
Loại: probe eBPF dừng sớm; Attach_Delay trên 10 giây; không có thời gian cài.
Gói pip lỗi chỉ được tính khi log cài cho thấy mã build/setup.py đã chạy: log có "Preparing metadata" hoặc
"Getting requirements to build wheel" hoặc "Building wheel" cùng "did not run successfully" hoặc "metadata-generation-failed",
VÀ không có "requires a different Python", "No matching distribution", "Could not find a version".
Gói pip lỗi kiểu khác bị loại. Gói cài thành công luôn được tính.

## Số báo cáo
1. Số chính: recall (Wilson 95%) trên các gói tính theo luật trên.
2. Số phụ (in kèm): chỉ gói cài thành công.
3. Số gói có vector đặc trưng trùng nhau (bản đổi tên), để người đọc biết số gói độc lập thực sự.
4. Báo cáo ghi mọi gói bị loại và lý do.

## Kết luận
- drop_g1g2 được giữ nếu recall số chính từ 80% trở lên. Dưới 80% thì báo cáo ghi biến thể không đạt ở lần C.
- Nếu số chính và số phụ khác nhau, báo cả hai, không chọn số đẹp hơn.
- Không chỉnh ngưỡng, seed hay cột theo kết quả lần C.
