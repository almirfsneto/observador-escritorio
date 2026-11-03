"""Rebuild the source snapshot without generated binaries or captured data."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root).decode().split('\0')
entries = []
for name in sorted(set(paths) - {'', 'MANIFESTO_SHA256.json'}):
    data = (root / name).read_bytes()
    entries.append(dict(path=name, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
(root / 'MANIFESTO_SHA256.json').write_text(json.dumps(dict(
    package='OBSERVADOR_ESCRITORIO_LAB', date='2026-11-03',
    note='Fontes e documentacao; exclui o proprio manifesto, dados e binarios. Nao comprova teste de desktop.',
    files=entries), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
