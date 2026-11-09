import { orderApi } from "../api.js";
import { escapeText as esc, formatMoney, formatTime } from "../format.js";
import { orderStatusNames } from "../order_ui.js";
import { toast } from "../ui.js";
import { mountOrderSocial } from "../social_ui.js";

export async function mount(root, params, context) {
  const order = await orderApi.detail(params.get("id"), context.signal);
  const snapshot = order.snapshot, funds = order.funds;
  const labels = { pay: "确认模拟付款", close: "关闭未付款订单", deliver: "标记已交付", confirm: "确认完成并结算" };
  root.innerHTML = `
    <div class="breadcrumb"><a href="#page=orders">我的订单</a><span>/</span><span>订单详情</span></div>
    <section class="card">
      <div class="section-header"><h1>订单详情</h1><span class="tag">${orderStatusNames[order.status]}</span></div>
      <p class="muted">订单号：${esc(order.order_no)}</p>
      <h2>${esc(snapshot.title)}</h2>
      <div class="image-previews">${snapshot.images.map((image) => `<img src="${image.url}" alt="下单时的商品图片">`).join("")}</div>
      <p class="description-text">${esc(snapshot.description)}</p>
      <p>买家：${esc(order.buyer_name)} · 卖家：${esc(order.seller_name)}</p>
      <p>当面交付 · ${esc(snapshot.meeting_description)}</p>
      <p>单价 ¥${formatMoney(order.unit_price_cents)} × ${order.quantity}，本单邮费 ¥${formatMoney(order.postage_cents)}</p>
      <p class="money">订单合计 ¥${formatMoney(order.total_cents)}</p>
      <p class="hint">以上资料为下单时保存的交易内容。</p>
      ${order.status === "UNPAID" ? `<p>付款截止：${formatTime(order.pay_due_at)}</p>` : ""}
      ${order.paid_at ? `<p>付款时间：${formatTime(order.paid_at)}</p>` : ""}
      ${order.delivered_at ? `<p>交付时间：${formatTime(order.delivered_at)}</p>` : ""}
      ${order.completed_at ? `<p>完成时间：${formatTime(order.completed_at)}</p>` : ""}
      ${order.status === "CLOSED" ? `<p>关闭原因：${order.close_reason === "PAYMENT_TIMEOUT" ? "十五分钟未付款" : order.close_reason === "CASE_REFUND" ? "客服全额退款关闭" : "买家取消"}</p>` : ""}
      <div class="actions" id="order-actions">${order.allowed_actions.map((action) => `<button type="button" data-action="${action}">${labels[action]}</button>`).join("")}</div>
      <p id="order-error" class="form-error" role="alert"></p>
    </section>
    <section class="card description-card"><h2>模拟资金记录</h2>
      <p>已付金额：¥${formatMoney(funds.paid_cents)}</p><p>平台暂存：¥${formatMoney(funds.balance_cents)}</p>
      <p>已退金额：¥${formatMoney(funds.refunded_cents)}</p>
      <p>卖家模拟到账：¥${formatMoney(funds.settled_cents)}</p>
      ${funds.transactions.map((event) => `<p class="muted">${{ PAYMENT: "模拟付款", SETTLEMENT: "模拟结算", REFUND: "模拟退款" }[event.kind]} · ¥${formatMoney(event.amount_cents)} · ${formatTime(event.created_at)}</p>`).join("")}
    </section>`;
  root.querySelector("#order-actions").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button || button.disabled) return;
    root.querySelectorAll("#order-actions button").forEach((item) => { item.disabled = true; });
    try {
      await orderApi.action(order.id, button.dataset.action, context.signal);
      if (!context.signal.aborted) { toast("订单已更新。"); context.navigate("order", { id: order.id }); }
    } catch (error) {
      if (error.name === "AbortError") return;
      root.querySelector("#order-error").textContent = error.message;
      if (error.code === "PAYMENT_EXPIRED") context.navigate("order", { id: order.id });
    } finally {
      if (!context.signal.aborted) root.querySelectorAll("#order-actions button").forEach((item) => { item.disabled = false; });
    }
  }, { signal: context.signal });
  await mountOrderSocial(root, order, context);
}
