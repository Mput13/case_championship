#!/usr/bin/env python3
"""Pin supplied Git inputs and package artifacts. Read-only outside this folder."""
import hashlib
import json
import subprocess
from pathlib import Path

BASE=Path(__file__).resolve().parent
REPO=BASE.parents[2]
ROOT='4a9971beeacbc40559943eae05b9004c90165917'
AUTHOR='4a9763565f70b9ab1eddde2f5daca07687560948'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    inputs=[]
    for commit,path in [
        (ROOT,'context/28_evening_run_20261110/briefs/digital_growth.md'),
        (ROOT,'context/28_evening_run_20261110/contract.md'),
        (ROOT,'context/28_evening_run_20261110/input_manifest.json'),
        (ROOT,'context/28_evening_run_20261110/hypotheses.csv'),
        (AUTHOR,'docs/09_redwings_site_insights.md'),
    ]:
        b=subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=REPO)
        inputs.append({'commit':commit,'path':path,'bytes':len(b),'sha256':sha(b),
                       'role':'supplied context; not universal acceptance'})
    artifacts=[]
    for path in sorted(BASE.rglob('*')):
        if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts:
            b=path.read_bytes()
            artifacts.append({'path':str(path.relative_to(BASE)),'bytes':len(b),'sha256':sha(b)})
    manifest={'schema':1,'root_commit':ROOT,'first_useful_slice_commit':'45c3bf06384ea5a6608eb5435aeb4f80cab3a1e2',
              'scope':'context/28_evening_run_20261110/digital_growth/',
              'browser_observed_msk':'2026-11-10 19:11–19:23','browser_closed':True,
              'publications_checked_on':'2026-11-10','inputs':inputs,'artifacts':artifacts,
              'live_sales_payments_refunds':'NOT_RUN','independent_review':'NOT_RUN_BY_THIS_AGENT',
              'limitations':['No personal data or confirmed paid service; anonymous shopping state only.',
                             'FAVT annual top5 and denominator read via primary search index; direct source download failed.',
                             'Full primary numeric ranking belowtop5 and numeric annual Ural result not recovered.',
                             'Traffic/conversion/margins/contact costs/resource productivity are explicit diagnostic scenarios.',
                             'No aircraft delivery availability or profitability proof; no future number2 deadline.']}
    (BASE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'inputs':len(inputs),'artifacts':len(artifacts),'output_manifest':'manifest.json'},ensure_ascii=False))


if __name__=='__main__':
    main()
