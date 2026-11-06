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
# đặt file mẫu độc (vd aaiohttp-0.1.tar.gz, lấy từ pypi_malregistry) ở thư mục gốc repo
```

Sau đó chụp snapshot VM `before-malicious`.

## 1. Gói benign (chạy sống)

```bash
sudo python3 src/main.py flask            # mặc định giám sát 120s như paper
```

Kết quả: `traces/flask/` (filetop, opensnoop, tcp, install log), `outputs/flask/` (strace),
`traces/flask/features.csv` (36 feature) và bảng dự đoán, trong đó Random-Forest là model paper triển khai.

## 2. Gói độc (chỉ trong VM cô lập)

1. VMware: tắt Shared Folders, ngắt card mạng.
2. Chạy:
   ```bash
   sudo OFFLINE=1 PYTHON=python3.8 python3 src/main.py aaiohttp-0.1.tar.gz
   ```
3. Chép `traces/` + `outputs/` ra ngoài nếu cần, rồi **revert snapshot `before-malicious`**.

## 3. Chạy lại không cần cài (dự phòng)

```bash
python3 src/main.py flask --skip          # đọc lại traces/flask + outputs/flask
python3 src/predict.py traces/flask/features.csv
```

## Kết quả tham chiếu (trace nhóm thu, Random-Forest)

| Gói | Nhãn thật | RF | Xác suất độc |
|---|---|---|---|
| flask | benign | BENIGN | 37.73% |
| adafruit-io | benign | BENIGN | 8.1% |
| Acquisition | benign | BENIGN | 6.7% |
| 1337x | benign | BENIGN | 31.9% |
| requests | benign | **MALICIOUS** (sai) | 65.6% |
| aaiohttp-0.1.tar.gz | malicious | MALICIOUS | 85.32% |
| aihottp-0.1.tar.gz | malicious | MALICIOUS | 88.1% |
| aiohhttp-0.1.tar.gz | malicious | MALICIOUS | 85.7% |

Không dùng `requests` làm gói benign khi demo: model đoán sai gói này.
