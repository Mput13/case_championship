(async()=>{
 const checks=[],test=(name,ok)=>{checks.push({name,pass:!!ok});if(!ok)throw Error(name);};
 const change=async(id,value)=>{$(id).value=value;$(id).dispatchEvent(new Event('change'));await RW.whenSettled();};
 try{
 await RW.ready;
 test('Root authorised conditional exact producer',RW.final.commit==='736859fdd08448c2564b7b9269b751abe00b5cbc'&&RW.getPack().coordinator_acceptance==='ACCEPTED_FOR_UI');
 test('Independent model review exact limits',RW.final.root_authorisation.independent_acceptance==='APPROVE_WITH_EXPLICIT_LIMITS');
 test('Four full sections and all20 city dossiers',document.querySelectorAll('main>section').length===4&&DATA.cities.length===20&&Object.keys(DATA.dossiers).length===20);
 test('9 real programmes and18 scenarios in index',$('programme').options.length===9&&RW.final.catalogue.flatMap(p=>p.evaluations).length===18);
 test('Default is conditional VOG example',state.programme==='VOG_RADIAL'&&state.scenario==='VOG_RADIAL:phased:base:passive');
 test('Native gzip decoded full wrapper',RW.transportAudit.length>0&&RW.transportAudit[0].codec==='DecompressionStream(gzip)');
 for(const pid of window.QA_PROGRAMMES||['VOG_RADIAL','KUF_RADIAL','SVX_RADIAL']){
  await change('programme',pid);
  for(const meta of RW.final.catalogue.find(p=>p.programme_id===pid).evaluations){
   await change('scenario',meta.context.evaluation_id);const e=current();
   test(pid+' '+meta.context.external_scenario_id+' exact context',e.result.project.context.evaluation_id===meta.context.evaluation_id&&state.programme===pid);
   test(pid+' '+meta.context.external_scenario_id+' exact values/null',Object.keys(meta.delta_summary).every(k=>Object.is(e.result.delta_summary[k],meta.delta_summary[k]))&&e.result.thresholds.net_missing_operating_cost_break_even===meta.thresholds.net_missing_operating_cost_break_even&&e.result.delta_summary.operating_result===null);
   test(pid+' '+meta.context.external_scenario_id+' full24months/calendars',e.result.project.results_monthly.length===24&&e.result.delta_monthly.length===24&&e.result.project.operations.rotations.length>100&&e.result.network_changes.length>100);
   test(pid+' '+meta.context.external_scenario_id+' source/funding/resource',e.projection_meta.projection_sha256===meta.projection_sha256&&e.projection_meta.input_pins.length>0&&e.result.project_incremental_funding.peak_dated_day_end===null&&e.resource_monthly.every(r=>r.project_available===null));
   test(pid+' '+meta.context.external_scenario_id+' real threshold rendered',$('economics-function').textContent.includes(ResultAdapter.fmt(e.result.thresholds.net_missing_operating_cost_break_even))&&$('monthly').querySelectorAll('tr').length===24);
  }
 }
 await change('programme','VOG_RADIAL');await change('scenario','VOG_RADIAL:phased:cautious:passive');
 test('Exact cautious H retained',headroom(current())===263891478.0220616);
 test('Full result not replaced by subtotal',current().result.delta_summary.operating_result===null&&$('economics-function').textContent.includes('Абсолютный известный операционный подытог VOG отрицателен'));
 await change('period','2027');test('Year filter uses producer annual and12rows',state.period==='2027'&&$('monthly').querySelectorAll('tr').length===12&&ResultAdapter.annual(current(),'2027').year===2027);
 await change('period','2027–2028');
 $('network-changes').closest('details').open=true;const initial=state.resultNetworkPage;document.querySelector('[data-result-page="Network"][data-page="1"]').click();test('Network pagination changes page not data',state.resultNetworkPage===initial+1&&current().result.network_changes.length>16);
 $('rotations').closest('details').open=true;document.querySelector('[data-result-page="Rotation"][data-page="1"]').click();test('Rotation pagination operates',state.resultRotationPage===1&&$('rotations').querySelectorAll('tbody tr').length===16);
 navigate('network');const econButton=document.querySelector('[data-final-source="economics"]');econButton.focus();econButton.click();test('Real canonical receipt/source dialog',$('source-dialog').open&&$('source-body').textContent.includes('source_full_result_sha256')&&$('source-body').textContent.includes('263891478.0220616'));$('source-close').click();await new Promise(requestAnimationFrame);test('Modal returns keyboard focus',document.activeElement===econButton);
 const programme=state.programme;chooseCity('GOJ');test('City research independent from canonical programme',state.city==='GOJ'&&state.programme===programme);
 await change('carrier','RW');await change('source-month','2026-12');test('Source filters actual rows, forecast independent',offers().every(r=>rw(r))&&state.period==='2027–2028'&&state.sourceMonth==='2026-12');
 const before=snapshot();$('tour-start').click();$('tour-next').click();test('Route stop2 is real canonical network',state.tour===1&&state.active==='network');$('tour-exit').click();await change('programme','AER_HYBRID');chooseCity('KUF');await $('tour-return').onclick();test('Return restores actual programme/scenario/city',state.programme===before.state.programme&&state.scenario===before.state.scenario&&state.city===before.state.city&&state.tour===1);$('tour-exit').click();
 $('overview-panel').open=true;await RW.loadOverview();test('All1958 overview retained separate mode',RW.final.overview.length===1958&&RW.final.overview_contract.result_mode==='P06_DISJOINT_DATE_COMPONENTS_WITH_ADDITIVE_P06_FINANCE');
 $('overview-programme').value='VOG_RADIAL';$('overview-programme').dispatchEvent(new Event('change'));test('Overview filter is source rows not canonical replacement',$('overview-data').textContent.includes('VOG')&&state.programme==='VOG_RADIAL');
 const meta=RW.final.overview[0]._source;test('Overview exact row/source hash',/^[a-f0-9]{64}$/.test(meta.row_sha256)&&meta.commit===RW.final.commit);
 $('overview-data').querySelector('details').open=true;$('disposition-search').value='AUTH_MOW';$('disposition-search').dispatchEvent(new Event('input'));test('Author statuses remain explicit',$('overview-data').textContent.includes('27')&&RW.final.dispositions.some(r=>r.status.includes('OPEN')));
 const old=snapshot(),dt=new DataTransfer();dt.items.add(new File([JSON.stringify({dataset_kind:'RED_WINGS',synthetic:false,coordinator_acceptance:'PENDING_COORDINATOR_ACCEPTANCE',commit:null,manifest_sha256:null,evaluations:[]})],'pending.json',{type:'application/json'}));$('result-file').files=dt.files;await $('result-file').onchange();test('Pending source import rejected, existing real result retained',pack.coordinator_acceptance==='ACCEPTED_FOR_UI'&&state.programme===old.state.programme&&$('import-status').className==='error');
 test('Concrete old datasets and excluded EMISS named',$('method-source-catalog').textContent.includes('OurAirports')&&$('method-source-catalog').textContent.includes('96 660')&&$('method-source-catalog').textContent.includes('NOAA')&&$('method-source-catalog').textContent.includes('18 360'));
 test('Expert5 insertions no completed unknowns',$('expert-insertions').querySelectorAll('details').length===5&&$('expert-insertions').textContent.includes('материальные неизвестные'));
 await change('scope','EXT_NO_NEW_TU214');test('Separate resource group never substitutes phased canonical',current()===undefined&&state.programme==='');await change('scope','CASE_SJ');
 await change('programme','VOG_RADIAL');await change('scenario','VOG_RADIAL:phased:base:passive');chooseCity('VOG');state.layer='proposed';$('layer').value='proposed';renderMap();
 test('20hubs and endpoint labels preserved',document.querySelectorAll('.map-point').length===20&&document.querySelectorAll('.map-endpoint').length>0);
 test('No document-wide overflow',document.documentElement.scrollWidth<=innerWidth+1);
 window.scrollTo(0,0);
 window.P15_FINAL_TEST_RESULT={status:'PASS',width:innerWidth,checks,transport:RW.transportAudit,programmes:window.QA_PROGRAMMES||['VOG_RADIAL','KUF_RADIAL','SVX_RADIAL']};
 console.log('P15_FINAL_CHECKS '+JSON.stringify({status:'PASS',width:innerWidth,count:checks.length,programmes:window.P15_FINAL_TEST_RESULT.programmes}));for(let i=0;i<checks.length;i+=3)console.log('P15_GROUP '+JSON.stringify(checks.slice(i,i+3)));
 }catch(e){window.P15_FINAL_TEST_RESULT={status:'FAIL',checks,error:e.message,width:innerWidth};console.error('P15_FINAL_CHECKS '+JSON.stringify({status:'FAIL',error:e.message,width:innerWidth,count:checks.length}));for(let i=0;i<checks.length;i+=3)console.log('P15_GROUP '+JSON.stringify(checks.slice(i,i+3)));}
})();
