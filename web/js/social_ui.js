import { socialApi } from "./api.js";
import { escapeText as esc, formatTime } from "./format.js";
import { session } from "./session.js";

export const caseKinds = { PRODUCT_REPORT: "商品举报", CHAT_REPORT: "聊天举报", DISPUTE: "订单纠纷", REPORTS: "商品及聊天举报" };
export const caseStates = { OPEN: "待受理", PROCESSING: "处理中", RESOLVED: "已结案", ACTIVE: "全部未结案" };

export function evaluationCards(items) {
  return items.length ? items.map((item) => `<article class="feedback-item"><p><a href="#page=profile&id=${item.author_id}">${esc(item.author_name)}</a> · ${item.rating} / 5 星 · ${formatTime(item.created_at)}</p><p class="description-text">${esc(item.body)}</p></article>`).join("") : '<p class="muted">暂无评价</p>';
}

export function contactButton(productId, orderId, context, label = "联系卖家") {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const conversation = await socialApi.open({ product_id: productId, ...(orderId ? { order_id: orderId } : {}) }, context.signal);
      if (!context.signal.aborted) context.navigate("chat", { id: conversation.id, ...(orderId ? { order_id: orderId } : {}) });
    } catch (error) { if (error.name !== "AbortError") { button.disabled = false; button.textContent = error.message; } }
  }, { signal: context.signal });
  return button;
}

export async function mountProductSocial(root, product, params, context) {
  if (product.status !== "PUBLISHED") return;
  const result = await socialApi.productEvaluations(product.id, new URLSearchParams({ offset: params.get("evaluation_offset") || "0" }), context.signal);
  if (context.signal.aborted) return;
  const target = root.querySelector("#product-evaluations");
  target.innerHTML = evaluationCards(result.items);
  target.insertAdjacentHTML("beforeend", `<div class="pagination">${result.offset > 0 ? `<a href="#page=product&id=${product.id}&evaluation_offset=${Math.max(0, result.offset - result.limit)}">更早一页</a>` : ""}${result.offset + result.limit < result.total ? `<a href="#page=product&id=${product.id}&evaluation_offset=${result.offset + result.limit}">更多评价</a>` : ""}</div>`);
  if (session.current.user && session.current.user.id !== product.seller_id) {
    root.querySelector("#product-actions").append(contactButton(product.id, null, context));
    root.querySelector("#product-actions").insertAdjacentHTML("beforeend", `<a href="#page=case_new&kind=PRODUCT_REPORT&target=${product.id}">举报商品</a>`);
  }
}

export async function mountOrderSocial(root, order, context) {
  const section = document.createElement("section");
  section.className = "card description-card";
  const result = await socialApi.orderEvaluations(order.id, context.signal);
  if (context.signal.aborted) return;
  section.innerHTML = `<div class="actions" id="order-contact"></div>${order.dispute_open ? '<p class="hint">纠纷处理中，履约、确认和结算暂停。请到“我的案件”查看进度。</p>' : order.paid_at ? `<a href="#page=case_new&kind=DISPUTE&target=${order.id}">申请客服处理</a>` : ""}<h2>双方评价</h2>${evaluationCards(result.items)}${order.status === "COMPLETED" && !result.items.some((item) => item.author_id === session.current.user.id) ? '<form id="evaluation-form"><label>评分<select name="rating"><option value="5">5 星</option><option value="4">4 星</option><option value="3">3 星</option><option value="2">2 星</option><option value="1">1 星</option></select></label><label>评价内容<textarea name="body" maxlength="1000" required></textarea></label><p class="form-error" role="alert"></p><button type="submit">提交评价</button></form>' : ""}`;
  section.querySelector("#order-contact").append(contactButton(order.product_id, order.id, context, session.current.user.id === order.buyer_id ? "联系卖家" : "联系买家"));
  root.append(section);
  section.querySelector("form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget, button = form.querySelector("button");
    button.disabled = true;
    try {
      await socialApi.evaluate(order.id, { rating: Number(form.elements.rating.value), body: form.elements.body.value }, context.signal);
      if (!context.signal.aborted) context.navigate("order", { id: order.id });
    } catch (error) { if (error.name !== "AbortError") form.querySelector(".form-error").textContent = error.message; }
    finally { if (!context.signal.aborted) button.disabled = false; }
  }, { signal: context.signal });
}
