# 本機完整建置記錄

外層 `build.ps1` 已在 Windows PowerShell 5.1 執行，依序完成四個專案、九個二進位的本機建置。
使用 NDK r30 30.0.16248370、ARM64/API28、8 個編譯工作。首次在新的獨立工作目錄建置，修正腳本問題後，再由外層入口完整重跑並通過；重跑沿用這次建立的依賴快取。

| 產物 | bytes | SHA256 |
|---|---:|---|
| zstd | 1,010,920 | `47d984b267efe90e223cd5338e37f661ad3ced6cae5daae62d887fa724408e81` |
| tar | 1,247,024 | `45f372224da44d0e2f18da92926ecf9018224337d7f5b046e4a5aacea5701073` |
| busybox | 932,208 | `51df9a8e1d8d2669c03eff48d3bf49e029c56903634e63acd2a7f539385d0867` |
| smbclient | 7,549,864 | `534efa4a802e3c5ac23048415db144742af2dcc3980a7edb76d15417d2a7ed69` |
| smbd | 11,151,352 | `f3776f82870ce6025bb7d94688e14b117681e27252cc466ca222869ddff86227` |
| samba-dcerpcd | 5,855,080 | `d67922a07b6c874757ec0b06f9f6789d92b2689bb55702048c5c8f86ebdf48a6` |
| rpcd_classic | 13,806,336 | `5261b6ae89ccb777d2a418412f6284f22e5148ce88b54729262626e7dea0d966` |
| rpcd_lsad | 8,810,128 | `bf37062b93d67216581562edadc57bca45a5a314be15008baa20e197bfe1460a` |
| rpcd_winreg | 6,983,600 | `2243c39c8e6a07a7d9819d9983f82070c9db3dc815e7458f19581b8f417542ea` |

全部 ELF 均為 AArch64 ET_EXEC，無 PT_INTERP／DT_NEEDED，segment alignment 至少 16 KiB，Android note 為 API28／NDK r30。

Samba 沿用原有 ADB configure 探測與 smbclient 版本檢查。未執行完整備份／還原或 SMB 伺服器功能測試；Android 9 執行相容性未驗證。

詳細機器可讀記錄見 `build-summary.json`。
