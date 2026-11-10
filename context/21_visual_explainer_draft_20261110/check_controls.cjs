const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),page=fs.readFileSync(path.join(root,'research-report-draft.html'),'utf8');
const data=JSON.parse(page.match(/<script id="map-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
function node(extra={}){return Object.assign({value:'',innerHTML:'',textContent:'',hidden:false,attributes:{},listeners:{},dataset:{},addEventListener(n,cb){this.listeners[n]=cb},setAttribute(k,v){this.attributes[k]=v},removeAttribute(k){delete this.attributes[k]},scrollIntoView(){}},extra)}
const ids=Object.fromEntries(['map-data','network-select','selected-map','selected-routes','program-search','program-count','toc-toggle'].map(k=>[k,node()]));ids['map-data'].textContent=JSON.stringify(data);
const programs=Array.from(page.matchAll(/<tr data-program data-search="([^"]+)"/g),m=>node({dataset:{search:m[1]}}));
const mapNodes=Array.from(page.matchAll(/data-map="([^"]+)"/g),m=>node({dataset:{map:m[1]},querySelector(){return node()}}));
const buttons=Array.from(page.matchAll(/data-select-map="([^"]+)"/g),m=>node({dataset:{selectMap:m[1]}}));
const sectionIds=Array.from(page.matchAll(/<section id="([^"]+)"/g),m=>m[1]);
const sections=sectionIds.map((id,i)=>({id,top:i*300,getBoundingClientRect(){return {top:this.top}}}));
const links=sectionIds.map(id=>node({hash:'#'+id}));const classes=new Set();
const toc={classList:{toggle(c){if(classes.has(c)){classes.delete(c);return false}classes.add(c);return true},remove(c){classes.delete(c)}}};
const document={getElementById:id=>ids[id],querySelector:s=>s==='.draft-toc'?toc:null,querySelectorAll:s=>s==='[data-map]'?mapNodes:s==='[data-select-map]'?buttons:s==='[data-program]'?programs:s==='#toc-links a'?links:s==='main section'?sections:[]};
const window={listeners:{},addEventListener(n,cb){this.listeners[n]=cb}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'maps.js'),'utf8'),{document,window});
const api=window.draftMaps;let endpoints=0;
for(const [id,m] of Object.entries(data.maps)){
 const svg=api.renderMap(id);assert.ok(svg.startsWith('<svg'),id);assert.equal((svg.match(/data-origin=/g)||[]).length,m.edges.length,id);
 const codes=[...new Set(m.paths.flat())];assert.equal((svg.match(/data-airport=/g)||[]).length,codes.length,id);
 const [w,s,e,n]=api.extentFor(m);
 for(const c of codes){const p=data.airports[c];assert.ok(p.lon>w&&p.lon<e&&p.lat>s&&p.lat<n,id+': extent '+c);assert.ok(svg.includes(p.city),id+': city '+c);assert.ok(p.airport_id.startsWith('OA:'));endpoints++;}
 assert.ok(!/NaN|Infinity/.test(svg),id);
 api.setSelection(id);assert.equal(ids['network-select'].value,id);assert.ok(ids['selected-map'].innerHTML.includes('data-map-id="'+id+'"'));assert.ok(ids['selected-routes'].innerHTML.includes(m.title.replace(/&/g,'&amp;')));
}
assert.deepEqual(data.maps.C09.edges,[['KUF','SVX'],['KUF','VOG'],['SVX','VOG']]);
assert.deepEqual(data.maps.C01_frozen.edges,[['MRV','UFA'],['NJC','UFA']]);
assert.equal(data.maps.shortlist.edges.length,0);assert.equal(data.maps.SVX_step.kind,'proposed');assert.equal(data.maps.SVX_current.kind,'published');
for(const id of ['C27','C28','C31','C33','C34','C11'])assert.equal(data.maps[id].kind,'geometry');
ids['network-select'].value='C14';ids['network-select'].listeners.change({target:ids['network-select']});assert.ok(ids['selected-map'].innerHTML.includes('data-map-id="C14"'));
buttons.find(b=>b.dataset.selectMap==='C09').listeners.click();assert.equal(ids['network-select'].value,'C09');
for(const [query,want] of [['',35],['киров',1],['C07',1],['неттакогогорода',0]]){ids['program-search'].value=query;ids['program-search'].listeners.input();assert.equal(programs.filter(x=>!x.hidden).length,want)}
ids['toc-toggle'].listeners.click();assert.equal(ids['toc-toggle'].attributes['aria-expanded'],'true');links[5].listeners.click();assert.equal(ids['toc-toggle'].attributes['aria-expanded'],'false');
sections.forEach(x=>x.top-=sections.length*300);window.listeners.scroll();assert.equal(links.at(-1).attributes['aria-current'],'location');assert.equal(links.filter(l=>l.attributes['aria-current']).length,1);
console.log(JSON.stringify({maps_rendered:Object.keys(data.maps).length,endpoints_checked:endpoints,all_selections:'PASS',change_event:'PASS',catalog_button:'PASS',filters:'PASS',toc_mobile:'PASS',deep_anchor:'PASS',scope:'Actual offline JavaScript in minimal DOM fixture; screenshots checked separately with native html_preview.'}));
