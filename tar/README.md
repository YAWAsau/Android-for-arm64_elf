# GNU tar Android arm64 建置

需求：Windows、Python 3.11+、MSYS2（預設 `C:/msys64`，含 make 等建置工具）、NDK r30 `30.0.16248370`。

```powershell
./build.ps1
./build.ps1 -Ndk 'C:/path/to/ndk/30.0.16248370' -Msys 'C:/msys64' -Python python
./build.ps1 -Jobs 8
```

從整包根目錄執行時使用 `./tar/build.ps1`。Python 入口的進階選項可用 `python build.py --help` 查閱。

上游是 GNU tar 1.35.90；`SOURCE_MANIFEST.json` 保存原始壓縮包來源、SHA256、裁剪項目和本包完整來源雜湊。`upstream/` 必須按清單完整保留，不能任意刪除或轉換換行。

入口會自動尋找既有 NDK r30（SambaAndroidBuild、ANDROID_NDK_HOME 或 Android SDK 安裝路徑），並優先使用此電腦的 Codex Python runtime，找不到時使用 PATH 中的 python。`-Jobs` 控制並行編譯數，預設 8；`-AsciiBuildRoot D:\TarAndroidBuild` 可指定英文建置暫存目錄。本資料夾可獨立搬走使用。

參數：API 28、`-O2`、不啟用 LTO、全靜態 AArch64、16 KiB segment。`android_build_note.py` 在私有暫存目錄準備符合 API 28／NDK r30 的 CRT 識別資訊。

編譯進度即時輸出；成功產物在 `out/tar`，日誌在 `out/build.log`，建置資訊在 `out/BUILD_MANIFEST.json`。失敗時保留並顯示暫存目錄以供診斷。

建置腳本檢查 ELF 架構、靜態連結、segment alignment 和 Android note；實機相容性需另行驗證。上游授權見 `upstream/COPYING`。
