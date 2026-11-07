#!/usr/bin/env python3
"""Build a discovery register; verification applies to individual claims, not domains."""
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / 'context'
rows = []

def read_csv(rel):
    with (CTX / rel).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def add(prefix, records, mapping, provenance, state, category):
    for i, original in enumerate(records, 1):
        def field(name, default=''):
            key = mapping.get(name)
            return original.get(key, default) if key else default
        url = field('url').strip()
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.netloc:
            raise ValueError(f'Invalid source URL in {provenance}: {url!r}')
        # Keep query parameters: they can identify the actual document or indicator.
        canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', parts.query, ''))
        source_key = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        rows.append(dict(
            record_id=f'{prefix}-{i:03d}', source_key=source_key,
            category=field('category', category), title=field('title', parts.netloc), url=url,
            source_record_id=field('source_record_id', str(i)),
            verification_scope=state, claimed_status=field('claimed_status', 'UNKNOWN'),
            period=field('period', 'UNKNOWN'), grain=field('grain', 'UNKNOWN'),
            useful_for=field('useful_for'), limitations=field('limitations'),
            license_claim=field('license_claim', 'UNKNOWN'),
            provenance=provenance,
        ))

add('ORG',read_csv('01_primary/organizer_catalog.csv'),dict(title='title',url='url',source_record_id='id',claimed_status='verification',useful_for='description_from_organizer'),'01_primary/organizer_catalog.csv','CATALOG_ENTRY_ONLY','organizer_catalog')
add('NB',json.loads((CTX/'03_notebooklm/research_leads.json').read_text()),dict(url='url',claimed_status='status',limitations='origin'),'03_notebooklm/research_leads.json','LEAD','notebooklm_bibliography')
add('FA',read_csv('04_research/flash_aviation_data/sources.csv'),dict(title='title',url='url',source_record_id='id',claimed_status='access_status',period='period',grain='grain',useful_for='use_case',limitations='limitation',license_claim='license_or_unknown'),'04_research/flash_aviation_data/sources.csv','FLASH_CLAIM_REQUIRES_REVIEW','aviation')
add('FE',read_csv('04_research/flash_external_data/sources.csv'),dict(title='name',url='url',source_record_id='source_id',category='category',claimed_status='status',grain='granularity',useful_for='case_relevance',limitations='limitations_notes',license_claim='license_terms'),'04_research/flash_external_data/sources.csv','FLASH_CLAIM_REQUIRES_REVIEW','external_data')
add('FM',read_csv('04_research/flash_methods/methods_sources.csv'),dict(title='name_title',url='url',source_record_id='source_id',claimed_status='status',period='period_year',grain='granularity_type',useful_for='relevance_to_case',limitations='unconfirmed_limitations'),'04_research/flash_methods/methods_sources.csv','FLASH_CLAIM_REQUIRES_REVIEW','methods')
add('TD',read_csv('07_verification/terra_data/verified_sources.csv'),dict(title='organization',url='url',source_record_id='id',claimed_status='status',period='period',grain='grain',useful_for='schema_units',limitations='confirmed_and_limits',license_claim='license'),'07_verification/terra_data/verified_sources.csv','TERRA_CHECKED_SCOPE_SEE_REPORT','independent_data_audit')

for prefix, topic, category in (
    ('TS', 'similar_studies', 'additional_studies'),
    ('TT', 'practical_tools', 'additional_tools'),
    ('TC', 'network_cases', 'additional_network_cases'),
):
    provenance = f'09_additional_research/terra_{topic}/sources.csv'
    add(prefix, read_csv(provenance), dict(
        title='title', url='url', source_record_id='source_id',
        claimed_status='status', useful_for='case_use',
        limitations='limitations', license_claim='access_or_license',
    ), provenance, 'TERRA_CHECKED_SCOPE_SEE_REPORT', category)

out = CTX/'05_datasets/source_registry.csv'
with out.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader();w.writerows(rows)
index={}
for row in rows:
    item=index.setdefault(row['source_key'], {'url':row['url'],'records':[]})
    item['records'].append(row['record_id'])
(CTX/'05_datasets/source_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
print(f'{len(rows)} discovery records; {len(index)} distinct normalized URLs')

# Reviews are kept separately: HTTP success, valid metadata and verified values
# are different findings. Do not manufacture one ranking of these statuses.
reviews = []
for r in read_csv('07_verification/terra_data/verified_sources.csv'):
    reviews.append(dict(review_id='TD-'+r['id'], original_record_id='TD-'+r['id'][1:].zfill(3), url=r['url'], reviewed_title=r['organization'], status=r['status'], checked_scope=r['schema_units'], access_observation=r['access_observation'], limitations=r['confirmed_and_limits'], license_status=r['license'], provenance='07_verification/terra_data/verified_sources.csv'))
for r in read_csv('07_verification/terra_methods_data_review/external_sources.csv'):
    reviews.append(dict(review_id='TM-'+r['source_id'], original_record_id='FE-'+r['source_id'][4:].zfill(3) if r['source_id'].startswith('SRC-') else '', url=r['url'], reviewed_title=r['actual_indicator'], status='SEE_ACCESS_AND_LIMITS', checked_scope=r['grain'], access_observation=r['access_status'], limitations=r['limits'], license_status=r['license_status'], provenance='07_verification/terra_methods_data_review/external_sources.csv'))
aviation_ids = {r['source_record_id']:r['record_id'] for r in rows if r['record_id'].startswith('FA-')}
for i,r in enumerate(read_csv('07_verification/terra_aviation_review/corrected_sources.csv'),1):
    reviews.append(dict(review_id=f'TA-{i:03d}', original_record_id=aviation_ids[r['original_id']], url=r['url'], reviewed_title=r['actual_title'], status=r['status'], checked_scope=r['verified_scope'], access_observation=r['license_access_limit'], limitations=r['use_case'], license_status='SEE_ACCESS_AND_LIMITS', provenance='07_verification/terra_aviation_review/corrected_sources.csv'))
with (CTX/'05_datasets/source_reviews.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(reviews[0]));w.writeheader();w.writerows(reviews)
print(f'{len(reviews)} source review records; original descriptions remain separate')
