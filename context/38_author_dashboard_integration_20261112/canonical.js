/* Accepted P09 in the unchanged published kiruha355 dashboard. No model formulas. */
(() => {
  'use strict';
  const input=JSON.parse(document.getElementById('accepted-research-data').textContent);
  const Q=input.results, E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const N=(v,d=0)=>v==null?'неизвестно':typeof v==='number'?v.toLocaleString('ru-RU',{maximumFractionDigits:d}):E(v);
  const M=v=>v==null?'неизвестно':N(v/1e6,2)+' млн ₽';
  const LABEL={KUF_RADIAL:'Самара · база',VOG_RADIAL:'Волгоград · база',SVX_RADIAL:'SVX · прямые',MRV_HYBRID:'Минводы · смешанная',AER_HYBRID:'Сочи · смешанная',VOG_HYBRID:'Волгоград · смешанная',AER_SEASONAL:'Сочи · сезонная',VOG_BANK9:'Волгоград · пересадки',SVX_BANK9:'SVX · пересадки'};
  const $=id=>document.getElementById(id), caches=new Map(), audit=[];
  const st={programme:Q.default_programme,scenario:'base',epoch:0,month:'all',flightPage:0,productPage:0,city:'all'};
  const section=$('p9').closest('section');
  section.querySelector('.eyebrow').textContent='Совместный расчёт · 2027–2028';
  $('p9-title').textContent='Сравнение программ на одном парке';
  section.querySelector('.hint').textContent='9 программ · базовый и осторожный сценарии · 24 месяца';
  section.querySelector('.sec-h').insertAdjacentHTML('afterend',`<div class="ctl"><label>Программа <select id="ac-programme">${Q.catalogue.map(x=>`<option value="${x.programme_id}">${E(x.label)}</option>`).join('')}</select></label><label>Сценарий <select id="ac-scenario"><option value="base">Базовый</option><option value="cautious">Осторожный</option></select></label></div>`);
  $('p9').insertAdjacentHTML('afterend','<div id="ac-summary"></div><div id="ac-comparison" class="tscroll"></div><div id="ac-detail"></div>');
  $('ac-programme').value=st.programme;
  // The accepted comparison comes first in the network tab. The original author
  // calculations remain available together, with their original inputs/controls.
  const originalNetwork=[...document.querySelectorAll('.wrap>[data-tab="network"]')].filter(x=>x!==section);
  const old=document.createElement('details');old.className='mapcard';old.dataset.tab='network';
  old.innerHTML='<summary>Исходная модель команды: годовые сети, обороты и чувствительность</summary><p class="ld-note">Отдельная модель с собственными сценариями. Её годовые значения не складываются с помесячной дельтой P09.</p>';
  originalNetwork[0].before(section,old);
  originalNetwork.forEach(x=>old.append(x));
  function graph(){
    const rs=Q.catalogue.map(c=>({id:c.programme_id,label:LABEL[c.programme_id]||c.label,b:c.evaluations.find(x=>x.context.external_scenario_id==='base'),c:c.evaluations.find(x=>x.context.external_scenario_id==='cautious')}));
    const val=x=>x.thresholds.net_missing_operating_cost_break_even;
    const vals=rs.flatMap(r=>[val(r.b),val(r.c)]),lo=Math.min(0,...vals),hi=Math.max(0,...vals),X=v=>250+(v-lo)/(hi-lo)*650;
    let s='<svg viewBox="0 0 1000 350" role="img" aria-label="Изменение известной части результата к KEEP"><line x1="'+X(0)+'" y1="20" x2="'+X(0)+'" y2="320" stroke="#B9B5AC"/>';
    rs.forEach((r,i)=>{const y=32+i*32,b=val(r.b),c=val(r.c),me=r.id===st.programme;
      s+=`<g data-ac-programme="${r.id}" style="cursor:pointer"><text x="238" y="${y+12}" text-anchor="end" fill="#111318" font-size="13" font-weight="${me?700:400}">${E(r.label)}</text><rect x="${Math.min(X(0),X(b))}" y="${y}" width="${Math.abs(X(b)-X(0))}" height="18" rx="4" fill="${me?'#E32A2F':'#8C96A6'}"><title>${E(r.label)} · базовый: ${b} ₽</title></rect><circle cx="${X(c)}" cy="${y+9}" r="5" fill="#fff" stroke="#111318" stroke-width="2"><title>Осторожный: ${c} ₽</title></circle><text x="${X(Math.max(0,b))+8}" y="${y+13}" fill="#111318" font-size="11">${N(b/1e6,1)}</text></g>`;});
    s+='<text x="250" y="345" fill="#5E6675" font-size="12">Полоса — базовый · точка — осторожный · млн ₽ за 2027–2028 · H не является прибылью</text></svg>';
    $('p9').innerHTML=s;
  }
  function comparison(){
    $('ac-comparison').innerHTML='<table class="mt"><thead><tr><th>Программа</th><th>+ поездки · база</th><th>+ поездки · осторожно</th><th>H · база</th><th>H · осторожно</th></tr></thead><tbody>'+Q.catalogue.map(c=>{const b=c.evaluations.find(x=>x.context.external_scenario_id==='base'),k=c.evaluations.find(x=>x.context.external_scenario_id==='cautious');return `<tr><td><button class="btn" data-ac-programme="${c.programme_id}">${E(c.label)}</button></td><td>${N(b.delta_summary.journeys)}</td><td>${N(k.delta_summary.journeys)}</td><td>${M(b.thresholds.net_missing_operating_cost_break_even)}</td><td>${M(k.thresholds.net_missing_operating_cost_break_even)}</td></tr>`;}).join('')+'</tbody></table>';
  }
  async function decode(pid){
    if(caches.has(pid))return caches.get(pid);
    const p=Q.packets[pid],gz=Uint8Array.from(atob(p.data),c=>c.charCodeAt(0));
    const b=await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    if(crypto.subtle){const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==p.sha256)throw Error('Не совпал hash результата.');}
    const env=JSON.parse(new TextDecoder().decode(b));
    if(env.commit!==Q.commit||env.manifest_sha256!==Q.manifest_sha256)throw Error('Другая версия результата.');
    audit.push({programme:pid,sha256:p.sha256,bytes:b.byteLength,source:Q.commit});caches.set(pid,env);return env;
  }
  const table=(heads,rows)=>'<div class="tscroll"><table class="mt"><thead><tr>'+heads.map(x=>'<th>'+E(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  let selected=null;
  function details(e){
    selected=e;const r=e.result,ds=r.delta_summary,H=r.thresholds.net_missing_operating_cost_break_even;
    const pairs=e.programme_card.after.end2028_pairs,base=r.project.summary;
    $('ac-summary').innerHTML=`<div class="kpis"><div><b>${N(ds.journeys)}</b><span>дополнительных конечных поездок</span></div><div><b>${M(ds.revenue_net)}</b><span>изменение билетной выручки</span></div><div><b>${M(H)}</b><span>H: изменение известной части результата</span></div><div><b>${pairs.length}</b><span>аэропортовых пар к концу 2028</span></div></div><p class="win-note">Полная дельта = H − разница недостающих расходов + иные неизвестные доходы. Полная прибыль и потребность в финансировании не установлены. Спрос сценарный; слоты, экипажи и ТО требуют подтверждения.</p>`;
    const pm=r.project.results_monthly,dm=r.delta_monthly;
    const months=pm.map((x,i)=>[E(x.month),N(x.journeys),N(x.passenger_segments),M(x.revenue_net),M(x.known_operating_subtotal),M(x.operating_result),N(dm[i].delta_journeys),M(dm[i].delta_revenue_net)]);
    const res=e.resource_monthly.map(x=>[E(x.month),E(x.aircraft_variant),N(x.transferred),N(x.entered_service),N(x.scenario_working_tails),N(x.reserve),N(x.project_available)]);
    $('ac-detail').innerHTML=`<details class="ld-note"><summary>Сеть, частоты и ресурс</summary><p>${pairs.map(p=>E(p.join(' — '))).join(' · ')}</p><p>${e.programme_card.after.working_slots.map(s=>`${E(s.base)}: ${s.spokes.map(E).join(', ')}`).join('; ')}. Резерв выделяется отдельно. Это сценарный календарь, не подтверждённый свободный парк.</p><p>${E(e.programme_card.before)}</p>${table(['Месяц','Тип','Передано','Введено','Рабочих по сценарию','Резерв','Фактически доступно'],res)}</details><details class="ld-note"><summary>Все 24 месяца: пассажиры и экономика</summary>${table(['Месяц','Поездки проекта','Пассажирские сегменты','Выручка проекта','Известный подытог проекта','Полный результат проекта','Δ поездок к KEEP','Δ выручки к KEEP'],months)}<p>Абсолютный подытог проекта и дельта к KEEP — разные показатели. Для VOG_RADIAL известный подытог отрицателен в обоих сценариях.</p></details><details class="ld-note"><summary>Датированные рейсы и работа бортов</summary><div class="ctl"><label>Месяц <select id="ac-month"><option value="all">Все месяцы</option>${pm.map(x=>`<option>${x.month}</option>`).join('')}</select></label></div><div id="ac-flights"></div></details><details class="ld-note"><summary>Источник, допущения и воспроизводимость</summary><p>P09: <code>${Q.commit}</code>. Независимая проверка: APPROVE_WITH_EXPLICIT_LIMITS. Это приёмка условного вычислительного сравнения, не рынка или запуска.</p><p><a href="../35_full_programme_execution_20261112/P09/handoff.md">Расчёт и replay</a> · <a href="../36_source_inventory_checkpoint_20261112/README.md">Перечень источников</a> · <a href="../35_full_programme_execution_20261112/expert_final_coverage/summary.md">Экспертная сверка</a></p><pre style="white-space:pre-wrap;overflow-wrap:anywhere">${E(JSON.stringify({context:r.project.context,result_mode:e.result_mode,projection_sha256:e.projection_sha256,source_full_result_sha256:e.source_full_result_sha256,assumption_ids:e.assumption_ids},null,2))}</pre></details>`;
    $('ac-month').value=st.month;$('ac-month').onchange=()=>{st.month=$('ac-month').value;st.flightPage=0;flights();};flights();
    $('p9-note').textContent='Расчёт 2027–2028 относительно одинакового будущего KEEP. Программы — альтернативы; их результаты не суммируются. Исходная годовая модель команды сохранена отдельно ниже.';
  }
  function flights(){
    const all=selected.result.project.operations.rotations.filter(x=>st.month==='all'||x.departure_utc.startsWith(st.month));
    st.flightPage=Math.max(0,Math.min(st.flightPage,Math.ceil(all.length/16)-1));const from=st.flightPage*16;
    $('ac-flights').innerHTML=table(['Борт','Из','В','Вылет UTC','Прилёт UTC','Экипаж'],all.slice(from,from+16).map(x=>[E(x.aircraft_id),E(x.origin),E(x.destination),E(x.departure_utc),E(x.arrival_utc),N(x.crew_id)]))+`<div class="ctl"><button class="btn" data-ac-flight="-1" ${from===0?'disabled':''}>Назад</button><span>${all.length?from+1:0}–${Math.min(from+16,all.length)} из ${all.length}</span><button class="btn" data-ac-flight="1" ${from+16>=all.length?'disabled':''}>Далее</button></div>`;
  }
  async function choose(pid=st.programme,sc=st.scenario){
    st.programme=pid;st.scenario=sc;const epoch=++st.epoch;$('ac-programme').value=pid;$('ac-scenario').value=sc;
    graph();comparison();
    const env=await decode(pid);if(epoch!==st.epoch)return;
    const e=env.evaluations.find(x=>x.result.project.context.external_scenario_id===sc);if(!e)throw Error('Нет сценария.');details(e);
    console.log('AUTHOR_CANONICAL_READY',pid,sc);
  }
  $('ac-programme').onchange=()=>choose($('ac-programme').value,st.scenario).catch(error);
  $('ac-scenario').onchange=()=>choose(st.programme,$('ac-scenario').value).catch(error);
  document.addEventListener('click',ev=>{const b=ev.target.closest('[data-ac-programme],[data-ac-flight]');if(!b)return;if(b.dataset.acProgramme)choose(b.dataset.acProgramme,st.scenario).catch(error);else{st.flightPage+=Number(b.dataset.acFlight);flights();}});
  function error(e){$('ac-summary').textContent='Не удалось открыть результат: '+e.message;console.error(e);}
  // Original colour, type, components and tab behaviour are retained. Correct
  // the unsupported queue of new hubs and reported-pax addition in growth text.
  no2Board=function(){
    const rw=D.steps.scale.find(x=>x.rw).pax,goal=D.steps.no2.no2_pax;
    $('n2-sub').textContent=`Исторический ориентир 2025: Red Wings ${N(rw,1)} млн, перевозчик №2 ${N(goal,1)} млн пассажиров. Дата достижения №2 не установлена.`;
    const runway=$('rwy'),X=v=>4+v/15*92;runway.textContent='';runway.append(h('div',{class:'strip'}));
    const fill=h('div',{class:'fill'});fill.style.cssText=`left:4%;width:${X(rw)-4}%`;runway.append(fill);
    for(const [value,label,cls] of [[rw,'Red Wings, 2025','dn rw'],[goal,'№2, 2025','up goal']]){const mark=h('div',{class:'mk '+cls},h('span',{},label),h('b',{},N(value,1)));mark.style.left=X(value)+'%';runway.append(mark);}
    const gap=h('div',{class:'gap'},'исторический разрыв '+N(goal-rw,1)+' млн');gap.style.left=((X(rw)+X(goal))/2)+'%';runway.append(gap);
    runway.append(h('div',{class:'scale'},...[0,3,6,9,12,15].map(v=>h('span',{},v+' млн'))));
    $('n2-stages').innerHTML='<li><span class="w">2027–2028</span><b>Выбрать первую программу на доступном ресурсе</b><span>Хаб, радиальная база, прямые рейсы или смешанный вариант сравниваются между собой.</span></li><li><span class="w">Следующий этап</span><b>Подтвердить результаты и условия расширения</b><span>Омск, Самара, Челябинск и Тюмень — альтернативы. Очередь открытия четырёх хабов не рассчитана.</span></li><li><span class="w">Дальнейший рост</span><b>Рассчитать весь бизнес Red Wings совместно</b><span>Новая база требует своего спроса, ресурса, расходов и учёта перетока из существующей сети.</span></li>';
    $('n2-three').innerHTML='<div class="n2-c"><span class="tg">Маршрутная сеть</span><h3>Сравниваем альтернативы</h3><p>Открытие нескольких близких узлов не следует из рейтинга городов. Для второй базы нужен отдельный совместный расчёт.</p></div><div class="n2-c"><span class="tg">Рост бизнеса</span><h3>Первый этап не доказывает №2</h3><p>Внутренние, международные и чартерные перевозки учитываются вместе. Поездки и физические сегменты нельзя автоматически прибавить к отчётным пассажирам.</p></div><div class="n2-c"><span class="tg">Цифровые сервисы</span><h3>Отдельные проверяемые улучшения</h3><p>Эффекты P11 не измерены и не прибавлены к выручке сетевой программы.</p></div>';
    let one=$('n2-one');if(!one){one=document.createElement('p');one.id='n2-one';one.className='n2-one';$('n2-three').after(one);}
    one.textContent='Нет обоснованного плана открыть хабы во всех городах рейтинга. Выбор первой программы и последующее расширение — разные решения.';
  };
  p09=()=>{graph();comparison();};no2Board();
  // Complete dated competitor export in the author's table component.
  const pc=document.createElement('section');pc.className='win';pc.dataset.tab='direct';pc.innerHTML='<div class="sec-h"><div><div class="eyebrow">Расписания и предложения · P02</div><h2>Red Wings и конкуренты по датам</h2></div></div><div class="ctl"><label>Город <select id="ac-city"><option value="all">Все 20 городов</option>'+Object.entries(BY).map(([id,c])=>'<option value="'+id+'">'+E(c.city)+'</option>').join('')+'</select></label></div><div id="ac-products"></div><p class="win-note">2274 опубликованных продукта и правила. Отсутствие строки не доказывает отсутствия рейса. Объявленное расписание не равно свободным креслам; цены не являются реализованным доходом.</p>';
  document.querySelector('[data-tab="direct"]').before(pc);
  function products(){const rows=input.products.filter(x=>st.city==='all'||x.origin===st.city||x.destination===st.city),from=st.productPage*16;
    $('ac-products').innerHTML=table(['Пара','Перевозчик / рейс','Период','Вылет / прилёт, местное','Тип','Цена, ₽','Источник'],rows.slice(from,from+16).map(x=>[E(x.origin+' — '+x.destination),E(x.carrier+' / '+x.flight),E(x.period||x.valid_from+' — '+x.valid_to),E(x.departure_local+' / '+x.arrival_local),E(x.aircraft),x.fare_rub==='UNKNOWN'?'неизвестно':N(x.fare_rub),`<a href="${E(x.source_url)}" target="_blank" rel="noopener">${E(x.source_id)}</a>`]))+`<div class="ctl"><button class="btn" data-ac-product="-1" ${from===0?'disabled':''}>Назад</button><span>${rows.length?from+1:0}–${Math.min(from+16,rows.length)} из ${rows.length}</span><button class="btn" data-ac-product="1" ${from+16>=rows.length?'disabled':''}>Далее</button></div>`;}
  $('ac-city').onchange=()=>{st.city=$('ac-city').value;st.productPage=0;products();};document.addEventListener('click',ev=>{const b=ev.target.closest('[data-ac-product]');if(b){st.productPage+=Number(b.dataset.acProduct);products();}});products();
  window.AuthorResearch={Q,input,choose,decode,audit,state:st,get current(){return selected;},ready:null};
  $('foot').textContent='Закреплённая сборка 12.11.2026. Авторский дизайн: kiruha355 / 6cbe817. Общий расчёт P09: 736859fd; условная исследовательская версия, без автоматического обновления источников.';
  $('src').querySelector('tbody').insertAdjacentHTML('afterbegin','<tr><td><a href="../36_source_inventory_checkpoint_20261112/README.md">Полный перечень исходных и новых источников</a></td><td>реестр</td><td>12.11.2026</td><td>41 группа</td><td>закреплён</td></tr><tr><td>Совместный расчёт P09, 2027–2028</td><td>модель</td><td>12.11.2026</td><td>9 программ / 18 полных сравнений</td><td>условный</td></tr><tr><td>Расписания Red Wings и конкурентов P02</td><td>выгрузка источников</td><td>12.11.2026</td><td>2274 продукта / правила</td><td>не inventory</td></tr>');
  window.AuthorResearch.ready=choose().catch(error);showTab(location.hash.slice(1));
})();
