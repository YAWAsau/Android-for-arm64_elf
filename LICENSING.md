# 授權範圍 / Licensing scope

本倉庫將四個獨立建置專案放在一起管理。

## GPL 3.0

本次新增的外層 `build.ps1`、自行撰寫的建置整合程式與文件，除另有標示者外，採 **GNU General Public License v3.0 only（SPDX: GPL-3.0-only）**。完整條文見根目錄 `LICENSE`。

This repository's original build orchestration, original integration code and documentation are licensed under GNU GPL version 3 only, unless a file states otherwise. The full text is in `LICENSE`.

## 上游程式保留原授權

根目錄的 GPL 3.0 不會改變第三方程式、補丁中引用的上游程式碼及隨附依賴的授權。

| 來源 | 授權文件 |
|---|---|
| BusyBox | **GPL-2.0-only**；`busybox/LICENSE-BusyBox.txt` 與來源包中的 `LICENSE` |
| GNU tar | GNU GPL 第 3 版或更新版本；`tar/upstream/COPYING` 及各來源檔標頭 |
| Samba | GNU GPL 第 3 版或更新版本為主；`samba/upstream-source/samba-*.tar.gz` 中的 `COPYING`、`COPYING.LIB` 及各檔案授權標示 |
| zstd | 保留上游 BSD／GPLv2 雙授權選項，見 `zstd/upstream/LICENSE`、`zstd/upstream/COPYING` 及各檔案標頭 |
| GMP、Nettle、GnuTLS、Parse::Yapp、libselinux、PCRE2、NDK Box Kitchen | 依各來源壓縮包內的授權文件及檔案標頭；未以本倉庫 LICENSE 重新授權 |

BusyBox 的衍生程式碼與 BusyBox 補丁仍依其 GPLv2 授權；不得把整個 BusyBox 改標為 GPLv3。[BusyBox 官方授權說明](https://busybox.net/license.html)。

Third-party source code retains its original license. In particular, BusyBox and modifications derived from BusyBox remain GPL-2.0-only. The repository-level GPL-3.0-only license does not relicense any upstream component. Consult the bundled source archives and file headers for the full set of third-party notices.

## 對應來源

本倉庫保留固定來源、來源雜湊、補丁與建置配置。散布自行建置的二進位時，也應提供該次建置所使用的對應來源與修改；Samba 若更新到新的上游版本，需同步保留該版來源與建置資訊。
