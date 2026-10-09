"""Windows local BusyBox 1.38.0 build; NDK r30, ARM64/API28, static ThinLTO."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent
REVISION = '30.0.16248370'
RECIPE_FILES = ('build.py', 'generate.sh', 'generate-makefile.py', 'arc4random_kernel.c', 'prepare_compat_libc.py',
                'config/android.config', 'config/reference-applets.txt',
                'config/removed-applets.txt', 'config/keep-applets.txt',
                'config/profile.json', 'patches/android-1.38.patch')
SOURCES = {
    'busybox-1.38.0.tar.bz2': ('https://busybox.net/downloads/busybox-1.38.0.tar.bz2',
        '34f9ea6ff8636f2c9241153b9114eefa9e65674a45318ae1ef95bb5f31c53bb2'),
    'ndk-box-kitchen.tar.gz': ('https://codeload.github.com/topjohnwu/ndk-box-kitchen/tar.gz/14d189ea3070a8167b3576bf83fe070d4a3441af',
        'e184cefe7c8ec5d9b0182ded726aa15e0b5e1445a52124cd310eac21d1a34c23'),
    'selinux.tar.gz': ('https://codeload.github.com/topjohnwu/selinux/tar.gz/48fcf8bba0635dc597bef75994294fd055d9f0ba',
        '47bb9702c1e447a4f0692e4d1d27c9c9fd7d8128e331c153326bcac48871fb1e'),
    'pcre.tar.gz': ('https://android.googlesource.com/platform/external/pcre/+archive/refs/tags/android-15.0.0_r1.tar.gz',
        '397b6033f171bd5d0ab6ede9581b526565558df9b510803366673e759e21aa59'),
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def recipe_hash():
    return hashlib.sha256(''.join(sha(ROOT/name) for name in RECIPE_FILES).encode()).hexdigest()

def applet_policy():
    reference = (ROOT/'config/reference-applets.txt').read_text(encoding='utf-8-sig').splitlines()
    removed = (ROOT/'config/removed-applets.txt').read_text(encoding='utf-8-sig').splitlines()
    keep = (ROOT/'config/keep-applets.txt').read_text(encoding='utf-8-sig').splitlines()
    profile = json.loads((ROOT/'config/profile.json').read_text(encoding='utf-8'))
    for label, names in (('reference', reference), ('removed', removed), ('keep', keep)):
        if any(not n or n != n.strip() for n in names) or len(names) != len(set(names)):
            raise RuntimeError('Invalid or duplicate names in '+label+' applet list')
    if set(removed) - set(reference):
        raise RuntimeError('Removed applets absent from reference: '+str(sorted(set(removed)-set(reference))))
    expected = set(reference) - set(removed)
    if not expected:
        raise RuntimeError('The applet configuration must retain at least one command')
    if expected != set(keep) or sorted(keep) != sorted(profile['kept_applets']):
        raise RuntimeError('Keep, removed and profile applet lists disagree')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',profile['name']):
        raise RuntimeError('Invalid build profile name')
    return reference, removed, expected, profile

def posix(path):
    value = str(Path(path).resolve()).replace('\\', '/')
    if not re.match(r'^[A-Za-z]:/', value):
        raise ValueError('Use an absolute Windows drive path: ' + value)
    return '/' + value[0].lower() + value[2:]

def run(command, *, cwd=None, log=None, env=None):
    subprocess.run([str(x) for x in command], cwd=cwd, env=env,
                   stdout=log, stderr=subprocess.STDOUT, check=True)

def unpack(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as source:
        source.extractall(destination, filter='data')

def prepare_crt(ndk, work):
    """Identification-only override; keep all r30 runtime code unchanged."""
    tc = ndk/'toolchains/llvm/prebuilt/windows-x86_64'
    libs = tc/'sysroot/usr/lib/aarch64-linux-android'
    crt = work/'crt'
    crt.mkdir(exist_ok=True)
    note = crt/'android.note'
    run([tc/'bin/llvm-objcopy.exe', '--dump-section', '.note.android.ident='+str(note),
         libs/'28/crtbegin_dynamic.o', crt/'dynamic-copy.o'])
    expected = (struct.pack('<III', 8, 132, 1) + b'Android\0' + struct.pack('<I', 28)
                + b'r30'.ljust(64,b'\0') + b'16248370'.ljust(64,b'\0'))
    if note.read_bytes() != expected:
        raise RuntimeError('Unexpected official r30/API28 identification note')
    patched = crt/'prepared.o'
    run([tc/'bin/llvm-objcopy.exe', '--update-section', '.note.android.ident='+str(note),
         libs/'crtbegin_static.o', patched])
    target = crt/'crtbegin_static.o'
    if not target.exists() or sha(patched) != sha(target):
        patched.replace(target)
    else:
        patched.unlink()

def elf_metadata(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<HH', data,16) != (2,183):
        raise RuntimeError('Expected AArch64 ELF64 static executable')
    offset = struct.unpack_from('<Q',data,32)[0]
    size, count = struct.unpack_from('<HH',data,54)
    loads = []
    for i in range(count):
        p = struct.unpack_from('<IIQQQQQQ',data,offset+i*size)
        if p[0] == 3: raise RuntimeError('Unexpected PT_INTERP')
        if p[0] == 2:
            for at in range(p[2],p[2]+p[5],16):
                tag,_ = struct.unpack_from('<QQ',data,at)
                if tag == 0: break
                if tag == 1: raise RuntimeError('Unexpected DT_NEEDED')
        if p[0] == 1:
            if p[7] < 16384 or p[2]%16384 != p[3]%16384:
                raise RuntimeError('Missing 16 KiB load-segment alignment')
            loads.append(p[7])
    return {'architecture':'AArch64', 'type':'ET_EXEC', 'pt_interp':False,
            'dt_needed':[], 'load_alignments':loads, 'bytes':len(data), 'sha256':sha(path)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--msys', type=Path, default=Path('C:/msys64'))
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--clean', action='store_true')
    args = parser.parse_args()
    reference, removed, expected_applets, profile = applet_policy()
    ndk, cache, msys = args.ndk.resolve(), args.cache.resolve(), args.msys.resolve()
    if re.search(r'^Pkg.Revision\s*=\s*'+re.escape(REVISION)+r'\s*$',
                 (ndk/'source.properties').read_text(), re.M) is None:
        raise RuntimeError('This recipe requires NDK r30 ('+REVISION+')')
    # Native ndk-build cannot reliably handle whitespace/non-ASCII project paths.
    if not str(cache).isascii() or any(c.isspace() for c in str(cache)):
        raise RuntimeError('Pass -CacheRoot with an ASCII path without spaces, e.g. C:\\BusyBoxAndroidBuild')
    work = cache/'busybox-1.38.0-r30-api28-lto-v1'
    out = ROOT/'out'
    out.mkdir(exist_ok=True)
    upstream = ROOT/'upstream'
    upstream.mkdir(exist_ok=True)
    for name,(url,expected) in SOURCES.items():
        archive = upstream/name
        if not archive.exists():
            print('Downloading '+name, flush=True)
            temporary = archive.with_suffix(archive.suffix+'.part')
            urllib.request.urlretrieve(url,temporary)
            if sha(temporary) != expected: raise RuntimeError('Source SHA256 mismatch: '+name)
            temporary.replace(archive)
        if sha(archive) != expected: raise RuntimeError('Source SHA256 mismatch: '+name)
    key = recipe_hash()
    marker = work/'.recipe-sha256'
    fresh = args.clean or not marker.exists() or marker.read_text() != key
    if fresh:
        if work.exists():
            # Delete only the fixed build workspace inside the selected cache.
            if work.resolve().parent != cache or work.is_symlink():
                raise RuntimeError('Unsafe build-cache path')
            shutil.rmtree(work)
        work.mkdir(parents=True)
        unpack(upstream/'busybox-1.38.0.tar.bz2',work)
        (work/'busybox-1.38.0').rename(work/'busybox')
        unpack(upstream/'ndk-box-kitchen.tar.gz',work)
        kitchen = work/'ndk-box-kitchen-14d189ea3070a8167b3576bf83fe070d4a3441af'
        shutil.copytree(kitchen/'jni',work/'jni')
        unpack(upstream/'selinux.tar.gz',work)
        (work/'selinux-48fcf8bba0635dc597bef75994294fd055d9f0ba').rename(work/'jni/selinux')
        unpack(upstream/'pcre.tar.gz',work/'jni/pcre')
        run([msys/'usr/bin/patch.exe','--batch','--fuzz=0','-p1','-i',
             posix(ROOT/'patches/android-1.38.patch')],cwd=work/'busybox')
        shutil.copy2(ROOT/'config/android.config',work/'busybox.config')
        for name in ('generate.sh','generate-makefile.py'):
            shutil.copy2(ROOT/name,work/name)
        mk=(kitchen/'busybox.mk').read_text()
        mk=mk.replace('$(SUBLEVEL).$(MINORLEVEL) topjohnwu','$(SUBLEVEL) Android')
        mk=mk.replace('LOCAL_MODULE := busybox','LOCAL_MODULE := busybox\nLOCAL_FORCE_STATIC_EXECUTABLE := true')
        mk=mk.replace('-w -include include/autoconf.h','-Wno-deprecated-declarations -include $(LOCAL_PATH)/include/autoconf.h')
        mk=mk.replace('LOCAL_LDFLAGS := -static','LOCAL_LDFLAGS := -B$(LOCAL_PATH)/../crt/ -static')
        (work/'busybox.mk').write_text(mk,newline='\n')
        (work/'jni/Application.mk').write_text('''APP_ABI := arm64-v8a
APP_PLATFORM := android-28
APP_CFLAGS := -Os -flto=thin -ffunction-sections -fdata-sections
APP_LDFLAGS := -flto=thin -Wl,--gc-sections -Wl,--icf=safe -Wl,-z,max-page-size=16384
APP_SHORT_COMMANDS := true
APP_SUPPORT_FLEXIBLE_PAGE_SIZES := true
''',newline='\n')
        print(f'[1/3] Generating configuration: {len(reference)} reference applets, {len(removed)} removed...',flush=True)
        run([msys/'usr/bin/bash.exe','-lc','cd '+shlex.quote(posix(work))
             +' && bash generate.sh '+shlex.quote(posix(work))])
        marker.write_text(key)
    prepare_crt(ndk,work)
    from prepare_compat_libc import prepare
    compat_info = prepare(ndk,work/"crt")
    mkfile=work/"busybox/Android.mk"
    text=mkfile.read_text()
    if "-L$(LOCAL_PATH)/../crt" not in text:
        mkfile.write_text(text.replace("LOCAL_LDFLAGS := ", "LOCAL_LDFLAGS := $(LOCAL_PATH)/../crt/arc4random.o -L$(LOCAL_PATH)/../crt "),newline="\n")
    names = re.findall(r'^"([^"\\]+)" "\\0"$',
                       (work/'busybox/include/applet_tables.h').read_text(), re.M)
    if set(names) != expected_applets or len(names) != len(expected_applets):
        raise RuntimeError('Unexpected applet set: missing='+str(sorted(expected_applets-set(names)))
                           +' extra='+str(sorted(set(names)-expected_applets)))
    actual_config = (work/'busybox/.config').read_text()
    for flag, value in profile['required_config'].items():
        if not re.search(r'^'+re.escape(flag+'='+value)+r'$',actual_config,re.M):
            raise RuntimeError('Required profile feature is missing: '+flag+'='+value)
    for flag in profile.get('disabled_config',[]):
        if not re.search(r'^# '+re.escape(flag)+r' is not set$',actual_config,re.M):
            raise RuntimeError('Excluded profile feature is not disabled: '+flag)
    configured_objects = set((work/'configured-objects.txt').read_text().split())
    included_forbidden = configured_objects.intersection(profile.get('forbidden_build_objects',[]))
    if included_forbidden:
        raise RuntimeError('Excluded decoder sources still selected: '+str(sorted(included_forbidden)))
    print(f'[2/3] Building {len(names)} applets with NDK r30 + ThinLTO; log: {out / "build.log"}',flush=True)
    try:
        with (out/'build.log').open('w',encoding='utf-8') as log:
            run([ndk/'ndk-build.cmd',f'-j{args.jobs}','NDK_PROJECT_PATH=.',
                 'NDK_APPLICATION_MK=jni/Application.mk'],cwd=work,log=log)
    except subprocess.CalledProcessError:
        print('\n'.join((out/'build.log').read_text(errors='replace').splitlines()[-60:]))
        raise
    print('[3/3] Publishing static ELF and build metadata...',flush=True)
    binary = out/'busybox'
    shutil.copy2(work/'libs/arm64-v8a/busybox',binary)
    info = elf_metadata(binary)
    tc = ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    with (out/'elf-info.txt').open('w') as log:
        run([tc/'llvm-readelf.exe','-h','-l','-d','-n',binary],log=log)
    shutil.copy2(work/'busybox/.config',out/'busybox.config')
    shutil.copy2(work/'busybox/LICENSE',out/'LICENSE-BusyBox.txt')
    (out/'applets.txt').write_text('\n'.join(names)+'\n',encoding='utf-8')
    # ThinLTO objects carry LLVM bitcode; keep build evidence without running device tests.
    objects = list((work/'obj/local/arm64-v8a/objs').rglob('*.o'))
    bitcode = sum(p.read_bytes()[:4] == b'BC\xc0\xde' for p in objects)
    manifest = {'name':'BusyBox','version':'1.38.0','target':'aarch64-linux-android28',
        'ndk':'r30','ndk_revision':REVISION,'optimization':'-Os -flto=thin',
        'link_flags':'--gc-sections --icf=safe -z max-page-size=16384',
        'ndk_default_hardening':True, 'llvm_bitcode_objects':bitcode,
        'recipe_sha256':key, 'config_sha256':sha(out/'busybox.config'),
        'reference':{'version':'1.36.1.1 topjohnwu','applets':len(reference),
                     'binary_sha256':'4d60ab3f5a59ebb2ca863f2f514e6924401b581e9b64f602665c008177626651'},
        'build_profile':profile['name'], 'profile_sha256':sha(ROOT/'config/profile.json'),
        'profile_input_sha256':profile['input_sha256'],
        'external_providers':profile['external_providers'],
        'required_config_match':True,
        'disabled_config_match':True, 'disabled_config':profile.get('disabled_config',[]),
        'omitted_decoder_objects':profile.get('forbidden_build_objects',[]),
        'zip_methods':profile.get('zip_methods',[]),
        'unicode':profile.get('unicode',{}),
        'applets':len(names), 'removed_applets':sorted(removed),
        'requested_applets_match':sorted(names)==sorted(expected_applets),
        'sources':SOURCES, 'elf':info,
        'android_note':'Private CRT note override: target 28 / r30 / 16248370; runtime code unchanged.',
        'arc4random_compat':compat_info,
        'runtime_testing':'Not run by builder; API 28 runtime compatibility unverified.'}
    (out/'BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (out/'SHA256SUMS.txt').write_text(sha(binary)+'  busybox\n')
    print(f'Build complete: {binary}\nSize: {info["bytes"]} bytes; applets: {len(names)}; LLVM bitcode objects: {bitcode}',flush=True)

if __name__ == '__main__':
    main()
