"""Create a verified private NDK r30 libc.a; never modify installed NDK."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile

SOURCE_SHA256 = '11a4947e3907dd36a83a3e8bec085b8f635d850749a8e11350433ca64c6f33f1'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare(ndk, output):
    ndk, output = Path(ndk), Path(output)
    if '30.0.16248370' not in (ndk / 'source.properties').read_text():
        raise ValueError('Expected pinned NDK r30 revision')
    tc = ndk / 'toolchains/llvm/prebuilt/windows-x86_64'
    source = tc / 'sysroot/usr/lib/aarch64-linux-android/libc.a'
    before = digest(source)
    if before != SOURCE_SHA256:
        raise ValueError('Pinned NDK libc.a hash mismatch')
    output.mkdir(parents=True, exist_ok=True)
    c = Path(__file__).with_name('arc4random_kernel.c')
    ar = str(tc / 'bin/llvm-ar.exe')
    def members(path):
        return subprocess.check_output([ar, 't', str(path)], text=True).splitlines()
    if members(source).count('arc4random.o') != 1:
        raise ValueError('Expected exactly one RNG archive member')
    with tempfile.TemporaryDirectory(dir=output, prefix='.rng-') as scratch:
        obj = Path(scratch) / 'arc4random.o'
        dest = Path(scratch) / 'libc.a'
        subprocess.run([str(tc / 'bin/clang.exe'), '--target=aarch64-linux-android28', '-O2', '-fPIC', '-ffunction-sections', '-fdata-sections', '-c', str(c), '-o', str(obj)], check=True)
        shutil.copyfile(source, dest)
        subprocess.run([ar, 'r', str(dest), str(obj)], check=True)
        if members(dest).count('arc4random.o') != 1 or subprocess.check_output([ar, 'p', str(dest), 'arc4random.o']) != obj.read_bytes():
            raise ValueError('Private RNG archive member verification failed')
        if digest(source) != before:
            raise ValueError('Installed NDK archive changed during build')
        private_hash = digest(dest)
        obj.replace(output / 'arc4random.o')
        dest.replace(output / 'libc.a')
    return {'kind': 'stateless-getrandom-arc4random-v1', 'source_libc_sha256': before, 'private_libc_sha256': private_hash, 'compat_source_sha256': digest(c), 'runtime_compatibility_changed': True, 'installed_ndk_unchanged': digest(source) == before}
