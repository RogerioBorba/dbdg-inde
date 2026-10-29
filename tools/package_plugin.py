"""Build an installable QGIS ZIP without repository files or caches.

Run: python tools/package_plugin.py
"""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build_package(output=None):
    output = Path(output) if output else ROOT / 'dist' / 'dbdg_inde.zip'
    files = list(ROOT.glob('*.py'))
    files += [ROOT / name for name in ('metadata.txt', 'icon.png', 'LICENSE', 'README.md')]
    for directory in ('service_handlers', 'defusedxml', 'certs'):
        files += [path for path in (ROOT / directory).rglob('*')
                  if path.is_file() and '__pycache__' not in path.parts
                  and path.suffix not in ('.pyc', '.pyo')]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, 'dbdg_inde/' + path.relative_to(ROOT).as_posix())
    return output


if __name__ == '__main__':
    print(build_package())
