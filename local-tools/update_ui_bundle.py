from pathlib import Path
import copy
import shutil
import zipfile

root = Path(__file__).resolve().parent
source = root / 'bundle-assets/m2data.zip'
target = root / 'bundle-assets/m2data-ui-v1.zip'
names = ('ui.py', 'modernui.py', 'uiInventory.py', 'uimobilehud.py',
         'interfacemodule.py', 'uiMiniMap.py', 'uiscript/inventorywindow.py',
         'uiscript/characterwindow.py')
updates = {name: (root / 'm2stage' / name).read_bytes() for name in names}
# Preserve compressed asset records; only the two changed scripts are recompressed.
with zipfile.ZipFile(source) as old, source.open('rb') as reader, target.open('wb') as output:
    entries = sorted(old.infolist(), key=lambda info: info.header_offset)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as new:
        for n, info in enumerate(entries):
            if info.filename in updates:
                continue
            limit = entries[n+1].header_offset if n+1 < len(entries) else old.start_dir
            reader.seek(info.header_offset)
            record = copy.copy(info)
            record.header_offset = output.tell()
            remaining = limit - info.header_offset
            while remaining:
                data = reader.read(min(8 * 1024 * 1024, remaining))
                if not data:
                    raise EOFError(info.filename)
                output.write(data)
                remaining -= len(data)
            new.filelist.append(record)
            new.NameToInfo[record.filename] = record
        new.start_dir = output.tell()
        for name, data in updates.items():
            new.writestr(name, data)
with zipfile.ZipFile(target) as check:
    assert len(check.namelist()) == len(set(check.namelist()))
    assert len(check.namelist()) == len({info.filename for info in entries} | set(updates))
    for name, data in updates.items():
        assert check.read(name) == data
    bad = check.testzip()
    assert bad is None, bad
shutil.move(str(target), str(source))
print('Updated bundle: all entries passed CRC validation', flush=True)
