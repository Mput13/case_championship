"""Re-extract selected rows from the retained, complete public KJA text (no network)."""
from pathlib import Path
import csv, hashlib

ROOT=Path(__file__).resolve().parent
lines=(ROOT/'sources/KJA-SCHEDULE.txt').read_text().splitlines()
airport_map={'Омск':'OMS','Иркутск':'IKT','Улан-Удэ':'UUD','Томск':'TOF','Абакан':'ABA','Чита':'HTA','Екатеринбург':'SVX','Самара':'KUF','Барнаул':'BAX','Горно-Алтайск':'RGK','Новосибирск':'OVB','Уфа':'UFA','Казань':'KZN','Талакан':'TLK','Кызыл':'KYZ','Баку':'GYD','Ташкент':'TAS','Шымкент':'CIT'}
rows=[]
total=0
for i,line in enumerate(lines):
 if line!='Направление' or i+25>=len(lines) or lines[i+2]!='Авиакомпания' or lines[i+3]!='Рейс':continue
 total+=1
 destination=lines[i+1]
 if destination not in airport_map:continue
 block=lines[i:i+32]
 def field(label):return block[block.index(label)+1] if label in block else 'UNKNOWN'
 carrier=block[block.index('Тип воздушного судна')+3] if 'Тип воздушного судна' in block else 'UNKNOWN'
 rows.append({'observation_id':f'KJA26-{total:04d}','origin':'KJA','destination':airport_map[destination],'carrier':carrier,'flight':field('Рейс'),'departure_local':field('Вылет'),'arrival_local':field('Прилёт'),'weekdays_iso':''.join(c for c in field('Дни недели') if c.isdigit()),'validity':field('Навигация'),'aircraft':field('Тип ВС'),'source_id':'KJA-SCHEDULE','source_locator':f'sources/KJA-SCHEDULE.txt:line:{i+1}','source_row_sha256':hashlib.sha256('\n'.join(block).encode()).hexdigest(),'period':'winter2026/27; source-specific validity','unit':'published station pair service; times local','coverage':'selected KJA outbound destinations only; not complete competitors; reverse unobserved','status':'published_offer','physical_adjacent_leg':'UNKNOWN','saleable_seats':'UNKNOWN','fare_rub':'UNKNOWN','baggage':'UNKNOWN','as_of':'2026-11-12'})
with (ROOT/'schedule_observations.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print({'source_blocks':total,'selected_rows':len(rows),'coverage':'SOURCE_EXPORT_ONLY'})
