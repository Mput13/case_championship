import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# One temporary dictionary read. Only the five needed settlements are retained.
key = Path(os.environ['YANDEX_RASP_API_KEY_FILE']).read_text().strip()
url = 'https://api.rasp.yandex-net.ru/v3.0/stations_list/?format=json&lang=ru_RU'
request = urllib.request.Request(url, headers={'Authorization': key, 'Accept-Encoding': 'identity'})
target = {'Ханты-Мансийск', 'Сургут', 'Екатеринбург', 'Миасс', 'Челябинск'}
receipt = {'checked_at': datetime.now(timezone.utc).isoformat(), 'source_url': 'https://yandex.ru/dev/rasp/doc/ru/reference/stations-list', 'retained_scope': sorted(target), 'key_in_url': False}
try:
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = bytearray()
        while chunk := response.read(65536):
            raw.extend(chunk)
            if len(raw) > 64 * 1024 * 1024:
                raise ValueError('dictionary_size_limit')
        receipt['http_status'] = response.status
    receipt['bytes'] = len(raw)
    receipt['sha256'] = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    result = []
    for country in data.get('countries', []):
        if country.get('title') != 'Россия':
            continue
        for region in country.get('regions', []):
            for city in region.get('settlements', []):
                if city.get('title') not in target:
                    continue
                result.append({'city': city['title'], 'region': region['title'], 'codes': city.get('codes', {}), 'stations': city.get('stations', [])})
    receipt['settlements'] = result
    receipt['status'] = 'completed'
except Exception as error:
    receipt['status'] = 'error'
    receipt['error_class'] = type(error).__name__
    if hasattr(error, 'code'):
        receipt['http_status'] = error.code
path = Path('context/44_travel_assistant_chat_20261113/receipts/station_nodes.json')
path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({**{k:v for k,v in receipt.items() if k != 'settlements'}, 'cities': [{'city':c['city'], 'codes':c['codes'], 'stations':len(c['stations'])} for c in receipt.get('settlements', [])]}, ensure_ascii=False, indent=2))
