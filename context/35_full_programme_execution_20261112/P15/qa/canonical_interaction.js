(async()=>{
 const checks=[],test=(name,ok)=>{checks.push({name,pass:!!ok});if(!ok)throw Error(name);};
 const change=async(id,value)=>{$(id).value=value;$(id).dispatchEvent(new Event('change'));await RW.whenSettled();};
 try{await RW.ready;const pid=window.QA_PID||'VOG_RADIAL';await change('programme',pid);navigate('network');
 test('9 real canonical programmes',$('programme').options.length===9);
 test('Exact approved producer/manifest',pack.commit===FINAL.commit&&pack.manifest_sha256===FINAL.manifest_sha256&&pack.coordinator_acceptance==='ACCEPTED_FOR_UI');
 test('P13 limited approval present',FINAL.root_authorisation.independent_acceptance==='APPROVE_WITH_EXPLICIT_LIMITS');
 for(const meta of FINAL.catalogue.find(p=>p.programme_id===pid).evaluations){document.querySelector('[data-final-scenario="'+meta.context.evaluation_id+'"]').click();await RW.whenSettled();const e=current();
  test(meta.context.evaluation_id+' context',e.result.project.context.evaluation_id===meta.context.evaluation_id&&e.result.project.context.fleet_scope_id==='CASE_SJ');
  test(meta.context.external_scenario_id+' exact canonical values',Object.keys(meta.delta_summary).every(k=>Object.is(e.result.delta_summary[k],meta.delta_summary[k]))&&e.result.thresholds.net_missing_operating_cost_break_even===meta.thresholds.net_missing_operating_cost_break_even);
  test(meta.context.external_scenario_id+' unknowns retained',e.result.delta_summary.operating_result===null&&e.result.project_incremental_funding.peak_dated_day_end===null&&e.resource_monthly.every(r=>r.project_available===null));
  test(meta.context.external_scenario_id+' full arrays',e.result.project.results_monthly.length===24&&e.result.delta_monthly.length===24&&e.result.project.operations.rotations.length>100&&e.result.network_changes.length>100);
  test(meta.context.external_scenario_id+' real numbers rendered',$('economics-function').textContent.includes(ResultAdapter.fmt(e.result.thresholds.net_missing_operating_cost_break_even))&&$('monthly').querySelectorAll('tr').length===24);
  test(meta.context.external_scenario_id+' source links',e.projection_meta.projection_sha256===meta.projection_sha256&&e.projection_meta.input_pins.length>0&&e.projection_meta.full_result_artifact.gzip_sha256.length===64);
 }
 test('Native transport used',RW.transportAudit.some(x=>x.programme_id===pid&&x.codec==='DecompressionStream(gzip)'));
 test('No viewport overflow',document.documentElement.scrollWidth<=innerWidth+1);
 window.P15_CANONICAL_TEST={status:'PASS',programme:pid,width:innerWidth,checks,transport:RW.transportAudit};console.log('P15_CANONICAL_TEST '+JSON.stringify({status:'PASS',programme:pid,width:innerWidth,count:checks.length}));for(let i=0;i<checks.length;i+=3)console.log('P15_CCHECKS '+JSON.stringify(checks.slice(i,i+3)));
 }catch(e){console.error('P15_CANONICAL_TEST '+JSON.stringify({status:'FAIL',programme:window.QA_PID,width:innerWidth,error:e.message,checks}));}
})();
