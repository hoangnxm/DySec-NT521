# Chạy kiểm chứng DySec trên máy khác (lần E)

Mục đích: chạy lại 110 gói lành của lần D và 160 gói độc của lần C trên một máy thật khác, cùng VM, cùng model.
Từ đó xem biến thể bỏ G1+G2 có còn tốt khi đổi máy hay không, giống như model của tác giả chạy được trên máy của tác giả.

Khác lần C và D: 270 gói chạy **xen kẽ** trong một lần chạy, khoảng 1 gói lành rồi 1–2 gói độc.
Thứ tự nằm cố định trong `data/mix-lapE.txt` (sinh bằng `data/make-mix-lapE.py`, không ngẫu nhiên).
Nhờ vậy gói lành và gói độc được đo trong cùng điều kiện máy và mạng theo thời gian, không bên nào được đo hết vào lúc máy rảnh.

File này được commit **trước khi chạy**. Sau khi đã thấy số thì không sửa luật bên dưới.

## 1. Luật chốt trước

- **Dữ liệu:** `data/benign-lapD.txt` (110 gói lành) và `data/malicious-lapC.txt` (160 gói độc), giữ nguyên, không thêm, không bớt.
  Thứ tự chạy theo `data/mix-lapE.txt`. Gói lành cài bằng python3 như lần D, gói độc bằng python3.8 như lần C.
- **Model:** giữ nguyên. Lúc chạy, script in sha256 của từng file model, và các mã này phải trùng với bảng dưới.

  | File model | sha256 (mấy ký tự đầu, cuối) |
  |---|---|
  | `models/Random-Forest.pkl` (gốc của tác giả) | `02eaa61f…df993` |
  | `variant/rf_drop_g1g2.pkl` | `f81c2554…` |
  | `variant/rf_drop_g1g2g3.pkl` | `1dcf7295…` |

  Nếu không trùng thì dừng lại, báo Hoàng.
  Hai file `variant/rf_*.pkl` trên git được huấn luyện trên Windows nên có hash khác. Script huấn luyện lại hai file này trong VM ở đầu lần chạy, và hash in ra lúc đó mới là hash cần so.
- **Lần đo bị loại:** như lần C và D. Đó là các lần probe eBPF dừng sớm (sau tối đa 2 lần chạy lại), pip báo lỗi, Attach_Delay trên 10 giây, hoặc không có thời gian cài. Script tự làm việc này.
- **Bỏ G1+G2 được ghi là "vẫn tốt trên máy khác" khi đạt cả hai điều kiện:**
  1. Trên các gói lành hợp lệ, cận trên khoảng tin cậy Wilson 95% của FPR bỏ G1+G2 thấp hơn cận dưới của model gốc.
  2. Trên các gói độc hợp lệ, recall của bỏ G1+G2 (điểm ước lượng) từ 80% trở lên.
- **Nếu không đạt:** ghi đúng như vậy. Không chạy lại để lấy số đẹp hơn.
- **Báo cáo:** đặt số của máy này cạnh số trên máy Hoàng.

  | Model | FPR lần D (105 gói lành) | Recall lần C (149 gói độc) |
  |---|---|---|
  | Gốc của tác giả | 45,7% | 96,0% |
  | Bỏ G1+G2 | 4,8% | 87,2% |
  | Bỏ G1+G2+G3 | 0% | 32,2% |
- **Giới hạn:**
  - Lần E dùng cùng một VM, nên chỉ kiểm được việc đổi máy thật (CPU, ổ đĩa, mạng). Nó không kiểm việc đổi bản Ubuntu hay đổi kernel.
  - Vì chạy xen kẽ, phần lớn gói lành được đo trong VM đã chạy gói độc trước đó. Lần D thì đo gói lành trên VM sạch.
    Nếu FPR khác lần D, phải ghi rõ khác biệt này. Gói nào làm hỏng VM (pip lỗi, probe chết) sẽ bị loại theo luật trên.

## 2. Chuẩn bị (làm trên Windows, VM đang tắt)

Cần VMware Workstation 17, máy có từ 16 GB RAM (VM dùng 8 GB) và khoảng 40 GB ổ trống. Máy phải cắm sạc và có mạng ổn định.

