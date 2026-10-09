"""Use a private static CRT with official target/NDK identification.

Private CRT metadata and stateless arc4random compatibility. Installed NDK is unchanged.
"""
from pathlib import Path
import hashlib
import struct
import subprocess


def elf_sections(data):
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected ELF64 little endian')
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset+i*size) for i in range(count)]
    names_header = headers[names_index]
    names = data[names_header[4]:names_header[4]+names_header[5]]
    result = {}
    for h in headers:
        name = names[h[0]:].split(b'\0', 1)[0].decode('ascii')
        payload = b'' if h[1] == 8 else data[h[4]:h[4]+h[5]]
        result[name] = (h, payload)
    return result


def prepare_static_crt(ndk, output, revision='30.0.16248370', target_api=28):
    if revision != '30.0.16248370' or target_api != 28:
        raise ValueError('Private static CRT requires pinned NDK r30/API28')
    ndk, output = Path(ndk), Path(output)
    props = dict(line.split('=', 1) for line in (ndk/'source.properties').read_text().splitlines() if '=' in line)
    if next((v.strip() for k, v in props.items() if k.strip() == 'Pkg.Revision'), None) != revision:
        raise ValueError('Unexpected NDK revision')
    output.mkdir(parents=True, exist_ok=True)
    toolchain = ndk/'toolchains/llvm/prebuilt/windows-x86_64'
    lib = toolchain/'sysroot/usr/lib/aarch64-linux-android'
    original_path = lib/'crtbegin_static.o'
    original = original_path.read_bytes()
    dynamic = (lib/'28/crtbegin_dynamic.o').read_bytes()
    note = elf_sections(dynamic)['.note.android.ident'][1]
    expected = (struct.pack('<III', 8, 132, 1)+b'Android\0'+struct.pack('<I', 28)
                +b'r30'.ljust(64,b'\0')+b'16248370'.ljust(64,b'\0'))
    if note != expected:
        raise ValueError('Unexpected official API28/r30 identification note')
    note_path = output/'android.note'
    note_path.write_bytes(note)
    private = output/'crtbegin_static.o'
    subprocess.run([str(toolchain/'bin/llvm-objcopy.exe'), '--update-section',
                    '.note.android.ident='+str(note_path), str(original_path), str(private)], check=True)
    before, after = elf_sections(original), elf_sections(private.read_bytes())
    if set(before) != set(after):
        raise ValueError('CRT section set changed')
    for name, (h, payload) in before.items():
        ah, ap = after[name]
        if name == '.note.android.ident':
            continue
        # Only file offsets may move when the identification note grows.
        if payload != ap or any(h[i] != ah[i] for i in (1,2,3,5,6,7,8,9)):
            raise ValueError('Unexpected CRT code/data/relocation change: '+name)
    if original_path.read_bytes() != original:
        raise ValueError('Installed NDK CRT changed during build')
    digest = lambda b: hashlib.sha256(b).hexdigest()
    from prepare_compat_libc import prepare
    compat = prepare(ndk, private.parent)
    return private, {
        'arc4random_compat':compat,
        'kind':'private-static-crt-target-ident-v1',
        'source_static_crt_sha256':digest(original),
        'private_static_crt_sha256':digest(private.read_bytes()),
        'official_target_note_sha256':digest(note),
        'original_android_notes':[{'type':k,'data':d.hex()} for k,d in android_notes(original)],
        'non_ident_sections_unchanged':True,
        'installed_ndk_unchanged':True,
        'runtime_compatibility_changed':True,
    }


def android_notes(data):
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected ELF64 little endian')
    section_offset = struct.unpack_from('<Q', data, 40)[0]
    section_size, section_count = struct.unpack_from('<HH', data, 58)
    notes = []
    for i in range(section_count):
        section = struct.unpack_from('<IIQQQQIIQQ', data, section_offset+i*section_size)
        if section[1] != 7:
            continue
        pos, end = section[4], section[4]+section[5]
        if end > len(data):
            raise ValueError('Truncated ELF note section')
        while pos < end:
            if end-pos < 12:
                raise ValueError('Truncated ELF note header')
            ns, ds, kind = struct.unpack_from('<III', data, pos)
            dp = pos+12+(ns+3)//4*4
            next_pos = dp+(ds+3)//4*4
            if next_pos > end:
                raise ValueError('Truncated ELF note payload')
            if data[pos+12:pos+12+ns].rstrip(b'\0') == b'Android':
                notes.append((kind, data[dp:dp+ds]))
            pos = next_pos
    return notes


def describe_static_android_build(binary, ndk, revision, target_api=28, private_crt=None):
    crt = Path(private_crt) if private_crt else Path(ndk)/'toolchains/llvm/prebuilt/windows-x86_64/sysroot/usr/lib/aarch64-linux-android/crtbegin_static.o'
    expected = android_notes(crt.read_bytes())
    actual = android_notes(Path(binary).read_bytes())
    if not expected or actual != expected:
        raise ValueError('Android ELF notes differ from the selected NDK static CRT')
    identities = [d for k, d in actual if k == 1 and len(d) >= 4]
    if len(identities) != 1:
        raise ValueError('Expected exactly one Android identity note')
    desc = identities[0]
    text = lambda b: b.split(b'\0', 1)[0].decode('ascii', errors='strict') or None
    return {
        'ndk_revision': revision,
        'target_api': target_api,
        'target_triple': f'aarch64-linux-android{target_api}',
        'crt_android_api_note': struct.unpack_from('<I', desc)[0],
        'crt_ndk_version_note': text(desc[4:68]) if len(desc) >= 68 else None,
        'crt_ndk_build_note': text(desc[68:132]) if len(desc) >= 132 else None,
        'static_crt_android_note': [{'type':k, 'data':d.hex()} for k, d in actual],
        'crt_note_matches_selected_ndk': private_crt is None,
        'crt_note_matches_selected_crt': True,
        'identification_override': private_crt is not None,
        'android_runtime_tested': False,
        'compatibility_status': 'Target API is a compiler setting; minimum runtime compatibility is not verified by ELF notes.',
    }


def print_android_build(info):
    print('NDK toolchain: r30 ('+info['ndk_revision']+')', flush=True)
    print('Compiler target: '+info['target_triple']+' (target API '+str(info['target_api'])+')', flush=True)
    print('Static CRT Android note: API '+str(info['crt_android_api_note'])+
          '; NDK version in note: '+(info['crt_ndk_version_note'] or 'absent')+
          '; matches selected CRT', flush=True)
    if info['identification_override']:
        print('Identification: official API28/r30 note on private static CRT; private libc uses stateless arc4random.', flush=True)
    print('Runtime compatibility: not tested by this build; target API and CRT note are distinct.', flush=True)
