# SpeedBackup 專用 BusyBox 精簡記錄

## 分析範圍

分析使用 M:/虛擬分區 的 start.sh、tools/tools.sh、根目錄 tools.sh、tools/dex_check.sh 本機副本；四份腳本於建立此配置時確認與前次盤點雜湊相同。另讀取配套 classes.dex、speednative、cmd、keycheck 做靜態字串檢視。
涵蓋入口、備份、還原、更新、診斷及備援分支。所有輸入雜湊、保留理由、必要配置及引用行號記錄在 config/profile.json。

## 選擇結果

原始 358 個指令的文字盤點有 89 個名稱命中。逐項排除變數、日誌、AWK/jq 函式與專用工具提供的指令，再保留 sh 所需 ash 實作，共保留 **68 個指令**，累計移除 **290 個**。
保留清單：config/keep-applets.txt；移除清單：config/removed-applets.txt。建置會精確比對這兩份清單及必要選項。

```text
[ [[ ash awk basename cat chcon chmod chown cksum clear cmp comm cp cut date dd df dirname du echo getenforce grep head id ifconfig ip kill ln ls md5sum mkdir mkfifo mktemp mount mv nc nohup paste printf ps pwd readlink renice rev rm rmdir sed seq sh sha256sum sleep sort stat tail test timeout touch tr true uname uniq unzip usleep wc which whoami xargs
```

## 關鍵保留項目

- chcon、getenforce：還原檔案 SELinux context 與狀態顯示。
- comm、cksum、md5sum、sha256sum：清單比較、遠端路徑鍵值與工具完整性驗證。
- usleep、timeout、nohup、renice、ps、kill：等待、程序與背景服務處理。
- nc：保留 -w/-z 探測；ip 保留 addr/route；ifconfig 保留既有備援路徑。
- unzip：更新包 -l/-p/-o/-d 操作；保留 Store／Deflate 格式。
- ash/sh、[、[[、test：shell 與條件判斷；保留 Android 路徑及 standalone 相容補丁。

## 中文檔名與 Unicode 範圍修正

- 前版已開啟 UTF-8 與中文寬字元支援，常用繁簡中文在原有支援範圍內。
- 上游 include/unicode.h 將配置 0 或 >= 0x30000 改為 U+2FFFF，導致 U+30000 以上擴展漢字在 ls 可列印字元處理中被換成問號。
- 本版配置明定 U+10FFFF，並同步修正標頭上限；保留既有字元合法性過濾與 U+20000–U+3FFFF 雙欄寬度處理。
- 建置檢查 Unicode、寬字元、組合字元及不依賴 LANG／LC_ALL 的配置。未更新上游字寬資料表，未做手機顯示實測。

## 解碼器精簡

- 依使用者要求，關閉 unzip 的 BZIP2／LZMA／XZ 格式與三者的透明解壓功能。
- 內建說明改存原文；壓縮配置與內嵌腳本也關閉，避免帶入 BZIP2 內部解碼器。說明內容仍保留。
- 建置檢查三份 decompress_bunzip2.o、decompress_unlzma.o、decompress_unxz.o 均不在編譯物件清單。
- 本版僅處理解壓 Store／Deflate 的 ZIP 項目；BZIP2／LZMA／XZ 的 ZIP 項目不再支援。

## 文字命中但不是 BusyBox 呼叫

| 名稱 | 實際用途 |
|---|---|
| split | AWK/jq 函式與 split APK 描述 |
| ts | 腳本自訂繁簡轉換函式，呼叫 DEX |
| diff、top、ipaddr | Shell 變數 |
| install | Android PackageManager 操作及日誌 |
| ping、resume、reset | Daemon／原生工具／函式的參數 |
| tty、uptime | /dev/tty、/proc/uptime 路徑 |
| route | ip route 子命令；其功能保留在 ip |
| env、link、patch、script、time、tree、yes、false | 路徑、日誌、設定值或 case 模式 |

## 已由配套工具提供

- tar：既有 GNU tar 是 SHA 驗證的核心工具；安裝程式明確跳過 BusyBox tar 連結。
- find：既有獨立 find 是 SHA 驗證的核心工具，且腳本使用 -printf 等 GNU 功能；BusyBox 安裝不會覆蓋實體工具。
- zstd、jq、smbclient、speednative、DEX 及 Android 系統工具繼續由原工具組提供。

## 實際體積

| 版本／配置 | 指令數 | ELF 大小 |
|---|---:|---:|
| 舊版 1.36.1.1 | 358 | 1,710,600 bytes（1.63 MiB） |
| 1.38.0 完整 LTO 版 | 358 | 2,102,136 bytes（2.00 MiB） |
| 1.38.0 trim41 LTO 版 | 317 | 2,029,496 bytes（1.94 MiB） |
| 前一版 SpeedBackup LTO（保留額外解碼器） | 68 | 937,264 bytes（915 KiB） |
| 前一版 SpeedBackup LTO（ZIP Store／Deflate） | 68 | 932,144 bytes（910.3 KiB） |
| 本版 SpeedBackup LTO（ZIP Store／Deflate、Unicode 範圍修正） | 68 | 932,208 bytes（910.4 KiB） |
| 使用者提供的小體積樣本 | 118 | 555,272 bytes（542 KiB） |

本版相較前一份 317 指令版減少 1,097,288 bytes（54.07%）。
相較保留額外解碼器的 68 指令版減少 5,056 bytes（0.54%）。
本次 Unicode 範圍修正相較 ZIP Store／Deflate 前版體積變動為 +64 bytes。
為完整移除 BZIP2 內部解碼器，說明文字改存原文，因此抵消了部分程式碼縮減的體積。
118 指令樣本的完整配置與工具鏈未知，不能只用指令數預測大小。本版沿用 NDK r30、API 28 編譯目標、完整靜態及 ThinLTO。

## 已完成與限制

- 已完成本機編譯、生成指令表精確比對、必要選項檢查，以及 ELF 無動態載入器／無外部共享庫依賴檢查。
- 語法解析器對部分 mksh 結構有恢復錯誤，所以只用作輔助，選擇依據包含原文人工語境複核。靜態分析不能證明所有動態或未來呼叫。
- 尚未進行手機功能測試；Android 9 執行相容性仍未驗證。
- 此配置不涵蓋任意自訂 hook、其他模組及獨立發佈維護腳本。
- 使用時仍需原有完整配套工具。替換 BusyBox 時須同步更新備份腳本核心工具 SHA256。
