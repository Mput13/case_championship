"""Render only the counted, pinned schedule sample; no demand inference."""
from pathlib import Path
import hashlib, html, json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
data = json.loads((HERE / 'svx_competition_counts.json').read_text())
source = ROOT / 'context/21_visual_explainer_draft_20261110/inputs/published-services.csv'
assert hashlib.sha256(source.read_bytes()).hexdigest() == data['source_sha256']
cities = {'AER': 'Сочи', 'KJA': 'Красноярск', 'KUF': 'Самара', 'KZN': 'Казань', 'MRV': 'Минеральные Воды', 'OMS': 'Омск', 'REN': 'Оренбург', 'VOG': 'Волгоград'}
carrier_names = {'RED WINGS': 'Red Wings', 'Ural airlines': 'Уральские авиалинии', 'ЮТэйр': 'Utair'}
maximum = max(sum(v.values()) for v in data['counts'].values())
rows = []
for city in ['AER', 'MRV', 'KUF', 'KJA', 'KZN', 'REN', 'OMS', 'VOG']:
    counts = data['counts'][city]
    rw = counts.get('RED WINGS', 0)
    others = sum(counts.values()) - rw
    segments = ''.join(f'<span class="freq-{kind}" style="width:{n / maximum * 100:.3f}%">{n}</span>' for kind, n in [('rw', rw), ('other', others)] if n)
    detail = '; '.join(f'{carrier_names.get(c, c)} — {n}' for c, n in counts.items())
    rows.append(f'<div class="freq-row"><b>Екатеринбург → {cities[city]}</b><div class="freq-track" aria-label="{html.escape(detail)}">{segments}</div><p>{html.escape(detail)}</p></div>')
out = '''<figure class="competition-figure"><figcaption><b>Опубликованные вылеты из Екатеринбурга, 7–13 декабря 2026</b></figcaption>
<p>Один столбик — одно направление. Показаны вылеты в одну сторону из сохранённого календаря Цири.</p>
<div class="freq-legend"><span><i class="freq-rw"></i>Red Wings</span><span><i class="freq-other"></i>Другие перевозчики в этом снимке</span></div>''' + ''.join(rows) + '''
<p class="source">Источник: <a href="https://github.com/Mput13/case_championship/blob/93fa5cf4a10ab67e05c93d19fc5375fc58ef9299/context/17_aircraft_route_review/evidence/published_service_facts.csv">датированный календарь, версия Цири 93fa5cf4</a>. Повторно посчитаны 65 строк; дублей по дате, рейсу, аэропортам и перевозчику не найдено. Это запланированные вылеты, не выполненные рейсы, кресла, пассажиры или доли рынка. Отсутствие другого перевозчика в столбике не доказывает отсутствия конкуренции вне этого среза. Лето 2027 года этим снимком не описано.</p></figure>'''
(HERE / 'competition_figure.html').write_text(out)
