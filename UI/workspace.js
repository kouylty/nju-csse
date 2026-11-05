/* 出售工作区与独立聊天页；数据保存在本次原型会话中。 */
const newProductDraft = () => ({id:null,name:'',price:'',tags:'',category:'数码电子',type:'物品',stock:1,shipping:'free',postage:'',description:'',images:[]});
const selling = {draft:newProductDraft(),items:[],nextId:1};
const conversations = [
  {id:'seller-headphones',name:'林间同学',initial:'林',role:'卖家',product:'headphones',topic:'无线头戴式耳机 · 雾黑',draft:'',messages:[{mine:false,text:'你好，耳机还在。配件齐全，可以邮寄，也可以当面交付。',time:'14:10'}]},
  {id:'seller-camera',name:'拾光',initial:'拾',role:'卖家',product:'camera',topic:'入门数码相机 · 黑色',draft:'',messages:[{mine:false,text:'相机包含充电器和相机带。你想了解哪一部分的使用情况？',time:'昨天'}]},
  {id:'buyer-zhou',name:'周同学',initial:'周',role:'买家',topic:'历史交易 · 桌面台灯',draft:'',messages:[{mine:true,text:'台灯已经寄出了，发货信息在订单里可以查看。',time:'昨天'},{mine:false,text:'已经收到了，谢谢！',time:'09:20'}]},
  {id:'support',name:'余闲客服',initial:'客',role:'管理员 / 客服',topic:'交易问题与平台协助',draft:'',messages:[{mine:false,text:'你好，请描述遇到的问题。涉及订单时，可以一并提供订单编号。',time:'09:00'}]},
];
let contactFilter='全部';
let currentContact='seller-headphones';

