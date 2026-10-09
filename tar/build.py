"""Build pinned GNU tar 1.35.90 for Android arm64 using NDK r30 + MSYS2.

The input archive is pristine GNU source. Build products stay in a private
ASCII staging directory and in out/, never in the source archive.
"""
from pathlib import Path
from android_build_note import describe_static_android_build, print_android_build, prepare_static_crt
import argparse, hashlib, json, os, shutil, struct, subprocess, tarfile, tempfile

SOURCE_SHA256='f4f30f81ec8c4bbff32796253375b61f124fe5e2e9226411d64a80ae0e255f96'
SOURCE_URL='https://alpha.gnu.org/gnu/tar/tar-1.35.90.tar.xz'
REVISION='30.0.16248370'
# Avoid colliding with private tzcode symbols inside static Bionic libc.
CFLAGS='-O2 -fPIE -ffunction-sections -fdata-sections -Dtzalloc=sb_tar_tzalloc -Dtzfree=sb_tar_tzfree'
LDFLAGS='-static -no-pie -Wl,--gc-sections -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384'
CONFIGURE=['--build=x86_64-pc-msys','--host=aarch64-linux-android','--disable-nls','--without-selinux','--without-posix-acls','--without-libsmack']
# NDK static libc exposes lchmod/qsort_r even when API28 headers hide them
# (__INTRODUCED_IN(36)). Use gnulib's compatibility implementation.
CONFIGURE_ENV={
    # This fixed linux-android cross build already takes gnulib's Linux
    # "guessing yes" branches. Cache those exact results to skip unused
    # host dangling-symlink fixtures, which MSYS2 deepcopy cannot create.
    # Keep "guessing" explicit: these are not Android runtime test results.
    'gl_cv_func_readlink_trailing_slash':'guessing yes',
    'gl_cv_func_readlink_truncate':'guessing yes',
    # These probes also create unused dangling symlinks before taking
    # their cross branches. Preserve each original outcome, including
    # the conservative fchownat fallback (default cross guess is no).
    'gl_cv_func_fchownat_nofollow_works':'guessing no',
    'gl_cv_func_linkat_nofollow':'guessing yes',
    'gl_cv_func_mkfifo_works':'guessing yes',
    'ac_cv_func_lchmod':'no', 'ac_cv_func_qsort_r':'no',
    # Autoconf considers a command-line macro to be a declaration. Pin the
    # API28 result before the namespace macros can fool the declaration test.
    'ac_cv_func_tzalloc':'no', 'ac_cv_have_decl_tzalloc':'no',
    'gl_cv_onwards_func_tzalloc':'future OS version',
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def msys(path):
    s=str(path).replace('\\','/')
    return '/'+s[0].lower()+s[2:] if s[1:3]==':/' else s

def verify_elf(path):
    data=Path(path).read_bytes()
    assert data[:6]==b'\x7fELF\x02\x01', 'Expected ELF64 little endian'
    etype,machine=struct.unpack_from('<HH',data,16)
    assert machine==183 and etype==2, 'Expected static AArch64 ET_EXEC'
    phoff=struct.unpack_from('<Q',data,32)[0]
    phsize,phnum=struct.unpack_from('<HH',data,54)
    loads=[];dynamic=[]
    for i in range(phnum):
        p=struct.unpack_from('<IIQQQQQQ',data,phoff+i*phsize)
        assert p[0]!=3, 'PT_INTERP means this is not fully static'
        if p[0]==1:
            assert p[7]>=16384 and p[2]%16384==p[3]%16384
            loads.append({'offset':p[2],'vaddr':p[3],'alignment':p[7]})
        if p[0]==2:
            for off in range(p[2],p[2]+p[5],16):
                tag,val=struct.unpack_from('<QQ',data,off)
                if tag==0: break
                assert tag!=1, 'DT_NEEDED means this is not fully static'
                dynamic.append(tag)
    assert loads
    return {'machine':'AArch64','class':'ELF64','type':'ET_EXEC','pt_interp':False,'dt_needed':[],'load_segments':loads,'size':len(data),'sha256':sha(path)}

def collect(src, out, ndk, build_script=None, private_crt=None, crt_info=None):
    out.mkdir(parents=True,exist_ok=True)
    tool=ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    binary=src/'src/tar'
    if not binary.exists(): binary=src/'src/tar.exe'
    shutil.copy2(binary,out/'tar')
    subprocess.run([str(tool/'llvm-strip.exe'),'--strip-all',str(out/'tar')],check=True)
    elf=verify_elf(out/'tar')
    android_build=describe_static_android_build(out/'tar', ndk, REVISION, private_crt=private_crt)
    android_build['crt_identification_override']=crt_info
    print_android_build(android_build)
    for name in ['config.h','config.log','config.status']:
        shutil.copy2(src/name,out/name)
    cfg=(src/'config.h').read_text()
    config={name:('#define '+name+' ' in cfg or '#define '+name+'\n' in cfg) for name in ['HAVE_XATTRS','HAVE_POSIX_ACLS','HAVE_SELINUX_SELINUX_H','ENABLE_NLS']}
    # Macros defined as zero do not enable a feature.
    for name in config:
        if '#define '+name+' 0' in cfg: config[name]=False
    compiler=subprocess.check_output([str(tool/'clang.exe'),'--version'],text=True).strip()
    manifest={'name':'GNU tar','version':'1.35.90','upstream_date':'2025-10-19','release_type':'GNU test release','source_url':SOURCE_URL,'source_sha256':SOURCE_SHA256,'upstream_source_modified':False,'ndk_revision':REVISION,'target':'aarch64-linux-android28','compiler':compiler,'cflags':CFLAGS,'ldflags':LDFLAGS,'configure':CONFIGURE,'configure_environment':CONFIGURE_ENV,'source_date_epoch':1760843340,'features':config,'elf':elf,'config_h_sha256':sha(src/'config.h'),'reproducibility':'Build recipe and provenance provided; byte-identical independent rebuild not yet verified.'}
    manifest.update(android_build)
    if build_script: manifest['executed_build_script']=build_script
    (out/'BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    (out/'SHA256SUMS.txt').write_text(sha(out/'tar')+'  tar\n',encoding='ascii')
    print(json.dumps(elf,indent=2),flush=True)
    return manifest

def main():
    root=Path(__file__).resolve().parent
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ndk',type=Path,default=Path(os.environ.get('ANDROID_NDK_HOME',str(Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/ndk'/REVISION))))
    ap.add_argument('--msys',type=Path,default=Path('C:/msys64'))
    ap.add_argument('--stage-root',type=Path)
    ap.add_argument('--jobs',type=int,default=8)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--keep-stage',action='store_true')
    args=ap.parse_args()
    assert args.jobs>0
    ndk=args.ndk.resolve()
    props = ndk/'source.properties'
    if not props.is_file():
        raise SystemExit(f'NDK r30 ({REVISION}) not found at {ndk}. Install it or pass --ndk with its directory.')
    revision = dict(line.split('=', 1) for line in props.read_text(encoding='utf-8').splitlines() if '=' in line)
    if next((v.strip() for k,v in revision.items() if k.strip() == 'Pkg.Revision'), None) != REVISION:
        raise SystemExit(f'NDK r30 ({REVISION}) required: {props}')
    upstream=root/'upstream'
    archive=root/'tar-1.35.90.tar.xz'
    if upstream.is_dir():
        snapshot=json.loads((root/'SOURCE_MANIFEST.json').read_text(encoding='utf8'))
        assert snapshot['original_archive_sha256']==SOURCE_SHA256
        files={p.relative_to(upstream).as_posix():p for p in upstream.rglob('*') if p.is_file()}
        assert set(files)==set(snapshot['files']), 'Source file set changed'
        for name,path in files.items():
            assert not path.is_symlink() and sha(path)==snapshot['files'][name], 'Source changed: '+name
    else:
        if not archive.exists(): archive=root/'downloads/tar-1.35.90.tar.xz'
        assert sha(archive)==SOURCE_SHA256, 'Source SHA256 mismatch'
    base=args.stage_root or Path(tempfile.gettempdir())
    base=base.resolve()
    assert str(base).isascii() and "'" not in str(base), 'Use --stage-root with an ASCII path without apostrophes'
    base.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='sbtar-',dir=base)).resolve()
    assert stage.parent==base and stage.name.startswith('sbtar-')
    print('Build stage:',stage,flush=True)
    out=(args.output or root/'out').resolve();out.mkdir(parents=True,exist_ok=True)
    try:
        src=stage/'tar-1.35.90'
        if upstream.is_dir(): shutil.copytree(upstream,src)
        else:
            with tarfile.open(archive) as t: t.extractall(stage,filter='data')
        # ZIP extraction assigns fresh mtimes in entry order. Keep the shipped
        # generated autotools files as old as their inputs to avoid unnecessary
        # regeneration/configure restarts. Only normalize our private stage.
        for item in src.rglob('*'):
            if item.is_file() and not item.is_symlink():
                os.utime(item, (1760843340, 1760843340))
        tool=ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
        private_crt,crt_info=prepare_static_crt(ndk,stage/'crt-api28-r30')
        crt_link_flags=LDFLAGS+' -B'+private_crt.parent.as_posix()+'/ -L'+private_crt.parent.as_posix()
        script=['#!/usr/bin/bash','set -eu','export PATH=/usr/bin:/bin','export LC_ALL=C','export TZ=UTC','export SOURCE_DATE_EPOCH=1760843340']
        for key,value in {'CC':msys(tool/'clang.exe')+' --target=aarch64-linux-android28','AR':msys(tool/'llvm-ar.exe'),'RANLIB':msys(tool/'llvm-ranlib.exe'),'NM':msys(tool/'llvm-nm.exe'),'STRIP':msys(tool/'llvm-strip.exe'),'CFLAGS':CFLAGS,'LDFLAGS':crt_link_flags,'FORCE_UNSAFE_CONFIGURE':'1',**CONFIGURE_ENV}.items():
            assert "'" not in value
            script.append("export "+key+"='"+value+"'")
        script += ["cd '"+msys(src)+"'",'./configure '+' '.join(CONFIGURE),'make -j'+str(args.jobs)+' -C gnu','make -j'+str(args.jobs)+' -C lib','make -j'+str(args.jobs)+' -C src tar']
        script_text='\n'.join(script)+'\n'
        (stage/'build.sh').write_text(script_text,encoding='utf8',newline='\n')
        with (out/'build.log').open('w',encoding='utf8') as log:
            command = [str(args.msys/'usr/bin/bash.exe'),'--noprofile','--norc',msys(stage/'build.sh')]
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1) as process:
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    print(line, end='', flush=True)
                code = process.wait()
                if code:
                    raise subprocess.CalledProcessError(code, command)
        collect(src,out,ndk,script_text,private_crt,crt_info)
    except BaseException:
        print('Failed; build stage retained for diagnosis:',stage,flush=True)
        raise
    else:
        if not args.keep_stage:
            # Only remove the exact directory created above, never user source.
            assert stage.resolve().parent==base and stage.name.startswith('sbtar-')
            if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in stage.rglob('*')):
                print('Stage retained: link encountered',stage)
            else: shutil.rmtree(stage)
    print('PASS: ELF structure / AArch64 / fully static / 16KiB alignment / API28-r30 identification; runtime compatibility untested /',out/'tar')

if __name__=='__main__':main()
