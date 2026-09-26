"""Generate NDK sources from BusyBox's configured Kbuild files without shell forks."""
from pathlib import Path
import re
import subprocess

root = Path.cwd()
src = root / 'busybox'
# Let GNU Make evaluate continuations, helper variables and conditionals.
# Regex-only parsing misses COMMON_FILES, := assignments and multiline lists.
collector = ['include busybox/.config', 'ARCH := arm64',
             '$(file >configured-objects.txt,)']
for kbuild in sorted(src.rglob('Kbuild')):
    directory = kbuild.parent.relative_to(root).as_posix() + '/'
    collector += ['lib-y :=', 'obj-y :=',
                  'include ' + kbuild.relative_to(root).as_posix(),
                  '$(file >>configured-objects.txt,$(addprefix ' + directory
                  + ',$(filter %.o,$(lib-y) $(obj-y))))']
collector += ['.PHONY: collect', 'collect: ; @:']
(root/'collect.mk').write_text('\n'.join(collector)+'\n', newline='\n')
subprocess.run(['make', '--no-print-directory', '-f', 'collect.mk', 'collect'], check=True)
files = set()
for obj in (root/'configured-objects.txt').read_text().split():
    base = root / obj
    source = base.with_suffix('.S')
    if not source.is_file(): source = base.with_suffix('.c')
    if not source.is_file(): raise SystemExit(f'Missing source: {source}')
    files.add(source.relative_to(src).as_posix())
header = 'LOCAL_PATH := $(call my-dir)\n' + '\n'.join((src/'Makefile').read_text().splitlines()[:3]) + '\n'
header += (root/'busybox.mk').read_text()
(src/'Android.mk').write_text(header + '\n'.join(f + ' \\' for f in sorted(files))
                             + '\n\ninclude $(BUILD_EXECUTABLE)\n', newline='\n')
print(f'Generated NDK recipe with {len(files)} source files.')