function sellerPage(){
  const tabs=[['selling','出售中的商品'],['publish','发布商品'],['drafts','草稿'],['pending','待审核']];
  const requested=route().get('tab')||'selling';
  const tab=tabs.some(([key])=>key===requested)?requested:'selling';
  app.innerHTML=header('sell')+`<main class="shell workspace"><h1>我的出售</h1><nav class="workspace-tabs" aria-label="出售工作区">${tabs.map(([key,label])=>`<a class="${key===tab?'active':''}" href="#page=sell&tab=${key}" ${key===tab?'aria-current="page"':''}>${label}${['drafts','pending'].includes(key)?`<span class="tab-count">${selling.items.filter(p=>p.status===key).length}</span>`:''}</a>`).join('')}</nav>${tab==='publish'?publishForm():sellerList(tab)}</main>${footer()}`;
  if(tab==='publish'){updateShippingFields();renderImagePreviews();}
}
function sellerList(tab){
  const items=selling.items.filter(p=>p.status===tab);
  if(!items.length){
    const message={selling:'当前暂无商品正在出售',drafts:'当前暂无商品草稿',pending:'当前暂无待审核商品'}[tab];
    return `<section class="card selling-empty"><span class="empty-symbol">${icon('box')}</span><h2>${message}</h2><a class="button" href="#page=sell&tab=publish">${icon('plus')}发布商品</a></section>`;
  }
  return `<section class="seller-list">${items.map(p=>`<article class="card seller-item">${p.images[0]?`<img class="seller-cover" src="${esc(p.images[0].url)}" alt="${esc(p.name||'商品图片')}">`:`<span class="seller-cover placeholder">${icon('box')}</span>`}<div class="seller-item-body"><div class="row wrap"><h3>${esc(p.name||'未命名商品')}</h3>${tag(tab==='pending'?'待审核':'草稿',tab==='pending')}</div><p class="muted tiny">${esc(p.category)} · ${esc(p.type)} · 库存 ${esc(p.stock||0)}</p><p class="seller-tags">${p.tags.split(/[,，]/).map(t=>t.trim()).filter(Boolean).map(t=>tag(esc(t))).join(' ')}</p><p>${p.price?price(Number(p.price).toFixed(2)):'尚未填写价格'}</p></div>${tab==='drafts'?`<button class="button secondary" data-edit-draft="${p.id}">继续编辑</button>`:'<span class="muted tiny">审核通过后展示在出售列表</span>'}</article>`).join('')}</section>`;
}
function publishForm(){
  const d=selling.draft;
  return `<form id="publish-form" class="card publish-form"><div class="form-heading"><h2>商品信息</h2><p class="muted tiny">填写商品情况，提交审核后发布。</p></div>
  <div class="form-field"><label for="listing-name">商品名称 <span>*</span></label><input id="listing-name" name="name" maxlength="60" required value="${esc(d.name)}" placeholder="例如：九成新无线耳机，配件齐全"></div>
  <div class="form-columns"><div class="form-field"><label for="listing-price">价格（元） <span>*</span></label><input id="listing-price" name="price" type="number" min="0.01" step="0.01" required value="${esc(d.price)}" placeholder="0.00"></div><div class="form-field"><label for="listing-stock">库存数量 <span>*</span></label><input id="listing-stock" name="stock" type="number" min="1" step="1" required value="${esc(d.stock)}"></div></div>
  <div class="form-columns"><div class="form-field"><label for="listing-category">分类</label><select id="listing-category" name="category">${['数码电子','书籍文具','生活好物','服饰配件','虚拟商品','技能服务'].map(c=>`<option ${d.category===c?'selected':''}>${c}</option>`).join('')}</select></div><div class="form-field"><label for="listing-type">商品类型</label><select id="listing-type" name="type"><option ${d.type==='物品'?'selected':''}>物品</option><option ${d.type==='服务'?'selected':''}>服务</option></select></div></div>
  <div class="form-field"><label for="listing-tags">标签</label><input id="listing-tags" name="tags" maxlength="100" value="${esc(d.tags)}" placeholder="例如：九成新、配件齐全；多个标签用逗号分隔"><p class="field-hint">填写成色、特点等信息，便于买家了解商品。</p></div>
  <fieldset class="shipping-field"><legend>运费与交付</legend><div class="shipping-options">${[['free','邮寄 · 包邮'],['paid','邮寄 · 不包邮'],['meet','仅当面交付']].map(([v,label])=>`<label><input type="radio" name="shipping" value="${v}" ${d.shipping===v?'checked':''}>${label}</label>`).join('')}</div><div id="postage-field" class="form-field postage-field"><label for="listing-postage">每单运费（元） <span>*</span></label><input id="listing-postage" name="postage" type="number" min="0.01" step="0.01" value="${esc(d.postage)}" placeholder="例如：6.00"></div><p id="shipping-description" class="field-hint"></p></fieldset>
  <div class="form-field"><label for="listing-images">商品图片 <span>*</span></label><div class="image-upload"><input id="listing-images" type="file" accept="image/jpeg,image/png,image/webp" multiple><span class="muted tiny">支持 JPG、PNG、WebP，可选择多张图片。</span></div><div id="image-previews" class="image-previews"></div></div>
  <div class="form-field"><label for="listing-description">商品描述 <span>*</span></label><textarea id="listing-description" name="description" required rows="5" maxlength="3000" placeholder="描述使用情况、配件、瑕疵和交付说明">${esc(d.description)}</textarea></div>
  <div class="form-actions"><button class="button secondary" type="submit" name="intent" value="draft" formnovalidate>保存草稿</button><button class="button" type="submit" name="intent" value="review">提交审核</button></div></form>`;
}
function captureProductDraft(form){
  const data=new FormData(form);
  for(const key of ['name','price','tags','category','type','stock','postage','description'])if(data.has(key))selling.draft[key]=String(data.get(key));
  if(data.has('shipping'))selling.draft.shipping=data.get('shipping');
}
function updateShippingFields(){
  const form=document.querySelector('#publish-form');if(!form)return;
  const service=selling.draft.type==='服务',paid=!service&&selling.draft.shipping==='paid';
  form.querySelectorAll('[name="shipping"]').forEach(el=>{el.disabled=service;});
  const postage=form.querySelector('#listing-postage');postage.disabled=!paid;postage.required=paid;
  form.querySelector('#postage-field').hidden=!paid;
  form.querySelector('#shipping-description').textContent=service?'服务无需运费，可通过站内聊天约定履约时间。':selling.draft.shipping==='meet'?'运费为 0 元，通过站内聊天约定交付地点。':paid?'运费按订单收取一次，多件同款合并计费。':'买家运费为 0 元。';
}
function renderImagePreviews(){
  const target=document.querySelector('#image-previews');if(!target)return;
  target.innerHTML=selling.draft.images.map((img,i)=>`<figure><img src="${esc(img.url)}" alt="商品图片 ${i+1}"><figcaption>${i===0?'封面图':`图片 ${i+1}`}</figcaption><button type="button" data-remove-image="${i}" aria-label="移除图片 ${i+1}">×</button></figure>`).join('');
}
function saveProduct(form,intent){
  captureProductDraft(form);const draft=selling.draft;
  if(intent!=='draft'){
    if(!form.reportValidity())return;
    if(!draft.name.trim()||!draft.description.trim()){toast('请填写商品名称和描述');return;}
    if(!draft.images.length){toast('请至少添加一张商品图片');document.querySelector('#listing-images').focus();return;}
  }
  const id=draft.id||selling.nextId++;
  const item={...draft,id,images:[...draft.images],status:intent==='draft'?'drafts':'pending',postage:draft.type==='服务'||draft.shipping!=='paid'?0:Number(draft.postage)};
  const index=selling.items.findIndex(p=>p.id===id);if(index<0)selling.items.push(item);else selling.items[index]=item;
  selling.draft=newProductDraft();
  go('sell',`&tab=${item.status}`);toast(intent==='draft'?'草稿已保存':'已提交审核，可在“待审核”中查看');
}

