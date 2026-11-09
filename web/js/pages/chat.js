import { socialApi } from "../api.js";
import { escapeText as esc, formatTime } from "../format.js";
import { pageLinks } from "../product_ui.js";
import { session } from "../session.js";

function messageHTML(item) {
  return `<article class="message ${item.sender_id === session.current.user.id ? "mine" : ""}" data-message-id="${item.id}"><p class="muted">${esc(item.sender_name)} · ${formatTime(item.created_at)}${item.order_id ? ` · <a href="#page=order&id=${item.order_id}">关联订单</a>` : ""}</p><p class="description-text">${esc(item.body)}</p></article>`;
}

export async function mount(root, params, context) {
  if (!params.has("id")) {
    const query = new URLSearchParams({ offset: params.get("offset") || "0" });
    const result = await socialApi.conversations(query, context.signal);
    root.innerHTML = `<h1>站内消息</h1>${result.items.length ? result.items.map((item) => `<a class="card conversation-item" href="#page=chat&id=${item.id}"><h2>${esc(item.product_title)}</h2><p>与 ${esc(item.buyer_id === session.current.user.id ? item.seller_name : item.buyer_name)} 沟通</p><p class="muted">${formatTime(item.updated_at)}</p></a>`).join("") : '<p class="card muted">暂无会话，可从商品或订单联系对方。</p>'}${pageLinks(result, "chat", params)}`;
    return;
  }
  const id = params.get("id"), first = await socialApi.messages(id, new URLSearchParams(), context.signal);
  const conversation = first.conversation;
  root.innerHTML = `<div class="breadcrumb"><a href="#page=chat">站内消息</a><span>/</span><span>${esc(conversation.product_title)}</span></div><section class="card"><h1>与 ${esc(conversation.buyer_id === session.current.user.id ? conversation.seller_name : conversation.buyer_name)} 的会话</h1><div class="actions"><a href="#page=product&id=${conversation.product_id}">查看商品</a><a href="#page=case_new&kind=CHAT_REPORT&target=${id}">举报聊天</a></div><button type="button" id="older" ${first.has_more ? "" : "hidden"}>加载更早消息</button><div id="messages" aria-live="polite">${first.items.map(messageHTML).join("")}</div><form id="message-form"><label>消息内容<textarea name="body" maxlength="2000" rows="3" required></textarea></label><label>关联订单（可选）<select name="order_id"><option value="">商品咨询</option>${first.related_orders.map((order) => `<option value="${order.id}" ${String(order.id) === params.get("order_id") ? "selected" : ""}>${esc(order.order_no)}</option>`).join("")}</select></label><p id="chat-error" class="form-error" role="alert"></p><button type="submit">发送消息</button></form></section>`;
  const seen = new Set(first.items.map((item) => item.id));
  let last = first.items.at(-1)?.id || 0, oldest = first.items[0]?.id || 0, timer;
  const panel = root.querySelector("#messages"), errorBox = root.querySelector("#chat-error");
  async function refresh() {
    const result = await socialApi.messages(id, new URLSearchParams({ after_id: last }), context.signal);
    if (context.signal.aborted) return false;
    for (const item of result.items) {
      if (!seen.has(item.id)) { panel.insertAdjacentHTML("beforeend", messageHTML(item)); seen.add(item.id); }
      last = Math.max(last, item.id);
      if (!oldest) oldest = item.id;
    }
    return result.has_more;
  }
  async function poll() {
    let delay = 4000;
    try { if (await refresh()) delay = 100; }
    catch (error) { if (error.name !== "AbortError") errorBox.textContent = error.message; }
    if (!context.signal.aborted) timer = setTimeout(poll, delay);
  }
  timer = setTimeout(poll, 4000);
  context.signal.addEventListener("abort", () => clearTimeout(timer), { once: true });
  root.querySelector("#older").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const result = await socialApi.messages(id, new URLSearchParams({ before_id: oldest }), context.signal);
      if (context.signal.aborted) return;
      const unseen = result.items.filter((item) => !seen.has(item.id));
      panel.insertAdjacentHTML("afterbegin", unseen.map(messageHTML).join(""));
      unseen.forEach((item) => seen.add(item.id));
      oldest = result.items[0]?.id || oldest;
      button.hidden = !result.has_more;
    } catch (error) { if (error.name !== "AbortError") errorBox.textContent = error.message; }
    finally { if (!context.signal.aborted) button.disabled = false; }
  }, { signal: context.signal });
  let intent;
  root.querySelector("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget, button = form.querySelector("button");
    if (button.disabled) return;
    const body = form.elements.body.value, order = form.elements.order_id.value;
    const signature = JSON.stringify([body, order]);
    if (intent?.signature !== signature) intent = { signature, key: crypto.randomUUID() };
    button.disabled = true;
    errorBox.textContent = "";
    try {
      await socialApi.send(id, { body, client_key: intent.key, ...(order ? { order_id: Number(order) } : {}) }, context.signal);
      await refresh();
      if (!context.signal.aborted) { form.elements.body.value = ""; intent = null; }
    } catch (error) { if (error.name !== "AbortError") errorBox.textContent = error.message; }
    finally { if (!context.signal.aborted) button.disabled = false; }
  }, { signal: context.signal });
  return () => clearTimeout(timer);
}
