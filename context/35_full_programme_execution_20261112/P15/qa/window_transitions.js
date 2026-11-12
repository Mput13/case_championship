(async()=>{
 const checks=[],assert=(name,pass)=>{checks.push({name,pass:!!pass});if(!pass)throw Error(name);};
 try{await RW.ready;
 for(const [tab,keys] of [['hubs',['city','observations']],['direct',['offers','fares','bases','international']],['network',['resource','calendar','overview']],['strategy',['expert','method']]]){
  document.querySelector('#tabs a[data-t="'+tab+'"]').click();assert(tab+' only one visible section',sections.filter(k=>!$(k).hidden).length===1&&!$(tab).hidden&&document.querySelector('#tabs a[aria-current=page]').dataset.t===tab);
  for(const key of keys){const button=document.querySelector('[data-detail="'+key+'"]');button.focus();button.click();assert(key+' visible current pane',$('detail-dialog').open&&$('detail-body').children.length===1&&$('detail-body').firstElementChild.id==='detail-'+key);$('detail-close').click();assert(key+' focus return and clear',!$('detail-dialog').open&&$('detail-body').children.length===0&&document.activeElement===button);}
 }
 navigate('network');for(const key of ['resource','calendar','overview']){RW.openWindow(key);assert('rapid transition '+key,$('detail-dialog').open&&$('detail-body').firstElementChild?.id==='detail-'+key&&$('detail-body').children.length===1);}RW.closeWindow();
 navigate('hubs');window.P15_WINDOW_TEST={status:'PASS',width:innerWidth,checks};console.log('P15_WINDOW_TEST '+JSON.stringify({status:'PASS',width:innerWidth,count:checks.length}));for(let i=0;i<checks.length;i+=3)console.log('P15_WINDOW_CHECKS '+JSON.stringify(checks.slice(i,i+3)));
 }catch(e){window.P15_WINDOW_TEST={status:'FAIL',error:e.message,checks};console.error('P15_WINDOW_TEST '+JSON.stringify(window.P15_WINDOW_TEST));}
})();
