'use strict';
const DATA = JSON.parse(document.getElementById('map-data').textContent);
const xml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cityName = code => DATA.airports[code]?.city || code;
let mapSerial = 0;
function kmBetween(a,b){const p=DATA.airports[a],q=DATA.airports[b];if(!p||!q)return null;const rad=Math.PI/180,dp=(q.lat-p.lat)*rad,dl=(q.lon-p.lon)*rad;return Math.round(12742*Math.asin(Math.min(1,Math.sqrt(Math.sin(dp/2)**2+Math.cos(p.lat*rad)*Math.cos(q.lat*rad)*Math.sin(dl/2)**2))));}
function extentFor(m) {
  const codes = [...new Set(m.paths.flat())];
  const pts = codes.filter(c => DATA.airports[c]).map(c => DATA.airports[c]);
  if (!pts.length) return null;
  const xs=pts.map(p=>p.lon), ys=pts.map(p=>p.lat);
  const xlo=Math.min(...xs), xhi=Math.max(...xs), ylo=Math.min(...ys), yhi=Math.max(...ys);
  const padx=Math.max(2.5,(xhi-xlo)*.19), pady=Math.max(2,(yhi-ylo)*.24);
  return [xlo-padx,Math.max(25,ylo-pady),xhi+padx,Math.min(78,yhi+pady)];
}
function renderMap(id) {
  const m=DATA.maps[id];
  if (!m) throw new Error('Unknown map '+id);
  if (m.missing.length) return '<p>Координаты не найдены: '+xml(m.missing.join(', '))+'. География не достроена.</p>';
  const W=800,H=470, box=extentFor(m), [west,south,east,north]=box;
  const cos=Math.cos((south+north)/2*Math.PI/180);
  const scale=Math.min((W-74)/((east-west)*cos),(H-74)/(north-south));
  const xoff=(W-(east-west)*cos*scale)/2,yoff=(H-(north-south)*scale)/2;
  const project=([lon,lat])=>[xoff+(lon-west)*cos*scale,yoff+(north-lat)*scale];
  const clip='mapclip'+(++mapSerial);
  const line=coords=>coords.map((p,i)=>{const [x,y]=project(p);return (i?'L':'M')+x.toFixed(1)+','+y.toFixed(1);}).join('');
  const intersects=coords=>{
    let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;
    coords.forEach(([x,y])=>{xmin=Math.min(xmin,x);xmax=Math.max(xmax,x);ymin=Math.min(ymin,y);ymax=Math.max(ymax,y);});
    return xmax>=west && xmin<=east && ymax>=south && ymin<=north;
  };
  function geoPath(feature,cls) {
    const g=feature.geometry;
    const rings=g.type==='Polygon'?g.coordinates:g.type==='MultiPolygon'?g.coordinates.flat():g.type==='LineString'?[g.coordinates]:[];
    return rings.filter(intersects).map(r=>{
      // Break antimeridian jumps: a frozen ring must never draw a line across Eurasia.
      let d='',previous=null;
      r.forEach(p=>{const [x,y]=project(p);d+=(previous && Math.abs(p[0]-previous[0])<180?'L':'M')+x.toFixed(1)+','+y.toFixed(1);previous=p;});
      return '<path class="'+cls+'" d="'+d+(g.type.includes('Polygon')?'Z':'')+'"/>';
    }).join('');
  }
  let svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+xml(m.title)+'" data-map-id="'+id+'" data-extent="'+box.join(',')+'"><title>'+xml(m.title)+'</title><desc>'+xml(m.note)+'</desc><defs><clipPath id="'+clip+'"><rect x="1" y="1" width="798" height="468" rx="6"/></clipPath></defs><g clip-path="url(#'+clip+')">';
  for(let lon=Math.ceil(west/10)*10;lon<=east;lon+=10){let a=project([lon,south]),b=project([lon,north]);svg+='<path class="map-grid" d="M'+a.join(',')+'L'+b.join(',')+'"/><text class="map-axis" x="'+a[0]+'" y="455">'+lon+'° в.д.</text>';}
  for(let lat=Math.ceil(south/5)*5;lat<=north;lat+=5){let a=project([west,lat]),b=project([east,lat]);svg+='<path class="map-grid" d="M'+a.join(',')+'L'+b.join(',')+'"/><text class="map-axis" x="5" y="'+a[1]+'">'+lat+'°</text>';}
  svg+=DATA.geo.countries.map(f=>geoPath(f,'map-land')).join('');
  svg+=DATA.geo.regions.map(f=>geoPath(f,'map-region')).join('');
  svg+=DATA.geo.lakes.map(f=>geoPath(f,'map-lake')).join('');
  for(const [a,b] of m.edges){const p=DATA.airports[a],q=DATA.airports[b];const [x,y]=project([p.lon,p.lat]),[xx,yy]=project([q.lon,q.lat]);svg+='<path class="map-route '+m.kind+'" data-origin="'+a+'" data-destination="'+b+'" d="M'+x.toFixed(2)+','+y.toFixed(2)+'L'+xx.toFixed(2)+','+yy.toFixed(2)+'"><title>'+xml(cityName(a)+' — '+cityName(b)+' · '+m.status)+'</title></path>';}
  const codes=[...new Set(m.paths.flat())];
  const points=codes.map(code=>{const p=DATA.airports[code];return {code,p,xy:project([p.lon,p.lat])};});
  const occupied=points.map(({xy:[x,y]})=>[x-8,y-8,x+8,y+8]);
  function overlap(a,b){return Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));}
  for(const {code,p,xy:[x,y]} of points){
    const w=Math.min(230,Math.max(85,p.city.length*11.5)),h=44;
    let best=null;
    for(const radius of [14,42,70,98,126])for(const [dx,dy] of [[1,-1],[1,1],[-1,-1],[-1,1],[0,-1],[0,1]]){
      let lx=dx===1?x+radius:dx===-1?x-radius-w:x-w/2, ly=dy<0?y-radius-h:y+radius;
      lx=Math.min(W-w-10,Math.max(10,lx));ly=Math.min(H-h-14,Math.max(12,ly));
      const rect=[lx,ly,lx+w,ly+h];const penalty=occupied.reduce((s,r)=>s+overlap(rect,r),0)*20+radius;
      if(!best||penalty<best.penalty)best={lx,ly,rect,penalty};
    }
    occupied.push(best.rect);
    svg+='<path class="map-leader" d="M'+x.toFixed(1)+','+y.toFixed(1)+'L'+Math.min(best.lx+15,best.rect[2]).toFixed(1)+','+(best.ly+15).toFixed(1)+'"/>';
    if(m.bases.includes(code))svg+='<circle class="map-base" cx="'+x+'" cy="'+y+'" r="10"/>';
    svg+='<circle class="map-point" data-airport="'+code+'" data-lon="'+p.lon+'" data-lat="'+p.lat+'" cx="'+x+'" cy="'+y+'" r="5"/><text class="map-label" x="'+best.lx+'" y="'+(best.ly+17)+'">'+xml(p.city)+'<tspan class="map-code" x="'+best.lx+'" dy="19">'+code+(m.bases.includes(code)?' · база / узел проекта':'')+'</tspan></text>';
  }
  const perPixel=111.195/scale,target=perPixel*130,order=10**Math.floor(Math.log10(target));let unit=order;for(const k of [1,2,5])if(k*order<=target)unit=k*order;
  const length=unit/perPixel;
  svg+='<g aria-label="Географический масштаб"><rect x="14" y="425" width="240" height="40" fill="#f8fbfb" opacity=".9"/><path d="M24,435v7h'+length.toFixed(1)+'v-7" fill="none" stroke="#47676c" stroke-width="2"/><text class="map-axis" x="24" y="459">≈'+unit+' км на средней широте карты</text></g>';
  return svg+'</g></svg>';
}
function routeHTML(m) {return '<ul class="route-list">'+m.paths.map(p=>'<li>'+p.map(c=>xml(cityName(c)+' ('+c+')')).join(' → ')+'<small class="route-distance">'+p.slice(1).map((b,i)=>xml(cityName(p[i])+' — '+cityName(b)+': ≈'+kmBetween(p[i],b)+' км')).join('; ')+'</small></li>').join('')+'</ul>';}
function setSelection(id) {
  const m=DATA.maps[id];if(!m)throw new Error('Unknown selection '+id);
  document.getElementById('network-select').value=id;
  document.getElementById('selected-map').innerHTML='<div class="map-status">'+xml(m.status)+'</div><div class="map-canvas">'+renderMap(id)+'</div><p class="map-note">'+xml(m.note)+'</p>';
  document.getElementById('selected-routes').innerHTML='<b>'+xml(m.title)+'</b>'+routeHTML(m)+(m.explanation||'<p>Сохранённый контур Цири, context21. Условный расчёт добавления на неделю 7–13 декабря 2026; не действующая сеть и не экономика замены. Предпосылки, конкуренты и результаты — в главе «Карты готовых контуров». Путь самолёта требует отдельного датированного назначения; конечные поездки учитываются отдельно.</p>');
}
document.querySelectorAll('[data-map]').forEach(node=>{node.querySelector('.map-canvas').innerHTML=renderMap(node.dataset.map);});
document.getElementById('network-select').addEventListener('change',e=>setSelection(e.target.value));
document.querySelectorAll('[data-select-map]').forEach(button=>button.addEventListener('click',()=>{setSelection(button.dataset.selectMap);document.getElementById('selected-map').scrollIntoView({behavior:'smooth',block:'start'});}));
setSelection('C01');
function filterPrograms(){const q=document.getElementById('program-search').value.trim().toLowerCase();let shown=0;document.querySelectorAll('[data-program]').forEach(row=>{row.hidden=!row.dataset.search.includes(q);if(!row.hidden)shown++;});document.getElementById('program-count').textContent=shown+' из 35 программ';}
document.getElementById('program-search').addEventListener('input',filterPrograms);
const toc=document.querySelector('.draft-toc'),toggle=document.getElementById('toc-toggle');
toggle.addEventListener('click',()=>{const open=toc.classList.toggle('open');toggle.setAttribute('aria-expanded',String(open));});
const links=[...document.querySelectorAll('#toc-links a')];
links.forEach(a=>a.addEventListener('click',()=>{toc.classList.remove('open');toggle.setAttribute('aria-expanded','false');}));
function activeAnchor(){const ss=[...document.querySelectorAll('main section')];let id=ss[0]?.id;for(const s of ss)if(s.getBoundingClientRect().top<130)id=s.id;links.forEach(a=>a.hash==='#'+id?a.setAttribute('aria-current','location'):a.removeAttribute('aria-current'));}
window.addEventListener('scroll',activeAnchor,{passive:true});activeAnchor();
window.draftMaps={renderMap,setSelection,extentFor,filterPrograms,data:DATA};
