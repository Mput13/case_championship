import { readFile, writeFile } from 'node:fs/promises';
import { loadConfig } from '../../../apps/red-wings-travel-assistant/src/config.mjs';
import { loadSnapshot, SnapshotSchedules } from '../../../apps/red-wings-travel-assistant/src/schedules.mjs';
import { planTrip, getExamples } from '../../../apps/red-wings-travel-assistant/src/planner.mjs';
const app = new URL('../../../apps/red-wings-travel-assistant/', import.meta.url);
const snapshot = await loadSnapshot();
const examples = getExamples(snapshot);
const responses = await Promise.all(examples.examples.map(e => planTrip(e.request, { snapshot, schedules: new SnapshotSchedules(snapshot), config: loadConfig({}) })));
const smoke = JSON.parse(await readFile(new URL('../receipts/app_pi_smoke.json', import.meta.url), 'utf8'));
if (smoke.status === 'completed') responses[0].assistant = smoke.response.assistant;
const payload = JSON.stringify({ examples, responses }).replaceAll('<', '\\u003c');
let html = await readFile(new URL('public/index.html', app), 'utf8');
const css = await readFile(new URL('public/styles.css', app), 'utf8');
const js = await readFile(new URL('public/app.js', app), 'utf8');
const glue = `
const PREVIEW_DATA = ${payload};
const previewKey = r => JSON.stringify([r.mode,r.origin,r.destination,r.date_from,r.date_to,r.flight_number||'',r.flight_date||'']);
window.fetch = async (path, options={}) => {
 if(path==='/api/health')return new Response(JSON.stringify({schedule_mode:'snapshot',schedule_configured:true}));
 if(path==='/api/examples')return new Response(JSON.stringify(PREVIEW_DATA.examples));
 if(path==='/api/plan'){
  const r=JSON.parse(options.body);const i=PREVIEW_DATA.examples.examples.findIndex(e=>previewKey(e.request)===previewKey(r));
  const data=i>=0&&!r.origin_address&&!r.destination_address?PREVIEW_DATA.responses[i]:{status:'needs_data',data_mode:'snapshot',variants:[],sources:[],message:'Во встроенном просмотре доступны примеры. Для других запросов откройте локальный прототип.'};
  return new Response(JSON.stringify(data));
 }
 throw new Error('Only saved preview data is available');
};`;
const initial = `
const initialExample=PREVIEW_DATA.examples.examples[0];
setMode(initialExample.request.mode);
for(const [name,value] of Object.entries(initialExample.request)){const f=field(name);if(f)f.value=value;}
syncDates();clearResults();document.querySelector('#empty-state').hidden=true;
renderResponse(PREVIEW_DATA.responses[0]);
`;
const theme = `html,body{background:transparent!important;color:var(--foreground)!important} :root{--ink:var(--foreground);--muted:var(--muted-foreground);--line:var(--border);--milk:var(--secondary);--paper:var(--card);--rose:var(--destructive-surface);--amber-bg:var(--warning-surface);--amber:var(--warning);--font:var(--font-sans);--red:var(--destructive);--red-dark:var(--destructive)} .site-header,.page-heading,.site-footer{display:none}.page{padding:0!important}.planner-panel{position:static!important}.page,.workspace{max-width:100%}.preview-label{margin:0 0 14px;font-size:12px;color:var(--muted-foreground)} .warnings{background:var(--secondary);color:var(--muted-foreground)}`;
html = html.replace('<link rel="stylesheet" href="/styles.css">', `<style>${css}\n${theme}</style>`).replace('<script src="/app.js" defer></script>', '').replace('<main id="planner" class="page">', '<p class="preview-label">Встроенный просмотр сохранённых примеров · Полный прототип: localhost:3080</p><main id="planner" class="page">').replace('</body>', `<script>${glue}\n${js}\n${initial}</script></body>`);
await writeFile(new URL('../preview.html', import.meta.url), html.split('\n').map(line => line.trimEnd()).join('\n'));
console.log(JSON.stringify({examples:examples.examples.length,source:'actual planner outputs; one real Pi response',path:new URL('../preview.html',import.meta.url).pathname}));
