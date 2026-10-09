# Android-for-arm64_elf

集中管理 **zstd、GNU tar、BusyBox、Samba（smbclient／smbd／RPC）**。所有編譯在 Windows 本機執行，沿用 **NDK r30（30.0.16248370）／ARM64／API 28 編譯目標／完整靜態連結**。

## 目錄

```text
Android-for-arm64_elf/
├── build.ps1                 # 依序編譯全部四個專案
├── README.md
├── SOURCE_MANIFEST.json      # 來源版本、整理記錄及檔案 SHA256
├── SOURCE_SHA256SUMS.txt
├── zstd/
│   ├── build.ps1             # 只編譯 zstd
│   └── upstream/             # 固定提交的原始碼
├── tar/
│   ├── build.ps1             # 只編譯 GNU tar
│   └── upstream/             # GNU tar 1.35.90 原始碼
├── busybox/
│   ├── build.ps1             # 只編譯 BusyBox
│   ├── config/               # 68 個指令及 Unicode 範圍修正
│   ├── patches/              # Android 補丁
│   └── upstream/             # 來源壓縮包及靜態依賴
└── samba/
    ├── build.ps1             # 共用來源編譯 smbclient、smbd 和 RPC
    ├── tools/samba_android/  # 最後一份 r30 建置包的配方與補丁
    └── upstream-source/     # Samba 及依賴來源、簽章
```

四個子目錄各自包含所需的來源、補丁、配置和建置輔助程式，可整個複製到其他位置獨立使用。Samba 用同一份來源管理客戶端與伺服器。

## 一次編譯全部

在本包根目錄執行：

```powershell
./build.ps1
```

依序編譯 `zstd` → `tar` → `busybox` → `samba`。任一步驟失敗就停止並回報失敗工具；四個均成功後才收集到外層 `out/`：

```text
out/
├── zstd
├── tar
├── busybox
├── smbclient
├── smbd
├── samba-dcerpcd
├── rpcd_classic
├── rpcd_lsad
├── rpcd_winreg
├── SHA256SUMS.txt
├── BUILD_MANIFEST.json
└── *-build.json              # 四個專案各自的建置資訊
```

每個工具的原始輸出、配置及日誌仍保留在自己的資料夾。若建置失敗，外層 `out/` 可能仍有之前成功的結果，請以此次執行是否完整結束為準。

**Samba 沿用最後一包的 ADB configure 探測及建置結尾的 smbclient 版本檢查，需要已授權、可使用 root 的 ARM64 Android 裝置。** 所有來源編譯與連結均在電腦執行，手機只執行該配方原有的短程式。多台裝置時指定序號：

```powershell
./build.ps1 -DeviceSerial 'DEVICE_SERIAL'
```

其餘三個工具單獨建置不需要 ADB。

## 只編譯一個

從本包根目錄執行任一行：

```powershell
./zstd/build.ps1
./tar/build.ps1
./busybox/build.ps1
./samba/build.ps1                       # smbclient、smbd 和四個 RPC 工具
./samba/build.ps1 -BuildScope client    # 只產出 smbclient
```

也可以先進入個別資料夾，再執行 `./build.ps1`。單獨編譯只更新該工具的輸出：

| 工具 | 個別輸出 | 既有建置設定 |
|---|---|---|
| zstd 1.6.0 固定提交 | `zstd/out-r30/zstd` | `-O3`、Full LTO、多執行緒 |
| GNU tar 1.35.90 | `tar/out/tar` | `-O2`、不啟用 LTO |
| BusyBox 1.38.0 | `busybox/out/busybox` | `-Os`、ThinLTO、68 個指令、ZIP Store／Deflate、U+10FFFF 字碼上限 |
| Samba | `samba/dist/android-arm64-size/` | `-Os`、ThinLTO；沿用加密依賴的 `-O2` 配方 |

本次沿用各專案的優化設定；tar 配方仍未啟用 LTO。四個專案都使用完整靜態連結。

## 環境與參數

需求：Windows PowerShell 5.1 或 PowerShell 7、Windows Python 3.12+、NDK r30、MSYS2。MSYS2 需有 `bash`、`make`、`gcc`、`python3`、`patch`、`bzip2` 及基本 shell 工具；Samba 另使用 Git for Windows 的 GPG、ADB，以及既有配方管理的 UCRT64 GCC、Flex／Bison、Perl 等建置依賴。

每個入口都會自動尋找 NDK：

1. `%USERPROFILE%\SambaAndroidBuild\toolchain\android-ndk-r30`
2. `ANDROID_NDK_HOME`
3. `%LOCALAPPDATA%\Android\Sdk\ndk\30.0.16248370`

zstd／tar／BusyBox 優先使用目前電腦的 Codex Python runtime，其次為 PATH 中的 `python`；Samba 沿用 MSYS2 的 `python3`。MSYS2 預設在 `C:\msys64`。

手動指定環境或編譯工作數：

```powershell
./build.ps1 -Ndk 'D:\Android\android-ndk-r30' -Msys 'C:\msys64' -Python python -Jobs 8
./build.ps1 -Adb 'D:\platform-tools\adb.exe' -Gpg 'C:\Program Files\Git\usr\bin\gpg.exe'
```

