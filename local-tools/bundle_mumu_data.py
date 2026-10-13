from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent / 'work'
assets = root / 'bundle-assets'
assets.mkdir(exist_ok=True)
with zipfile.ZipFile(assets / 'm2data.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as z:
    for base, prefix in ((root / 'm2stage', ''), (root / 'm2serverpack/server', 'server/')):
        for path in base.rglob('*'):
            if path.is_file():
                z.write(path, prefix + path.relative_to(base).as_posix())
    z.write(root / 'loginInfo.py', 'loginInfo.py')
print('Bundled:', (assets / 'm2data.zip').stat().st_size, flush=True)
