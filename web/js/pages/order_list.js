import { orderApi } from "../api.js";
import { escapeText as esc, formatMoney, formatTime } from "../format.js";
import { orderStatusNames } from "../order_ui.js";
import { pageLinks } from "../product_ui.js";

export async function mount(root, params, context) {
  const query = new URLSearchParams(params);
  query.delete("page");
  const result = await orderApi.list(query, context.signal);
  const direction = params.get("direction") || "buy";
  root.innerHTML = `
    <nav class="tabs"><a href="#page=orders&direction=buy">我的购买</a><a href="#page=orders&direction=sell">出售订单</a></nav>
    <h1>${direction === "sell" ? "出售订单" : "我的购买"}</h1>
    <nav class="tabs"><a href="#page=orders&direction=${direction}">全部订单</a>${Object.entries(orderStatusNames).map(([key, label]) => `<a href="#page=orders&direction=${direction}&status=${key}">${label}</a>`).join("")}</nav>
    <div class="order-list">${result.items.length ? result.items.map((order) => `
      <a class="card order-item" href="#page=order&id=${order.id}">
        <div class="section-header"><span>${esc(order.order_no)}</span><span class="tag">${orderStatusNames[order.status]}</span></div>
        <h2>${esc(order.snapshot.title)}</h2>
        <p>数量 ${order.quantity} · 合计 ¥${formatMoney(order.total_cents)}</p>
        <p class="muted">${direction === "sell" ? `买家：${esc(order.buyer_name)}` : `卖家：${esc(order.seller_name)}`} · ${formatTime(order.created_at)}</p>
      </a>`).join("") : '<p class="card muted">当前没有对应订单。</p>'}</div>
    ${pageLinks(result, "orders", params)}`;
}
