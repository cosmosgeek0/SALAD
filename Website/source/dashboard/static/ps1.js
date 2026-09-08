(() => {
  "use strict";
  /* Tabler Icons — https://tabler.io/icons
MIT License

Copyright (c) 2020-2026 Paweł Kuna

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
  const serviceIcons={"HG":"<path d=\"M4 18v-5l4 -2l4 2v5l-4 2l-4 -2\" /> <path d=\"M8 11v-5l4 -2l4 2v5\" /> <path d=\"M12 13l4 -2l4 2v5l-4 2l-4 -2\" />","PS":"<path d=\"M12 4l-8 4l8 4l8 -4l-8 -4\" /> <path d=\"M4 12l8 4l8 -4\" /> <path d=\"M4 16l8 4l8 -4\" />","PR":"<path d=\"M3 7a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v2a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3v-2\" /> <path d=\"M3 15a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v2a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3l0 -2\" /> <path d=\"M7 8l0 .01\" /> <path d=\"M7 16l0 .01\" />","RP":"<path d=\"M4 7a8 4 0 1 0 16 0a8 4 0 1 0 -16 0\" /> <path d=\"M4 7c0 .664 .088 1.324 .263 1.965l2.737 10.035c.5 1.5 2.239 2 5 2s4.5 -.5 5 -2c.333 -1 1.246 -4.345 2.737 -10.035a7.45 7.45 0 0 0 .263 -1.965\" />","EF":"<path d=\"M4 15a2 2 0 0 1 2 -2h1a2 2 0 0 1 2 2v3a2 2 0 0 1 -2 2h-1a2 2 0 0 1 -2 -2l0 -3\" /> <path d=\"M15 15a2 2 0 0 1 2 -2h1a2 2 0 0 1 2 2v3a2 2 0 0 1 -2 2h-1a2 2 0 0 1 -2 -2l0 -3\" /> <path d=\"M4 15v-3a8 8 0 0 1 16 0v3\" />","TM":"<path d=\"M3 17l6 -6l4 4l8 -8\" /> <path d=\"M14 7l7 0l0 7\" />","PA":"<path d=\"M12 3a3 3 0 0 1 3 3c0 1.113 -.6 2.482 -1.5 3l1.5 7h-6l1.5 -7c-.9 -.518 -1.5 -1.887 -1.5 -3a3 3 0 0 1 3 -3\" /> <path d=\"M8 9h8\" /> <path d=\"M6.684 16.772a1 1 0 0 0 -.684 .949v1.279a1 1 0 0 0 1 1h10a1 1 0 0 0 1 -1v-1.28a1 1 0 0 0 -.684 -.948l-2.316 -.772h-6l-2.316 .772\" />","EA":"<path d=\"M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0\" /> <path d=\"M14 8h-4v8h4\" /> <path d=\"M10 12h2.5\" />","GR":"<path d=\"M2 9a10 10 0 1 0 20 0\" /> <path d=\"M12 19a10 10 0 0 1 10 -10\" /> <path d=\"M2 9a10 10 0 0 1 10 10\" /> <path d=\"M12 4a9.7 9.7 0 0 1 2.99 7.5\" /> <path d=\"M9.01 11.5a9.7 9.7 0 0 1 2.99 -7.5\" />","◫":"<path d=\"M4 5a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1l0 -4\" /> <path d=\"M14 5a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1l0 -4\" /> <path d=\"M4 15a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1l0 -4\" /> <path d=\"M14 15a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1l0 -4\" />"};
  window.serviceIcon=code=>'<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+serviceIcons[code]+'</svg>';
  const sidebar=document.getElementById('sidebar'),themeButton=document.getElementById('themeToggle');
  function applyTheme(theme){document.documentElement.dataset.bsTheme=theme;if(themeButton){const label=theme==='dark'?'Switch to light mode':'Switch to dark mode';themeButton.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(theme==='dark'?'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"/>':'<path d="M20.9 13A9 9 0 0 1 11 3.1 9 9 0 1 0 20.9 13Z"/>')+'</svg>';themeButton.setAttribute('aria-label',label);themeButton.title=label;}}
  applyTheme(localStorage.getItem('salad-theme')==='dark'?'dark':'light');
  if(themeButton)themeButton.onclick=()=>{const theme=document.documentElement.dataset.bsTheme==='dark'?'light':'dark';applyTheme(theme);localStorage.setItem('salad-theme',theme);};
  if(sidebar){for(const mark of sidebar.querySelectorAll('.service-mark')){mark.innerHTML=window.serviceIcon(mark.textContent);}const setSidebar=expanded=>{sidebar.dataset.state=expanded?'expanded':'collapsed';document.body.classList.toggle('sidebar-collapsed',!expanded);document.getElementById('sidebarScrim').hidden=!expanded||!matchMedia('(max-width:900px)').matches;document.getElementById('sidebarExpand').setAttribute('aria-expanded',String(expanded));};document.getElementById('sidebarExpand').onclick=()=>setSidebar(true);document.getElementById('sidebarCollapse').onclick=()=>setSidebar(false);document.getElementById('sidebarScrim').onclick=()=>setSidebar(false);matchMedia('(max-width:900px)').addEventListener('change',()=>setSidebar(false));setSidebar(false);}
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const formats = new Map();
  const number = (value, digits = 1) => {
    if (!finite(value)) return "—";
    if (!formats.has(digits)) formats.set(digits, new Intl.NumberFormat(undefined, {maximumFractionDigits: digits}));
    const format=formats.get(digits), small=value>0&&value<10**-digits;
    return (small?"<":"")+format.format(small?10**-digits:value);
  };
  window.formatBandwidth=number;
  const responses=new Map(),requests=new Map(),storage=caches.open('salad-responses').catch(()=>null);
  const responseKey=(service,hours)=>service.id+':'+hours;
  const responseURL=(service,hours)=>service.url+(service.url.includes('?')?'&':'?')+'compact=1&hours='+hours;
  async function read(url,signal,key){
    const deadline=AbortSignal.timeout(30000);
    try{
      const response=await fetch(url,{cache:'no-store',signal:signal?AbortSignal.any([signal,deadline]):deadline});
      if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(typeof error.error==='string'?error.error:'HTTP '+response.status);}
      const copy=key?response.clone():null,result=await response.json();
      if(key){
        const at=Date.now(),headers=new Headers(copy.headers);headers.set('X-Salad-Read-Ms',String(at));responses.set(key,{data:result,at});
        storage.then(cache=>cache?.put(url,new Response(copy.body,{status:copy.status,headers}))).catch(()=>{});
      }
      return result;
    }catch(error){if(deadline.aborted&&!signal?.aborted)throw new Error('The server response timed out after 30 seconds');throw error;}
  }
  async function restore(service,hours){
    const key=responseKey(service,hours);
    if(!responses.has(key))try{
      const response=await(await storage)?.match(responseURL(service,hours));
      if(response){const data=await response.json(),at=Number(response.headers.get('X-Salad-Read-Ms'));if(!responses.has(key))responses.set(key,{data,at});}
    }catch(_){}
    return responses.get(key)?.data;
  }
  function load(service,hours,force=true){
    const key=responseKey(service,hours),entry=responses.get(key),age=Date.now()-entry?.at;
    if(!force&&!requests.has(key)&&entry&&age>=0&&age<=5000)return Promise.resolve(entry.data);
    if(!requests.has(key))requests.set(key,read(responseURL(service,hours),null,key).finally(()=>requests.delete(key)));
    return requests.get(key);
  }
  window.bandwidthData={read,restore,load,get:(service,hours)=>responses.get(responseKey(service,hours))?.data,
    updated:(service,hours)=>responses.get(responseKey(service,hours))?.at,
    age:(at,now=Date.now())=>Number.isFinite(at)&&at<=now?Math.floor((now-at)/1000)+'s':'—',
    providerFresh:(service,p,now=Date.now())=>p?.fresh===true&&Number.isFinite(p.observed_ms)&&now>=p.observed_ms&&now-p.observed_ms<=(service==='hg'?360000:service==='proxyrack'?900000:180000)};
  const clockFormat = new Intl.DateTimeFormat(undefined, {hour: "2-digit", minute: "2-digit", hour12: false});
  const clock = value => value == null ? "—" : clockFormat.format(value);
  const make = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const countryCache = new Map();
  const countryAttempts = new Map();
  const countryCode = node => /^[A-Z]{2}$/i.test(node.country || "") ? node.country.toUpperCase() : countryCache.get(node.ip);
  const needsCountry = node => node.ip && !countryCode(node) && (!countryAttempts.has(node.ip) || Date.now() - countryAttempts.get(node.ip) >= 60000);
  const countryName=node=>countryCode(node)||'—';
  let countryLookup = null;
  async function lookupCountries(nodes) {
    if (!nodes.some(needsCountry)) return;
    if (countryLookup) await countryLookup;
    const ips=[...new Set(nodes.filter(needsCountry).map(n=>n.ip))];
    if (!ips.length) return;
    for (const ip of ips) countryAttempts.set(ip, Date.now());
    countryLookup=(async()=>{
      try {
        const response=await fetch("https://api.country.is/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(ips),signal:AbortSignal.timeout(5000)});
        if (!response.ok) return;
        for (const row of await response.json()) if(ips.includes(row.ip) && /^[A-Z]{2}$/.test(row.country)) countryCache.set(row.ip,row.country);
      } catch (_) {}
    })();
    await countryLookup; countryLookup=null;
  }
  window.bandwidthCountries = {name: countryName, lookup: lookupCountries};
  const nodeColor=()=> 'var(--blue)';
  function nodeLabel(node,includeCountry=true) {
    const label=make('span',null,'node-label'),square=make('i',null,'node-square');square.style.backgroundColor=nodeColor(node);square.setAttribute('aria-hidden','true');
    label.append(square);if(includeCountry)label.append(make('span',countryName(node),'node-country'));label.append(make('span',node.ip||'—','node-ip'));label.title=node.ip||'';return label;
  }
  function clientStatus(node){if(!node)return '—';if(node.stale||node.pending||node.unknown)return 'Unknown';if(node.working===true)return 'Online';if(/error|failed|rejected|exited|stopped|disconnect|limit|unusable|overused|offline/i.test(node.status||'')||['stopped','failed','succeeded'].includes(node.salad))return 'Offline';return 'Unknown';}
  const stateLabel=node=>!node?'—':node.stale||!node.salad?'Unknown':node.salad[0].toUpperCase()+node.salad.slice(1);
  window.bandwidthNodes = {color:nodeColor,label:nodeLabel,status:clientStatus,state:stateLabel};
  window.createMinuteChart=({plot,breakdown,pageCount,previous,next,scroll,popup,active,unit})=>{
    let data=null,series=[],geometry=null,hover=null,hoverBand=null,page=0,postingMinutes=new Map(),plotKey="";
    const svg=(tag,attrs={},text)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!=null)n.textContent=text;return n;};
    const ticks=maximum=>{const target=(maximum>0?maximum:1)*1.04,raw=target/5,power=10**Math.floor(Math.log10(raw)),step=[1,2,2.5,5,10].map(n=>n*power).find(n=>n>=raw);return Array.from({length:Math.ceil(target/step)+1},(_,i)=>i*step);};
    function axes(target,maximum,height){
      const width=Math.round(target.parentElement.clientWidth),left=width<450?38:50,right=width-16,top=16,bottom=height-26,scale=maximum>0&&maximum<.001?1e6:maximum>0&&maximum<1?1e3:1,values=ticks(maximum*scale),ceiling=values.at(-1)/scale;
      unit.textContent=scale===1e6?"B":scale===1e3?"kB":"MB";
      target.setAttribute('viewBox',`0 0 ${width} ${height}`);target.style.height=height+'px';target.replaceChildren();
      const x=i=>left+(i+.5)/data.candles.length*(right-left),y=n=>top+(1-n/ceiling)*(bottom-top);
      for(const value of values){target.append(svg('line',{x1:left,x2:right,y1:y(value/scale),y2:y(value/scale),stroke:'var(--plot-grid)','stroke-dasharray':'2 4'}),svg('text',{x:left-6,y:y(value/scale)+3,'text-anchor':'end'},number(value,1)));}
      const count=Math.max(3,Math.min(12,Math.floor(width/160)));
      for(let i=0;i<count;i++){const index=Math.round(i/(count-1)*(data.candles.length-1));target.append(svg('text',{x:x(index),y:height-12,'text-anchor':i===0?'start':i===count-1?'end':'middle'},clock(data.candles[index].minute_ms)));}
      target.append(svg('line',{x1:left,x2:right,y1:bottom,y2:bottom,stroke:'var(--axis-line)'}),svg('line',{x1:left,x2:left,y1:top,y2:bottom,stroke:'var(--axis-line)'}));
      return {width,left,right,top,bottom,x,y};
    }
    function draw(){
      if(!data||!active())return;
      if(!popup.classList.contains('hidden')){const width=scroll.parentElement.getBoundingClientRect().width;popup.style.left=Math.max(4,Math.min(parseFloat(popup.style.left)||4,width-popup.offsetWidth-4))+'px';}
      const bars=data.candles,mobile=matchMedia('(max-width:768px)').matches,credits=bars.map(bar=>postingMinutes.get(bar.minute_ms)?.credited_mb);
      if(!bars.some(b=>finite(b.mb))&&!credits.some(finite)){plot.replaceChildren();plot.setAttribute('viewBox','0 0 600 380');plot.style.height=(mobile?240:380)+'px';const message=data.loading?'Loading…':'No measurements';plot.append(svg('text',{x:300,y:190,'text-anchor':'middle'},message));plot.setAttribute('aria-label',message);geometry=null;return;}
      const maximum=Math.max(0,...bars.map(b=>b.mb||0),...credits.map(value=>value||0)),g=axes(plot,maximum,mobile?240:380),step=(g.right-g.left)/bars.length,barWidth=step*(bars.length<=60?.9:.72);
      hoverBand=svg('rect',{x:0,y:g.top,width:step,height:g.bottom-g.top,fill:'var(--chart-hover)',visibility:'hidden'});plot.append(hoverBand);geometry={...g,step};
      const paths=Array.from({length:8},()=>[]);
      bars.forEach((bar,i)=>{
        const x=g.left+i*step+(step-barWidth)/2;
        const layers=[[bar.mb,0],[credits[i],1]];if(credits[i]>bar.mb)layers.reverse();
        for(const [layer,[value,color]]of layers.entries())if(finite(value))paths[(layer*2+color)*2+(color===0&&bar.partial?1:0)].push(`M${x} ${g.y(value)}h${barWidth}v${Math.max(.75,g.bottom-g.y(value))}h${-barWidth}Z`);
      });
      for(const [i,path]of paths.entries())if(path.length)plot.append(svg('path',{d:path.join(''),fill:Math.floor(i/2)%2?'var(--earned)':'var(--blue)',opacity:i%2?0.65:1}));
      plot.setAttribute('aria-label',`Past ${Math.round(bars.length/60)} hours. Linear minute bars: blue is network MB; green is provider MB changes observed during the minute, overlaid at the same baseline. Pale blue marks partial coverage. Zero is a baseline mark; gaps have no sample. Arrow keys inspect a minute.`);
      drawHover();
    }
    function drawHover(){if(!geometry||!hoverBand)return;const i=data.candles.findIndex(b=>b.minute_ms===hover);hoverBand.setAttribute('visibility',i<0?'hidden':'visible');if(i>=0)hoverBand.setAttribute('x',geometry.left+i*geometry.step);}
    function buildBreakdown(){
      const grouped=new Map(),bars=data.candles;
      bars.forEach((bar,i)=>{for(const node of bar.nodes||[]){if(!finite(node.mb)||node.mb<0)continue;const key=node.ip||node.instance||'Unknown',item=grouped.get(key)||{...node,total:0,peak:0,minutes:0,lastMinute:-1,currentMinute:0};item.total+=node.mb;if(item.lastMinute!==i){item.lastMinute=i;item.currentMinute=0;item.minutes++;}item.currentMinute+=node.mb;item.peak=Math.max(item.peak,item.currentMinute);grouped.set(key,item);}});
      series=[...grouped.values()].sort((a,b)=>b.total-a.total);
      page=Math.min(page,Math.max(0,Math.ceil(series.length/25)-1));const shown=series.slice(page*25,(page+1)*25);
      pageCount.textContent=series.length?(page*25+1)+'–'+Math.min((page+1)*25,series.length)+' of '+series.length+(series.some(n=>!n.ip)?' contributor records':' IPs'):'No recorded contributors';previous.disabled=page===0;next.disabled=(page+1)*25>=series.length;
      breakdown.replaceChildren();
      for(const item of shown){
        const current=data.nodes?.find(n=>!n.pending&&(item.ip?n.ip===item.ip:item.instance&&n.id===item.instance)),row=make('tr'),identity=make('td'),client=make('td'),status=clientStatus(current);identity.append(nodeLabel(item,false));
        client.append(make('span',status,'status-pill '+(status==='Online'?'online':'')));client.title=current?[current.status,current.error,current.note].filter(Boolean).join(' · '):'No current client observation';
        row.append(identity,make('td',countryName(item)),client,make('td',stateLabel(current)),make('td',number(item.peak),'numeric'),make('td',number(item.total),'numeric'),make('td',number(item.minutes,0)));breakdown.append(row);
      }
      const rendered=data,renderedPage=page;lookupCountries(shown).then(()=>{if(data!==rendered||page!==renderedPage)return;for(const [i,item]of shown.entries())if(breakdown.rows[i])breakdown.rows[i].cells[1].textContent=countryName(item);});
      if(!series.length){const row=make('tr'),cell=make('td',data.loading?'Loading…':'IP contributions unavailable','empty-cell');cell.colSpan=7;row.append(cell);breakdown.append(row);}
    }
    function hide(){hover=null;popup.classList.add('hidden');drawHover();}
    function showMinute(index,event,preservePosition=false){
      const bar=data.candles[index];if(!bar)return;const minute=bar.minute_ms,changed=hover!==minute,wrap=scroll.parentElement.getBoundingClientRect();
      if(!preservePosition){const width=Math.min(parseFloat(getComputedStyle(popup).width),wrap.width-8),cursorX=event?event.clientX-wrap.left:wrap.width-width-16,side=cursorX+width+16<=wrap.width?cursorX+16:cursorX-width-16,top=Math.max((geometry?.top||16)+8,12-wrap.top);popup.style.left=Math.max(4,Math.min(side,wrap.width-width-4))+'px';popup.style.top=top+'px';popup.style.maxHeight=Math.min(innerHeight*.65,innerHeight-wrap.top-top-12)+'px';}
      if(changed){hover=minute;drawHover();const posted=postingMinutes.get(minute),heading=make('div',null,'popup-heading');heading.append(make('span',new Date(minute).toLocaleDateString('en-CA')),make('span',clock(minute)+'–'+clock(minute+60000)));popup.replaceChildren(heading);
        const row=(label,meta,value,cls)=>{const item=make('div',null,'popup-row '+cls),name=make('span',null,'popup-label');name.append(make('i',null,'popup-square'),make('span',label));item.append(name,make('span',meta,'popup-meta'),make('span',value,'popup-value'));popup.append(item);};
        row('Network',finite(bar.mb)&&finite(bar.count)?number(bar.count,0)+' nodes':'',(bar.estimated?'≈ ':'')+number(bar.mb)+' MB','network');
        row('Credited',finite(posted?.earned_usd)?'$'+number(posted.earned_usd,6):'—',number(posted?.credited_mb)+' MB','credited');
        popup.lastChild.title=posted?'Provider changes observed between '+new Date(posted.start_ms).toLocaleString()+' and '+new Date(posted.end_ms).toLocaleString()+'. Posting time is unknown.'+(data.usdConversion?' Dollar value is a USD equivalent.':''):'No provider change observed';
      }
      popup.classList.remove('hidden');
    }
    function indexAt(event){if(!geometry)return null;const x=event.clientX-plot.getBoundingClientRect().left;return x<geometry.left||x>=geometry.right?null:Math.floor((x-geometry.left)/geometry.step);}
    plot.addEventListener('pointermove',event=>{const index=indexAt(event);if(index!=null)showMinute(index,event);});plot.addEventListener('pointerleave',hide);plot.addEventListener('blur',hide);plot.addEventListener('click',event=>{const i=indexAt(event);if(i!=null)showMinute(i,event);});
    plot.addEventListener('keydown',event=>{if(!data||!['ArrowLeft','ArrowRight','Home','End','Escape'].includes(event.key))return;event.preventDefault();if(event.key==='Escape'){hide();return;}const i=hover==null?data.candles.length-1:data.candles.findIndex(b=>b.minute_ms===hover);showMinute(event.key==='Home'?0:event.key==='End'?data.candles.length-1:Math.max(0,Math.min(data.candles.length-1,i+(event.key==='ArrowLeft'?-1:1))));});
    previous.onclick=()=>{if(page>0){page--;buildBreakdown();}};next.onclick=()=>{if((page+1)*25<series.length){page++;buildBreakdown();}};
    const resize=new ResizeObserver(draw);resize.observe(scroll);
    return {hide,count:()=>data?.loading?null:series.length,update(next){const selected=hover;if(data?.key!==next.key)page=0;data=next;postingMinutes=new Map();const first=data.candles[0].minute_ms,last=data.candles.at(-1).minute_ms;
      for(const p of data.postings||[]){if(p.end_ms<first||p.end_ms>=last+60000)continue;const minute=Math.floor(p.end_ms/60000)*60000,posted=postingMinutes.get(minute)||{credited_mb:null,earned_usd:null,start_ms:p.start_ms,end_ms:p.end_ms};posted.start_ms=Math.min(posted.start_ms,p.start_ms);posted.end_ms=Math.max(posted.end_ms,p.end_ms);for(const key of ['credited_mb','earned_usd'])if(finite(p[key]))posted[key]=(posted[key]??0)+p[key];postingMinutes.set(minute,posted);}
      buildBreakdown();const key=JSON.stringify([data.key,data.loading,data.candles.map(b=>[b.minute_ms,b.mb,b.partial,b.estimated]),[...postingMinutes]]);
      if(key!==plotKey){plotKey=key;draw();}if(selected!=null){hover=null;const i=data.candles.findIndex(b=>b.minute_ms===selected);if(i<0)hide();else showMinute(i,undefined,true);}}};
  };

})();

"use strict";
// Preserve the existing provider-tab bridge; it is separate from presentation.
(() => {
  const button = document.getElementById("psConnect"), message = document.getElementById("psFeedStatus") || {textContent:""};
  let providerWindow = null, state = null, pending = null;
  let channel = sessionStorage.getItem("ps-billing-channel") || "";
  function refresh() {
    if(pending) return pending;
    pending = (async () => {
      try {
        const response=await fetch("/api/ps1/view",{cache:"no-store",signal:AbortSignal.timeout(8000)});
        if(!response.ok)throw new Error();
        state=await response.json();
        message.textContent=state.feed_age_ms!=null&&state.feed_age_ms<150000?"Provider readings are connected.":"Provider readings are missing or stale. Keep the connected provider tab open.";
      } catch(_) {state=null;message.textContent="Provider connection status is unknown.";}
    })().finally(()=>{pending=null;});
    return pending;
  }
  button?.addEventListener("click",()=>{
    if(providerWindow&&!providerWindow.closed){providerWindow.focus();return;}
    if(!channel){channel=crypto.randomUUID();sessionStorage.setItem("ps-billing-channel",channel);}
    providerWindow=window.open(`https://app.packetstream.io/dashboard#ps-sync=${channel}`,"psBillingSync");
    message.textContent="Provider tab opened. Waiting for credited-traffic readings.";refresh();
  });
  window.addEventListener("message",async event=>{
    if(event.origin!=="https://app.packetstream.io"||!channel||event.data?.type!=="ps-credited"||event.data.channel!==channel)return;
    if(providerWindow&&event.source!==providerWindow)return;
    if(event.data.error){message.textContent="Provider reading could not be retrieved.";return;}
    await refresh();if(!state?.bridge_token||!Number.isFinite(event.data.gb))return;
    try{
      const save=()=>fetch("/api/ps1/credited",{method:"POST",headers:{"Content-Type":"application/json","X-PS-Token":state.bridge_token},body:JSON.stringify({gb:event.data.gb,bytes:event.data.bytes,time_ms:event.data.time_ms})});
      let response=await save();
      if(response.status===403){await refresh();if(!state?.bridge_token)throw new Error();response=await save();}
      if(!response.ok)throw new Error();message.textContent="Provider reading saved.";
    }
    catch(_){message.textContent="Provider reading could not be saved.";}
  });
  document.getElementById("history")?.addEventListener("toggle",event=>{if(event.currentTarget.open)refresh();});
})();
