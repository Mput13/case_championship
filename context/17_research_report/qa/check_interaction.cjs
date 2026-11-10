const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const page = fs.readFileSync(path.join(__dirname, '../../../research-report.html'), 'utf8');
const code = fs.readFileSync(path.join(__dirname, 'report.js'), 'utf8');
function node(extra = {}) {
  return Object.assign({value:'',hidden:false,textContent:'',listeners:{},attributes:{},
    addEventListener(name, callback){this.listeners[name] = callback;},
    setAttribute(name,value){this.attributes[name] = value;},removeAttribute(name){delete this.attributes[name];}}, extra);
}
const programs = Array.from(page.matchAll(/<tr data-program data-queue="(true|false)" data-tested="(true|false)" data-search="([^"]*)"/g), m => node({dataset:{queue:m[1],tested:m[2],search:m[3]}}));
const ids = Object.fromEntries(['program-search','program-scope','program-count','program-empty','toc-toggle'].map(id => [id,node()]));
ids['program-scope'].value = 'all';
const classes = new Set();
const toc = {classList:{add(name){classes.add(name);},remove(name){classes.delete(name);},toggle(name){if(classes.has(name)){classes.delete(name);return false;}classes.add(name);return true;}}};
const links = Array.from(page.matchAll(/<a href="#([^"]+)"><small>/g), m => node({hash:'#'+m[1]}));
const sections = Array.from(page.matchAll(/<section id="([^"]+)"/g), (m,i) => ({id:m[1],top:i*300,getBoundingClientRect(){return {top:this.top};}}));
const document = {documentElement:{classList:{add(){}}},getElementById(id){return ids[id];},
  querySelector(selector){return selector === '.toc' ? toc : null;},
  querySelectorAll(selector){return selector === '[data-program]' ? programs : selector === '.toc-links a' ? links : sections;}};
const window = {innerWidth:390,listeners:{},addEventListener(name,cb){this.listeners[name] = cb;},requestAnimationFrame(cb){cb();}};
vm.runInNewContext(code,{document,window});
const results=[];
function check(scope,query,want){
  ids['program-scope'].value=scope;ids['program-search'].value=query;
  ids['program-search'].listeners.input();
  assert.equal(programs.filter(row=>!row.hidden).length,want);
  assert.equal(ids['program-empty'].hidden,want!==0);
  assert.equal(ids['program-count'].textContent,`Показано ${want} из 35`);
  results.push({scope,query,shown:want});
}
check('all','',35);check('queue','',9);check('tested','',3);check('tested','C07',1);
check('all','несуществующая программа',0);check('all','УФА',1);check('all','',35);
ids['toc-toggle'].listeners.click();assert.equal(ids['toc-toggle'].attributes['aria-expanded'],'true');
links[4].listeners.click();assert.equal(ids['toc-toggle'].attributes['aria-expanded'],'false');
assert.equal(links[0].attributes['aria-current'],'location');
sections.forEach(section=>section.top-=3900);window.listeners.scroll();
assert.equal(links[13].attributes['aria-current'],'location');
assert.equal(links.filter(link=>link.attributes['aria-current']).length,1);
const result={filter_cases:results,toc_toggle:'PASS',toc_closes_after_link:'PASS',active_anchor_at_end:'PASS',
  scope:'Actual report JavaScript in a minimal DOM fixture; visual rendering checked separately with html_preview'};
fs.writeFileSync(path.join(__dirname,'../interaction_checks.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
