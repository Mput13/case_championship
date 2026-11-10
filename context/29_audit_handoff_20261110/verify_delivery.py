import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parent
manifest=json.loads((root/'delivery_manifest.json').read_text())
for row in manifest['files']:
    path=root/row['path']
    assert path.is_file(), row['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'], row['path']
repo=root.parent.parent
owner=json.loads((root/'protected_owner_files.json').read_text())
for name,sha in owner.items():
    assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==sha,name
print(json.dumps({'delivery_files':len(manifest['files']),'owner_files_unchanged':len(owner),'full_audit_complete':False,'scope':'delivery hashes only; not source truth or full replay'}))
