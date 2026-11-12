(async()=>{
 const report=[];const check=(name,p)=>{report.push({name,pass:!!p});if(!p)throw Error(name);};
 try{
 const before=JSON.stringify(state),version=RW.snapshot().resultVersion;
 for(const p of [{},{dataset_kind:'RED_WINGS',synthetic:true},{dataset_kind:'RED_WINGS',synthetic:false,coordinator_acceptance:'UNACCEPTED'}]){let threw=false;try{RW.load(p);}catch(e){threw=true;}check('reject invalid/unaccepted package '+report.length,threw);}
 check('rejected imports preserve full UI state',JSON.stringify(state)===before);
 check('snapshot records pinned version',version===DATA.version);
 check('saved source tranche retained',RW.getPack()===null&&evaluations.length===0);
 const snap=RW.snapshot();RW.chooseCity('KHV');RW.restore(snap);check('restore includes dataset and city',state.city===snap.state.city&&RW.snapshot().resultVersion===version);
 const dt=new DataTransfer();dt.items.add(new File(['{malformed'],'broken.json',{type:'application/json'}));$('result-file').files=dt.files;await $('result-file').onchange();check('malformed file shows error and retains state',$('import-status').className==='error'&&state.city===snap.state.city);
 console.log('P12_TARGETED_ERRORS '+JSON.stringify({status:'PASS',checks:report.length,results:'NOT_RUN'}));for(const x of report)console.log(JSON.stringify(x));
 }catch(e){console.error('P12_TARGETED_ERRORS '+JSON.stringify({status:'FAIL',error:e.message,report}));}
})();
