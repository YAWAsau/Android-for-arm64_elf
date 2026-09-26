"""Build fully static pinned zstd using NDK r30; optional MSVC host tests.

Usage: python build_native.py android|host [--jobs 8]
Set ANDROID_NDK_HOME or VS_VCVARS64 to override the installed tool locations.
"""
from pathlib import Path
from android_build_note import describe_static_android_build, print_android_build, prepare_static_crt
import argparse
import tempfile
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import subprocess
import struct
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT/'upstream'
COMMIT = '01b7154f1172432f8abe9b3bb9909e14a1176b7d'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mode', nargs='?', choices=('android', 'host'), default='android')
parser.add_argument('--jobs', type=int, default=8)
options = parser.parse_args()
if not 1 <= options.jobs <= 128:
    parser.error('--jobs must be between 1 and 128')
MODE = options.mode
OUT = ROOT/('android-r30-direct' if MODE == 'android' else 'host-direct')
OUT.mkdir(exist_ok=True)
if (SRC/'.git').exists():
    assert subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip() == COMMIT
    assert not subprocess.check_output(['git','-C',str(SRC),'status','--porcelain','--untracked-files=no'],text=True).strip()
else:
    snapshot=json.loads((ROOT/'upstream_source_sha256.json').read_text())
    assert snapshot['commit']==COMMIT
    for name,digest in snapshot['files'].items():
        item=SRC/name
        content=os.readlink(item).encode() if item.is_symlink() else item.read_bytes()
        assert hashlib.sha256(content).hexdigest()==digest,name
env = {k.upper():v for k,v in os.environ.items()}
inc = [SRC/p for p in ['lib','lib/common','lib/compress','lib/dictBuilder','programs','tests']]
lib_sources = sorted(p for d in ['common','compress','decompress','dictBuilder'] for p in (SRC/'lib'/d).glob('*.c'))
lib_sources += [SRC/f'lib/legacy/zstd_v0{i}.c' for i in range(4,8)]
cli_sources = sorted((SRC/'programs').glob('*.c'))
tests = {'fuzzer':['tests/fuzzer.c'], 'zstreamtest':['tests/zstreamtest.c','tests/seqgen.c','tests/external_matchfinder.c']}
extra = sorted({SRC/p for entries in tests.values() for p in entries}) if MODE == 'host' else []
sources = lib_sources + cli_sources + extra
defs = ['ZSTD_MULTITHREAD','ZSTD_LEGACY_SUPPORT=4','XXH_NAMESPACE=ZSTD_','ZSTD_DISABLE_ASM','NDEBUG']
if MODE == 'android':
    ndk = Path(env.get('ANDROID_NDK_HOME',str(Path(env['LOCALAPPDATA'])/'Android/Sdk/ndk/30.0.16248370')))
    props = ndk/'source.properties'
    if not props.is_file():
        raise SystemExit(f'NDK r30 (30.0.16248370) not found at {ndk}. Install it or set ANDROID_NDK_HOME.')
    revision = dict(line.split('=', 1) for line in props.read_text(encoding='utf-8').splitlines() if '=' in line)
    if next((v.strip() for k,v in revision.items() if k.strip() == 'Pkg.Revision'), None) != '30.0.16248370':
        raise SystemExit(f'NDK r30 (30.0.16248370) required: {props}')
    tool = ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    crt_stage = tempfile.TemporaryDirectory(prefix='sbzstd-crt-')
    private_crt,crt_info = prepare_static_crt(ndk, Path(crt_stage.name))
    cc = str(tool/'clang.exe')
    target = ['--target=aarch64-linux-android28']
    flags = target+['-O3','-flto=full','-fPIE','-ffunction-sections','-fdata-sections','-pthread']
    flags += ['-D'+d for d in defs]+['-I'+str(p) for p in inc]
else:
    vc = env.get('VS_VCVARS64','C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat')
    setup = OUT/'vc_environment.cmd'
    setup.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\nset\n',encoding='utf8')
    raw = subprocess.check_output(['cmd.exe','/d','/c',str(setup)],text=True,errors='replace')
    env.update((line.split('=',1)[0].upper(),line.split('=',1)[1]) for line in raw.splitlines() if '=' in line and not line.startswith('='))
    cc = str(Path(env['VCTOOLSINSTALLDIR'])/'bin/Hostx64/x64/cl.exe')
    flags = ['/nologo','/O2','/MT','/D_CRT_SECURE_NO_WARNINGS']+['/D'+d for d in defs]+['/I'+str(p) for p in inc]

