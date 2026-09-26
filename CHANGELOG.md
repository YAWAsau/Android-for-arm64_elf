# 初始整合版

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
