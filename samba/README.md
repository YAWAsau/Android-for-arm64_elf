# Samba：smbclient、smbd 與 RPC 共用建置

來源基於本對話最後的 `samba-android-arm64-ndkr30-api28-build-scripts.zip`；完整原始雜湊與來源包出處在 `ORIGIN.json`。

```powershell
./build.ps1
./build.ps1 -BuildScope client
./build.ps1 -DeviceSerial 'DEVICE_SERIAL' -Jobs 8
./build.ps1 -Ndk 'D:\Android\android-ndk-r30' -Msys 'C:\msys64'
```

預設同時建置 `smbclient`、`smbd`、`samba-dcerpcd`、`rpcd_classic`、`rpcd_lsad`、`rpcd_winreg`，輸出至 `dist/android-arm64-size/`。`-BuildScope client` 只建置客戶端。兩者共用同一套來源與補丁。

沿用 NDK r30 30.0.16248370、ARM64／API 28、全靜態、Samba `-Os`／ThinLTO 和加密依賴 `-O2`；`-BuildProfile standard` 可選原有 `-O2` Samba 配方，其輸出在 `dist/android-arm64/`。

NDK 會自動尋找既有安裝。MSYS2 預設 `C:\msys64`，ADB 預設 `C:\platform-tools\adb.exe`，GPG 預設 Git for Windows 的 `C:\Program Files\Git\usr\bin\gpg.exe`；皆可用對應的 `-Ndk`、`-Msys`、`-Adb`、`-Gpg` 參數指定。

建置快取預設 `%USERPROFILE%\SambaAndroidBuild`；可用 `-CacheRoot D:\SambaAndroidBuild` 指定英文、不含空白或單引號的路徑。`-Clean` 清除所選 profile 的目標工作來源，保留原有加密依賴快取。

## 來源與裝置需求

- `upstream-source/` 隨附 Samba 4.25.0、GMP／Nettle／GnuTLS／Parse::Yapp 的來源及可用的簽章。會先填入缺少的快取，再執行原有 SHA／GPG 驗證。
- 沿用每次查詢 Samba 官方最新穩定版的行為；查詢失敗才採用最新的隨附／既有快取版本，並顯示警告。依賴版本維持固定。
- 必須連接已授權且可 root 的 ARM64 Android 裝置，供原有 configure 探測和建置最後的 `smbclient --version` 檢查使用。編譯與連結全部在 Windows 完成。
- 2026-09-26 的整合版已在 Windows PowerShell 5.1 建置六個二進位，通過全靜態 ELF 檢查；原有 ADB configure 探測及 `smbclient --version` 也通過，版本為 4.25.0。2026-10-05 新增的 Android 暫存路徑補丁尚未重新編譯或進行裝置測試；外層 `verification/` 是前述歷史建置記錄。完整配方說明見 `tools/samba_android/SERVER-BUILD.md`。

## 官方源碼更新後的補丁

每次執行 `build.ps1` 都會查詢官方最新穩定版、驗證簽章，再由 `build-samba.sh` 執行 `tools/samba_android/patch-samba.py`，最後才進入 Waf 配置與編譯。使用來源快取時仍會執行補丁；已套用的相同補丁不會重複插入。

本次新增 Android 預設暫存目錄 `/data/local/tmp`，涵蓋 Samba `tmpdir()`／IPC$、檔案式 Kerberos 憑證快取、Heimdal `%{TEMP}` 與 SMB1 診斷封包輸出。保留環境變數覆寫、Heimdal 的 `secure_getenv` 與非 Android 行為。新增補丁遇到來源檔案移動、預期區塊不符或重複時，會報錯中止編譯，需更新配方後重跑；不會猜測如何套用。

成功建置後的 `build-metadata.json` 會包含 `android_patchset` 與 `android_patch_recipe_sha256`。外層入口收集的 `out/samba-build.json` 也保留這些資訊。ThinLTO／靜態連結仍由原建置配方執行。

詳細移植範圍及參考來源見 [ANDROID-PATCHES.md](ANDROID-PATCHES.md)。日後上游改動仍可能需要維護補丁，不能保證所有未來版本免修改就能編譯。

此資料夾可以獨立搬走使用。外層總建置入口會以 `size`／`all` 呼叫此腳本，並把六個產物一同收集。
