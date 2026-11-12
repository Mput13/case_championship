"""Generate temporary QA copies of the same full offline UI, without a server."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
page=(P/'dashboard_candidate.html').read_text()
def write(name,script):
    (P/'qa'/f'{name}.html').write_text(page.replace('</body>','<script>'+script+'</script></body>'))
for name in ['network','strategy','direct']:
    write(name,'RW.ready.then(()=>navigate('+json.dumps(name)+'));')
for name,file in [('interaction','final_interaction.js'),('windows','window_transitions.js')]:write(name,(P/'qa'/file).read_text())
for pid in ['VOG_RADIAL','KUF_RADIAL','SVX_RADIAL','MRV_HYBRID','AER_HYBRID','VOG_HYBRID','AER_SEASONAL','VOG_BANK9','SVX_BANK9']:
    write('canonical-'+pid,'window.QA_PID='+json.dumps(pid)+';'+(P/'qa/canonical_interaction.js').read_text())
for phase in ['overview','navigation']:write('states-'+phase,'window.QA_PHASE='+json.dumps(phase)+';'+(P/'qa/ui_states.js').read_text())
for key,tab,script in [('calendar-window','network','RW.openWindow("calendar");$("network-changes").closest("details").open=true;'),('resource-window','network','RW.openWindow("resource");$("fleet-monthly").closest("details").open=true;'),('overview-window','network','RW.openWindow("overview");$("overview-panel").open=true;await RW.loadOverview();'),('city-window','hubs','RW.openWindow("city");'),('source','hubs','chooseCity("GOJ");researchSource("evidence","0");')]:
    write(key,'RW.ready.then(async()=>{navigate('+json.dumps(tab)+');'+script+'});')