function openProductChat(){
  const p=route().get('page')==='product'?currentProduct():products.find(p=>p.id===order.product)||products[0];
  const id=`seller-${p.id}`;
  if(!conversations.some(c=>c.id===id))conversations.push({id,name:p.seller,initial:p.initial,role:'卖家',product:p.id,topic:p.name,draft:'',messages:[]});
  contactFilter='全部';currentContact=id;go('chat',`&contact=${id}`);
}
function chatPage(){
  const explicit=route().get('contact');
  if(conversations.some(c=>c.id===explicit))currentContact=explicit;
  const contacts=conversations.filter(c=>contactFilter==='全部'||c.role===contactFilter);
  if(!contacts.some(c=>c.id===currentContact))currentContact=contacts[0]?.id;
  const current=contacts.find(c=>c.id===currentContact);
  app.innerHTML=header('chat')+`<main class="shell workspace"><h1>聊天</h1><div class="chat-workspace card"><aside class="contacts-panel"><div class="contacts-heading"><h2>联系人</h2><div class="contact-filters" aria-label="联系人类型">${['全部','卖家','买家','管理员 / 客服'].map(t=>`<button class="${contactFilter===t?'active':''}" data-contact-filter="${t}">${t==='管理员 / 客服'?'客服':t}</button>`).join('')}</div></div><div class="contacts-list">${contacts.map(c=>`<button class="contact ${current?.id===c.id?'active':''}" data-contact="${c.id}" ${current?.id===c.id?'aria-current="true"':''}>${avatar(c.initial,true)}<span class="contact-body"><span class="row between"><strong>${esc(c.name)}</strong><small>${esc(c.messages.at(-1)?.time||'')}</small></span><span class="contact-role">${c.role}</span><span class="contact-preview">${esc(c.messages.at(-1)?.text||'开始聊天')}</span></span></button>`).join('')}</div></aside>
  <section class="conversation-panel">${current?`<div class="conversation-heading row between"><div class="row">${avatar(current.initial)}<div><h2>${esc(current.name)}</h2><p class="muted tiny">${current.role}</p></div></div>${current.role==='管理员 / 客服'?tag('平台客服'):'<button class="muted tiny" data-chat-report="true">举报</button>'}</div><div class="conversation-context row between"><span>${icon(current.product?'box':'chat')} ${esc(current.topic)}</span>${current.product?`<a class="link" href="#page=product&id=${current.product}">查看商品 →</a>`:''}</div><div class="conversation-history" id="conversation-history" role="log" aria-label="与${esc(current.name)}的聊天记录">${current.messages.length?current.messages.map(m=>`<div class="message-row ${m.mine?'mine':''}">${avatar(m.mine?'木':current.initial)}<div class="message-content"><div class="message-meta">${m.mine?'我':esc(current.name)} · ${esc(m.time)}</div><div class="message-bubble">${esc(m.text)}</div></div></div>`).join(''):'<p class="conversation-empty">可以在这里发送第一条消息。</p>'}</div><form id="conversation-form" class="conversation-compose"><label for="conversation-message" class="tiny muted">发送给 ${esc(current.name)}</label><textarea id="conversation-message" name="message" rows="3" required maxlength="2000" placeholder="输入消息…">${esc(current.draft)}</textarea><div class="row between"><span class="tiny muted">在站内沟通商品和交易事项</span><button type="submit" class="button">发送</button></div></form>`:'<p class="empty">当前没有该类型的联系人</p>'}</section></div></main>${footer()}`;
  scrollChatToBottom();
}
function scrollChatToBottom(){const el=document.querySelector('#conversation-history');if(el)el.scrollTop=el.scrollHeight;}
function sendConversationMessage(form){
  const text=String(new FormData(form).get('message')||'').trim();if(!text)return;
  const contact=conversations.find(c=>c.id===currentContact);if(!contact)return;
  contact.messages.push({mine:true,text,time:new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})});contact.draft='';chatPage();document.querySelector('#conversation-message').focus();
}
document.addEventListener('input',e=>{
  const form=e.target.closest('#publish-form');if(form&&e.target.id!=='listing-images')captureProductDraft(form);
  if(e.target.id==='conversation-message'){const c=conversations.find(c=>c.id===currentContact);if(c)c.draft=e.target.value;}
});
document.addEventListener('change',e=>{
  const form=e.target.closest('#publish-form');if(!form)return;
  if(e.target.id==='listing-images'){
    for(const file of e.target.files){
      if(!['image/jpeg','image/png','image/webp'].includes(file.type)){toast('请选择 JPG、PNG 或 WebP 图片');continue;}
      selling.draft.images.push({url:URL.createObjectURL(file),name:file.name});
    }
    e.target.value='';renderImagePreviews();
  }else{captureProductDraft(form);updateShippingFields();}
});
document.addEventListener('click',e=>{
  const button=e.target.closest('[data-remove-image],[data-edit-draft],[data-contact],[data-contact-filter],[data-chat-report]');if(!button)return;
  if(button.hasAttribute('data-remove-image')){selling.draft.images.splice(Number(button.dataset.removeImage),1);renderImagePreviews();}
  if(button.dataset.editDraft){const item=selling.items.find(p=>p.id===Number(button.dataset.editDraft));if(item){selling.draft={...item,images:[...item.images]};go('sell','&tab=publish');}}
  if(button.dataset.contact){currentContact=button.dataset.contact;go('chat',`&contact=${currentContact}`);}
  if(button.dataset.contactFilter){contactFilter=button.dataset.contactFilter;const first=conversations.find(c=>contactFilter==='全部'||c.role===contactFilter);currentContact=first?.id;const hash=`#page=chat&contact=${currentContact||''}`;if(location.hash===hash)chatPage();else location.hash=hash;}
  if(button.hasAttribute('data-chat-report'))modal('举报聊天',`<p class="tiny muted">对象：${esc(conversations.find(c=>c.id===currentContact).name)}</p><form id="report-form"><label for="report-reason">举报原因</label><textarea id="report-reason" name="reason" required placeholder="请描述具体问题"></textarea><button class="button wide" type="submit">提交举报</button></form>`);
});
