/* Author v2 presentation6cbe8173; accepted canonical data736859fd remain unchanged. */
const viewLede={hubs:'20 городов: исходные данные, альтернативы и причины выбора.',direct:'Собственные и конкурентные рынки, цены и варианты прямой сети.',network:'Девять программ на одном ресурсе: базовый и осторожный сценарии, порог расходов и календарь.',strategy:'Первый этап2027–2028, масштаб дальнейшего роста и цифровые сервисы.'};
const viewStorage=document.createElement('div');viewStorage.hidden=true;viewStorage.id='detail-storage';document.body.append(viewStorage);
let detailTrigger=null;
function makeWindow(key,title,nodes,host,description=''){
 const pane=document.createElement('div');pane.id='detail-'+key;pane.className='detail-pane';pane.dataset.title=title;
 for(const node of nodes.filter(Boolean))pane.append(node);viewStorage.append(pane);
 const win=document.createElement('div');win.className='win window-launch';
 win.innerHTML=`<div><h3>${title}</h3>${description?'<p class="win-note">'+description+'</p>':''}</div><button class="btn" data-detail="${key}">Открыть</button>`;
 host.append(win);return win;
}
function clearDetail(){while($('detail-body').firstChild)viewStorage.append($('detail-body').firstChild);}
function closeWindow(){if($('detail-dialog').open)$('detail-dialog').close();clearDetail();detailTrigger?.focus();}
function openWindow(key){
 const pane=$('detail-'+key);if(!pane)return;
 const nextTrigger=document.activeElement;
 if($('detail-dialog').open)$('detail-dialog').close();clearDetail();detailTrigger=nextTrigger;
 $('detail-title').textContent=pane.dataset.title;$('detail-body').append(pane);$('detail-dialog').showModal();
}
$('detail-close').onclick=closeWindow;
$('detail-dialog').addEventListener('close',()=>{if(!$('detail-dialog').open){clearDetail();detailTrigger?.focus();}});
document.addEventListener('click',ev=>{const b=ev.target.closest('[data-detail]');if(b)openWindow(b.dataset.detail);});
const viewHubWindows=document.createElement('div');viewHubWindows.className='two';
$('hubs').append(viewHubWindows);
const monthlyCard=$('monthly-source-evidence').closest('.card');
makeWindow('city','Варианты города и основания',[$('research-summary'),$('research-programme-panel'),$('hypothesis-panel'),$('market-panel')],viewHubWindows,'Механизм, контрпримеры, KEEP, гипотезы и материальные неизвестные.');
makeWindow('observations','Исторические наблюдения',[monthlyCard],viewHubWindows,'2025 и доступный2026: сегменты и агрегаты аэропортов; подтверждённого endpoint OD нет.');
const directWindows=document.createElement('div');directWindows.className='two';$('direct').append(directWindows);
const offerCard=$('source-month').closest('.card'),priceCard=$('local-fares').closest('.card'),baseCard=$('existing-base-data').closest('.card'),internationalCard=$('international-data').closest('.card');
makeWindow('offers','Расписания, конкуренты и ротации',[offerCard],directWindows,'2274 опубликованных продукта P02. Период источника выбирается отдельно от2027–2028.');
makeWindow('fares','Цена и условия поездки',[priceCard],directWindows,'Дата, состав тарифа, багаж, возврат, пересадка и неизвестные компоненты.');
makeWindow('bases','Программы существующих баз',[baseCard],directWindows,'6 SVX и57 московских рецептов:30 условно рассчитаны,27 calendar-infeasible / NOT_RUN.');
makeWindow('international','Международные альтернативы',[internationalCard],directWindows,'87 карточек; дополнительная ветвь с условиями допуска, без присвоенной выручки.');
const netWindows=document.createElement('div');netWindows.className='two';$('network').append(netWindows);
const resourceCard=$('resource-funding').closest('.card'),calendarCard=$('monthly').closest('.card'),researchResource=$('research-resource').closest('.card'),overviewCard=$('overview-panel').closest('.card');
makeWindow('resource','Ресурс, резерв и финансирование',[resourceCard,researchResource],netWindows,'Поэтапный SJ100/ПД8 — условный N(t). Фактически доступный парк, crew/ТО и финансирование неизвестны.');
makeWindow('calendar','Календарь2027–2028 и денежные потоки',[calendarCard],netWindows,'Все24месяца и все изменения рейсов; таблицы рейсов по16строк. Полная прибыль и cash остаются неизвестными.');
makeWindow('overview','Обзор1958 сценариев',[overviewCard],netWindows,'178 конструкций. Отдельный producer result_mode; исходные строки, hashes, OPEN и NOT_RUN сохранены.');
const mapWin=document.createElement('div');mapWin.className='win window-launch';mapWin.innerHTML='<div><h3>Карта сети и конкурентов</h3><p class="win-note">20 хабов и конечные аэропорты. Слои предложения, наблюдения и проекта разделены.</p></div><button class="btn" id="canonical-map-open">На карту</button>';netWindows.append(mapWin);$('canonical-map-open').onclick=()=>{navigate('hubs');$('map').closest('.mapcard').scrollIntoView({block:'start',behavior:'auto'});};
const strategyWindows=document.createElement('div');strategyWindows.className='two';$('strategy').append(strategyWindows);
const expertCard=$('expert-insertions').closest('.card'),methodCard=$('method-source-catalog').closest('.card'),evidenceCard=$('evidence-panel');
makeWindow('expert','Экспертная сверка',[expertCard],strategyWindows,'Пять применимых вставок; покрытие частичное. Операционные неизвестные не объявлены пройденными проверками.');
makeWindow('method','Данные, метод и происхождение',[methodCard,evidenceCard],strategyWindows,'OurAirports, Tochno, Росстат/БДМО, NOAA и исключённый из OD EMISS; exact commit, строки и допущения.');
// Author v2 window classes, tab behavior and typography; no author monetary JS imported.
for(const node of document.querySelectorAll('main>section>.card'))node.classList.add('win');
const threshold=$('threshold-economics');$('network').insertBefore(threshold,$('network').querySelector('.ticket'));
const initialNavigate=navigate;
navigate=function(id){
 if(!sections.includes(id))id='hubs';
 if($('detail-dialog').open)closeWindow();
 state.active=id;for(const key of sections)$(key).hidden=key!==id;
 for(const a of document.querySelectorAll('#tabs a')){if(a.dataset.t===id)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}
 $('tab-lede').textContent=viewLede[id];if(document.readyState!=='loading'&&location.hash!=='#'+id)history.replaceState(null,'','#'+id);
 if(document.readyState!=='loading')$(id+'-title').focus({preventScroll:true});window.scrollTo({top:0,behavior:'auto'});
};
for(const a of document.querySelectorAll('#tabs a'))a.onclick=ev=>{ev.preventDefault();navigate(a.dataset.t);};
window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)));
const oldRestore=restore;restore=async function(s){await oldRestore(s);navigate(s.state.active||'hubs');window.scrollTo(0,s.scrollY);};RW.restore=restore;
RW.navigate=navigate;RW.openWindow=openWindow;RW.closeWindow=closeWindow;RW.view={author_commit:'6cbe817320f75db9823984e7c4eeb6091fd7d996',presentation_only:true};
navigate(location.hash.slice(1)||'hubs');
