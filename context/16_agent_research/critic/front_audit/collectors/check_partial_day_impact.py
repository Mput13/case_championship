from pathlib import Path
import ast,re,csv,json,html,datetime,collections
R=Path(__file__).resolve().parents[1];F=R/'raw/front';raw=list(csv.DictReader((F/'data/raw/favt_posts.csv').open()))
t=ast.parse((F/'src/kover_days.py').read_text());nodes=[n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(k,ast.Name) and k.id in ['NAMES','AIRPORT_MSG','LIFTED'] for k in n.targets) or isinstance(n,ast.FunctionDef) and n.name=='find_airports'];ns={'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),'reviewed_airport_flags','exec'),ns)
correct={};rx=re.compile(r'tgme_widget_message_text\s+js-message_text[^>]*>(.*?)</div>',re.S)
for p in (R/'raw/primary').glob('favt_info_*.html'):
 for pid,body in re.findall(r'data-post="favt_info/(\d+)"(.*?)(?=data-post="|\Z)',p.read_text(),re.S):
  m=rx.search(body)
  if m:
   tx=html.unescape(re.sub(r'<br\s*/?>','\n',m.group(1)));correct[pid]=re.sub('<[^>]+>','',tx).strip()
def events(replace):
 out=collections.defaultdict(set);e=[]
 for r in raw:
  txt=replace.get(r['id'],r['text'])
  if ns['AIRPORT_MSG'].search(txt) and not ns['LIFTED'].search(txt):
   for i in ns['find_airports'](txt):out[i].add(r['dt_msk'][:10]);e.append((i,r['dt_msk'][:10],r['id']))
 return out,e
before,eb=events({});after,ea=events(correct)
diff=[]
for i in ns['NAMES']:
 drop=sorted(before[i]-after[i]);add=sorted(after[i]-before[i])
 if drop or add:
  diff.append({'iata':i,'removed_intro_post_days':drop,'added_intro_post_days':add,'removed_evidence_posts':[{'day':d,'id':pid} for ii,d,pid in eb if ii==i and d in drop],'added_evidence_posts':[{'day':d,'id':pid} for ii,d,pid in ea if ii==i and d in add]})
out={'replaced_posts':len(correct),'sampling':'three selected Telegram pages, not random or full-history','algorithm':'original kover_days intro logic retained, body extraction corrected only for sampled posts','differences':diff,'limitations':'This is a partial reparse impact, NOT a corrected total or an estimate of full-history error.'};(R/'partial_day_impact.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
