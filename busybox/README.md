# BusyBox 1.38.0 SpeedBackup 專用精簡建置包（ZIP Store／Deflate、Unicode 範圍修正）

Windows 本機編譯，使用已安裝的 NDK r30（30.0.16248370）、ARM64／API 28 編譯目標、完整靜態連結、`-Os` 與 ThinLTO。

v858：直接連入 `arc4random_kernel.c` 的無狀態 `getrandom` 實作，修正部分舊核心不支援 `MADV_WIPEONFORK` 時的啟動中止。已安裝的 NDK 不修改；亂數來源錯誤仍中止。備用機程序級沙盒可重現此限制，但不代表完整 Android 11 ROM 測試。

本配置保留 **68 個指令**，依目前 SpeedBackup 的入口、備份、還原、更新、診斷與備援分支整理。需搭配原有整套工具；`tar`、`find` 使用工具目錄已有的獨立版本。

## 使用方式

解壓縮整包後，在此目錄執行：

```powershell
./build.ps1
```

產物在 `out/busybox`。本建置不需要 ADB，也不會將產物安裝到手機。

```powershell
# 指定已安裝的 NDK
./build.ps1 -Ndk C:\Android\android-ndk-r30

# 重新編譯
./build.ps1 -Clean

# 更改工作快取（需英文且不含空白的路徑）
./build.ps1 -CacheRoot D:\BusyBoxAndroidBuild -Jobs 8
```

需求：Windows PowerShell 5.1 或 PowerShell 7、Windows Python 3.12+、MSYS2（gcc、make、python、patch、bzip2 與基本 shell 工具）、NDK r30。
腳本優先使用此電腦已備妥的 Python 與 `%USERPROFILE%\SambaAndroidBuild\toolchain\android-ndk-r30`；亦可使用 `-Python`、`-Msys`、`-Ndk` 指定路徑。

來源包與補丁已隨附。`build.py` 固定所有來源 SHA256；若來源包缺少會下載相同版本。BusyBox 版本固定 **1.38.0**，不會自行升級其他版本。

## 保留的功能

基準為使用者提供的 `BusyBox v1.36.1.1 topjohnwu`：

- 基準檔案 SHA256：`4d60ab3f5a59ebb2ca863f2f514e6924401b581e9b64f602665c008177626651`。
- 保留 **68 個 applets**，從原始 358 個移除 290 個。每次建置比對完整保留清單及必要功能旗標，任何額外遺漏、新增或必要選項消失都會停止交付。
- `config/keep-applets.txt` 與 `config/removed-applets.txt` 分別記錄完整保留／移除清單；`config/profile.json` 記錄選擇理由、腳本雜湊、必要選項與外部工具依賴。
- 以上資料及配置均納入快取識別，修改後自動重新配置與編譯。`./build.ps1` 持續使用這份配置。
- `config/reference.config` 是原檔的 `bbconfig`，`config/android.config` 是移植到 1.38 的完整配置。
- 保留 Android shell 路徑、`ASH_STANDALONE=1`／`ash -o standalone`、自身重新執行路徑、靜態 DNS、mount 與 SELinux 相容補丁。
- libselinux、PCRE2 一併靜態編譯並套用 ThinLTO。
- 保留 NDK 預設保護設定；連結使用 `--gc-sections`、`--icf=safe` 與 16 KiB segment alignment。

新版上游本身仍可能改變指令行為。相同 applet 清單不等於所有選項與執行行為完全相同。

## 保留的指令

```text
[ [[ ash awk basename cat chcon chmod chown cksum clear cmp comm cp cut
date dd df dirname du echo getenforce grep head id ifconfig ip kill ln ls
md5sum mkdir mkfifo mktemp mount mv nc nohup paste printf ps pwd readlink
renice rev rm rmdir sed seq sh sha256sum sleep sort stat tail test timeout
touch tr true uname uniq unzip usleep wc which whoami xargs
```

`chcon`、`getenforce`、`comm`、`usleep`、`nc` 均有實際呼叫，故保留。也保留 `ip addr/route`、`nc -w/-z`、`unzip -l/-p/-o/-d` 所需配置。

## 中文檔名與 Unicode 範圍

- 使用 BusyBox 內建 UTF-8 處理，Unicode、寬字元與組合字元支援均保留；不依賴 `LANG`／`LC_ALL` 啟用。
- 前版已支援常用繁簡中文，但 BusyBox 1.38.0 的 `include/unicode.h` 會將配置值 `0` 或 `>= 0x30000` 強制改成 `0x2FFFF`。因此 `ls` 的可列印字元處理會將較新的 U+30000 以上擴展漢字換成 `?`。
- 本版將 `CONFIG_LAST_SUPPORTED_WCHAR` 明確設定為 `1114111`（U+10FFFF），並修正上述標頭的上限；只改 `.config` 仍會被原始標頭覆蓋。原有 U+20000–U+3FFFF 漢字雙欄寬度處理繼續使用。
- 必要的 Unicode 配置與不依賴 locale 的設定均納入建置檢查，補丁與配置變更會自動使舊快取失效。
- 此修正擴大字碼範圍，未更新上游字寬資料表；不可列印或不合法字元仍沿用原有替代處理。終端字型也必須包含對應字形。尚未做手機顯示實測。