外層的 `-Jobs` 會傳給四個內層建置；`-Python` 用於 zstd／tar／BusyBox，Samba 繼續使用 MSYS2 Python。若使用者目錄含中文或空白，可指定純英文、不含空白或單引號的工作目錄：

```powershell
./build.ps1 -WorkRoot 'D:\AndroidToolsBuild'
```

這會分別使用 `D:\AndroidToolsBuild\tar`、`busybox`、`samba` 存放三個專案的建置暫存或快取。zstd 的編譯中間檔在自己的 `android-r30-direct/`。

個別入口的對應參數：

```powershell
./tar/build.ps1 -AsciiBuildRoot 'D:\AndroidToolsBuild\tar' -Jobs 8
./busybox/build.ps1 -CacheRoot 'D:\AndroidToolsBuild\busybox' -Jobs 8
./samba/build.ps1 -CacheRoot 'D:\AndroidToolsBuild\samba' -Jobs 8 -DeviceSerial 'DEVICE_SERIAL'
./zstd/build.ps1 -Jobs 8
```

tar／zstd 每次都重新編譯；BusyBox 依配置及補丁雜湊管理快取。`./build.ps1 -Clean` 會要求 BusyBox 和 Samba 重新準備其目標工作來源；Samba 仍沿用原配方保留已建置的加密依賴。

## 來源與更新規則

- zstd 固定提交 `01b7154f1172432f8abe9b3bb9909e14a1176b7d`，來源標頭版本為 1.6.0；檔案 SHA 在 `zstd/upstream_source_sha256.json`。
- tar 固定 GNU 1.35.90 測試版，原始壓縮包 SHA 與來源清單在 `tar/SOURCE_MANIFEST.json`。
- BusyBox 固定 1.38.0，包含最後的 Unicode 修正版；來源壓縮包 SHA 固定在 `busybox/build.py`。
- Samba 採對話最後的 `samba-android-arm64-ndkr30-api28-build-scripts.zip`。腳本仍會查詢官方最新穩定版；查詢失敗時，明確警告並採用最新快取版本。本包附上 4.25.0 及相同版本的加密依賴來源，首次先放入建置快取，仍執行原有簽章檢查。

前三個專案不會自動升級版本。Samba 自動查詢上游版本的行為沿用原建置包，未來的上游變更可能需要更新 Android 補丁；不保證任何未來版本直接建置成功。

tar／zstd 取自目前 `android_build_sync63/source/` 的乾淨來源，BusyBox 取自 `busybox_android/` 的 Unicode 修正版。Samba 的腳本、來源包出處及原始雜湊記錄在 `samba/ORIGIN.json`。本次調整建置入口參數、來源包使用及外層輸出收集；上游來源與編譯旗標沿用各自原配方。

## 本機建置驗證（2026-09-26 基準版本）

2026-10-05 新增的 Samba Android 暫存路徑補丁已納入每次建置的補丁流程，**本次尚未重新編譯或進行裝置測試**。下列結果及 `verification/` 記錄對應 2026-09-26 的基準版本；新補丁說明見 [samba/ANDROID-PATCHES.md](samba/ANDROID-PATCHES.md)。

**已在 Windows PowerShell 5.1 實際執行外層 `build.ps1`，四個專案與九個二進位全部建置成功，退出碼為 0。** 首次使用新的獨立工作目錄建置，修正 GPG／UCRT64 問題後，再由外層入口完整重跑；重跑沿用本次建立的依賴快取。

最終產物已檢查 AArch64、全靜態、16 KiB segment alignment 及 API28／NDK r30 識別資訊。版本、大小與 SHA256 見 [verification/README.md](verification/README.md) 和 [build-summary.json](verification/build-summary.json)。六份 PowerShell 腳本也通過 Windows PowerShell 5.1 語法解析。

Samba 執行了原有的 ADB configure 探測與備用機上的 `smbclient --version`，回報 4.25.0。**本次未重跑完整備份／還原或 SMB 伺服器功能測試**。建置日誌仍保留上游 configure、PIDL 與 Clang 的診斷訊息。

公開倉庫及來源 ZIP 包含原始碼、補丁、建置入口與驗證記錄；ELF 會由本機建置產生於 `out/`。

各配方使用私有靜態 CRT 的 Android 版本識別資訊修正，詳情見各工具文件。API 28 編譯目標及 ELF note 不代表已驗證 Android 9 執行相容性。

## 授權

本次新增的建置整合程式與文件採 **GPL-3.0-only**，全文見 `LICENSE`；上游程式各自保留原授權。範圍與第三方聲明見 [LICENSING.md](LICENSING.md)。

原授權隨各來源保留：zstd 的 `upstream/LICENSE` 與 `upstream/COPYING`；tar 的 `upstream/COPYING`；BusyBox 的 `LICENSE-BusyBox.txt` 及來源壓縮包；Samba 和加密依賴的授權位於 `upstream-source/` 原始壓縮包。BusyBox 的 libselinux、PCRE2 及 Android 補丁來源亦隨包提供。

## 目前下載

[2026-10-09 ELF 與完整來源包](https://github.com/YAWAsau/Android-for-arm64_elf/releases/tag/elf-20261009-r30-api28)。BusyBox 為新產物，其餘八個 ELF 沿用 2026-09-26 版本；Samba 新增路徑補丁尚未編入本次產物。API 28 實機相容性未驗證。
