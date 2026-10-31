/* Presentation-only localization for this prototype.
 * The simulation keeps its canonical messages. This module translates text and
 * accessible names without recreating controls, changing state, or restarting
 * animations. Text-node identity preserves the original Chinese on round trips.
 * Add UI copy to the literal catalog or the parameterized message rules below.
 */
(()=>{
 'use strict';
 const root=document.getElementById('signal-warehouse');
 let language='en',scheduled=false;
 const originals=new WeakMap(),attributeOriginals=new WeakMap();
 const catalog=new Map(Object.entries({
  '小信号商店':'Little Signal Shop',
  'Little Signal · 开店，也看懂每一次决定':'Little Signal · Run the shop. Understand each decision.',
  '清晨 · 准备开店':'Morning · Ready to open',
  '游戏功能':'Game sections',
  '仓库小剧场':'Warehouse', '研究台':'Research Lab', '经营回放':'Business Replay',
  '同一间小店，三个观察角度':'One shop. Three ways to explore it.',
  '现金（Cash）':'Cash', '净资产（Net Worth）':'Net worth',
  '累计调查费（Tool Cost）':'Total tool cost', '累计发货':'Orders shipped',
  '今天，也要把每一单好好打包。':'Every order deserves a little care.',
  '等待营业':'Ready to open', '每个包裹，都带着一点期待。':'A little anticipation in every parcel.',
  '快递收发口':'Loading bay', '现货货架':'Stock shelves', '开店准备中':'Getting ready',
  '打包台':'Packing desk', '待发区':'Dispatch', '早上好！先看看今天的订单吧。':'Good morning! Let’s check today’s orders.',
  '快递专用道 · 慢慢开，好好送':'Delivery lane · Handle with care',
  '小信号快递':'Signal Express', '供应商补货车':'Supply delivery',
  '收单':'Orders', '打包':'Packing', '发车':'Shipping', '入库':'Restock',
  '营业进度':'Business-day progress',
  '明早有 18 副智能眼镜到货；今天先把现有订单送出去。':'18 smart glasses arrive tomorrow. Let’s ship today’s orders first.',
  '播放速度':'Speed', '暂停':'Pause', '继续':'Resume', '跳过本日动画':'Skip day animation',
  '减少动态效果':'Reduce motion', '经营事件和工具选择':'Business events and information tools',
  '今日经营事件':'Today’s business event', '调查工具':'Information tools',
  '让店长调查一次':'Let the manager investigate', '停止调查，开始营业':'Open for business',
  '店长使用演示规则（Demonstration Rules）。调查结果会影响补货与定价。':'The manager uses demonstration rules. Tool observations affect replenishment and pricing.',
  '商品库存':'Product inventory', '仓库日记':'Warehouse journal',
  '每一个动作，都有一笔生意。':'Every little action has a business behind it.',
  '订单有货才打包；补货到期才入库。发车和收货完成后，统一更新当天账目。':'Only available orders are packed. Supplies arrive on their due dates. The ledger updates after shipping and receiving.',
  '每个动画纸箱代表一批货，件数以文字为准。试玩从第 28 天开始，已有 18 件预付补货在途；第 90 天进行期末库存估值。':'Each animated box represents a batch; labels show exact quantities. The playable store starts on day 28 with 18 prepaid units in transit. Remaining stock is valued at the end of day 90.',
  '把经营疑问变成可以比较的实验':'Turn business questions into comparable experiments',
  '什么时候，额外的信息值得花钱？':'When is more information worth its cost?',
  '本地模拟 · 90 天 / 回合':'Local simulation · 90 days per episode',
  '实验设置':'Experiment setup',
  '固定经营规则、起始现金 $5,000 和相同库存；只改变信息获取方式。':'The same business rules, $5,000 starting cash, and inventory. Only information-gathering policies differ.',
  '预测可靠度（Forecast Reliability）':'Forecast reliability',
  '高 · 预测误差较小':'High · Smaller forecast errors',
  '中 · 预测含有噪声':'Medium · Noisy forecasts',
  '低 · 预测波动较大':'Low · Larger forecast errors',
  '市场波动（Market Volatility）':'Market volatility',
  '平稳 · 0.5×':'Calm · 0.5×', '日常起伏 · 1×':'Everyday changes · 1×', '风云变幻 · 1.7×':'Volatile · 1.7×',
  '工具费用（Tool Cost）':'Tool cost', '较低 · 0.5×':'Lower · 0.5×', '标准 · 1×':'Standard · 1×', '昂贵 · 2×':'Expensive · 2×',
  '市场种子（Market Seeds）':'Market seeds', '3 个 · 快速试玩':'3 seeds · Quick preview',
  '6 个 · 多次比较':'6 seeds · More comparisons', '12 个 · 更完整的分布':'12 seeds · Broader sample',
  '每天最多调查 2 次。三个方法共用相同的市场种子；预测可靠度控制误差范围。':'At most two calls per day. All policies share market seeds. Reliability controls the forecast error range.',
  '重新运行对比':'Run comparison', '暂停实验':'Pause experiment', '结束实验':'Stop experiment', '继续实验':'Resume experiment',
  '学习模型还没有接入':'Learning model not connected',
  '深度 Q 网络（Deep Q-Network, DQN）尚未训练。这里展示三个固定规则方法的真实模拟结果。':'The Deep Q-Network (DQN) has not been trained. These results come from three fixed policies running the simulation.',
  '正在准备示范实验':'Preparing the sample comparison', '经营曲线（Net Worth Trajectory）':'Net worth trajectory',
  '已完成回合的每日均值':'Daily mean across completed episodes',
  '三个工具选择方法的净资产经营曲线':'Net worth trajectories for three tool-selection policies',
  '不调查':'No tools', '用满调查预算':'Use full tool budget', '固定规则':'Rule-based',
  '对比结果':'Comparison results', '点击回放查看首个市场种子的记录':'Replay the first market seed for each policy',
  '信息获取方式':'Information policy', '期末净资产':'Final net worth', '均值 ± 标准差':'Mean ± SD',
  '平均工具费':'Mean tool cost', '平均缺货单':'Mean unfilled orders', '回放':'Replay', '回放 →':'Replay →',
  '标准差（Standard Deviation）描述不同市场种子的结果差异。这里只做简化模拟与界面演示；曲线不是训练曲线，也不代表已验证的研究结论。':'Standard deviation describes variation across market seeds. This is a simplified simulation and interface prototype. These are business trajectories, not training curves or validated research findings.',
  '沿着一笔生意，回看当时发生了什么':'Follow an order back to the decisions behind it',
  '经营回放（Business Replay）':'Business replay', '只读 · 不改变当前小店':'Read-only · Live store stays unchanged',
  '记录来源':'Recording', '营业日期':'Business day', '← 前一天':'← Previous', '后一天 →':'Next →',
  '前一天':'Previous day', '后一天':'Next day', '播放这一天':'Play this day',
  '使用原始记录播放，不重新抽取市场结果。':'Plays the original receipt. No new market outcomes are sampled.',
  '当时的决策依据':'Decision rule at the time', '信息获取记录':'Information-gathering log',
  '事后对照（Post Hoc Comparison）':'Post hoc comparison',
  '以下真实需求仅供回顾，没有直接提供给经营决策。':'Realized demand is shown only for review. It was not passed directly to the business policy.',
  '交互原型（Interactive Prototype） · 合成经营数据 · 支持暂停、加速及减少动态效果':'Interactive prototype · Synthetic business data · Pause, speed, and reduced motion supported',
  '请启用浏览器的 JavaScript（脚本语言）以运行游戏。':'Enable JavaScript in your browser to run the game.',
  '无线耳机':'Wireless headphones', '桌面小灯':'Desk lamp', '智能眼镜':'Smart glasses',
  '需求预测':'Demand forecast', '市场调查':'Market research', '供应商分析':'Supplier analysis', '库存分析':'Inventory analysis', '定价分析':'Pricing analysis',
  '智能眼镜突然被问爆了':'Everyone is asking about smart glasses',
  '评论区出现许多询价。是持续热潮，还是一阵风？':'The comments are full of questions. Is this lasting demand or a passing trend?',
  '竞争对手开始周末促销':'A competitor starts a weekend sale',
  '同类商品降价了。跟着降，还是保住每单的利润？':'Similar products are on sale. Match the price or protect the margin?',
  '宿舍开学，桌面焕新':'A new term, a new desk',
  '小灯的收藏数上涨。热度会转成多少真实订单？':'More shoppers are saving the lamp. How many will actually order?',
  '今天平静得有点可爱':'A pleasantly ordinary day',
  '订单照常进来，打包台终于没那么拥挤了。':'Orders arrive as usual. The packing desk finally has room to breathe.',
  '先看看市场，再决定要不要调查。18 副预付的智能眼镜明早到货。':'Check the market before paying for more information. 18 prepaid smart glasses arrive tomorrow.',
  '第 27 天 · 18 副智能眼镜已付款，预计第 29 天入库。':'Day 27 · 18 smart glasses prepaid; expected in stock on day 29.',
  '90 天营业结束':'90 days completed', '货架已经准备好':'Ready on the shelf', '库存偏低，留意缺货':'Low stock; watch for unfilled orders',
  '关灯 · 期末盘点完成':'Lights off · Final inventory valued',
  '小店正在营业…':'The shop is working…', '90 天经营完成':'90 days completed',
  '新订单来了':'New orders', '机器人打包中':'Robot packing', '快递发车':'Courier dispatch', '补货入库':'Receiving stock', '收工盘点':'Closing the ledger', '准备营业':'Ready to open',
  '先算算补多少合适。':'How much should we restock?', '热度有了，现金也要留住。':'Demand is growing. Keep some cash in reserve.',
  '快一点到货，少一点空货架。':'Faster deliveries, fewer empty shelves.', '包裹还在路上，别重复买。':'Stock is on its way. Don’t order it twice.', '试试新价格，再看订单。':'Try the new price and watch the orders.',
  '白天 · 开门接单':'Daytime · Taking orders', '叮！新订单来啦，开始忙起来。':'Ding! New orders. Time to get moving.',
  '货架取货，核对订单，再封好箱子。':'Pick from the shelves, check the order, seal the box.',
  '这一车，装着大家期待的小东西。':'A van full of little things people are waiting for.', '傍晚 · 装车发货':'Evening · Loading and dispatch',
  '今天没有可发的订单，机器人检查空货架。':'No orders can ship today. The robot checks the shelves.',
  '没有现货可发，记得安排补货。':'Nothing available to ship. Plan the next replenishment.',
  '打包台收拾好，明天继续。':'Tidy the packing desk. Tomorrow is another day.',
  '补货车来啦！清点数量，搬上货架。':'The supply van is here! Count the units and stock the shelves.',
  '次日清晨 · 补货到达':'Next morning · Supplies arrive',
  '今天没有到货，先看看剩下的库存。':'No deliveries today. Check what’s left on the shelves.',
  '90 天经营完成，期末库存估值已计入净资产。':'90 days completed. Ending inventory valuation is included in net worth.',
  '最后一箱发完啦，谢谢你陪我开店。':'The last box is on its way. Thanks for running the shop with me.',
  '新货都放好了，今天也要好好开店。':'Fresh stock is on the shelves. Let’s make it a good day.',
  '包裹都送走啦，再看看今天的新消息。':'Parcels are on their way. Let’s check today’s news.',
  '经营完成':'Business completed', '新一天 · 准备营业':'New day · Ready to open',
  '已发货 / 缺货订单':'Shipped / unfilled orders', '销售收入':'Sales revenue', '采购付款':'Procurement payment', '日常与仓储':'Operating and holding costs', '次日补货入库':'Next-morning stock received',
  '实验暂停与动画暂停各自独立':'Experiment pause and animation pause are independent',
  '回放使用历史记录，不改动当前小店':'Historical playback leaves the live store unchanged',
  '小店状态已保留，可以继续调查和营业。':'Your store is unchanged. Continue investigating or open for business.',
  '回到我们的小店，继续好好开店。':'Back to our little shop. Let’s keep it going.',
  '当前小店状态已保留':'Live store state preserved', '当前小店 · 手动经营':'Live store · Manual operation',
  '暂无完整记录':'No completed recordings', '暂无日期':'No recorded days',
  '还没有完整的经营记录':'No completed business records yet',
  '先让小店营业一天，或在研究台完成至少一个回合。':'Run a day in the shop or finish one research episode first.',
  '完整记录会出现在这里。':'Completed records will appear here.', '等待记录':'Waiting for a recording',
  '还没有完整记录，先让小店营业一天。':'No complete recording yet. Run a day in the shop first.',
  '等有了经营记录，就能回看这一天。':'Once a day is recorded, we can watch it again.',
  '当前小店 · 已完成的经营记录':'Live store · Completed business records',
  '期初现金 → 期末现金':'Opening → closing cash', '当日净资产变化':'Net worth change',
  '工具费 / 日常与仓储':'Tools / operating & holding costs', '销售收入 / 采购付款':'Revenue / procurement', '发货 / 缺货订单':'Shipped / unfilled orders', '次日入库':'Next-day stock received',
  '直接经营':'Proceed without tools', '这一天没有付费获取额外信息。':'No additional paid information was acquired that day.',
  '历史记录 · 只读回放':'Historical record · Read-only',
  '已载入原始记录：可查看当时信息，也可以播放当天动画。':'Original record loaded. Inspect the information or replay that day.',
  '那一天，我们是这样把生意做下去的。':'This is how we kept the shop running that day.',
  '历史回放':'Historical replay', '历史记录 · 回放完成':'Historical record · Playback complete',
  '这一段故事播放完了，当前小店没有变化。':'That chapter is complete. The live store has not changed.', '回放完成':'Replay complete',
  '不调查：不付费获取额外信息，直接按固定经营规则补货与定价。':'No-tools policy: buy no extra information; replenish and price using the fixed business rules.',
  '用满调查预算：按固定次序调用需求预测、市场调查，每天最多两次。':'Full-budget policy: call demand forecasting and market research in a fixed order, at most twice per day.',
  '固定规则：可见库存不足预计 1.5 天用量，调用需求预测和供应商分析。已有在途仍计入采购判断。':'Rule-based policy: visible stock covers less than 1.5 days of nominal demand, so query the forecast and supplier tools. Incoming stock still counts when purchasing.',
  '固定规则：昨天发货超过 18 单，查询一次市场调查。':'Rule-based policy: more than 18 orders shipped yesterday, so request market research once.',
  '固定规则：可见库存与昨天销量未触发调查阈值，直接经营。':'Rule-based policy: visible stock and yesterday’s sales do not trigger an investigation; proceed directly.',
  '由你选择调查工具，随后使用同一套补货与定价规则经营。':'You selected the information tools; the same replenishment and pricing rules then ran the shop.',
  '示范实验已完成':'Sample experiment complete', '示范对比已完成':'Sample comparison complete', '正在运行对比实验':'Running comparison',
  '实验已结束 · 保留完整回合':'Experiment stopped · Completed episodes retained', '对比实验已完成':'Comparison complete', '实验已暂停':'Experiment paused',
  '每回合独立经营 90 天；不播放仓库动画，经营规则保持一致。':'Each independent episode runs for 90 days, using the same business rules without warehouse animation.',
  '等待完成':'Waiting for a completed episode', '学习控制器':'Learning controller',
  '尚未接入 · 不生成模型成绩':'Not connected · No model scores generated',
  '完成回合的每日平均净资产':'Daily mean net worth across completed episodes',
  '三个信息获取方式的每日平均净资产，单位美元':'Daily mean net worth for three information policies, in US dollars',
  '净资产 ($)':'Net worth ($)', '经营天数':'Business days',
  '回放已结束，当前小店状态保持不变。':'Replay finished. The live store is unchanged.',
  '实验中止 · 已保留完整回合':'Experiment interrupted · Completed episodes retained',
  '动画已结束，当日经营结算已完成。':'Animation finished. The day has been settled.', '已暂停':'Paused', '继续播放':'Playing',
  '设置已更改。下方仍显示上一次结果，重新运行后更新。':'Settings changed. Results still show the previous run; run again to update them.',
  '线上商店的打包工作室':'Online-store packing workshop',
  '仓库小剧场：机器人拣货、打包、装车与补货入库':'Warehouse theatre: robot picking, packing, loading, and receiving stock',
  '经营事件和工具选择':'Business events and information tools',
  '实验完成进度':'Experiment completion',
  '先看看市场，再决定要不要调查。':'Check the market before buying more information.'
 }));
 // Ordered rules keep dynamic quantities, currency, and recorded messages intact.
 const rules=[
  [/^第 (\d+) 天 · 营业小票$/,(_,d)=>`Day ${d} · Business receipt`],
  [/^第 (\d+) 天 · (\d+) 单出发$/,(_,d,n)=>`Day ${d} · ${n} orders dispatched`],
  [/^第 (\d+) 天 · 回到那次经营现场$/,(_,d)=>`Day ${d} · Back at the warehouse`],
  [/^第 (\d+) 天 · (\d+) 单$/,(_,d,n)=>`Day ${d} · ${n} orders`],
  [/^第 (\d+) 天收到 (\d+) 单，其中 (\d+) 单有货可发。$/,(_,d,n,v)=>`Day ${d}: ${n} orders received; ${v} can ship from stock.`],
  [/^机器人准备拣货，共 (\d+) 单。$/,(_,n)=>`The robot is picking stock for ${n} orders.`],
  [/^(\d+) 单已封箱，等待快递装车。$/,(_,n)=>`${n} orders packed, ready for the courier.`],
  [/^(\d+) 单已装车 · 本日销售收入 (.+)$/,(_,n,v)=>`${n} orders loaded · Sales revenue ${v}`],
  [/^第 (\d+) 天收工：日常与仓储 (.+)，采购 (.+)。$/,(_,d,c,p)=>`Day ${d} closing: operating and holding ${c}; procurement ${p}.`],
  [/^第 (\d+) 天清晨：(\d+) 件补货到达，正在卸货入库。$/,(_,d,n)=>`Day ${d}, morning: ${n} units arrive for unloading and shelving.`],
  [/^(\d+) 件补货入库 · 新一天准备好了$/,(_,n)=>`${n} units received · Ready for a new day`],
  [/^第 (\d+) 天清晨：今天没有到期补货，库存按实际余量保留。$/,(_,d)=>`Day ${d}, morning: no supplies are due. Remaining stock carries forward.`],
  [/^第 (\d+) 天准备营业。昨天发出 (\d+) 单(?:，今早入库 (\d+) 件)?。$/,(_,d,n,a)=>`Day ${d} is ready. ${n} orders shipped yesterday${a?`; ${a} units arrived this morning`:''}.`],
  [/^(\d+) 件新货已上架 · 第 (\d+) 天，早上好！$/,(_,n,d)=>`${n} new units shelved · Good morning, day ${d}!`],
  [/^(\d+) 单已经出发 · 第 (\d+) 天，早上好！$/,(_,n,d)=>`${n} orders dispatched · Good morning, day ${d}!`],
  [/^第 (\d+) 天回放结束：发出 (\d+) 单，次日入库 (\d+) 件。$/,(_,d,n,a)=>`Day ${d} replay complete: ${n} orders shipped; ${a} units arrived the next morning.`],
  [/^第 (\d+) 天 · (.+)，花费 (.+)，等待 (\d+) 小时。$/,(_,d,t,c,h)=>`Day ${d} · ${english(t)}: ${c}, ${h} hour(s).`],
  [/^第 (\d+) 天 · 发货 (\d+) 单 \/ 收入 (.+)；采购 (\d+) 件 \/ (.+)。$/,(_,d,n,v,q,c)=>`Day ${d} · ${n} orders / revenue ${v}; purchased ${q} units / ${c}.`],
  [/^第 (\d+) 天 · (\d+) 件补货卸车，清点入库。$/,(_,d,n)=>`Day ${d} · ${n} replenishment units unloaded, counted, and shelved.`],
  [/^第 90 天 · 完成期末盘点，小店收工。$/,()=>`Day 90 · Ending inventory valued. The shop closes.`],
  [/^昨天发出 (\d+) 单，错失 (\d+) 单。今早 (\d+) 件补货已经上架。$/,(_,n,m,a)=>`${n} orders shipped yesterday; ${m} unfilled. ${a} units arrived this morning.`],
  [/^昨天发出 (\d+) 单，错失 (\d+) 单。补货仍按预计日期送达。$/,(_,n,m)=>`${n} orders shipped yesterday; ${m} unfilled. Supplies remain scheduled for their due dates.`],
  [/^期末剩余与在途库存折价 20%，估值减记 (.+)，不扣减现金。$/,(_,v)=>`Remaining and incoming inventory is discounted 20%: valuation reduced by ${v}, with no cash deduction.`],
  [/^小店净值较试玩开始变化 (.+)，期末剩余库存已折价 20%。$/,(_,v)=>`Net worth changed by ${v} since the preview began. Ending inventory is discounted 20%.`],
  [/^需求预测（Demand Forecast）：(.+) 预计日需求 (\d+) 件，预测含误差；补货目标将参考此数值。$/,(_,p,n)=>`Demand forecast: ${english(p)}, estimated ${n} units/day. This noisy forecast informs replenishment.`],
  [/^市场调查（Market Research）：(.+) 的调查需求估计为 (\d+) 件，热度不保证成交。$/,(_,p,n)=>`Market research: estimated demand for ${english(p)} is ${n} units. Interest does not guarantee sales.`],
  [/^供应商分析（Supplier Analysis）：今天新采购预计 1 天到货，货款照常支付。$/,()=>`Supplier analysis: new purchases today are expected to arrive in one day; goods still require payment.`],
  [/^库存分析（Inventory Analysis）：(.+) 现货最少；已有在途会计入补货判断。$/,(_,p)=>`Inventory analysis: ${english(p)} has the least stock. Incoming units count toward replenishment.`],
  [/^定价分析（Pricing Analysis）：建议今天将 (.+) 售价调到 (.+)。$/,(_,p,v)=>`Pricing analysis: suggested price for ${english(p)} today is ${v}.`],
  [/^当前结果：预测可靠度 (.+) \/ 100 · 市场波动 (.+)× · 工具费 (.+)× · 种子 (.+)$/,(_,a,v,c,seeds)=>`Results: forecast reliability ${a}/100 · volatility ${v}× · tool cost ${c}× · seeds ${seeds}`],
  [/^(.+) · 市场种子 (\d+) · 第 (\d+) \/ 90 天$/,(_,p,s,d)=>`${english(p)} · market seed ${s} · day ${d}/90`],
  [/^(.+) · 市场种子 (\d+)$/,(_,p,s)=>`${english(p)} · market seed ${s}`],
  [/^实验记录 · (.+)$/,(_,p)=>`Experiment record · ${english(p)}`],
  [/^(.+)：第 90 天均值 (.+)$/,(_,p,v)=>`${english(p)}: day 90 mean ${v}`],
  [/^(.+)：实际请求 (\d+) 件，发出 (\d+) 件，售价 (.+)。$/,(_,p,d,n,v)=>`${english(p)}: ${d} units requested; ${n} shipped; price ${v}.`],
  [/^(.+) · (.+) \/ (\d+) 小时$/,(_,p,v,h)=>`${english(p)} · ${v} / ${h} hour(s)`],
  [/^现货 (\d+) 件 · 在途 (\d+)$/,(_,n,a)=>`In stock ${n} · Incoming ${a}`],
  [/^现货$/,()=>`In stock`], [/^件 · 在途 (\d+)$/,(_,n)=>`units · Incoming ${n}`],
  [/^售价 (.+) · 成本 (.+)$/,(_,p,c)=>`Price ${p} · Cost ${c}`],
  [/^最近到货：第 (\d+) 天$/,(_,d)=>`Next delivery: day ${d}`],
  [/^库存 (\d+) 件$/,(_,n)=>`Stock: ${n} units`],
  [/^历史第 (\d+) 天$/,(_,d)=>`Recorded day ${d}`], [/^原记录 (\d+) 单$/,(_,n)=>`Recorded: ${n} orders`],
  [/^今日已发 (\d+)$/,(_,n)=>`Shipped: ${n}`], [/^打包 (\d+) \/ (\d+)$/,(_,a,n)=>`Pack ${a}/${n}`],
  [/^(\d+) 个完整回合$/,(_,n)=>`${n} completed episode(s)`],
  [/^(\d+) \/ (\d+) 回合$/,(_,n,t)=>`${n} / ${t} episodes`],
  [/^(\d+) \/ 2 次$/,(_,n)=>`${n} / 2 calls`],
  [/^(\d+) 单$/,(_,n)=>`${n} orders`], [/^(\d+) 件$/,(_,n)=>`${n} units`],
  [/^(.+) · (\d+) 小时$/,(_,v,h)=>`${v} · ${h} hour(s)`],
  [/^(.+) × (\d+)$/,(_,p,n)=>`${english(p)} × ${n}`]
 ];
 function english(value){
  if(catalog.has(value))return catalog.get(value);
  for(const [pattern,format] of rules){const match=value.match(pattern);if(match)return format(...match)}
  return value;
 }
 function transform(value){const trimmed=value.trim();if(!trimmed)return value;return language==='zh'?value:value.replace(trimmed,english(trimmed))}
 const observer=new MutationObserver(()=>{if(!scheduled){scheduled=true;queueMicrotask(()=>{scheduled=false;refresh()})}});
 const settings={subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['aria-label','title','alt','placeholder']};
 function refresh(){
  observer.disconnect();
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  let node;
  while((node=walker.nextNode())){
   if(node.parentElement?.closest('script,style,[data-language-toggle]'))continue;
   let record=originals.get(node);
   if(!record||node.nodeValue!==record.rendered)record={source:node.nodeValue};
   const rendered=transform(record.source);if(node.nodeValue!==rendered)node.nodeValue=rendered;
   record.rendered=rendered;originals.set(node,record);
  }
  for(const el of root.querySelectorAll('[aria-label],[title],[alt],[placeholder]')){
   if(el.hasAttribute('data-language-toggle'))continue;
   let records=attributeOriginals.get(el);if(!records){records={};attributeOriginals.set(el,records)}
   for(const key of settings.attributeFilter){if(!el.hasAttribute(key))continue;const value=el.getAttribute(key);let record=records[key];if(!record||value!==record.rendered)record={source:value};const rendered=transform(record.source);if(value!==rendered)el.setAttribute(key,rendered);record.rendered=rendered;records[key]=record;}
  }
  root.dataset.language=language;document.documentElement.lang=language==='en'?'en':'zh-CN';
  document.title=language==='en'?'Little Signal Shop':'小信号商店 · Little Signal Shop';
  const toggle=root.querySelector('[data-language-toggle]');
  if(toggle){toggle.textContent=language==='en'?'中文':'English';toggle.setAttribute('aria-label',language==='en'?'Switch interface to Chinese':'切换界面语言为英文');toggle.lang=language==='en'?'zh-CN':'en';}
  observer.observe(root,settings);
 }
 function setLanguage(next){language=next==='zh'?'zh':'en';refresh()}
 root.querySelector('[data-language-toggle]')?.addEventListener('click',()=>setLanguage(language==='en'?'zh':'en'));
 window.signalI18n=Object.freeze({getLanguage:()=>language,setLanguage,refresh});
 refresh();
})();
