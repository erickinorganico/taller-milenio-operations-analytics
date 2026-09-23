/* Nonvisual route and interaction regression checks. This is not a browser test. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(process.argv[2]||'artifacts/operating-model-v4');
const data=JSON.parse(fs.readFileSync(path.join(root,'operating_model.json'),'utf8'));
const elements=new Map();
class Element {
  constructor(id){this.id=id;this.value='';this._html='';this.textContent='';this.listeners={};this.dataset={};this.disabled=false;}
  set innerHTML(html){this._html=html;for(const m of html.matchAll(/\bid="([^"]+)"/g)){const el=new Element(m[1]);elements.set(m[1],el);}
    for(const m of html.matchAll(/<select id="([^"]+)">([\s\S]*?)<\/select>/g)){const first=m[2].match(/<option[^>]*value="([^"]*)"[^>]*selected/)||m[2].match(/<option[^>]*value="([^"]*)"/);if(first)elements.get(m[1]).value=first[1];}}
  get innerHTML(){return this._html;}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(){} removeAttribute(){}
}
elements.set('model-data',{textContent:JSON.stringify(data)});
for(const id of ['content','breadcrumb','cutoff'])elements.set(id,new Element(id));
const document={getElementById:id=>{assert(elements.has(id),'Missing element: '+id);return elements.get(id);},
  querySelectorAll:selector=>selector==='[data-sort]'?[...elements.get('source-rows').innerHTML.matchAll(/data-sort="([^"]+)"/g)].map(m=>{const b=new Element('sort');b.dataset.sort=m[1];return b;}):[]};
const context=vm.createContext({document,window:{scrollTo(){},addEventListener(){}},location:{hash:''},console,Intl,encodeURIComponent,decodeURIComponent});
vm.runInContext(fs.readFileSync(path.join(root,'operating.js'),'utf8'),context);
let checks=0;const files=new Set(),routes=new Set();
function inspect(){const html=[...elements.values()].map(x=>x.innerHTML||'').join('\n');
  assert(!html.includes('undefined'),'Undefined value leaked into rendered route');
  for(const m of html.matchAll(/(?:href|src)="([^"]+)"/g)){const url=m[1];if(url.startsWith('#'))routes.add(url);else if(!url.startsWith('data:'))files.add(url);}}
function route(url){context.location.hash=url;vm.runInContext('route()',context);inspect();checks++;}
route('#overview');
for(const t of data.sources.tables){route('#sources/'+encodeURIComponent(t.name));assert(elements.get('source-count').textContent.includes(String(Math.min(t.row_count,25))));if(t.rows.length){const key=t.logical_key.map(k=>t.rows[0][k]);route('#record/'+t.name+'/'+encodeURIComponent(JSON.stringify(key)));}}
const observed=data.sources.tables.find(t=>t.name==='lifecycle_events').rows[0];
if(observed){const t=data.sources.tables.find(t=>t.name===observed.entity_type),r=t.rows.find(r=>r.id===observed.entity_id);route('#record/'+t.name+'/'+encodeURIComponent(JSON.stringify(t.logical_key.map(k=>r[k]))));assert(elements.get('content').innerHTML.includes(observed.process_id));}
for(const m of data.registry.metrics)route('#metrics/'+m.metric_id);
for(const a of data.agents.agents)route('#agents/'+a.agent_id);
for(const p of data.processes)route('#processes/'+p.process_id);
for(const c of data.decisions)route('#decision/'+encodeURIComponent(c.action_id));
route('#decisions');elements.get('case-search').value='WO-003';elements.get('case-search').listeners.input();assert(elements.get('cases-list').innerHTML.includes('WO-003'));checks++;
route('#sources/work_orders');elements.get('source-search').value='WO-003';elements.get('source-search').listeners.input();assert.equal(elements.get('source-count').textContent,'1–1 de 1 filas');checks++;
route('#sources/work_orders');elements.get('next').onclick();assert(elements.get('source-count').textContent.startsWith('26–'));checks++;
route('#delivery');
for(const file of files){assert(!path.isAbsolute(file)&&!file.split('/').includes('..'),'Unsafe file link '+file);assert(fs.existsSync(path.join(root,file)),'Broken file link '+file);}
for(const url of routes){const [kind,id,key]=url.slice(1).split('/').map(decodeURIComponent);if(kind==='processes')assert(data.processes.some(p=>p.process_id===id),'Unknown process '+id);if(kind==='metrics')assert(data.registry.metrics.some(m=>m.metric_id===id),'Unknown metric '+id);if(kind==='sources')assert(data.sources.tables.some(t=>t.name===id),'Unknown source '+id);if(kind==='record'){const t=data.sources.tables.find(t=>t.name===id),values=JSON.parse(key);assert(t?.rows.some(r=>t.logical_key.every((k,i)=>r[k]===values[i])),'Unknown record '+url);}}
console.log(JSON.stringify({status:'pass',checks,internal_routes:routes.size,local_files:files.size,scope:'Node VM route/handler/links only; no browser, layout, accessibility tree or visual claim'}));
