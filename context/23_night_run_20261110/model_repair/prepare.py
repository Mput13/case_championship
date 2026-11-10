#!/usr/bin/env python3
"""Restore pinned Git inputs. Only --restore-public uses HTTP; replay is offline."""
import argparse
import csv
import hashlib
import io
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUTHOR = '2f03b693a62c219e9475fcd1e26295039f6a49d7'
STAGE22 = '6ec84a7d2a6eb50b547a61df82fc5a424f48f146'
CIRI = '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
URL = ('https://storage.yandexcloud.net/tochno-st-catalog/Geo/'
       'data_intercity_connectivity_162_v20260629/'
       'data_intercity_connectivity_162_v20260629_csv.zip')
RAW_SHA = 'aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53'
RAW_NAME = 'data_intercity_connectivity_162_v20260629.csv'


def show(sha, path):
    return subprocess.check_output(['git', 'show', f'{sha}:{path}'], cwd=ROOT)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--restore-public', action='store_true')
    args = ap.parse_args()
    paths = ['src/' + x + '.py' for x in ['network_model', 'demand_model', 'rules', 'airports_meta']]
    paths += ['data/assumptions/' + x + '.csv' for x in [
        'network', 'demand', 'range', 'resort_airports', 'south_west_regions', 'hub_candidates_extra']]
    paths += ['data/manual/' + x + '.csv' for x in ['closed_airports', 'airport_names']]
    paths += ['data/processed/' + x for x in [
        'catchments.csv', 'demand_pairs.csv', 'demand_fit.json', 'kover_days.csv',
        'longlist.csv', 'longlist_scores_min500.csv']]
    exports = ['network_routes.csv', 'network_summary.csv', 'mandatory_routes_table.csv']
    manifest = []
    for path in paths + ['data/processed/' + x for x in exports]:
        data = show(AUTHOR, path)
        dest = ROOT / ('frozen_exports' if path.split('/')[-1] in exports else 'author') / (
            path.split('/')[-1] if path.split('/')[-1] in exports else path)
        put(dest, data)
        manifest.append(dict(source_commit=AUTHOR, author_ref='Анастасия/kiruha355', source_path=path,
                             local_path=str(dest.relative_to(ROOT)), sha256=digest(data), bytes=len(data),
                             git_blob=subprocess.check_output(['git','rev-parse',f'{AUTHOR}:{path}'],cwd=ROOT,text=True).strip()))
    same = show(AUTHOR, 'src/network_model.py') == show(STAGE22, 'src/network_model.py')
    assert same
    extract = ROOT / 'inputs/tochno_runtime_projection.csv'
    if args.restore_public:
        rawdir = ROOT / 'raw'
        rawdir.mkdir(exist_ok=True)
        payload = urllib.request.urlopen(URL, timeout=60).read()
        archive = zipfile.ZipFile(io.BytesIO(payload))
        member = next(n for n in archive.namelist() if n.endswith(RAW_NAME))
        raw = archive.read(member)
        assert digest(raw) == RAW_SHA, (digest(raw), RAW_SHA)
        put(rawdir / RAW_NAME, raw)
        # Exact row/column projection for dm.links(): all air/rail rows, all columns it reads.
        source = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), delimiter=';'))
        cols = ['transport_type', 'distance_km', 'comment', 'city_from', 'city_to', 'distance_hr']
        projected = [{k:r[k] for k in cols} for r in source if r['transport_type'] in ('air','rail')]
        out = io.StringIO(newline='')
        w = csv.DictWriter(out, cols, delimiter=';', lineterminator='\n')
        w.writeheader(); w.writerows(projected)
        put(extract, out.getvalue().encode())
        receipt = dict(url=URL, raw_sha256=RAW_SHA, zip_bytes=len(payload), raw_bytes=len(raw),
                       raw_rows=len(source), projected_rows=len(projected), projection_columns=cols,
                       license='CC BY 4.0; Если быть точным', status='PINNED_RAW_HASH_VERIFIED',
                       new_observation=False, expected_hash_origin=f'{AUTHOR}:data/raw/_manifest.json')
        put(ROOT/'public_restore_receipt.json', (json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode())
    assert extract.exists(), 'First restore pinned public input with --restore-public'
    put(ROOT/'author/data/raw/tochno_intercity'/RAW_NAME, extract.read_bytes())
    manifest.append(dict(source_commit=AUTHOR, source_path='data/raw/tochno_intercity/'+RAW_NAME,
                         raw_sha256=RAW_SHA, local_path=str(extract.relative_to(ROOT)),
                         sha256=digest(extract.read_bytes()), bytes=extract.stat().st_size,
                         grain='air/rail row projection; same dm.links input semantics; not a new observation'))
    result = dict(inputs=manifest, stage22_network_code_identical=same,
                  author_commit=AUTHOR, stage22_commit=STAGE22, ciri_commit=CIRI,
                  acceptance_scope='RAW_HASH_VERIFIED; extraction checked again by replay.py')
    put(ROOT/'source_manifest.json', (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(dict(files=len(manifest),stage22_identical=same)))


if __name__ == '__main__':
    main()
