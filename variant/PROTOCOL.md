# Luật đánh giá (viết và commit TRƯỚC khi có số đo cuối)

Mục đích: kết luận không bị chọn theo kết quả. Không sửa file này sau khi đã thấy số của lần đo B.

## Đối tượng
- Model gốc của tác giả (36 cột), models/Random-Forest.pkl
- Biến thể 1: bỏ G1+G2 (25 cột). Biến thể 2: bỏ G1+G2+G3 (22 cột).
- Cả ba huấn luyện chỉ trên dataset/train.csv (variant/train_variant.py: 100 cây, max_depth 8, seed 50, ngưỡng 0,5). Không chỉnh tham số, ngưỡng hay seed theo số đo.

## Dữ liệu kiểm
| Tập | Nguồn | Vai trò |
|---|---|---|
| Gói độc mới (40) | data/malicious-more.txt, lấy từ dataset/test.csv, chưa dùng để chọn cấu hình | recall |
| Gói lành lần A (105) | data/benign-test.txt + flask. ĐÃ dùng để chọn cấu hình, nên chỉ để tham khảo | FPR (lạc quan) |
| Gói lành lần B (40) | data/benign-fresh.txt, chọn bằng data/select-benign-fresh.py, seed 2027, chưa từng đo và không có trong dataset | FPR (độc lập), số chính |

Mỗi lần đo chạy trên VM vừa revert từ snapshot sạch. Gói lành đo trước gói độc.

## Lần đo bị loại (áp dụng chung cho cả ba model, quyết định trước khi chấm)
probe eBPF dừng sớm; pip báo lỗi; Attach_Delay trên 10 giây; không có thời gian cài. Báo cáo liệt kê từng gói bị loại và in thêm số liệu khi không loại gì.

## Luật kết luận
Khoảng tin cậy là Wilson 95%.
1. Biến thể được coi là **có hiệu quả thật** khi cả hai điều kiện đúng:
   - FPR trên gói lành lần B: cận trên khoảng tin cậy của biến thể thấp hơn cận dưới của model gốc.
   - Recall trên 40 gói độc mới: điểm ước lượng từ 80% trở lên.
2. Nếu cả hai biến thể đạt: chọn biến thể có recall cao hơn (bài báo ưu tiên giảm false negative). Bằng nhau thì chọn biến thể ít cột bỏ hơn.
3. Nếu không biến thể nào đạt: báo cáo ghi biến thể không có hiệu quả đã kiểm chứng; kết quả ablation round 1 chỉ là quan sát trên một đợt đo.
4. Báo cáo ghi cả kết quả lần A, kể cả khi mâu thuẫn với lần B.

## Dấu vết
Log của mỗi lần đo ghi commit và sha256 của các file .pkl dùng để chấm. Điểm của cả ba model được in ngay lúc đo (src/batch.py) và lưu trong file kết quả, không chấm lại sau.
