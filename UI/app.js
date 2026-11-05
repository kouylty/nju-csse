/* 余闲 UI 第一版：本地页面与示例交互。直接以 file:// 打开即可。 */
const paths = {
  leaf:'M5 19C2 8 9 3 20 4c0 11-5 17-15 15Zm0 0L16 8',
  search:'m16 16 5 5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  laptop:'M4 4h16v12H4zM2 20h20l-2-4H4z',
  book:'M12 5C8 2 4 3 2 4v15c4-2 7-1 10 1 3-2 6-3 10-1V4c-4-2-7-1-10 1Zm0 0v15',
  home:'m3 10 9-8 9 8M5 8v13h14V8M9 21v-8h6v8',
  bag:'M5 7h14l2 14H3L5 7Zm3 0V5a4 4 0 0 1 8 0v2',
  spark:'m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7',
  arrow:'M4 12h16m-6-6 6 6-6 6',
  shield:'m12 2 8 3v6c0 5-5 9-8 11-3-2-8-6-8-11V5l8-3Zm-4 10 3 3 5-6',
  chat:'M21 11a9 9 0 0 1-9 9H3l2-5A9 9 0 1 1 21 11ZM8 10h8M8 14h5',
  plus:'M12 4v16M4 12h16',
  box:'m3 6 9-4 9 4v12l-9 4-9-4V6Zm0 0 9 4 9-4M12 10v12M7 4l10 4v5',
  clock:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 6v6l4 2',
  check:'m5 12 4 4L19 6',
  pin:'M19 9c0 6-7 13-7 13S5 15 5 9a7 7 0 0 1 14 0ZM14 9a2 2 0 1 1-4 0 2 2 0 0 1 4 0',
};
const icon = name => `<svg aria-hidden="true" viewBox="0 0 24 24"><path d="${paths[name] || paths.spark}"/></svg>`;
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const products = [
  {id:'headphones',name:'无线头戴式耳机 · 雾黑',brief:'九成新 / 配件齐全 / 同款两副',price:210,category:'数码电子',seller:'林间同学',initial:'林',stock:2,image:'headphones.jpg',desc:'毕业整理，转让平时在宿舍使用的头戴式耳机。声音清晰，佩戴舒适，耳罩和头梁状态良好。同款共两副，按单副出售。随附收纳袋与充电线，可邮寄，也可以在校内当面交付。'},
  {id:'camera',name:'入门数码相机 · 黑色',brief:'日常记录 / 功能正常 / 实拍展示',price:680,category:'数码电子',seller:'拾光',initial:'拾',stock:1,image:'camera.jpg',desc:'陪我记录过很多校园日常的相机，功能正常，适合摄影入门。包含相机、充电器和相机带。使用痕迹可在联系卖家时进一步了解。'},
  {id:'books',name:'周末阅读书单 · 四本一组',brief:'整组出售 / 书页完整 / 少量笔记',price:45,category:'书籍文具',seller:'慢慢读',initial:'慢',stock:1,image:'books.jpg',desc:'四本闲置读物打包转让，书页完整，部分页面有铅笔标注。希望找到同样喜欢阅读的同学。页面价格为整组价格。'},
  {id:'plant',name:'桌面小绿植 · 含陶瓷盆',brief:'好养护 / 含花盆 / 给桌面添点绿',price:28,category:'生活好物',seller:'小叶',initial:'叶',stock:1,image:'plant.jpg',desc:'桌面小绿植一盆，连同陶瓷花盆一起转让。适合放在有散射光的窗边，卖家会提供日常养护建议。'},
];
const state = {category:'全部好物',query:'',sort:'recommend',quantity:1,delivery:'post',rating:5};
function localTimestamp(date=new Date()) {
  const pad=n=>String(n).padStart(2,'0');
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function makeOrder(id,product,status,extra={}) {
  return {id,product,status,quantity:1,delivery:'post',recipient:'木衣',address:'南京市 · 仙林校区学生宿舍',phone:'138****2608',createdAt:'2026-10-28 14:20',paidAt:null,deliveredAt:null,completedAt:null,reviewed:false,rating:5,reviewText:'',caseReason:'',snapshot:{...products.find(p=>p.id===product)},...extra};
}
const orders = [
  makeOrder('YX202610280018','headphones','shipped',{paidAt:'2026-10-28 14:23',deliveredAt:'2026-10-28 16:30'}),
  makeOrder('YX202610270012','books','completed',{createdAt:'2026-10-27 10:00',paidAt:'2026-10-27 10:02',deliveredAt:'2026-10-28 09:00',completedAt:'2026-10-28 18:30'}),
  makeOrder('YX202610290019','camera','unpaid',{createdAt:localTimestamp()}),
];
let order = orders[0];
let nextOrderNumber=20;
const app = document.querySelector('#app'), dialog = document.querySelector('#dialog');
const route = () => new URLSearchParams(location.hash.slice(1));
const currentProduct = () => products.find(p => p.id === route().get('id')) || products[0];
const price = n => `<span class="price"><i>¥</i>${n}</span>`;
const tag = (text, warm=false) => `<span class="tag${warm?' warm':''}">${text}</span>`;
const avatar = (name, large=false) => `<span class="avatar${large?' large':''}">${esc(name)}</span>`;
const footer = () => `<footer><span>余闲 YUXIAN · 让每一件好物，都有新的故事。</span><span>校园好物流转，让生活轻一点。</span></footer>`;
function header(active='home') {
  return `<header class="header"><div class="shell header-inner"><a class="brand" href="#page=home" aria-label="余闲首页"><div class="brand-name">余闲</div></a>
  <nav class="nav" aria-label="主导航"><a class="${active==='home'?'active':''}" href="#page=home">逛逛好物</a><a class="${active==='order'?'active':''}" href="#page=order">我的购买</a><a class="${active==='sell'?'active':''}" href="#page=sell">我的出售</a><a class="${active==='chat'?'active':''}" href="#page=chat">聊天</a></nav>
  <div class="header-tools"><button class="button" data-action="publish">${icon('plus')} 发布闲置</button><button class="account" data-action="account">${avatar('木')}<span>木衣</span></button></div></div></header>`;
}
const categories = [['全部好物','grid'],['数码电子','laptop'],['书籍文具','book'],['生活好物','home'],['服饰配件','bag'],['虚拟商品','spark'],['技能服务','spark']];
function home() {
  app.innerHTML = header()+`<main class="shell home-layout"><aside class="sidebar"><p class="side-title">商品分类</p>${categories.map(([n])=>`<button class="side-item ${state.category===n?'active':''}" data-category="${n}"><span class="menu-chevron" aria-hidden="true">&gt;</span>${n}</button>`).join('')}
  <div class="divider"></div><p class="side-title">我的余闲</p><a class="side-item" href="#page=order"><span class="menu-chevron" aria-hidden="true">&gt;</span>我买到的</a><button class="side-item" data-action="sell"><span class="menu-chevron" aria-hidden="true">&gt;</span>我发布的</button></aside>
  <section class="home-content">
  <div class="reassurance"><span>${icon('shield')}商品审核后发布</span><span>${icon('chat')}站内沟通，轻松交流</span><span>${icon('box')}确认完成后结算</span></div>
  <div class="section-head row between"><h2>发现好物</h2><span id="result-count" class="muted tiny"></span></div>
  <label class="searchbox product-search">${icon('search')}<input id="search" type="search" placeholder="搜索商品名称或描述" aria-label="搜索商品" value="${esc(state.query)}"></label>
  <div class="filters"><button class="chip active" data-category="全部好物">全部</button><button class="chip" data-category="数码电子">数码</button><button class="chip" data-category="书籍文具">书籍</button><button class="chip" data-category="生活好物">生活</button><button class="chip" data-category="虚拟商品">虚拟商品</button><select id="sort" aria-label="商品排序"><option value="recommend">推荐排序</option><option value="low">价格从低到高</option><option value="high">价格从高到低</option></select></div>
  <div class="grid" id="products"></div></section></main>${footer()}`;
  document.querySelector('#sort').value = state.sort;
  renderProducts();
}
function renderProducts() {
  let list=products.filter(p=>(state.category==='全部好物'||p.category===state.category)&&`${p.name}${p.brief}${p.desc}`.includes(state.query));
  if(state.sort!=='recommend') list.sort((a,b)=>state.sort==='low'?a.price-b.price:b.price-a.price);
  document.querySelector('#result-count').textContent=`共 ${list.length} 件商品`;
  document.querySelectorAll('[data-category]').forEach(el=>el.classList.toggle('active',el.dataset.category===state.category));
  document.querySelector('#products').innerHTML=list.length?list.map(p=>`<a class="card product-card" href="#page=product&id=${p.id}"><div class="product-photo"><img src="assets/${p.image}" alt="${p.name}">${tag(p.category)}</div><div class="product-info"><h3>${p.name}</h3><p>${p.brief}</p><div class="row between">${price(p.price)}<small class="tiny">在售 · ${p.stock} 件</small></div><div class="seller-mini row between"><span class="row" style="gap:6px">${avatar(p.initial)}${p.seller}</span><span>刚刚上新</span></div></div></a>`).join(''):`<div class="empty card">暂时没有匹配的好物。<br><button class="link" data-action="clear-search">查看全部商品 →</button></div>`;
}
function product() {
  const p=currentProduct();state.quantity=1;state.delivery='post';
  app.innerHTML=header()+`<main class="shell"><div class="breadcrumb"><a href="#page=home">逛逛好物</a><span>/</span><span>${p.category}</span><span>/</span><span>商品详情</span></div><div class="detail-layout"><section><div class="gallery-main"><img id="main-photo" src="assets/${p.image}" alt="${p.name}">${tag('实物展示')}<span class="image-count">01 / 01</span></div><div class="thumbs"><button class="active" aria-label="商品主图"><img src="assets/${p.image}" alt="商品缩略图"></button><span class="thumb-hint">好物的细节，值得慢慢看。</span></div></section>
  <section class="product-detail"><div class="row between seller-top"><div class="row">${avatar(p.initial,true)}<div><div class="seller-name">${p.seller}</div><p>用心生活，认真分享闲置。</p></div></div><button class="link tiny" data-action="chat">联系卖家 →</button></div><div class="row">${tag('审核通过')}${tag('物品',true)}</div><h1>${p.name}</h1><p class="product-subtitle">${p.brief}</p><div class="price-box"><div>${price(p.price)}<small> / 件</small></div></div>
  <div class="spec-row"><span>交付方式</span><button class="choice active" data-delivery="post">邮寄 · ¥6 / 单</button><button class="choice" data-delivery="meet">当面交付 · 免邮费</button></div><div class="spec-row"><span>购买数量</span><div class="stepper"><button data-qty="-1" aria-label="减少数量">−</button><input id="quantity" type="number" min="1" max="${p.stock}" value="1" aria-label="购买数量"><button data-qty="1" aria-label="增加数量">＋</button></div><small>可售 ${p.stock} 件</small></div><div class="spec-row"><span>合计</span><strong id="product-total">¥${p.price+6}.00</strong><small id="shipping-hint">含本单邮费 ¥6</small></div>
  <div class="buy-actions"><button class="button" data-action="checkout">立即购买 ${icon('arrow')}</button><button class="button secondary" data-action="chat">${icon('chat')}聊一聊</button></div><p class="purchase-note">${icon('shield')}交易款先由平台暂存，确认完成后结算给卖家</p></section></div>
  <div class="detail-bottom"><section class="card description"><div class="row between"><h3>关于这件好物</h3><button class="muted tiny" data-action="report">举报商品</button></div><p>${p.desc}</p></section><section class="card description"><div class="row between"><h3>这件商品的评价</h3><span class="muted tiny">暂无评价</span></div><div class="review"><p>还没有买家留下评价。<br>完成交易后，你也可以分享自己的使用感受。</p></div></section></div></main>${footer()}`;
}
const configs={
  unpaid:{title:'待付款',description:'请在 15 分钟内完成虚拟付款，付款后卖家将安排交付。',step:0,icon:'clock',action:'pay',button:'确认虚拟付款',times:['刚刚创建','等待付款','等待交付','等待确认']},
  paid:{title:'付款成功，等待卖家交付',description:'交易款已由平台暂存，你可以联系卖家沟通交付安排。',step:1,icon:'box',action:'chat',button:'联系卖家',times:['10-28 14:20','10-28 14:23','等待交付','等待确认']},
  shipped:{title:'待收货',description:'卖家已发货，请收到商品并检查后确认收货。',step:2,icon:'box',action:'confirm',button:'确认收货',times:['10-28 14:20','10-28 14:23','10-28 16:30','等待确认']},
  completed:{title:'已完成',description:'¥{total} 已虚拟结算给卖家，分享你的交易体验吧。',step:3,icon:'check',action:'review',button:'评价这次交易',times:['10-28 14:20','10-28 14:23','10-28 16:30','已确认完成']},
  dispute:{title:'客服正在处理，进度会及时告诉你',description:'自动确认与结算已暂停，可在处理记录中查看最新进度。',step:2,icon:'chat',action:'case',button:'查看处理记录',times:['10-28 14:20','10-28 14:23','10-28 16:30','客服处理中']},
  cancelled:{title:'订单已关闭',description:'本次订单占用的库存已释放，喜欢的好物可以重新购买。',step:0,icon:'clock',action:'back-product',button:'再看看这件商品',times:['订单已创建','付款前取消','—','—']},
  cancelling:{title:'取消申请已提交，等待卖家回应',description:'协商期间暂停履约与结算，对方同意后将全额虚拟退款。',step:1,icon:'chat',action:'withdraw',button:'撤回取消申请',times:['10-28 14:20','10-28 14:23','取消协商中','等待回应']},
};
function purchaseListPage(){
  app.innerHTML=header('order')+`<main class="shell workspace"><div class="purchase-heading row between"><h1>我的购买</h1><span class="muted tiny">共 ${orders.length} 笔订单</span></div><section class="purchase-list" aria-label="购买订单列表">${orders.length?orders.map(item=>`<a class="card purchase-item" href="#page=order&id=${item.id}" aria-label="查看订单 ${item.id}"><div class="purchase-item-meta"><span>订单号：${item.id}</span><time>${item.createdAt}</time></div><div class="purchase-item-content"><img src="assets/${item.snapshot.image}" alt="${esc(item.snapshot.name)}"><div class="purchase-item-info"><h2>${esc(item.snapshot.name)}</h2><p>卖家：${esc(item.snapshot.seller)} · 数量：${item.quantity}</p></div><span class="purchase-item-link">查看详情 ${icon('arrow')}</span></div></a>`).join(''):'<div class="card selling-empty"><h2>当前暂无购买订单</h2><a class="button" href="#page=home">浏览商品</a></div>'}</section></main>${footer()}`;
}
function createPurchase(data){
  const product=currentProduct();
  order=makeOrder(`YX${localTimestamp().slice(0,10).replaceAll('-','')}${String(nextOrderNumber++).padStart(6,'0')}`,product.id,'unpaid',{quantity:state.quantity,delivery:state.delivery,recipient:data.get('recipient')||'木衣',phone:data.get('phone')||'',address:data.get('address')||'',createdAt:localTimestamp()});
  orders.unshift(order);go('order',`&id=${order.id}`);dialog.close();
}
function orderPage(){
  const id=route().get('id');
  const selected=id?orders.find(item=>item.id===id):orders[0];
  if(!selected){purchaseListPage();return;}
  order=selected;
  const explicit=route().get('state');
  if(configs[explicit]&&order.status!==explicit){
    order.status=explicit;
    order.paidAt=['unpaid','cancelled'].includes(explicit)?null:(order.paidAt||order.createdAt);
    order.deliveredAt=['shipped','completed','dispute'].includes(explicit)?(order.deliveredAt||order.createdAt):null;
    order.completedAt=explicit==='completed'?(order.completedAt||localTimestamp()):null;
  }
  const c=configs[order.status]||configs.shipped,p=order.snapshot,shipping=order.delivery==='post'?6:0,total=p.price*order.quantity+shipping;
  const afterDelivery=Boolean(order.deliveredAt);
  const times=[order.createdAt,order.paidAt||'等待付款',order.deliveredAt||'等待交付',order.completedAt||'等待确认'];
  const autoConfirmAt=order.deliveredAt?localTimestamp(new Date(new Date(order.deliveredAt.replace(' ','T')).getTime()+7*86400000)):'';
  const description=order.status==='shipped'&&order.delivery==='meet'?'卖家已标记当面交付，请检查商品后确认收货。':c.description.replace('{total}',total.toFixed(2));
  app.innerHTML=header('order')+`<main class="shell"><div class="breadcrumb"><a href="#page=home">余闲首页</a><span>/</span><a href="#page=order">我的购买</a><span>/</span><span>订单详情</span></div><div class="order-heading row between"><div><h1>订单详情</h1><p>订单编号 ${order.id} · 下单时的商品信息与金额已保存</p></div>${tag('虚拟支付交易')}</div><div class="order-layout"><section><div class="status-card ${['dispute','cancelling','cancelled'].includes(order.status)?'status-warning':''}"><div class="row"><span class="status-icon">${icon(c.icon)}</span><p class="order-status-text">${description}</p></div><div class="progress">${['提交订单','虚拟付款','卖家交付','确认完成'].map((s,i)=>`<div class="progress-step ${i<=c.step?'done':''}"><span class="number">${i<c.step?'✓':i+1}</span>${s}<small>${times[i]}</small></div>`).join('')}</div></div>
  <section class="card section-card"><div class="section-label"><h3>商品信息</h3><span class="tiny muted">下单时的信息快照</span></div><div class="order-product"><img src="assets/${p.image}" alt="${p.name}"><div><h3>${p.name}</h3><p>${p.brief}</p><p>交付方式：${order.delivery==='post'?'邮寄':'当面交付'} · 数量：${order.quantity}</p></div><div class="amount"><strong>¥${p.price}.00</strong><p>× ${order.quantity}</p></div></div><div class="meta-grid"><div><span>卖家</span>${p.seller}</div><div><span>订单创建</span>${order.createdAt}</div><div><span>交付方式</span>${order.delivery==='post'?'快递邮寄':'站内约定地点'}</div><div><span>付款方式</span>平台虚拟支付</div></div></section>
  <section class="card section-card"><div class="section-label"><h3>${afterDelivery?'交付信息':'交付安排'}</h3>${tag(order.status==='dispute'?'客服处理中':afterDelivery?'卖家已交付':'等待交付',order.status==='dispute')}</div>${order.delivery==='post'?`<div class="logistics-row">${icon('pin')}<div><p>${esc(order.recipient)}　${esc(order.phone)}</p><small>${esc(order.address)}</small></div></div>`:`<div class="logistics-row">${icon('pin')}<div><p>校内当面交付</p><small>具体地点与时间请通过站内聊天约定。</small></div></div>`}${afterDelivery?`<div class="timeline"><div>${order.delivery==='post'?'卖家已填写发货信息':'卖家已标记当面交付'}<small>${order.deliveredAt}${order.delivery==='post'?` · 快递公司：示例快递 · 单号：DEMO${order.id.slice(2)}`:''}</small></div><div>交易款由平台暂存<small>${order.paidAt} · 虚拟付款成功</small></div></div><p class="tiny muted">${order.status==='shipped'?`自动确认时间：${autoConfirmAt}。收货有问题可申请客服。`:order.status==='dispute'?'本单自动确认已暂停，后续按客服处理结果执行。':'交易已完成，交付记录持续保留。'}</p>`:`<p class="tiny muted">${order.status==='unpaid'?'虚拟付款成功后，卖家即可安排交付。':'可通过站内聊天与卖家沟通交付时间。'}</p>`}</section></section>
  <aside><section class="card summary"><h3>订单金额</h3><div class="money-row"><span>商品金额</span><span>¥${(p.price*order.quantity).toFixed(2)}</span></div><div class="money-row"><span>邮费（按单收取）</span><span>¥${shipping.toFixed(2)}</span></div><div class="money-row total"><span>订单总额</span>${price(total.toFixed(2))}</div><p class="tiny muted">${icon('shield')} ${order.status==='completed'?'交易已完成，模拟到账已记录。':'虚拟交易款暂存平台，确认完成后结算给卖家。'}</p><button class="button" data-action="${c.action}">${order.status==='completed'&&order.reviewed?'查看我的评价':c.button}</button>${['unpaid','paid'].includes(order.status)?'<button class="button secondary" data-action="cancel">取消订单</button>':'<button class="button secondary" data-action="chat">联系卖家</button>'}${order.status==='shipped'?'<p class="tiny muted">确认前，请核对收到的商品与订单约定。</p>':''}</section><section class="help-card"><h3>交易遇到问题？</h3><p>沟通解决疑问，客服协助处理争议。</p><button class="link" data-action="support">申请客服介入 →</button></section></aside></div></main>${footer()}`;
}
function go(page,extra=''){location.hash=`page=${page}${extra}`;}
function render(){dialog.close();const page=route().get('page')||'home';if(page==='product')product();else if(page==='order'){if(route().has('id')||route().has('state'))orderPage();else purchaseListPage();}else if(page==='sell')sellerPage();else if(page==='chat')chatPage();else home();window.scrollTo(0,0);}
function toast(message){const el=document.querySelector('#toast');el.textContent=message;el.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('show'),2800);}
function modal(title,body){document.querySelector('#dialog-body').innerHTML=`<div class="modal"><div class="modal-head"><h2>${title}</h2><button class="close" data-action="close" aria-label="关闭弹窗">×</button></div>${body}</div>`;if(!dialog.open)dialog.showModal();}
function updateQuantity(value){const p=currentProduct();state.quantity=Math.max(1,Math.min(p.stock,Math.floor(Number(value)||1)));document.querySelector('#quantity').value=state.quantity;document.querySelector('#product-total').textContent=`¥${(p.price*state.quantity+(state.delivery==='post'?6:0)).toFixed(2)}`;document.querySelector('#shipping-hint').textContent=state.delivery==='post'?'含本单邮费 ¥6':'当面交付，邮费 ¥0';}
function changeStatus(status){order.status=status;if(status==='paid'&&!order.paidAt)order.paidAt=localTimestamp();if(status==='completed')order.completedAt=localTimestamp();location.hash=`page=order&id=${order.id}`;orderPage();dialog.close();}
function checkout(){const p=currentProduct(),shipping=state.delivery==='post'?6:0;modal('确认这份喜欢',`<div class="order-product"><img src="assets/${p.image}" alt="${p.name}"><div><h3>${p.name}</h3><p>¥${p.price} × ${state.quantity} · ${state.delivery==='post'?'邮寄':'当面交付'}</p></div></div><form id="checkout-form">${state.delivery==='post'?'<label for="recipient">收件人</label><input id="recipient" name="recipient" required placeholder="请输入收件人姓名"><label for="phone">联系电话</label><input id="phone" name="phone" required type="tel" pattern="1[0-9]{10}" placeholder="请输入 11 位手机号"><label for="address">收货地址</label><input id="address" name="address" required placeholder="校区、楼栋与详细地址">':'<p class="muted tiny" style="margin-top:20px">下单后可通过站内聊天约定交付地点与时间。</p>'}<div class="money-row"><span>商品金额</span><span>¥${p.price*state.quantity}.00</span></div><div class="money-row"><span>本单邮费</span><span>¥${shipping}.00</span></div><div class="money-row total"><span>应付合计</span>${price(p.price*state.quantity+shipping)}</div><button class="button wide" type="submit">提交订单，前往付款 ${icon('arrow')}</button><p class="tiny muted" style="margin-top:12px">下单后为你保留库存 15 分钟，请及时完成虚拟付款。</p></form>`);}
function chat(){openProductChat();}
const actions={
  close:()=>dialog.close(),
  'clear-search':()=>{state.category='全部好物';state.query='';home();},checkout,chat,
  account:()=>modal('我的余闲',`<div class="row">${avatar('木',true)}<div><h3>木衣</h3><p class="muted tiny">把闲置分享给需要的人。</p></div></div><div class="divider"></div><a class="button wide" href="#page=order" data-action="close">查看我的购买</a><button class="button secondary wide" data-action="sell">查看我的出售</button>`),
  sell:()=>{dialog.close();go('sell');},
  publish:()=>{dialog.close();go('sell','&tab=publish');},
  pay:()=>modal('确认虚拟付款',`<p class="muted">本次金额为 ¥${((order.snapshot.price*order.quantity)+(order.delivery==='post'?6:0)).toFixed(2)}。付款后记录为平台暂存款，确认完成后结算给卖家。</p><button class="button wide" data-action="paid">确认虚拟付款</button>`),paid:()=>{changeStatus('paid');toast('虚拟付款成功，等待卖家交付');},
  confirm:()=>modal('确认已经收到好物？','<p class="muted">请确认商品与约定一致。完成后，平台暂存的虚拟交易款将结算给卖家。</p><button class="button wide" data-action="completed">确认收货并完成交易</button><button class="button secondary wide" data-action="close">再检查一下</button>'),completed:()=>{changeStatus('completed');toast('交易完成，虚拟结算已记录');},
  cancel:()=>modal(order.status==='unpaid'?'取消这笔订单？':'与卖家协商取消',`<p class="muted">${order.status==='unpaid'?'取消后将释放这笔订单占用的库存。':'卖家同意后，全额虚拟退款并关闭订单。'}</p><form id="cancel-form"><label for="cancel-reason">取消原因</label><textarea id="cancel-reason" name="reason" required placeholder="请填写取消原因"></textarea><button class="button wide" type="submit">${order.status==='unpaid'?'确认取消':'提交取消申请'}</button></form>`),
  withdraw:()=>{changeStatus('paid');toast('已撤回取消申请，恢复等待交付');},
  support:()=>modal('申请客服介入','<form id="support-form"><p class="tiny muted">请描述具体情况，客服将结合订单记录协助处理。</p><label for="support-reason">问题描述</label><textarea id="support-reason" name="reason" required placeholder="例如：收到的商品与描述有差异…"></textarea><button class="button wide" type="submit">提交申请</button></form>'),
  case:()=>modal('纠纷处理记录',`<span class="tag warm">处理中</span><div class="timeline"><div>客服已受理，正在联系双方<small>处理进度将记录在此处</small></div><div>已提交客服申请<small>${esc(order.caseReason||'商品情况需要进一步沟通')}</small></div></div><p class="tiny muted">自动确认与结算已暂停。后续按双方协商和客服处理结果执行。</p>`),
  report:()=>modal('举报这件商品','<form id="report-form"><label for="report-reason">举报原因</label><textarea id="report-reason" name="reason" required placeholder="请描述具体问题，便于管理员核查"></textarea><button class="button wide" type="submit">提交举报</button></form>'),
  review:()=>{state.rating=5;return order.reviewed?modal('我的交易评价',`<p class="stars">${'★'.repeat(order.rating)}</p><p style="margin-top:16px">${esc(order.reviewText)}</p>`):modal('分享你的交易体验',`<form id="review-form"><label>本次评分</label><div class="review-stars">${[1,2,3,4,5].map(n=>`<button class="on" type="button" data-rating="${n}" aria-label="${n} 星">★</button>`).join('')}</div><label for="review-text">评价内容</label><textarea id="review-text" name="review" required placeholder="聊聊商品和交易过程吧…"></textarea><button class="button wide" type="submit">提交评价</button></form>`);},
  'back-product':()=>go('product',`&id=${order.product}`),
};
document.addEventListener('click',e=>{const btn=e.target.closest('[data-action],[data-category],[data-qty],[data-delivery],[data-rating]');if(!btn)return;if(btn.dataset.action)actions[btn.dataset.action]?.();if(btn.dataset.category){state.category=btn.dataset.category;renderProducts();}if(btn.dataset.qty)updateQuantity(state.quantity+Number(btn.dataset.qty));if(btn.dataset.delivery){state.delivery=btn.dataset.delivery;document.querySelectorAll('[data-delivery]').forEach(el=>el.classList.toggle('active',el.dataset.delivery===state.delivery));updateQuantity(state.quantity);}if(btn.dataset.rating){state.rating=Number(btn.dataset.rating);document.querySelectorAll('[data-rating]').forEach(el=>el.classList.toggle('on',Number(el.dataset.rating)<=state.rating));}});
document.addEventListener('input',e=>{if(e.target.id==='search'){state.query=e.target.value;renderProducts();}});
document.addEventListener('change',e=>{if(e.target.id==='sort'){state.sort=e.target.value;renderProducts();}if(e.target.id==='quantity')updateQuantity(e.target.value);});
document.addEventListener('submit',e=>{e.preventDefault();const data=new FormData(e.target);switch(e.target.id){
  case 'checkout-form':createPurchase(data);break;
  case 'conversation-form':sendConversationMessage(e.target);break;
  case 'cancel-form':changeStatus(order.status==='unpaid'?'cancelled':'cancelling');break;
  case 'support-form':order.caseReason=data.get('reason');changeStatus('dispute');break;
  case 'report-form':modal('举报已记录','<p class="muted">管理员将核查你提交的情况，商品按当前状态继续展示。</p><button class="button wide" data-action="close">知道了</button>');break;
  case 'review-form':order.reviewed=true;order.rating=state.rating;order.reviewText=data.get('review');dialog.close();orderPage();toast('评价已保存');break;
  case 'publish-form':saveProduct(e.target,e.submitter?.value||'review');break;
}});
dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
window.addEventListener('hashchange',render);
render();
