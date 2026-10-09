# NDK r30 舊核心相容性修正

BusyBox、tar、zstd、smbclient 的新版產物使用 stateless getrandom arc4random，避免舊核心不支援 MADV_WIPEONFORK 時 abort。保留 EINTR 重試、短讀補齊及取亂數失敗時中止。安裝的 NDK 未修改。

來源為 SpeedBackup v858 修正。2026-10-09 既有紀錄：Xiaomi 13 的程序級 seccomp 沙盒分別模擬 ENOENT/EINVAL，四個舊工具 rc134，新工具通過；壓縮、中文檔名、連結、亂數 fork/threads/uniform/errno 與 SMB 傳輸驗證通過。未有 Android 11 實機驗證；此處未重新執行測試。

smbclient 同時包含 stream-v1 FIFO 上傳修正。對應實際建置配方另附 NATIVE_SOURCE_BUILD_KIT。整合配方保留 Android runtime-path 補丁；此額外組合未重新編譯，不宣稱目前 smbclient 包含路徑補丁。

smbd、samba-dcerpcd、rpcd_classic、rpcd_lsad、rpcd_winreg 仍為 2026-09-26 產物，未包含本次 arc4random 修正。共用 Samba 建置配方已接入修正，伺服端仍需重建及測試。