1. Mở VM: **File > Open**, chọn `NT521.vmx`. Nếu VMware hỏi thì chọn **I Copied It**.
2. Khôi phục snapshot sạch: **VM > Snapshot > Revert to Snapshot**, chọn `clean-ebpf-6.8.0-53`. **Bước này bắt buộc.**
3. Vào **VM > Settings**:
   - **Options > Shared Folders:** chọn **Disabled**.
   - **Options > Guest Isolation:** bỏ tick **Enable drag and drop** và **Enable copy and paste**.
   - **Network Adapter:** chọn **NAT**.
   - **Processors:** 4. **Memory:** 8 GB. Giữ đúng như vậy, không tăng.
   - **CD/DVD:** bỏ tick **Connect at power on** (file ISO không có trên máy này).
4. Chặn Windows ngủ. Mở PowerShell bằng quyền Administrator và chạy:
   ```powershell
   powercfg /change standby-timeout-ac 0
   powercfg /change hibernate-timeout-ac 0
   ```

## 3. Chạy (trong VM, mở Terminal)

Chặn VM ngủ hoặc khoá màn hình:

```bash
# chặn suspend/hibernate ở mức hệ thống
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
# chặn tắt màn hình, khoá màn hình và tự suspend của GNOME
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
# kiểm tra: phải ra "masked"
systemctl is-enabled suspend.target
```

Kiểm tra trước khi chạy:

```bash
cd ~/DySec-NT521
git pull
git log --oneline -1          # phải là commit có file CHAY_KIEM_CHUNG.md hoặc mới hơn
nproc                         # phải ra 4
python3.8 --version           # phải có Python 3.8 (gói độc chạy bằng bản này)
ls lape_* 2>/dev/null         # phải không ra gì; có file thì là chưa revert, quay lại bước 2.2
wc -l data/mix-lapE.txt       # phải ra 270
```

Chạy (một lệnh, 270 gói xen kẽ):

```bash
sudo systemd-inhibit --what=sleep:idle --why=dysec bash variant/verify_mix.sh 2>&1 | tee -a lape.log
```

- **Thời gian (ước tính):** 14–18 tiếng. Mỗi gói in một dòng `--- [số thứ tự/270] B|M tên gói (giờ)`, B là gói lành, M là gói độc. Cứ để máy chạy, không dùng máy thật vào việc nặng.
- **Nếu bị dừng giữa chừng** (mất điện, lỡ tắt): chạy lại **đúng lệnh trên**. Script bỏ qua các gói đã đo xong và chạy tiếp.
- **Nếu script in `!!! Shared Folders on: stop` hoặc `!!! hgfs mounted: stop`:** tắt Shared Folders (bước 2.3), khởi động lại VM rồi chạy lại lệnh.
  Script chỉ chạy khi Shared Folders đã tắt.
- Khi xong, terminal in dòng `=== ALL DONE ...` kèm mã sha256 của file kết quả.

## 4. Lấy kết quả ra (TRƯỚC khi revert)

1. Trong VM, chạy lệnh dưới. Chụp màn hình hoặc chép toàn bộ output gửi Hoàng:
   ```bash
   cd ~/DySec-NT521
   grep -E "=== START|\.pkl|malicious samples|ALL DONE" lape.log
   cat lape_ben_summary.txt lape_mal_summary.txt
   ```
2. Trên Windows, copy file kết quả ra. Thay 3 chỗ trong ngoặc nhọn; mật khẩu VM thì hỏi Hoàng:
   ```powershell
   & "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe" -T ws -gu hoang -gp <mật khẩu VM> CopyFileFromGuestToHost "<đường dẫn tới NT521.vmx>" /home/hoang/DySec-NT521/lape_out.tar.gz "<thư mục>\lape_out.tar.gz"
   Get-FileHash "<thư mục>\lape_out.tar.gz"
   ```
   Mã hash phải trùng với dòng `ALL DONE`. Gửi file này cho Hoàng.
3. Sau đó **revert** về `clean-ebpf-6.8.0-53` (VM đã chạy mã độc).

## 5. Không được làm

- Không bật Shared Folders, kéo thả hoặc copy/paste giữa VM và máy thật khi phần gói độc đang chạy hoặc trước khi revert.
- Không `git pull`/`git push` sau khi script đã bắt đầu. Script xoá thông tin đăng nhập GitHub trong VM trước gói đầu tiên.
- Không copy file nào khác ra ngoài ngoài `lape_out.tar.gz` (trong đó chỉ có csv, txt và log).
- Không dùng VM này vào việc khác trước khi revert.
