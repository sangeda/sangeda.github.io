#!/usr/bin/env python3
"""Stage public files and restore Observatory downloads from its existing release.

No OpenAlex re-harvest and no change to original snapshot timestamps.
"""
import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
import build_muhas_observatory as observatory

ROOT = Path(__file__).resolve().parents[1]

def main():
    repo = 'sangeda/sangeda.github.io'
    releases = json.loads(subprocess.check_output([
        'gh', 'api', f'repos/{repo}/releases?per_page=100'], text=True))
    eligible = [r for r in releases if r['tag_name'].startswith('muhas-pubs-') and not r['draft']]
    if not eligible:
        raise SystemExit('No Observatory release found. Stop rather than remove existing downloads.')
    release = max(eligible, key=lambda r: (r['tag_name'][11:21], r['published_at']))
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        subprocess.run(['gh', 'release', 'download', release['tag_name'], '--repo', repo,
            '--dir', str(folder), '--pattern', '*.xlsx', '--pattern', '*.sqlite',
            '--pattern', '*_works.csv', '--pattern', '*_authorships.csv', '--pattern', '*_manifest.json'], check=True)
        for asset in release['assets']:
            file = folder / asset['name']
            if file.exists() and asset.get('digest', '').startswith('sha256:'):
                if hashlib.sha256(file.read_bytes()).hexdigest() != asset['digest'][7:]:
                    raise SystemExit('Observatory release checksum mismatch.')
        manifests = list(folder.glob('*_manifest.json'))
        if len(manifests) != 1:
            raise SystemExit('Ambiguous Observatory release manifest.')
        manifest = json.loads(manifests[0].read_text())
        snapshot = manifest['snapshot_id']
        if Path(snapshot).name != snapshot:
            raise SystemExit('Invalid snapshot name.')
        downloads = ROOT/'muhas-publications/downloads'
        downloads.mkdir(parents=True, exist_ok=True)
        for suffix, alias in [('.xlsx', 'MUHAS_Publications_LATEST.xlsx'),
                ('.sqlite', 'MUHAS_Publications_LATEST.sqlite'),
                ('_works.csv', 'MUHAS_Publications_LATEST.csv'),
                ('_authorships.csv', 'MUHAS_Authorships_LATEST.csv')]:
            source = folder / (snapshot + suffix)
            shutil.copy2(source, downloads/source.name)
            shutil.copy2(source, downloads/alias)
        with sqlite3.connect(downloads/'MUHAS_Publications_LATEST.sqlite') as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise SystemExit('Observatory database integrity check failed.')
            if db.execute('SELECT COUNT(*) FROM works').fetchone()[0] != manifest['works_processed']:
                raise SystemExit('Observatory database count mismatch.')
        with (downloads/'MUHAS_Publications_LATEST.csv').open(encoding='utf-8-sig', newline='') as f:
            works = list(csv.DictReader(f))
        if len(works) != manifest['works_processed']:
            raise SystemExit('Observatory CSV count mismatch.')
        for row in works:
            row['publication_year'] = int(row['publication_year'])
        annual, quarters, types = observatory.summaries(works)
        observatory.build_dashboard(works, annual, quarters, types, manifest)
        observatory.DATA.joinpath('snapshot_manifest.json').write_text(json.dumps(manifest, indent=2))
    stage = ROOT/'_site'
    stage.mkdir(exist_ok=True)
    for directory in ['assets', 'data', 'muhas-publications', 'dcepd-courses']:
        shutil.copytree(ROOT/directory, stage/directory, dirs_exist_ok=True)
    for file in [*ROOT.glob('*.html'), ROOT/'.nojekyll']:
        shutil.copy2(file, stage/file.name)
    print('Staged catalogue and existing Observatory release:', release['tag_name'])

if __name__ == '__main__':
    main()