## ZIP 解壓格式

- `unzip` 保留 Store（不壓縮）與 Deflate，一般 ZIP 更新包可使用這兩種格式。
- 已關閉 BZIP2／LZMA／XZ 的 ZIP 解壓、透明解壓與獨立指令入口。
- 內建說明改存未壓縮文字，並關閉壓縮配置與內嵌腳本，避免重新帶入 BZIP2 解碼器。完整說明內容仍保留。
- 建置會檢查關閉的配置，以及三份解碼器物件均未納入編譯；一鍵建置會持續套用此限制。
- 使用 BZIP2／LZMA／XZ 壓縮的 ZIP 項目不再支援解壓。

## 外部依賴與適用範圍

- GNU `tar` 與獨立 `find` 是原腳本 SHA 驗證的核心工具。腳本明確跳過 BusyBox `tar` 連結，且不會以 BusyBox 連結蓋掉已有的 `find`，本版因此移除兩個重複 applet。
- 原有 `zstd`、`jq`、`smbclient`、`speednative`、DEX 與 Android 系統工具繼續由原工具組提供。
- 此配置不是通用 BusyBox；不涵蓋任意自訂 hook、其他模組或獨立發佈維護腳本。腳本改版若新增外部指令，需重新審查保留清單。
- 分析包含文字盤點、指令語境複核及 DEX／原生工具字串檢視。語法解析器對部分 mksh 語法有恢復錯誤，僅作輔助；尚未做手機功能測試。

## Android 版本標記與相容性

r30 共用的靜態 `crtbegin_static.o` 帶有 Android 37 的標記。本建置在工作快取產生私有副本，僅將 `.note.android.ident` 換成官方 API 28 動態 CRT 內的 `28 / r30 / 16248370` 資料，並在靜態連結時選用該副本。**沒有連結動態 CRT 程式碼，也沒有修改已安裝的 NDK。**

這是版本識別資訊調整；仍使用 r30 的靜態 Bionic 執行庫。NDK 因此可能顯示「static executable 的 APP_PLATFORM 不是最新 API」提示。該提示會保留在建置日誌。API 28 目標與 `file` 顯示均不保證 Android 9 執行相容性。

本整合源碼包已由外層 `build.ps1` 在 Windows PowerShell 5.1 完成本機編譯、ELF 結構與配置檢查；共 68 個指令，採 ThinLTO。結果記錄於外層 `verification/`。**尚未進行新版的手機執行與功能測試**。

## 建置後的輸出

- `out/busybox`：完整靜態 ELF。
- `out/applets.txt`、`out/busybox.config`：指令清單與實際配置。
- `out/BUILD_MANIFEST.json`：NDK、來源、優化、ELF 與基準資料。
- `out/SHA256SUMS.txt`、`out/elf-info.txt`、`out/build.log`：校驗碼與建置記錄。

隨附 `upstream/`、`patches/` 為對應來源與可重複套用的修改；`USAGE-AUDIT.md` 保存此配置先前的指令盤點與體積記錄。本資料夾可以獨立搬走使用。

目前備份腳本內有固定 BusyBox SHA256 的核心工具驗證表。日後手動替換二進制時，需同步更新該表中的 BusyBox 雜湊。

## 來源與授權

BusyBox 官方將 1.38.0 的初版公告標記為 unstable。來源與公告：
https://busybox.net/news.html
https://busybox.net/downloads/busybox-1.38.0.tar.bz2

Android 補丁基於 topjohnwu/ndk-box-kitchen 的提交 `14d189ea3070a8167b3576bf83fe070d4a3441af`，移植 ash 變更到 1.38；完整合併補丁在 `patches/android-1.38.patch`：
https://github.com/topjohnwu/ndk-box-kitchen

libselinux 固定於提交 `48fcf8bba0635dc597bef75994294fd055d9f0ba`：
https://github.com/topjohnwu/selinux

PCRE2 採 Android `android-15.0.0_r1` 原始碼：
https://android.googlesource.com/platform/external/pcre/

BusyBox 為 GPLv2；libselinux 與 PCRE2 各自授權全文保留於隨附原始碼包中。重新散布二進制時，應一併提供本建置包中的對應來源、補丁、配置及授權。
