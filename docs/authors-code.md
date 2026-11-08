# Đối chiếu với mã nguồn công khai của tác giả

Kiểm tra ngày 07/11/2026, cập nhật số đo ngày 08/11/2026.

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

Trên trace thu tại VM của nhóm, pipeline của tác giả (bản đúng notebook) báo độc 83/106 gói lành (RF ≥ 0,5) và 4/4 trace gói độc. Pipeline của repo (36 feature mã hoá thứ tự) báo độc 42/106 gói lành. Hai số này tính trên trace của lần đo đầu tiên (06/11, script cũ).

## Thay đổi phần thu trace theo `trace.sh` / `monitor.sh` của tác giả

| Điểm | Trước | Bây giờ | Theo tác giả |
|---|---|---|---|
| Thứ tự bật công cụ | eBPF trước, monitor sau | monitor (strace) trước, rồi 3 công cụ eBPF, chờ 5 s | đúng |
| Cờ pip | `--no-cache-dir` | `--break-system-packages --no-build-isolation --no-cache-dir` | đúng |
| Khi cài lỗi | không thử lại | thử lại bằng `pip3 install`, sau đó `pip install --break-system-packages` | đúng |
| strace bám nhầm tiến trình của chính chương trình | `main.py`/`batch.py` (python3) cũng bị strace | bỏ qua các tiến trình cha của `monitor.sh` | tác giả chạy từ shell nên không gặp lỗi này |
| Tiến trình sót của gói trước | `monitor.sh`/`tcpstates` có lần không tắt, tranh strace với gói sau, làm syscall về 0 | dọn tiến trình sót trước và sau mỗi gói (`kill -KILL` nếu cần), ghi `probe_died=strace` nếu không có syscall nào | tác giả chạy từng gói bằng tay |

Những chỗ cố ý giữ khác tác giả:
- Tạo venv bằng `python -m venv` và ghim `pip 24.3.1 / setuptools 75.3.0 / wheel` theo phiên bản thấy trong trace thô, thay vì `virtualenv` + `pip install setuptools` bản mới nhất. Bản mới nhất hôm nay đã khác bản tác giả dùng năm 2024.
- Giữ cửa sổ 120 s như bài báo. `trace.sh` của tác giả không tự dừng công cụ.
- Khi thử lại, không xoá file trace. Script của tác giả xoá file trace trong lúc các công cụ vẫn đang ghi, làm mất dữ liệu.

Lỗi strace bám vào `main.py`/`batch.py` chỉ làm thừa vài syscall của chính chương trình. Nó không giúp bắt pip sớm hơn, vì `strace -f` chỉ theo các tiến trình con sinh ra **sau** lúc strace gắn vào, mà pip là con của `trace.sh`.

## Đo lại trên VM sạch (07–08/11/2026, commit 9f72d5e)

Cách đo: dùng script mặc định (`STRACE=poll`, đúng cách tác giả gắn strace) trên VM vừa khôi phục snapshot, mạng NAT bật. Gói lành đo trước, rồi mới tới gói độc. Các lần đo trên VM chưa khôi phục snapshot sau khi đã chạy gói độc bị loại.

| | Kết quả |
|---|---|
| 106 gói lành mới (`data/benign-test.txt` + flask, bỏ nvdlfw-inspect vì filetop dừng sớm cả 3 lần) | RF báo nhầm **51/106 = 48,1%** (khoảng tin cậy Wilson 95%: 38,8–57,5%) |
| 11 gói độc (pypi_malregistry, đều có trong QUT-DV25) | RF bắt **11/11** (0,836–0,958) |
| flask, so với dòng Flask trong dataset | Network 115 / Process 90 / File 10.442 / IO 947, tác giả: 115 / 89 / 12.177 / 1.110 |
| aaiohttp, so với dataset | 41 / 14 / 1.051 / 100, tác giả: 41 / 13 / 1.197 / 100 |

### Thời điểm gắn strace quyết định kết quả

- `monitor.sh` của tác giả dò pip mỗi giây rồi mới `strace -p`, nên luôn gắn trễ. Trace thô tác giả công bố cũng bắt đầu giữa chừng:
  - 1337x: dòng đầu là lúc pip đang nạp `pip/_vendor/rich/color.py`, không có `execve`;
  - aaiohttp: chỉ có 1 file 1.582 dòng, bắt đầu khi pip đang đọc output của `setup.py` lúc build wheel.
- Gói cài nhanh thì chỉ bắt được khúc cuối, trace ngắn. Model học quy luật "trace ngắn thì độc":
  - `setup.py` của cilorama chỉ chạy payload khi `os.name == "nt"` (Windows). Trên Linux gói không làm gì, nhưng RF vẫn chấm 0,937.
  - 11 lần pip báo lỗi không cài gì (do thiếu file) đều bị chấm độc, điểm 0,71–0,92.
  - Chia 99 lần đo gói lành theo Network_Operations: dưới 60 thì 60% bị báo nhầm (32/53); từ 100 trở lên thì 0/4.
- `STRACE=wrap` (pip chạy dưới strace từ syscall đầu) thì chỉ bắt được 4/11 gói độc, vì trace có thêm đoạn pip khởi động (File_Operations 7.792–11.406). Với cùng 11 gói, File_Operations của tác giả trải từ 905 đến 15.053, nằm giữa poll (1.051–2.092) và wrap. Như vậy phép đo của chính tác giả cũng dao động theo thời điểm gắn strace. Số chính dùng poll vì poll là đúng cách làm của tác giả. Wrap chỉ dùng để so sánh.