records = []
def compile_one(source):
    obj = OUT/(str(source.relative_to(SRC)).replace('\\','_').replace('/','_')+'.obj')
    args = [cc,*flags,'-c',str(source),'-o',str(obj)] if MODE == 'android' else [cc,*flags,'/c',str(source),'/Fo'+str(obj)]
    result = subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
    (OUT/(obj.name+'.log')).write_text(result.stdout,encoding='utf8')
    if result.returncode:
        print(result.stdout,flush=True)
        raise RuntimeError(source)
    return source,obj,args

with ThreadPoolExecutor(max_workers=options.jobs) as pool:
    for source,obj,args in pool.map(compile_one,sources):
        records.append({'source':str(source.relative_to(SRC)),'object':str(obj),'command':args})
        print('compiled',source.relative_to(SRC),flush=True)
objects = {Path(r['source']):r['object'] for r in records}
def link(name, inputs):
    dest = OUT/(name if MODE == 'android' else name+'.exe')
    objs = [objects[p.relative_to(SRC)] for p in inputs]
    if MODE == 'android':
        args = [cc,*target,'-B'+private_crt.parent.as_posix()+'/','-flto=full','-static','-no-pie','-pthread','-Wl,--gc-sections','-Wl,-z,max-page-size=16384','-Wl,-z,common-page-size=16384',*objs,'-lm','-o',str(dest)]
    else:
        args = [cc,'/nologo',*objs,'/Fe'+str(dest)]
    result = subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
    (OUT/(name+'.link.log')).write_text(result.stdout,encoding='utf8')
    if result.returncode: raise RuntimeError(result.stdout)
    return dest,args

binary,linkargs = link('zstd',lib_sources+cli_sources)
if MODE == 'host':
    for name, entries in tests.items():
        common = [SRC/'programs'/n for n in ['datagen.c','util.c','timefn.c']]
        link(name,lib_sources+common+[SRC/p for p in entries])
else:
    release = ROOT/'out-r30'
    release.mkdir(exist_ok=True)
    subprocess.run([str(tool/'llvm-strip.exe'),'--strip-unneeded','-o',str(release/'zstd'),str(binary)],check=True)
    binary = release/'zstd'
    body = binary.read_bytes()
    assert body[:6] == b'\x7fELF\x02\x01'
    assert struct.unpack_from('<HH', body, 16) == (2, 183), 'Expected static AArch64 EXEC'
    offset = struct.unpack_from('<Q', body, 32)[0]
    size, count = struct.unpack_from('<HH', body, 54)
    headers = [struct.unpack_from('<IIQQQQQQ', body, offset+i*size) for i in range(count)]
    assert not any(p[0] in (2, 3) for p in headers), 'Unexpected dynamic/interpreter segment'
    loads = [p for p in headers if p[0] == 1]
    assert loads and all(p[7] == 16384 and p[2] % 16384 == p[3] % 16384 for p in loads)
    android_build = describe_static_android_build(binary, ndk, '30.0.16248370', private_crt=private_crt)
    android_build['crt_identification_override'] = crt_info
    expected_notes = [(n['type'], bytes.fromhex(n['data'])) for n in android_build['static_crt_android_note']]
    print_android_build(android_build)
    android_note = False
    for p in headers:
        if p[0] != 4:
            continue
        pos = p[2]
        while pos < p[2]+p[5]:
            ns, ds, kind = struct.unpack_from('<III', body, pos)
            name = body[pos+12:pos+12+ns].rstrip(b'\0')
            dp = pos+12+(ns+3)//4*4
            desc = body[dp:dp+ds]
            if name == b'Android':
                assert (kind, desc) in expected_notes
                android_note = True
            pos = dp+(ds+3)//4*4
    assert android_note, 'Expected NDK r30 static CRT note'
info = {'commit':COMMIT,'mode':MODE,'compiler':subprocess.check_output([cc,'--version'] if MODE=='android' else [cc],env=env,stderr=subprocess.STDOUT,text=True,errors='replace') if MODE=='android' else 'MSVC 2022 /O2 /MT',
        'sources':records,'link':linkargs,'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'binary':str(binary)}
(OUT/'build.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
if MODE == 'android':
    (release/'BUILD_INFO.json').write_text(json.dumps({
        **android_build,
        'commit':COMMIT, 'ndk':'30.0.16248370', 'api':28, 'target':'arm64-v8a',
        'lto':'full', 'static':True, 'page_size':16384, 'sha256':info['sha256'],
        'static_crt_android_note': [{'type':k,'data':d.hex()} for k,d in expected_notes],
        'compiler':info['compiler'], 'android_runtime_tested':False,
    },indent=2)+'\n',encoding='utf8')
    (release/'SHA256SUMS.txt').write_text(info['sha256']+'  zstd\n',encoding='ascii')
print('PASS',MODE,info['sha256'],flush=True)
if MODE == 'android':
    crt_stage.cleanup()
