# 2026-10-09：補齊 v858 NDK r30 相容產物

同步 tar、zstd、smbclient 的 getrandom 相容版本與配方，BusyBox 已包含。保留 FIFO 上傳補丁及整合來源的 Android 路徑修正。smbd/RPC 未重建，不能視為已修復；測試範圍見 verification/NDK-R30-COMPAT.md。

# 2026-10-09：發布目前 ELF 與最新配方

BusyBox 更新為 kernel getrandom / arc4random 相容版本（929328 bytes），API 28 實機相容性未驗證。其餘八個 ELF 沿用 2026-09-26 產物；Samba 路徑補丁只更新來源，尚未重建。發布清單見 `verification/release-20261009.json`。

# 2026-10-05：Android 暫存路徑補丁

- 以目前 Samba 4.25.0 對照使用者提供的 Android Samba 4.5.1 源碼包，移植適合新版的暫存路徑修正。
- Android 的 Samba `tmpdir()` 預設改為 `/data/local/tmp`，IPC$ 也沿用此預設；Samba 檔案式 Kerberos 快取及 SMB1 診斷封包改用 `tmpdir()`。
- 現代 Heimdal `%{TEMP}` 保留安全環境變數讀取，依序使用 `TEMP`、`TMPDIR`、`/data/local/tmp`。只修改 Android 分支。
- 新增補丁每次編譯前都會執行，支援已套用的來源快取；來源區塊不匹配就報錯中止。成功建置的 metadata 記錄補丁版本及配方 SHA256。
- 未移植參考包中的身分映射、權限檢查繞過或認證語義修改。現有 ThinLTO 配方不變。
- 本次只更新源碼建置配方，尚未重新編譯或進行裝置測試；下列初始整合版的建置記錄保留為歷史結果。

# 初始整合版（2026-09-26）

- 整理 zstd、GNU tar、BusyBox、Samba 為四個可獨立使用的源碼目錄；Samba 共用來源建置 smbclient、smbd 和四個 RPC 工具。
- 外層 `build.ps1` 依序呼叫各專案，全部成功後收集九個 ELF、SHA256 與建置資訊。
- 保留 NDK r30／API 28／ARM64／全靜態設定。zstd 保留 Full LTO，BusyBox／Samba 保留 ThinLTO，tar 沿用不開啟 LTO 的既有配方。
- 保留 BusyBox 68 個指令、ZIP Store／Deflate 精簡配置，以及 U+10FFFF 的 Unicode 範圍修正。
- Samba 採用對話最後的 r30 配方，補齊其來源壓縮包與簽章，支援指定 NDK、MSYS2、快取與工作數。
- 修正 Samba 在 PowerShell 5.1 將 GPG 首次建立金鑰庫提示當成致命錯誤的問題，仍檢查原生退出碼與指定的簽章指紋。
- 修正 UCRT64 只檢查資料夾存在、未確認主機編譯器是否完整的問題，以及重試複製造成的重複目錄層級。
- 統一 Samba shell 輔助程式為 LF 換行，並在成功或失敗後結束該次私人金鑰庫的 GPG agent，讓 Windows 日誌管線正常關閉。
- 本倉庫原創整合程式採 GPL-3.0-only；第三方程式維持原授權。

Windows PowerShell 5.1 的完整外層建置已通過，退出碼為 0；九個產物的 ELF、大小及 SHA256 記錄於 `verification/build-summary.json`。Samba 的 ADB configure 探測及 smbclient 版本檢查通過，完整手機功能測試未重跑。
