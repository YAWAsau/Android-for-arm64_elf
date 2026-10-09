# Android 補丁與官方更新

## 目前版本

最近實際建置的 Samba 為 **4.25.0**，使用 NDK r30（30.0.16248370）、ARM64／API 28、全靜態連結，預設 `-Os`／ThinLTO。2026-09-26 的建置記錄見外層 `verification/`。本次 2026-10-05 的新增補丁尚未重新編譯或進行裝置測試。

`build.ps1` 的 Samba 版本不是固定值：每次查詢官方最新穩定版並驗證來源簽章。只有查詢失敗時才警告並選用最新來源快取。其他工具與加密依賴的更新規則不受影響。

## 每次編譯都套用

1. `build.ps1` 選取並驗證官方源碼。
2. `build-samba.sh` 在 Waf 配置及編譯之前呼叫 `patch-samba.py`，來源快取也走相同流程。
3. 新增的路徑補丁要求來源區塊唯一且完整匹配；已套用時直接沿用。檔案移動或區塊變更就中止，需維護補丁後重跑。
4. 成功建置後，`build-metadata.json` 記錄 `android_patchset = android-runtime-paths-v1` 及 `android_patch_recipe_sha256`。外層建置收集為 `out/samba-build.json`。

這套流程可把補丁重複套用到可匹配的新版官方源碼；無法預先保證未來的上游結構或 API 永遠相容。更新來源版本不會自動改寫本地補丁。

## 本次移植

對照來源是使用者提供的 `Android_Samba_smbd_fixed_source.tar.gz`，版本為 **4.5.1**，SHA256：

```text
848d959fd9cbc31d43bbab3908f81a9f31f128f194d424ed825ae5a5acef1df4
```

與官方 Samba 4.5.1 原始碼對照後，按 4.25.0 的實際程式位置重新實作以下 Android 修正：

| 程式位置 | 新增行為 |
|---|---|
| `lib/util/util.c` | 未指定 `TMPDIR` 時，`tmpdir()` 預設使用 `/data/local/tmp`；IPC$ 原本就呼叫此函式，因此一併適用。 |
| `auth/credentials/credentials_krb5.c` | 啟用 Samba 檔案式憑證快取且未指定快取名稱時，使用 `tmpdir()` 組合路徑。 |
| `third_party/heimdal/lib/base/expand_path.c` | `%{TEMP}` 依序使用非空的 `TEMP`、`TMPDIR`，最後預設 `/data/local/tmp`；保留 `secure_getenv` 的權限語義。 |
| `source3/smbd/smb1_process.c` | 原有高除錯等級的封包輸出使用 `tmpdir()`；未啟用任何額外除錯或協定功能。 |

所有新程式碼以 `__ANDROID__` 限定；保留非 Android 的原行為。服務可以透過自己的環境變數指定私有、可寫的暫存目錄。這些是路徑相容性修正，沒有新增輪詢或常駐行程，也沒有測得速度或功耗提升。

現有配方已包含 Bionic 空 `passwd` 欄位處理及 `umask(0077)` 修正。既有 smbd 的 ELF 記錄顯示 TLS 對齊為 `0x40`，因此未額外注入 TLS 資料。

## 未採用的參考改動

- `berserker.c` 把部分帳號（包括 nobody）對應到 UID／GID 0，不適合沿用到本配方。
- 跳過目錄擁有者檢查、passdb 初始化，以及忽略或重解釋部分加密／認證設定的處理，不屬於可直接移植的 Android 路徑修正。
- 舊 netlink `getifaddrs` 替代實作有 `ifa_addr = NULL` 的賦值判斷；目前 API 28 的 NDK 已提供 `getifaddrs` 宣告，未引入這套舊替代程式。
- 舊 Linux／NDK 建置腳本及允許重複符號的連結選項不適用於現有 Windows 本機配方。

參考包沒有作為新的上游來源，也沒有被執行；它不隨本來源包重新分發。

## 參考來源

- [官方 Samba 4.5.1 原始碼](https://download.samba.org/pub/samba/stable/samba-4.5.1.tar.gz)：用於區分參考包的修改。
- [Google Samba Documents Provider](https://github.com/google/samba-documents-provider)：基於 Samba 4.5.1 的 Android 客戶端／`libsmbclient.so` 移植參考。
- [elliott10/samba-4.5.1](https://github.com/elliott10/samba-4.5.1)：舊 NDK 交叉編譯參考。
- [berserker/android_samba](https://github.com/berserker/android_samba)：舊 Android Samba 移植參考。
