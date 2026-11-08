# Demo end-to-end: cài gói → eBPF trace → 36 feature → predict

Chạy trong VM Ubuntu 24.04 x86_64, kernel **6.8.0-xx-generic** (kernel HWE 7.0 làm BCC lỗi biên dịch).
Mọi lệnh chạy từ thư mục gốc repo.

## 0. Chuẩn bị (1 lần)

```bash
sudo bash src/scripts/prerequisites.sh     # bpfcc-tools, strace, python3-venv, thư viện ML đúng phiên bản (requirements.txt)
sudo opensnoop-bpfcc -d 2                  # kiểm eBPF chạy được
```

Gói độc cần thêm Python 3.8 (giống môi trường thu trace malicious của QUT-DV25) và wheelhouse để cài offline:

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get install -y python3.8 python3.8-venv
python3.8 -m venv /tmp/dl38 && /tmp/dl38/bin/pip download -d wheelhouse/python3.8 pip==24.3.1 setuptools==75.3.0 wheel==0.45.1
# tải file mẫu độc về thư mục gốc repo (chỉ tải, không giải nén); snapshot cũ có thể không có file này
wget -q https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/aaiohttp/0.1/aaiohttp-0.1.tar.gz && ls -l aaiohttp-0.1.tar.gz
```

Sau đó chụp snapshot VM `before-malicious`.

## 1. Gói benign (chạy sống)

```bash
sudo python3 src/main.py flask            # mặc định giám sát 120s như paper
```

Kết quả: `traces/flask/` (filetop, opensnoop, tcp, install log), `outputs/flask/` (strace),
`traces/flask/features.csv` (36 feature) và bảng dự đoán, trong đó Random-Forest là model paper triển khai.

## 2. Gói độc (chỉ trong VM cô lập, **có mạng** như bài báo)

Bài báo cài gói thật từ PyPI trên mạng riêng có đường ra internet (Algorithm 1: `pip install`; trace TCP của gói lành toàn là kết nối HTTPS 443 tới files.pythonhosted.org). Tắt mạng sẽ làm mất các feature TCP và làm lệch kết quả, nên chạy có mạng:

1. VMware: card mạng **NAT**, tắt Shared Folders, không lưu token/khoá SSH nào trong VM. Chụp snapshot `before-malicious`.
2. Chạy:
   ```bash
   sudo PYTHON=python3.8 python3 src/main.py aaiohttp-0.1.tar.gz
   ```
3. Chép `traces/` + `outputs/` ra ngoài nếu cần, rồi **revert snapshot `before-malicious`**.

Chạy offline (`OFFLINE=1`, cần wheelhouse) vẫn được nhưng chỉ để dự phòng, điểm thấp hơn khoảng 1 điểm phần trăm.

## 3. Chạy lại không cần cài (dự phòng)

```bash
python3 src/main.py flask --skip          # đọc lại traces/flask + outputs/flask
python3 src/predict.py traces/flask/features.csv
```

## Kết quả tham chiếu (VM sạch, có mạng, commit 9f72d5e, Random-Forest)

Đo ngày 07–08/11/2026 bằng `trace.sh` theo đúng cách gắn strace của tác giả (`monitor.sh` dò pip mỗi giây).

| Gói | Nhãn thật | RF | Xác suất độc |
|---|---|---|---|
| flask | benign | BENIGN | 24.33% |
| aaiohttp-0.1.tar.gz | malicious | MALICIOUS | 85.61% |
| cilorama-1.0.0.tar.gz | malicious | MALICIOUS | 93.74% |

- Cùng một gói, mỗi lần chạy một khác, vì thời điểm strace gắn vào pip thay đổi. Trên VM sạch, flask ra 18–24% qua các lần đo, lần nào cũng dưới 50%.
- Trên 106 gói lành mới, RF báo nhầm 51/106 (48,1%), và 11/11 gói độc bị bắt. Gói lành nhỏ, cài nhanh dễ bị báo nhầm. Demo nên dùng flask.
- `STRACE=wrap` (chạy pip dưới strace từ đầu) chỉ dùng để so sánh, **không phải** cách của tác giả. Với wrap, chỉ 4/11 gói độc bị bắt.
