# 36 Feature của DySec — format ĐÃ CHỐT với Hưng (01/10/2026)

Extractor xuất CSV: header = `Package_Name` + 36 cột dưới đây (đúng thứ tự), **giá trị thô** (chưa encode, chưa scale).
`src/predict.py` encode bằng `src/preprocess.py` (OrdinalEncoder `unknown_value=-1`, fit trên train) rồi `model.predict`.
Kiểm tra extractor với dataset gốc: `python src/validate.py` → 199/216 giá trị khớp tuyệt đối (92,1%).

Chuỗi phải **khớp đúng định dạng** của CSV QUT-DV25 (`dataset/QUT-DV25-Processed/`), lệch 1 ký tự là thành -1.

| # | Cột | Kiểu | Nguồn trace | Định dạng (ví dụ từ dataset) |
|---|---|---|---|---|
| 1–7 | Root_DIR_Installation, Temporary_DIR_Installation, Home_DIR_Installation, User_Access, Sys_Access, Etc_DIR_Installation, Other_DIR_Installation | số | opensnoop | số lần truy cập theo thư mục |
| 8 | State_Transition | **chuỗi** | tcpstates | `{'SYN_SENT -> ->': 1429, '443 -> CLOSE': 1064, ...}` |
| 9–12 | Local_IP_Address_Access, Remote_IP_Address_Access, Local_Port_Access, Remote_Port_Access | số | tcpstates | số IP/port duy nhất |
| 13–17 | Read_Processes, Write_Processes, Read_Data_Transfer_Processes, Write_Data_Transfer_Processes, File_Access_Processes | **chuỗi** | filetop | 5 tên process: `pgrep, opensnoop-bpfcc, pip, filetop-bpfcc, DOMCacheThread` |
| 18 | Total_Dependencies | **chuỗi** | install log | `attrs-24.2.0; beautifulsoup4-4.12.3; ...` (tên-phiên bản, từ dòng "Successfully installed", bỏ gói chính) |
| 19 | Direct_Dependencies | **chuỗi** | install log | `paho-mqtt; requests;` (từ `Collecting X (from <gói chính>)`) |
| 20 | Indirect_Dependencies | **chuỗi** | install log | `certifi>=2017.4.17; idna<4,>=2.5;` |
| 21–26 | File_Operations, Network_Operations, Process_Management_Operations, IO_Operations, Time_Operations, Security_Operations | số | strace | số syscall theo nhóm |
| 27–36 | Pattern_1 … Pattern_10 | **chuỗi** | strace | chuỗi syscall: `newfstatat -> openat -> fstat`, `read -> read -> close -> no-error -> no-fd` |

Tổng: **19 cột chuỗi + 17 cột số**. Nhãn `Level` (0 benign / 1 malicious) không cần cho predict.

## Lưu ý khi demo (đã báo Hưng)
Tỷ lệ giá trị duy nhất trên 14.271 gói QUT-DV25:
- State_Transition 91%, Total_Dependencies 38% (có số phiên bản), Filetop 5–22% (chứa process nền của máy tác giả) → gói mới gần như chắc chắn ra -1.
- Pattern_1..10 chỉ 0,3–0,9% → encode được.

→ Ý biện luận TC3 (feature phụ thuộc thời điểm + máy thu) và hướng cải tiến TC4 (đổi các cột này sang dạng số).
