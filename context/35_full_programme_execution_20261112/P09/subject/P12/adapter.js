/* Display adapter only. No allocation, pricing, finance, extrapolation or scenario generation. */
const ResultAdapter = (() => {
 const known = v => typeof v === 'number' && Number.isFinite(v);
 const fmt = v => known(v) ? new Intl.NumberFormat('ru-RU',{maximumFractionDigits:1}).format(v) : 'Нет расчёта';
 const requiredContext=['evaluation_id','programme_id','programme_version','fleet_scope_id','external_scenario_id','delivery_calendar_id','evaluation_mode','keep_evaluation_id','input_manifest_sha256','period_start','period_end'];
 function validate(pack){
  if(pack?.dataset_kind!=='RED_WINGS' || pack?.synthetic!==false) throw Error('Нужен пакет результатов Red Wings. Синтетические примеры не подключаются.');
  if(pack.coordinator_acceptance!=='ACCEPTED_FOR_UI' || !/^[a-f0-9]{40}$/.test(pack.commit||'') || !/^[a-f0-9]{64}$/.test(pack.manifest_sha256||'')) throw Error('Нет закреплённой принятой версии и manifest.');
  if(!Array.isArray(pack.evaluations)||!pack.evaluations.length) throw Error('В пакете нет расчётов.');
  const ids=new Set();
  for(const e of pack.evaluations){
   const c=e.result?.project?.context;
   if(!c || requiredContext.some(k=>!c[k])) throw Error('Неполный контекст расчёта.');
   if(c.period_start!=='2027-01'||c.period_end!=='2028-12') throw Error('Нужен полный горизонт 2027–2028.');
   if(ids.has(c.evaluation_id)) throw Error('Повтор evaluation_id.');ids.add(c.evaluation_id);
   if(/toy|synthetic/i.test(JSON.stringify(c))) throw Error('Синтетический контекст не является результатом Red Wings.');
   if(!e.label||!e.scenario_label||!e.source_refs?.length||!Array.isArray(e.assumption_ids))throw Error('Нет подписи, источников или реестра допущений.');
   const rows=e.result.project.results_monthly;
   const expected=Array.from({length:24},(_,i)=>`${2027+Math.floor(i/12)}-${String(i%12+1).padStart(2,'0')}`);
   if(!Array.isArray(rows)||rows.length!==24||expected.some(m=>rows.filter(r=>r.month===m).length!==1)) throw Error('Нужны 24 уникальных месячных результата.');
   if(!Array.isArray(e.result.network_changes)||!Array.isArray(e.result.project.operations?.rotations)||typeof e.result.project.status!=='string') throw Error('Нет сетевых изменений или операционного статуса.');
   if(e.result.network_changes.some(r=>!(r.project||r.keep)?.origin_airport||!(r.project||r.keep)?.destination_airport))throw Error('Неполная запись изменения сети.');
   if(e.result.project.operations.rotations.some(r=>typeof r.departure_utc!=='string'))throw Error('Неполная ротация.');
   if(e.result.network_changes.some(r=>typeof (r.project||r.keep).departure_utc!=='string'))throw Error('Нет даты сетевого изменения.');
   if(e.resource_monthly!==undefined&&(!Array.isArray(e.resource_monthly)||e.resource_monthly.some(r=>typeof r.month!=='string')))throw Error('Некорректный месячный ресурс.');
   if(e.result.delta_annual!==undefined&&!Array.isArray(e.result.delta_annual))throw Error('Некорректные годовые результаты.');
   const keep=e.result.keep?.context;
   if(!keep || keep.evaluation_id!==c.keep_evaluation_id || ['fleet_scope_id','external_scenario_id','delivery_calendar_id','period_start','period_end'].some(k=>keep[k]!==c[k])) throw Error('Результат и KEEP не согласованы.');
   if(!Array.isArray(e.result.delta_monthly)||e.result.delta_monthly.length!==24)throw Error('Нет месячного сравнения с KEEP.');
  }
  return pack;
 }
 function matching(a,b){return !!a&&!!b&&['programme_id','programme_version','fleet_scope_id','evaluation_mode','period_start','period_end','affected_scope_id'].every(k=>a.result.project.context[k]===b.result.project.context[k])&&((a.comparison_group_id&&a.comparison_group_id===b.comparison_group_id)||['market_version','choice_version','cost_version'].every(k=>a.result.project.context[k]===b.result.project.context[k]));}
 function annual(e,period){
  if(!e)return null;
  // Only precomputed producer aggregates; never sum monthly or stand-alone programmes here.
  if(period==='2027–2028')return e.result.delta_summary;
  return e.result.delta_annual?.find(r=>String(r.year)===period)||null;
 }
 return {known,fmt,validate,matching,annual};
})();
if(typeof module!=='undefined') module.exports=ResultAdapter;
