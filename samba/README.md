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
- 本整合版已在 Windows PowerShell 5.1 建置六個二進位，通過全靜態 ELF 檢查；原有 ADB configure 探測及 `smbclient --version` 也通過，版本為 4.25.0。未重跑完整 SMB 伺服器功能測試。整合驗證記錄見外層 `verification/`；完整配方說明見 `tools/samba_android/SERVER-BUILD.md`。

此資料夾可以獨立搬走使用。外層總建置入口會以 `size`／`all` 呼叫此腳本，並把六個產物一同收集。
