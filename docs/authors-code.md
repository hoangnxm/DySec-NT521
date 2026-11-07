# Đối chiếu với mã nguồn công khai của tác giả

Kiểm tra ngày 07/11/2026.

## Nguồn

| Repo | Chủ sở hữu | Nội dung |
|---|---|---|
| github.com/tanzirmehedi/DySec | Sk Tanzir Mehedi (QUT), tác giả thứ nhất của bài báo. README trích dẫn đúng bài báo, giấy phép MIT | Bản rút gọn: script eBPF, notebook tiền xử lý, mô hình `.pkl`, file kết quả |
| github.com/tanzirmehedi/QUT-DV25 | cùng tác giả | Bản đầy đủ hơn: các `trace.sh` riêng cho gói độc và gói lành, notebook **huấn luyện** `TML *.ipynb`, hướng dẫn chạy, mô hình DL |
| doi.org/10.7910/DVN/LBMXJY (Harvard Dataverse) | cùng tác giả | Dataset: trace thô mẫu + 6 file CSV đã xử lý (78 cột ứng viên, 14.271 gói) |

## Tác giả có công khai / không công khai

| Có công khai | Không công khai |
|---|---|
| `prerequisites.sh`, `trace.sh` (bản gói độc và bản gói lành), `monitor.sh` | Code chuyển trace thô thành feature |
| Hướng dẫn dựng Raspberry Pi; danh sách hệ điều hành (có `ubuntu-24.04-desktop-amd64.iso`) | File huấn luyện thật `FinalCombinedBenignMaliciousDataset-v3.csv` |
| Dataset đã xử lý: 6 CSV, 78 cột ứng viên | Code chọn feature theo importance (chỉ có ảnh PNG) |
| Notebook huấn luyện 6 mô hình cho từng nhóm trace và cho Combined | Code phát hiện thời gian thực; trace của 1.000 gói thử thật |
| Mô hình `.pkl` đã train, `model_comparison_results.csv` | |

## Code của tác giả khác bài báo

| Mục | Bài báo | Notebook / `.pkl` của tác giả |
|---|---|---|
| Biểu diễn cột chuỗi | chuỗi syscall dạng n-gram | **ghép cả 19 cột chuỗi** thành một đoạn văn bản, `CountVectorizer(ngram_range=(2,3))` |
| Chuẩn hoá | Min-Max | `StandardScaler(with_mean=False)` (chỉ dùng cho RF, DT) |
| RF | 100 cây, `max_depth=8` | **10 cây, `max_depth=10`** |
| DT | `max_depth=8`, `min_samples_split=10` | `max_depth=2`, `min_samples_split=20` |
| GB | 100 learner, depth 5, lr 0,1 | 10 learner, depth 2, lr 0,01 |
| Số cột đầu vào RF Combined | 36 | 168.778 |
| Fit vectorizer/scaler | — | trên **toàn bộ** dữ liệu, trước khi chia |
| Bảng kết quả | Bảng IV | `model_comparison_results.csv` được **gõ tay** trong notebook; ô chạy RF in ra 96,87%, nhưng bảng ghi 95,99% |
| Bảng IV | Pattern 94,62%, SystemCall 88,51% | file kết quả ghi ngược lại: SystemCall 94,63%, Pattern 88,51% |

## Chạy lại pipeline của tác giả (`src/authors.py`)

```bash
python src/authors.py train                                # đúng notebook: chia ngẫu nhiên, random_state=42, fit trên toàn bộ dữ liệu
python src/authors.py train --split group --fit-scope train   # không rò rỉ: chia theo họ gói như repo, fit chỉ trên train
python src/authors.py predict batch_features.csv
sudo python3 src/main.py flask --pipeline authors           # demo bằng pipeline của tác giả
```

Kết quả (RF 10/10, tập test):

| Dữ liệu đầu vào | Số cột | Accuracy | FPR | Recall |
|---|---|---|---|---|
| 36 feature công khai, đúng notebook | 161.314 | 87,06% | 7,93% | 82,04% |
| 36 feature, chia theo họ gói, fit chỉ trên train | 125.469 | 86,14% | 5,59% | 77,80% |
| 36 + `Unique_System_Calls_List` | 168.125 | 91,64% | 6,53% | 89,80% |
| 36 + 11 cột `Unique_*_List` | 169.131 | 99,02% | 1,96% | 100% |
| 36 + 11 cột `Unique_*_List`, đã sắp xếp lại phần tử | 163.577 | 89,35% | 5,32% | 84,00% |
| Bài báo / file của tác giả | 168.778 | 95,99% | khoảng 3,3% | — |

Các cột `Unique_*_List` chứa cùng một tập syscall ở cả hai nhãn, chỉ khác **thứ tự in**. Riêng `Unique_Memory_Operations_List` đã phân loại đúng 99%; sắp xếp lại phần tử thì chỉ còn 67%. Thứ tự này phản ánh lô trích xuất (gói lành hay gói độc), không phản ánh hành vi. File `v3` của tác giả có 168.778 cột, nằm giữa "36 feature" và "36 + toàn bộ list". Vì vậy con số 95,99% nhiều khả năng có chứa một phần hiệu ứng này. Đây là suy luận, chưa kiểm chứng được vì file `v3` không công khai.

Trên trace thu tại VM của nhóm, pipeline của tác giả (bản đúng notebook) báo độc 83/106 gói lành (RF ≥ 0,5) và 4/4 trace gói độc. Pipeline của repo (36 feature mã hoá thứ tự) báo độc 42/106 gói lành.

## Thay đổi phần thu trace theo `trace.sh` / `monitor.sh` của tác giả

| Điểm | Trước | Bây giờ | Theo tác giả |
|---|---|---|---|
| Thứ tự bật công cụ | eBPF trước, monitor sau | monitor (strace) trước, rồi 3 công cụ eBPF, chờ 5 s | đúng |
| Cờ pip | `--no-cache-dir` | `--break-system-packages --no-build-isolation --no-cache-dir` | đúng |
| Khi cài lỗi | không thử lại | thử lại bằng `pip3 install`, sau đó `pip install --break-system-packages` | đúng |
| strace bám nhầm tiến trình của chính chương trình | `main.py`/`batch.py` (python3) cũng bị strace | bỏ qua các tiến trình cha của `monitor.sh` | tác giả chạy từ shell nên không gặp lỗi này |

Những chỗ cố ý giữ khác tác giả:
- Tạo venv bằng `python -m venv` và ghim `pip 24.3.1 / setuptools 75.3.0 / wheel` theo phiên bản thấy trong trace thô, thay vì `virtualenv` + `pip install setuptools` bản mới nhất. Bản mới nhất hôm nay đã khác bản tác giả dùng năm 2024.
- Giữ cửa sổ 120 s như bài báo. `trace.sh` của tác giả không tự dừng công cụ.
- Khi thử lại, không xoá file trace. Script của tác giả xoá file trace trong lúc các công cụ vẫn đang ghi, làm mất dữ liệu.
