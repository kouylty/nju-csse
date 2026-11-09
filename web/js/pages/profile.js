import { socialApi } from "../api.js";
import { escapeText as esc, formatMoney, formatTime } from "../format.js";
import { pageLinks } from "../product_ui.js";
import { evaluationCards } from "../social_ui.js";
import { session } from "../session.js";

export async function mount(root, params, context) {
  const id = Number(params.get("id") || session.current.user?.id), own = id === session.current.user?.id;
  const evaluations = await socialApi.userEvaluations(id, new URLSearchParams({ offset: params.get("evaluation_offset") || "0" }), context.signal);
  root.innerHTML = `<h1>${own ? "我的交易与评价" : "收到的评价"}</h1>${own ? '<nav class="tabs"><a href="#page=notifications">站内通知</a><a href="#page=cases">我的案件</a><a href="#page=logs">我的业务记录</a></nav><div id="seller-summary"></div>' : ""}<section class="card description-card"><h2>收到的评价</h2>${evaluationCards(evaluations.items)}<div class="pagination">${evaluations.offset > 0 ? `<a href="#page=profile&id=${id}&evaluation_offset=${Math.max(0, evaluations.offset - evaluations.limit)}">上一页评价</a>` : ""}${evaluations.offset + evaluations.limit < evaluations.total ? `<a href="#page=profile&id=${id}&evaluation_offset=${evaluations.offset + evaluations.limit}">下一页评价</a>` : ""}</div></section>`;
  if (!own) return;
  const query = new URLSearchParams({ start: params.get("start") || "", end: params.get("end") || "", offset: params.get("offset") || "0" });
  const result = await socialApi.summary(query, context.signal);
  if (context.signal.aborted) return;
  root.querySelector("#seller-summary").innerHTML = `<form class="card filter-form"><label>开始日期<input type="date" name="start" value="${esc(query.get("start"))}"></label><label>结束日期<input type="date" name="end" value="${esc(query.get("end"))}"></label><button type="submit">查询卖家统计</button></form><p class="hint">日期按 UTC 统计，包含所选结束日。成交按完成时间，模拟到账按结算时间。</p><div class="summary-grid"><div class="card"><h2>完成订单</h2><p>${result.completed_order_count} 笔</p></div><div class="card"><h2>成交金额</h2><p>¥${formatMoney(result.turnover_cents)}</p></div><div class="card"><h2>模拟到账</h2><p>¥${formatMoney(result.settled_cents)}</p></div></div><section class="card description-card"><h2>完成订单明细</h2>${result.completed_orders.map((order) => `<p><a href="#page=order&id=${order.id}">${esc(order.order_no)}</a> · ¥${formatMoney(order.total_cents)} · ${formatTime(order.completed_at)}</p>`).join("") || '<p class="muted">当前范围没有完成订单。</p>'}<h2>模拟到账明细</h2>${result.settlements.map((item) => `<p><a href="#page=order&id=${item.order_id}">${esc(item.order_no)}</a> · ¥${formatMoney(item.amount_cents)} · ${formatTime(item.created_at)}</p>`).join("") || '<p class="muted">当前范围没有模拟到账。</p>'}</section>${pageLinks({ ...result, total: Math.max(result.completed_order_count, result.settlement_count) }, "profile", query)}`;
  root.querySelector("form").addEventListener("submit", (event) => {
    event.preventDefault();
    context.navigate("profile", Object.fromEntries(new FormData(event.currentTarget)));
  }, { signal: context.signal });
}
