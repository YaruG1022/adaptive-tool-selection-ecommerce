(()=>{
 'use strict';
 const root=document.getElementById('signal-warehouse'),q=s=>root.querySelector(s),all=s=>[...root.querySelectorAll(s)];
 const products=[{name:'无线耳机',icon:'headphones',cost:22,price:42,base:8},{name:'桌面小灯',icon:'lamp-desk',cost:13,price:29,base:6},{name:'智能眼镜',icon:'glasses',cost:48,price:85,base:4}];
 const tools=[{name:'需求预测',en:'Demand Forecast',fee:18,time:1},{name:'市场调查',en:'Market Research',fee:25,time:2},{name:'供应商分析',en:'Supplier Analysis',fee:12,time:1},{name:'库存分析',en:'Inventory Analysis',fee:8,time:1},{name:'定价分析',en:'Pricing Analysis',fee:15,time:1}];
 const events=[{title:'智能眼镜突然被问爆了',copy:'评论区出现许多询价。是持续热潮，还是一阵风？',regime:1.8,topic:2},{title:'竞争对手开始周末促销',copy:'同类商品降价了。跟着降，还是保住每单的利润？',regime:.85,topic:0},{title:'宿舍开学，桌面焕新',copy:'小灯的收藏数上涨。热度会转成多少真实订单？',regime:1.6,topic:1},{title:'今天平静得有点可爱',copy:'订单照常进来，打包台终于没那么拥挤了。',regime:1,topic:0}];
 const defaultConfig={seed:7,accuracy:.75,volatility:1,feeScale:1};
 let s={day:28,cash:3260,stock:[36,25,9],pending:[{i:2,qty:18,due:29}],calls:[],toolLog:[],time:0,fees:0,sales:0,lost:0,total:0,estimate:null,quote:null,finished:false,result:'先看看市场，再决定要不要调查。18 副预付的智能眼镜明早到货。',logs:['第 27 天 · 18 副智能眼镜已付款，预计第 29 天入库。']};
 const money=n=>(n<0?'−':'')+'$'+Math.round(Math.abs(n)).toLocaleString('en-US');
 const sum=a=>a.reduce((v,n)=>v+n,0),inventory=t=>sum(t.stock.map((v,i)=>v*products[i].cost))+sum(t.pending.map(o=>o.qty*products[o.i].cost)),worth=t=>t.cash+inventory(t)*(t.finished?.8:1);
 const initialWorth=worth(s),event=()=>marketFor(s.day,defaultConfig),noise=(d,i,k=0)=>{const n=Math.sin(d*127.1+i*311.7+k*91.3)*43758.5453;return n-Math.floor(n)};
 function marketFor(day,config){const e=events[((day-28)%events.length+events.length)%events.length];return {...e,regime:Math.max(.25,1+(e.regime-1)*config.volatility)}}
 const motionQuery=matchMedia('(prefers-reduced-motion: reduce)');let reduced=motionQuery.matches,busy=false,paused=false,skipping=false,speed=1,runId=0,lastReceipt=null;
 const active=new Set();q('[data-reduce]').checked=reduced;
 const sceneMain=q('.sw-main'),shopSlot=q('.sw-layout'),liveRun={id:'live',name:'当前小店 · 手动经营',records:[]};
 const replayRuns=new Map([['live',liveRun]]);let activeView='shop',replayRunId='demo-rules',replayIndex=27;
 const methodNames={none:'不调查',always:'用满调查预算',rules:'固定规则'};
 const lab={running:false,paused:false,stopped:false,token:0,done:0,total:0,config:null,samples:{none:[],always:[],rules:[]},status:'示范实验已完成'};
 function icons(){if(globalThis.lucide)lucide.createIcons({attrs:{width:18,height:18}})}
 function parcel(){return '<div class="sw-box"></div>'}
 function render(){
  q('[data-day]').textContent=s.day;q('[data-cash]').textContent=money(s.cash);q('[data-worth]').textContent=money(worth(s));q('[data-fees]').textContent=money(s.fees);q('[data-total]').textContent=s.total+' 单';
  q('[data-event-title]').textContent=s.finished?'90 天营业结束':event().title;q('[data-event-copy]').textContent=s.finished?'小店净值较试玩开始变化 '+money(worth(s)-initialWorth)+'，期末剩余库存已折价 20%。':event().copy;
  q('[data-budget]').textContent=s.calls.length+' / 2 次';q('[data-result]').textContent=s.result;
  q('.sw-tools').innerHTML=tools.map((t,i)=>`<button class="sw-tool" data-tool="${i}">${t.name}<small>${t.en}</small><small>${money(t.fee)} · ${t.time} 小时</small></button>`).join('');
  q('.sw-products').innerHTML=products.map((p,i)=>{const po=s.pending.filter(o=>o.i===i),n=sum(po.map(o=>o.qty));return `<div class="sw-product" data-product="${i}"><div class="sw-product-title"><span class="sw-product-icon"><i data-lucide="${p.icon}" aria-hidden="true"></i></span>${p.name}</div><p>现货 <b>${s.stock[i]}</b> 件 · 在途 ${n}</p><p>售价 ${money(p.price)} · 成本 ${money(p.cost)}</p><div class="sw-stocktrack" role="img" aria-label="库存 ${s.stock[i]} 件"><span style="width:${Math.min(100,s.stock[i]/60*100)}%"></span></div><div class="sw-stocknote">${po.length?'最近到货：第 '+Math.min(...po.map(o=>o.due))+' 天':s.stock[i]<p.base?'库存偏低，留意缺货':'货架已经准备好'}</div></div>`}).join('');
  all('[data-shelf]').forEach(row=>{const i=Number(row.dataset.shelf);row.innerHTML=parcel().repeat(Math.min(3,Math.ceil(s.stock[i]/10)))});
  q('[data-journal]').innerHTML=s.logs.slice(-4).reverse().map(l=>'<li>'+l+'</li>').join('');
  q('[data-day-label]').textContent=s.finished?'关灯 · 期末盘点完成':'清晨 · 准备开店';
  syncControls();icons();
 }
 function syncControls(){
  all('[data-tool]').forEach(b=>{const i=Number(b.dataset.tool);b.disabled=busy||s.finished||s.calls.length>=2||s.calls.includes(i)||s.cash<tools[i].fee});
  q('[data-investigate]').disabled=busy||s.finished||s.calls.length>=2||!tools.some((t,i)=>!s.calls.includes(i)&&s.cash>=t.fee);
  q('[data-open]').disabled=busy||s.finished;q('[data-open] span').textContent=busy?'小店正在营业…':s.finished?'90 天经营完成':'停止调查，开始营业';
  q('[data-pause]').disabled=!busy||reduced;q('[data-pause]').textContent=paused?'继续':'暂停';q('[data-skip]').disabled=!busy;
  q('.sw-world').setAttribute('aria-busy',String(busy));
  all('[data-view]').forEach(b=>b.disabled=busy);all('[data-replay-source],[data-replay-day],[data-replay-prev],[data-replay-next]').forEach(b=>b.disabled=busy);
  q('[data-replay-play]').disabled=busy||!currentRecord();
 }
 function phase(name,text,bubble){all('[data-phase]').forEach(n=>n.dataset.active=String(n.dataset.phase===name));q('[data-live]').textContent=text;q('[data-status]').textContent=({orders:'新订单来了',packing:'机器人打包中',shipping:'快递发车',restock:'补货入库',closing:'收工盘点',ready:'准备营业'})[name]||'准备营业';q('[data-bubble]').textContent=bubble||text;}
 function toast(text){q('[data-scene-toast]').hidden=false;q('[data-scene-toast]').textContent=text;}
 function animate(el,frames,ms,options={}){
  if(reduced||skipping||!ms)return Promise.resolve();
  const a=el.animate(frames,{duration:ms,easing:'ease-in-out',fill:'none',...options});a.playbackRate=speed;if(paused)a.pause();active.add(a);
  return a.finished.catch(()=>{}).finally(()=>{active.delete(a);a.cancel()});
 }
 function wait(ms){return animate(q('.sw-world'),[{outlineOffset:'0px'},{outlineOffset:'0px'}],ms)}
 async function move(el,left,top,ms){const a={left:el.offsetLeft+'px',top:el.offsetTop+'px'};await animate(el,[a,{left:left+'px',top:top+'px'}],ms);el.style.left=left+'px';el.style.top=top+'px';}
 function dimensions(){const w=q('.sw-world');return {w:w.clientWidth,h:w.clientHeight}}
 function position(name){const {w,h}=dimensions();return {home:[w*.36,h-172],shelf:[w*.24,251],bench:[w*.51,270],dock:[w*.74,h-178],truck:[Math.max(8,w-170),h-107],outside:[w+170,h-107]}[name]}
 const robot=()=>q('.sw-robot'),truck=()=>q('.sw-truck');
 async function walk(name){const [x,y]=position(name);const feet=q('.sw-feet');await Promise.all([move(robot(),x,y,720),animate(feet,[{transform:'rotate(-9deg)'},{transform:'rotate(9deg)'},{transform:'rotate(-9deg)'},{transform:'rotate(9deg)'},{transform:'rotate(0)'}],720)]);}
 function setTruckCargo(n){q('.sw-truck-cargo').innerHTML=parcel().repeat(Math.min(3,n))}
 async function driveIn(inbound=false){const [x,y]=position('truck');truck().style.left=position('outside')[0]+'px';truck().style.top=y+'px';q('[data-truck-sign]').textContent=inbound?'供应商补货车':'小信号快递';setTruckCargo(inbound?3:0);await move(truck(),x,y,1100)}
 async function driveOut(){const {w}=dimensions();await move(truck(),w+170,truck().offsetTop,1100);setTruckCargo(0)}
 async function transfer(from,to,ms=650){const box=q('.sw-flying-box');box.hidden=false;box.style.left=from[0]+'px';box.style.top=from[1]+'px';await move(box,to[0],to[1],ms);box.hidden=true;}
 function observeTool(state,i,config=defaultConfig){
  const t=tools[i],fee=Math.round(t.fee*config.feeScale);if(state.finished||state.calls.length>=2||state.calls.includes(i)||state.cash<fee)return false;
  const e=marketFor(state.day,config),jitter=(noise(state.day+config.seed*997,i,3)*2-1)*(1-config.accuracy),estimate=Math.max(1,Math.round(products[e.topic].base*e.regime*(1+jitter)));
  state.cash-=fee;state.fees+=fee;state.time+=t.time;state.calls.push(i);
  if(i===0||i===1)state.estimate={topic:e.topic,value:estimate};if(i===4)state.quote={topic:e.topic,multiplier:e.regime>1?1.06:.96};
  const low=state.stock.indexOf(Math.min(...state.stock));
  const messages=[`需求预测（Demand Forecast）：${products[e.topic].name} 预计日需求 ${estimate} 件，预测含误差；补货目标将参考此数值。`,`市场调查（Market Research）：${products[e.topic].name} 的调查需求估计为 ${estimate} 件，热度不保证成交。`,`供应商分析（Supplier Analysis）：今天新采购预计 1 天到货，货款照常支付。`,`库存分析（Inventory Analysis）：${products[low].name} 现货最少；已有在途会计入补货判断。`,`定价分析（Pricing Analysis）：建议今天将 ${products[e.topic].name} 售价调到 ${money(Math.round(products[e.topic].price*(state.quote?.multiplier||1)))}。`];
  state.result=messages[i];state.toolLog=state.toolLog||[];state.toolLog.push({i,fee,time:t.time,text:messages[i]});state.logs.push(`第 ${state.day} 天 · ${t.name}，花费 ${money(fee)}，等待 ${t.time} 小时。`);return true;
 }
 function useTool(i){if(busy||activeView!=='shop'||!observeTool(s,i))return;q('[data-bubble]').textContent=['先算算补多少合适。','热度有了，现金也要留住。','快一点到货，少一点空货架。','包裹还在路上，别重复买。','试试新价格，再看订单。'][i];render()}
 function simulateDay(base=s,config=defaultConfig){
  const next=structuredClone(base),e=marketFor(base.day,config),toolFees=sum((base.toolLog||[]).map(t=>t.fee)),receipt={day:base.day,sold:0,missed:0,revenue:0,spent:0,bought:0,cost:0,arrived:0,arrivals:[],lines:[],orders:[],before:structuredClone(base),toolFees,openingCash:base.cash+toolFees,openingWorth:worth(base)+toolFees,event:e.title,reason:base.reason||'由你选择调查工具，随后使用同一套补货与定价规则经营。'};
  products.forEach((p,i)=>{const transit=sum(next.pending.filter(o=>o.i===i).map(o=>o.qty)),informed=(base.calls.includes(0)||base.calls.includes(1))&&base.estimate?.topic===i,factor=informed?base.estimate.value/p.base:1,target=Math.round(p.base*factor*(base.calls.includes(2)?2:3));let qty=Math.max(0,target-next.stock[i]-transit);qty=Math.min(qty,Math.max(0,Math.floor((next.cash-300)/p.cost)));if(qty){next.cash-=qty*p.cost;receipt.spent+=qty*p.cost;receipt.bought+=qty;next.pending.push({i,qty,due:base.day+(base.calls.includes(2)?1:2)})}});
  products.forEach((p,i)=>{const market=i===e.topic?e.regime:1,multiplier=base.calls.includes(4)&&base.quote?.topic===i?base.quote.multiplier:1,price=Math.round(p.price*multiplier),demand=Math.max(0,Math.round(p.base*market*(.7+noise(base.day+config.seed*997,i)*.7)*(1-base.time*.04)/Math.pow(multiplier,1.4))),qty=Math.min(next.stock[i],demand);next.stock[i]-=qty;receipt.sold+=qty;receipt.missed+=demand-qty;receipt.revenue+=qty*price;receipt.lines.push({i,demand,qty,price});if(qty)receipt.orders.push({i,qty,price})});
  receipt.cost=28+Math.round(sum(next.stock)*.12);next.cash+=receipt.revenue-receipt.cost;next.sales=receipt.sold;next.lost=receipt.missed;next.total+=receipt.sold;next.calls=[];next.toolLog=[];next.time=0;next.estimate=null;next.quote=null;next.reason='';
  next.logs.push(`第 ${base.day} 天 · 发货 ${receipt.sold} 单 / 收入 ${money(receipt.revenue)}；采购 ${receipt.bought} 件 / ${money(receipt.spent)}。`);
  if(base.day===90){next.finished=true;next.result=`期末剩余与在途库存折价 20%，估值减记 ${money(inventory(next)*.2)}，不扣减现金。`;next.logs.push('第 90 天 · 完成期末盘点，小店收工。')}
  else{next.day++;next.pending=next.pending.filter(o=>{if(o.due<=next.day){next.stock[o.i]+=o.qty;receipt.arrived+=o.qty;receipt.arrivals.push(o);return false}return true});if(receipt.arrived)next.logs.push(`第 ${next.day} 天 · ${receipt.arrived} 件补货卸车，清点入库。`);next.result=`昨天发出 ${receipt.sold} 单，错失 ${receipt.missed} 单。${receipt.arrived?'今早 '+receipt.arrived+' 件补货已经上架。':'补货仍按预计日期送达。'}`}
  next.logs=next.logs.slice(-6);receipt.next=next;return receipt;
 }
 async function sealPackage(){
  const box=q('.sw-table-box');box.hidden=false;
  await Promise.all([animate(q('.sw-arm-left'),[{transform:'rotate(12deg)'},{transform:'rotate(-65deg)'},{transform:'rotate(12deg)'}],280,{iterations:3}),animate(q('.sw-arm-right'),[{transform:'rotate(-12deg)'},{transform:'rotate(65deg)'},{transform:'rotate(-12deg)'}],280,{iterations:3}),animate(box,[{transform:'scaleY(.88) rotate(-3deg)'},{transform:'scaleY(1) rotate(2deg)'},{transform:'scaleY(1) rotate(0deg)'}],840)]);
 }
 async function playDay(r){
  q('[data-day-label]').textContent='白天 · 开门接单';phase('orders',`第 ${r.day} 天收到 ${r.sold+r.missed} 单，其中 ${r.sold} 单有货可发。`,'叮！新订单来啦，开始忙起来。');
  const stream=q('.sw-order-stream');stream.innerHTML=r.orders.map(o=>`<span class="sw-ticket">${products[o.i].name} × ${o.qty}</span>`).join('');
  await Promise.all([...stream.children].map((n,i)=>animate(n,[{transform:'translateY(-35px) rotate(-5deg)',opacity:0},{transform:'translateY(0) rotate(0deg)',opacity:1}],520,{delay:i*150})));await wait(500);stream.innerHTML='';
  if(r.sold){
   phase('packing',`机器人准备拣货，共 ${r.sold} 单。`,'货架取货，核对订单，再封好箱子。');await walk('shelf');q('.sw-carry').hidden=false;await wait(250);await walk('bench');q('.sw-carry').hidden=true;
   const batches=Math.min(3,r.orders.length),out=q('.sw-outgoing');
   for(let i=0;i<batches;i++){q('[data-monitor]').textContent='打包 '+Math.round(r.sold*(i+1)/batches)+' / '+r.sold;await sealPackage();const {w,h}=dimensions();await transfer([w*.48+75,207],[w*.79,h-148],520);q('.sw-table-box').hidden=true;out.innerHTML+=parcel();}
   phase('shipping',`${r.sold} 单已封箱，等待快递装车。`,'这一车，装着大家期待的小东西。');q('[data-day-label]').textContent='傍晚 · 装车发货';await driveIn();await walk('dock');q('.sw-carry').hidden=false;
   for(let i=0;i<Math.min(3,r.orders.length);i++){const {w,h}=dimensions();await transfer([w*.8,h-148],[truck().offsetLeft+35,truck().offsetTop+25],470);setTruckCargo(i+1);if(out.firstChild)out.firstChild.remove();}
   q('.sw-carry').hidden=true;toast(r.sold+' 单已装车 · 本日销售收入 '+money(r.revenue));await wait(400);await driveOut();out.innerHTML='';
  }else{phase('packing','今天没有可发的订单，机器人检查空货架。','没有现货可发，记得安排补货。');await walk('shelf');await wait(650);}
  phase('closing',`第 ${r.day} 天收工：日常与仓储 ${money(r.cost)}，采购 ${money(r.spent)}。`,'打包台收拾好，明天继续。');q('[data-monitor]').textContent='今日已发 '+r.sold;await walk('home');
  await animate(q('.sw-dusk'),[{opacity:0},{opacity:.35},{opacity:0}],900);q('[data-scene-toast]').hidden=true;
  if(!r.next.finished&&r.arrived){
   phase('restock',`第 ${r.next.day} 天清晨：${r.arrived} 件补货到达，正在卸货入库。`,'补货车来啦！清点数量，搬上货架。');q('[data-day-label]').textContent='次日清晨 · 补货到达';await driveIn(true);await walk('dock');q('.sw-carry').hidden=false;
   const {w,h}=dimensions();for(let i=0;i<Math.min(3,r.arrivals.length);i++){await transfer([truck().offsetLeft+35,truck().offsetTop+25],[w*.12+24,160+i*45],650);}
   await walk('shelf');q('.sw-carry').hidden=true;toast(r.arrived+' 件补货入库 · 新一天准备好了');setTruckCargo(0);await driveOut();await walk('home');
  }else if(!r.next.finished){phase('restock',`第 ${r.next.day} 天清晨：今天没有到期补货，库存按实际余量保留。`,'今天没有到货，先看看剩下的库存。');await wait(400)}
 }
 async function startDay(){
  if(busy||s.finished||activeView!=='shop')return;const id=++runId,r=simulateDay();busy=true;paused=false;skipping=false;q('[data-receipt]').hidden=true;q('[data-scene-toast]').hidden=true;syncControls();
  try{await playDay(r)}finally{
   if(id!==runId)return;
   active.forEach(a=>{try{a.finish()}catch{a.cancel()}});active.clear();
   s=r.next;lastReceipt=r;liveRun.records.push(r);busy=false;paused=false;skipping=false;render();refreshReplaySources();
   q('.sw-carry').hidden=true;q('.sw-table-box').hidden=true;q('.sw-flying-box').hidden=true;q('.sw-outgoing').innerHTML='';q('.sw-order-stream').innerHTML='';q('.sw-dusk').style.opacity=0;truck().style.left=position('outside')[0]+'px';const home=position('home');robot().style.left=home[0]+'px';robot().style.top=home[1]+'px';
   phase('ready',s.finished?'90 天经营完成，期末库存估值已计入净资产。':`第 ${s.day} 天准备营业。昨天发出 ${r.sold} 单${r.arrived?'，今早入库 '+r.arrived+' 件':''}。`,s.finished?'最后一箱发完啦，谢谢你陪我开店。':r.arrived?'新货都放好了，今天也要好好开店。':'包裹都送走啦，再看看今天的新消息。');
   q('[data-status]').textContent=s.finished?'经营完成':'新一天 · 准备营业';q('[data-monitor]').textContent=s.finished?'经营完成':'开店准备中';
   const receipt=q('[data-receipt]');receipt.hidden=false;receipt.innerHTML=`<div class="sw-receipt-title">第 ${r.day} 天 · 营业小票</div><div><span>已发货 / 缺货订单</span><b>${r.sold} / ${r.missed}</b></div><div><span>销售收入</span><b>${money(r.revenue)}</b></div><div><span>采购付款</span><b>−${money(r.spent)}</b></div><div><span>日常与仓储</span><b>−${money(r.cost)}</b></div><div><span>次日补货入库</span><b>${r.arrived} 件</b></div>`;
   toast(s.finished?'90 天经营完成':r.arrived?r.arrived+' 件新货已上架 · 第 '+s.day+' 天，早上好！':r.sold+' 单已经出发 · 第 '+s.day+' 天，早上好！');
  }
 }
 function finishActive(){for(const a of active){try{a.finish()}catch{a.cancel()}}}
 function currentRecord(){return replayRuns.get(replayRunId)?.records[replayIndex]||null}
 function resetScene(state){
  q('.sw-carry').hidden=true;q('.sw-table-box').hidden=true;q('.sw-flying-box').hidden=true;q('.sw-outgoing').innerHTML='';q('.sw-order-stream').innerHTML='';q('[data-scene-toast]').hidden=true;q('.sw-dusk').style.opacity=0;
  const home=position('home');robot().style.left=home[0]+'px';robot().style.top=home[1]+'px';truck().style.left=position('outside')[0]+'px';
  all('[data-shelf]').forEach(row=>row.innerHTML=parcel().repeat(Math.min(3,Math.ceil(state.stock[Number(row.dataset.shelf)]/10))));
 }
 function setView(view){
  if(busy)return;activeView=view;all('[data-screen]').forEach(n=>n.hidden=n.dataset.screen!==view);all('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===view)));
  q('[data-nav-note]').textContent=view==='shop'?'同一间小店，三个观察角度':view==='lab'?'实验暂停与动画暂停各自独立':'回放使用历史记录，不改动当前小店';
  if(view==='shop'){shopSlot.insertBefore(sceneMain,q('.sw-panel'));render();resetScene(s);q('.sw-scene-title h3').textContent='今天，也要把每一单好好打包。';phase('ready','小店状态已保留，可以继续调查和营业。','回到我们的小店，继续好好开店。');q('[data-status]').textContent=s.finished?'经营完成':'准备营业'}
  else if(view==='lab'){q('[data-day]').textContent=s.day;q('[data-day-label]').textContent='当前小店状态已保留';renderLab()}
  else{q('[data-replay-stage]').append(sceneMain);refreshReplaySources();renderReplay()}
  syncControls();icons();
 }
 function refreshReplaySources(){
  const available=[...replayRuns.values()].filter(r=>r.records.length);
  if(!replayRuns.get(replayRunId)?.records.length)replayRunId=available.find(r=>r.id==='demo-rules')?.id||available[0]?.id||'live';
  q('[data-replay-source]').innerHTML=available.length?available.map(r=>`<option value="${r.id}" ${r.id===replayRunId?'selected':''}>${r.name}</option>`).join(''):'<option value="live">暂无完整记录</option>';
 }
 function renderReplay(){
  const run=replayRuns.get(replayRunId);if(!run?.records.length){q('[data-replay-day]').innerHTML='<option>暂无日期</option>';q('[data-replay-title]').textContent='还没有完整的经营记录';q('[data-replay-event]').textContent='先让小店营业一天，或在研究台完成至少一个回合。';q('[data-replay-ledger]').innerHTML='';q('[data-tool-trace]').innerHTML='';q('[data-replay-reason]').textContent='完整记录会出现在这里。';q('[data-replay-truth]').innerHTML='';q('[data-replay-source-label]').textContent='等待记录';q('[data-day]').textContent=s.day;q('[data-day-label]').textContent='当前小店状态已保留';resetScene(s);phase('ready','还没有完整记录，先让小店营业一天。','等有了经营记录，就能回看这一天。');syncControls();q('[data-replay-prev]').disabled=true;q('[data-replay-next]').disabled=true;return}
  replayIndex=Math.max(0,Math.min(replayIndex,run.records.length-1));const r=currentRecord();
  q('[data-replay-day]').innerHTML=run.records.map((record,i)=>`<option value="${i}" ${i===replayIndex?'selected':''}>第 ${record.day} 天 · ${record.sold} 单</option>`).join('');
  q('[data-replay-source-label]').textContent=run.id==='live'?'当前小店 · 已完成的经营记录':'实验记录 · '+run.name;
  q('[data-replay-title]').textContent='第 '+r.day+' 天 · '+r.sold+' 单出发';q('[data-replay-event]').textContent=r.event;
  q('[data-replay-ledger]').innerHTML=`<div><span>期初现金 → 期末现金</span><b>${money(r.openingCash)} → ${money(r.next.cash)}</b></div><div><span>当日净资产变化</span><b>${money(worth(r.next)-r.openingWorth)}</b></div><div><span>工具费 / 日常与仓储</span><b>${money(r.toolFees)} / ${money(r.cost)}</b></div><div><span>销售收入 / 采购付款</span><b>${money(r.revenue)} / ${money(r.spent)}</b></div><div><span>发货 / 缺货订单</span><b>${r.sold} / ${r.missed}</b></div><div><span>次日入库</span><b>${r.arrived} 件</b></div>`;
  q('[data-replay-reason]').textContent=r.reason;
  q('[data-tool-trace]').innerHTML=r.before.toolLog.length?r.before.toolLog.map(t=>`<div>${tools[t.i].name} · ${money(t.fee)} / ${t.time} 小时<span>${t.text}</span></div>`).join(''):'<div>直接经营<span>这一天没有付费获取额外信息。</span></div>';
  q('[data-replay-truth]').innerHTML=r.lines.map(l=>`<p>${products[l.i].name}：实际请求 ${l.demand} 件，发出 ${l.qty} 件，售价 ${money(l.price)}。</p>`).join('');
  if(activeView==='replay'){
   q('[data-day]').textContent=r.day;q('[data-day-label]').textContent='历史记录 · 只读回放';resetScene(r.before);q('.sw-scene-title h3').textContent='第 '+r.day+' 天 · 回到那次经营现场';
   phase('ready','已载入原始记录：可查看当时信息，也可以播放当天动画。','那一天，我们是这样把生意做下去的。');q('[data-status]').textContent='历史回放';q('[data-monitor]').textContent='历史第 '+r.day+' 天';
  }
  syncControls();q('[data-replay-prev]').disabled=busy||replayIndex===0;q('[data-replay-next]').disabled=busy||replayIndex===run.records.length-1;
 }
 async function playReplay(){
  const r=currentRecord();if(busy||activeView!=='replay'||!r)return;
  busy=true;paused=false;skipping=false;resetScene(r.before);syncControls();
  try{await playDay(r)}finally{finishActive();busy=false;paused=false;skipping=false;resetScene(r.next);q('[data-day]').textContent=r.day;q('[data-day-label]').textContent='历史记录 · 回放完成';phase('ready',`第 ${r.day} 天回放结束：发出 ${r.sold} 单，次日入库 ${r.arrived} 件。`,'这一段故事播放完了，当前小店没有变化。');q('[data-status]').textContent='回放完成';q('[data-monitor]').textContent='原记录 '+r.sold+' 单';syncControls();}
 }
 function newTrial(){return {day:1,cash:5000,stock:[36,25,9],pending:[],calls:[],toolLog:[],time:0,fees:0,sales:0,lost:0,total:0,estimate:null,quote:null,finished:false,result:'',logs:[]}}
 function applyMethod(state,method,config){
  if(method==='none'){state.reason='不调查：不付费获取额外信息，直接按固定经营规则补货与定价。';return}
  if(method==='always'){state.reason='用满调查预算：按固定次序调用需求预测、市场调查，每天最多两次。';observeTool(state,0,config);observeTool(state,1,config);return}
  const cover=Math.min(...state.stock.map((v,i)=>v/products[i].base));
  if(cover<1.5){state.reason='固定规则：可见库存不足预计 1.5 天用量，调用需求预测和供应商分析。已有在途仍计入采购判断。';observeTool(state,0,config);observeTool(state,2,config)}
  else if(state.sales>18){state.reason='固定规则：昨天发货超过 18 单，查询一次市场调查。';observeTool(state,1,config)}
  else state.reason='固定规则：可见库存与昨天销量未触发调查阈值，直接经营。';
 }
 function readConfig(){return {accuracy:Number(q('[data-config="accuracy"]').value),volatility:Number(q('[data-config="volatility"]').value),feeScale:Number(q('[data-config="feeScale"]').value),seeds:Number(q('[data-config="seeds"]').value)}}
 function average(values){return values.length?sum(values)/values.length:0}
 function deviation(values){if(values.length<2)return 0;const mean=average(values);return Math.sqrt(sum(values.map(v=>(v-mean)**2))/(values.length-1))}
 function resetExperiment(config){
  lab.config={...config};lab.samples={none:[],always:[],rules:[]};lab.done=0;lab.total=config.seeds*3;lab.partialDay=0;lab.stopped=false;
  for(const method of Object.keys(methodNames))replayRuns.delete('demo-'+method);
 }
 function finishTrial(method,trial,trajectory,records,missed,seed){
  lab.samples[method].push({worth:worth(trial),fees:trial.fees,missed,trajectory,seed});lab.done++;lab.partialDay=0;
  if(records.length)replayRuns.set('demo-'+method,{id:'demo-'+method,name:methodNames[method]+' · 市场种子 '+seed,records,config:{...lab.config,seed}});
 }
 function primeExperiment(){
  resetExperiment(readConfig());
  for(let seed=101;seed<101+lab.config.seeds;seed++)for(const method of Object.keys(methodNames)){
   let trial=newTrial(),records=[],missed=0,trajectory=[worth(trial)];const config={...lab.config,seed};
   for(let day=1;day<=90;day++){applyMethod(trial,method,config);const receipt=simulateDay(trial,config);trial=receipt.next;missed+=receipt.missed;trajectory.push(worth(trial));if(seed===101)records.push(receipt)}
   finishTrial(method,trial,trajectory,records,missed,seed);
  }
  lab.status='示范对比已完成';renderLab();refreshReplaySources();
 }
 async function runExperiment(){
  if(lab.running)return;resetExperiment(readConfig());lab.running=true;lab.paused=false;lab.status='正在运行对比实验';const token=++lab.token;renderLab();refreshReplaySources();
  const nextFrame=()=>new Promise(resolve=>requestAnimationFrame(resolve));
  outer:for(let seed=101;seed<101+lab.config.seeds;seed++)for(const method of Object.keys(methodNames)){
   let trial=newTrial(),records=[],missed=0,trajectory=[worth(trial)];const config={...lab.config,seed};
   for(let day=1;day<=90;day++){
    while(lab.paused&&!lab.stopped&&token===lab.token)await nextFrame();if(lab.stopped||token!==lab.token)break outer;
    applyMethod(trial,method,config);const receipt=simulateDay(trial,config);trial=receipt.next;missed+=receipt.missed;trajectory.push(worth(trial));if(seed===101)records.push(receipt);lab.partialDay=day;
    if(day%10===0){q('[data-lab-detail]').textContent=methodNames[method]+' · 市场种子 '+seed+' · 第 '+day+' / 90 天';updateProgress();await nextFrame()}
   }
   finishTrial(method,trial,trajectory,records,missed,seed);renderLab();refreshReplaySources();
  }
  lab.running=false;lab.paused=false;lab.partialDay=0;lab.status=lab.stopped?'实验已结束 · 保留完整回合':'对比实验已完成';renderLab();refreshReplaySources();if(activeView==='replay'&&!busy)renderReplay();
 }
 function updateProgress(){const percent=lab.total?Math.min(100,(lab.done*90+(lab.partialDay||0))/(lab.total*90)*100):0;const track=q('.sw-run-track');track.setAttribute('aria-valuenow',Math.round(percent));track.firstElementChild.style.width=percent+'%';q('[data-lab-count]').textContent=lab.done+' / '+lab.total+' 回合'}
 function renderLab(){
  q('[data-lab-status]').textContent=lab.paused?'实验已暂停':lab.status;
  if(!lab.running)q('[data-lab-detail]').textContent='每回合独立经营 90 天；不播放仓库动画，经营规则保持一致。';
  updateProgress();const c=lab.config;if(c)q('[data-config-summary]').textContent=`当前结果：预测可靠度 ${Math.round(c.accuracy*100)} / 100 · 市场波动 ${c.volatility}× · 工具费 ${c.feeScale}× · 种子 101—${100+c.seeds}`;
  all('[data-config]').forEach(n=>n.disabled=lab.running);q('[data-lab-run]').disabled=lab.running;q('[data-lab-pause]').disabled=!lab.running;q('[data-lab-stop]').disabled=!lab.running;q('[data-lab-pause]').textContent=lab.paused?'继续实验':'暂停实验';
  q('[data-lab-table]').innerHTML=Object.keys(methodNames).map(method=>{const a=lab.samples[method],v=a.map(t=>t.worth);return `<tr><td>${methodNames[method]}<small>${a.length} 个完整回合</small></td><td>${a.length?money(average(v))+'<small>± '+money(deviation(v))+'</small>':'等待完成'}</td><td>${a.length?money(average(a.map(t=>t.fees))):'—'}</td><td>${a.length?average(a.map(t=>t.missed)).toFixed(1):'—'}</td><td><button data-trace="${method}" ${replayRuns.has('demo-'+method)?'':'disabled'}>回放 →</button></td></tr>`}).join('')+'<tr><td>学习控制器<small>DQN</small></td><td colspan="4">尚未接入 · 不生成模型成绩</td></tr>';
  drawPlot();
 }
 function drawPlot(){
  const container=q('.sw-plot'),width=container.clientWidth;if(width<100)return;
  const height=250,left=58,right=15,top=24,bottom=37,series=Object.keys(methodNames).filter(k=>lab.samples[k].length).map(k=>({key:k,values:Array.from({length:91},(_,i)=>average(lab.samples[k].map(v=>v.trajectory[i])))}));
  const values=series.flatMap(s=>s.values),min=values.length?Math.min(0,...values):0,max=values.length?Math.max(...values)*1.08:10000,span=Math.max(1,max-min),x=d=>left+d/90*(width-left-right),y=v=>height-bottom-(v-min)/span*(height-top-bottom);
  const yTicks=Array.from({length:4},(_,i)=>min+span*i/3),days=width<400?[0,30,60,90]:[0,15,30,45,60,75,90];
  const lines={none:{color:'var(--sw-green)',dash:''},always:{color:'light-dark(#527b97,#add0e9)',dash:'6 4'},rules:{color:'light-dark(#a65a38,#e4b197)',dash:'2 3'}};
  container.innerHTML=`<svg width="${width}" height="250" viewBox="0 0 ${width} 250" role="img" aria-label="完成回合的每日平均净资产"><title>三个信息获取方式的每日平均净资产，单位美元</title>${yTicks.map(v=>`<line x1="${left}" x2="${width-right}" y1="${y(v)}" y2="${y(v)}" stroke="var(--sw-border)" stroke-width="1"/><text x="${left-8}" y="${y(v)+4}" text-anchor="end">${Math.round(v/1000)}k</text>`).join('')}${days.map(d=>`<text x="${x(d)}" y="${height-bottom+18}" text-anchor="${d===90?'end':d===0?'start':'middle'}">${d}</text>`).join('')}<text x="0" y="13" class="sw-axis-label">净资产 ($)</text><text x="${width-right}" y="247" text-anchor="end" class="sw-axis-label">经营天数</text>${series.map(s=>`<path d="${s.values.map((v,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(v).toFixed(1)).join(' ')}" fill="none" stroke="${lines[s.key].color}" stroke-width="2" stroke-dasharray="${lines[s.key].dash}"><title>${methodNames[s.key]}：第 90 天均值 ${money(s.values[90])}</title></path>`).join('')}</svg>`;
 }
 const plotObserver=new ResizeObserver(()=>drawPlot());plotObserver.observe(q('.sw-plot'));
 root.addEventListener('click',ev=>{
  const b=ev.target.closest('button');if(!b||b.disabled)return;
  if(b.hasAttribute('data-view'))setView(b.dataset.view);
  else if(b.hasAttribute('data-trace')){replayRunId='demo-'+b.dataset.trace;replayIndex=27;setView('replay')}
  else if(b.hasAttribute('data-replay-prev')){replayIndex--;renderReplay()}
  else if(b.hasAttribute('data-replay-next')){replayIndex++;renderReplay()}
  else if(b.hasAttribute('data-replay-play'))playReplay().catch(()=>{q('[data-live]').textContent='回放已结束，当前小店状态保持不变。'});
  else if(b.hasAttribute('data-lab-run'))runExperiment().catch(()=>{lab.running=false;lab.status='实验中止 · 已保留完整回合';renderLab()});
  else if(b.hasAttribute('data-lab-pause')){lab.paused=!lab.paused;renderLab()}
  else if(b.hasAttribute('data-lab-stop')){lab.stopped=true;lab.paused=false}
  else if(b.hasAttribute('data-tool'))useTool(Number(b.dataset.tool));
  else if(b.hasAttribute('data-investigate')){const i=[0,1,2,3,4].find(i=>!s.calls.includes(i)&&s.cash>=tools[i].fee);if(i!==undefined)useTool(i)}
  else if(b.hasAttribute('data-open'))startDay().catch(()=>{q('[data-live]').textContent='动画已结束，当日经营结算已完成。'});
  else if(b.hasAttribute('data-pause')){paused=!paused;for(const a of active)paused?a.pause():a.play();q('[data-status]').textContent=paused?'已暂停':'继续播放';syncControls()}
  else if(b.hasAttribute('data-skip')){skipping=true;paused=false;finishActive();syncControls()}
 });
 q('[data-replay-source]').addEventListener('change',ev=>{replayRunId=ev.target.value;replayIndex=0;renderReplay()});
 q('[data-replay-day]').addEventListener('change',ev=>{replayIndex=Number(ev.target.value);renderReplay()});
 all('[data-config]').forEach(n=>n.addEventListener('change',()=>{q('[data-lab-detail]').textContent='设置已更改。下方仍显示上一次结果，重新运行后更新。'}));
 q('[data-speed]').addEventListener('change',ev=>{speed=Number(ev.target.value);for(const a of active)a.updatePlaybackRate(speed)});
 q('[data-reduce]').addEventListener('change',ev=>{reduced=ev.target.checked;if(reduced){paused=false;finishActive()}syncControls()});
 motionQuery.addEventListener('change',ev=>{reduced=ev.matches;q('[data-reduce]').checked=reduced;if(reduced){paused=false;finishActive()}syncControls()});
 const observer=new ResizeObserver(()=>{if(!busy){const p=position('home');robot().style.left=p[0]+'px';robot().style.top=p[1]+'px';truck().style.left=position('outside')[0]+'px'}});observer.observe(q('.sw-world'));
 render();primeExperiment();
})();
