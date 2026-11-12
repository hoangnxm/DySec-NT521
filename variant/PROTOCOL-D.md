# Luật lần D: FPR trên 110 gói lành mới (viết và commit TRƯỚC khi chạy lần D)

Lý do: ở lần B (37 gói lành hợp lệ), biến thể bỏ G1+G2 báo nhầm 5,4% so với 24,3% của model gốc, nhưng khoảng tin cậy
còn chồng nhau nên điều kiện (i) của PROTOCOL.md chưa đạt. Lần D đo trên mẫu lớn hơn. PROTOCOL.md và PROTOCOL-C.md không bị sửa.

## Dữ liệu
- data/benign-lapD.txt: 110 gói lành, chọn bằng data/select-benign-fresh.py (seed 2028), cùng tiêu chí với lần B,
  loại mọi gói có trong dataset, benign-test.txt, benign-heavy.txt, benign-fresh.txt và flask (đã kiểm: trùng 0 gói).
- Không đổi danh sách sau khi thấy số.
- Ba model giữ nguyên: huấn luyện trên dataset/train.csv, seed 50, ngưỡng 0,5; sha256 của .pkl in ra lúc đo.
- Chạy trên VM vừa revert, 4 vCPU, mạng NAT bật, như lần A, B, C.

## Lần đo bị loại (chung cho ba model, như PROTOCOL.md)
Probe eBPF dừng sớm (sau tối đa 2 lần chạy lại); pip báo lỗi; Attach_Delay trên 10 giây; không có thời gian cài.

## Số chính và kết luận
1. Số chính: FPR của từng model trên các lần đo hợp lệ của lần D, khoảng tin cậy Wilson 95%.
2. Điều kiện (i) đạt khi cận trên khoảng tin cậy của bỏ G1+G2 thấp hơn cận dưới của model gốc, trên lần D.
3. Điều kiện (ii) lấy từ lần C (recall 87,2%, đã đạt).
4. Nếu (i) đạt: bỏ G1+G2 được ghi là có hiệu quả thật. Nếu không đạt: ghi là chưa chứng minh được; không đo thêm lần nào nữa cho câu hỏi này.

## Số phụ (luôn in kèm, không dùng để quyết định)
- So cặp trên cùng lần đo (McNemar chính xác, hai phía) giữa model gốc và bỏ G1+G2.
- FPR gộp lần B (đo đầy đủ ngày 12/11, 37 gói) và lần D.
- Tách theo thời gian cài dưới/từ 5 giây.

Báo cáo ghi cả lần B và lần D, kể cả khi hai lần cho kết quả khác nhau.
