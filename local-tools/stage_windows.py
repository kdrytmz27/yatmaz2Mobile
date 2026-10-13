from pathlib import Path
import hashlib
import shutil
import struct
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'work/toolchain/python-packages'))
from Crypto.Cipher import ChaCha20

source = ROOT / 'work/m2dev-client'
output = ROOT / 'work/m2stage'
tools = ROOT / 'work/metin2-android/r10dev.net OPENGL-ITJA/android/tools'
git = shutil.which('git')
output.mkdir(exist_ok=True)
for pack in sorted((source / 'assets').iterdir(), key=lambda p: p.name.encode()):
    if pack.is_dir() and pack.name != 'root':
        shutil.copytree(pack, output, dirs_exist_ok=True)
        print('Merged', pack.name, flush=True)
shutil.copytree(source / 'assets/root', output, dirs_exist_ok=True)
for name in ('lib', 'bgm'):
    shutil.copytree(source / name, output / name, dirs_exist_ok=True)
for path in (source / 'config').glob('*.cfg'):
    shutil.copy2(path, output / path.name)
shutil.copy2(source / 'channel.inf', output / 'channel.inf')
(output / 'loca.cfg').write_bytes(b'1252 en\n')

keys = {'item': (173217, 72619434, 408587239, 27973291),
        'mob': (4813894, 18955, 552631, 6822045)}
for kind, key in keys.items():
    data = (source / f'assets/locale/locale/en/{kind}_proto').read_bytes()
    header_size = 20 if data[:4] == b'MIPX' else 12
    payload = data[header_size:]
    magic, encrypted, compressed, real = struct.unpack_from('<4sIII', payload)
    assert magic == b'MCOZ'
    if encrypted:
        key_bytes = struct.pack('<4I', *key)
        derived = hashlib.blake2b(key_bytes, key=b'M2DevPackEncrypt', digest_size=32).digest()
        nonce = hashlib.blake2b(key_bytes, key=b'M2DevNonce', digest_size=32).digest()[:24]
        size = (encrypted + 7) // 8 * 8
        cipher = payload[16:16+encrypted].ljust(size, b'\0')
        plain = ChaCha20.new(key=derived, nonce=nonce).decrypt(cipher)
        assert plain[:4] == b'MCOZ', f'{kind}: wrong key or format'
        body = struct.pack('<4sIII', b'MCOZ', 0, compressed, real) + b'MCOZ' + plain[4:4+compressed]
        data = data[:header_size-4] + struct.pack('<I', len(body)) + body
    (output / f'locale/en/{kind}_proto').write_bytes(data)
    print('Converted', kind, flush=True)

overlay = tools / 'data-overlay'
for name in ('m2compat.py', 'uimobilehud.py', 'uiscale.py', 'uidevoptions.py'):
    shutil.copy2(overlay / name, output / name)
shutil.copytree(overlay / 'fonts', output / 'fonts', dirs_exist_ok=True)
subprocess.run([sys.executable, str(overlay / 'make_hud_art.py'), str(output)], check=True)
subprocess.run([git, 'apply', '--check', '--ignore-space-change', '--ignore-whitespace', str(overlay / 'client-data.patch')], cwd=output, check=True)
subprocess.run([git, 'apply', '--ignore-space-change', '--ignore-whitespace', str(overlay / 'client-data.patch')], cwd=output, check=True)
polish = overlay / 'ui-polish-v1.patch'
if polish.exists():
    subprocess.run([git, 'apply', '--ignore-space-change', '--ignore-whitespace', str(polish)], cwd=output, check=True)
modern = overlay / 'modern-ui'
if modern.exists():
    shutil.copytree(modern, output, dirs_exist_ok=True)

archive = ROOT / 'work/toolchain/downloads/Python-2.7.18.tgz'
if not archive.exists():
    urllib.request.urlretrieve('https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz', archive)
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        if member.isfile() and member.name.startswith('Python-2.7.18/Lib/'):
            relative = Path(member.name).relative_to('Python-2.7.18/Lib')
            if relative.parts[0] in {'test', 'lib-tk', 'idlelib', 'lib2to3', 'ensurepip', 'bsddb', 'msilib', 'distutils', 'curses', 'pydoc_data', 'unittest'} or relative.parts[0].startswith('plat-'):
                continue
            target = output / 'lib' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
print('STAGED', output, flush=True)
