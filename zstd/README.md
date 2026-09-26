# zstd Android arm64 建置

需求：Windows、Python 3.11+、NDK r30 `30.0.16248370`。

```powershell
./build.ps1
./build.ps1 -Ndk 'C:/path/to/ndk/30.0.16248370' -Python python
./build.ps1 -Jobs 8
```

從整包根目錄執行時使用 `./zstd/build.ps1`。需要同步腳本內的 zstd SHA 時加上 `-SpeedBackupRoot`，指定含 `tools/tools.sh` 的根目錄；舊式根目錄 `tools.sh` 亦相容。此參數只更新 SHA，不搬移二進位。

上游固定於 commit `01b7154f1172432f8abe9b3bb9909e14a1176b7d`；來源與 SHA256 見 `upstream_source_sha256.json`。`upstream/` 必須完整保留，包含授權和 host 模式所需測試源碼。

入口會自動尋找既有 NDK r30（SambaAndroidBuild、ANDROID_NDK_HOME 或 Android SDK 安裝路徑），並優先使用此電腦的 Codex Python runtime，找不到時使用 PATH 中的 python。`-Jobs` 控制並行編譯數，預設 8。本資料夾可獨立搬走使用。

參數：API 28、`-O3`、Full LTO、多執行緒、全靜態 AArch64、16 KiB segment。`android_build_note.py` 在私有暫存目錄準備符合 API 28／NDK r30 的 CRT 識別資訊。

成功產物為 `out-r30/zstd`；中間產物和逐檔編譯日誌在 `android-r30-direct/`。建置會檢查 ELF 架構、靜態連結、alignment 和 Android note；實機相容性需另行驗證。

上游授權見 `upstream/LICENSE` 和 `upstream/COPYING`。乾淨源碼打包入口會排除編譯產物與日誌。
