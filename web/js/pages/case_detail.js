import { caseApi } from "../api.js";
import { uploadEvidence } from "../case_ui.js";
import { escapeText as esc, formatMoney, formatTime } from "../format.js";
import { caseKinds, caseStates } from "../social_ui.js";
import { session } from "../session.js";

const decisions = { REJECT: "驳回举报", RECORD: "记录处理意见并结案", RECTIFY: "要求整改并暂停出售", BLOCK: "违规下架", CONTINUE: "继续履约，由买家手动确认", REFUND: "全额模拟退款并关闭", COMPLETE: "确认完成并结算" };

export async function mount(root, params, context) {
  const item = await caseApi.detail(params.get("id"), context.signal);
  const options = item.kind === "DISPUTE" ? ["CONTINUE", "REFUND", "COMPLETE", "RECORD"] : item.kind === "PRODUCT_REPORT" ? ["REJECT", "RECTIFY", "BLOCK", "RECORD"] : ["REJECT", "RECORD"];
  const participant = [item.reporter_id, item.respondent_id].includes(session.current.user.id);
  root.innerHTML = `<div class="breadcrumb"><a href="#page=cases">我的案件</a><span>/</span><span>案件 #${item.id}</span></div><section class="card"><h1>${caseKinds[item.kind]}</h1><p>状态：${caseStates[item.status]}</p><h2>${esc(item.product_title)}</h2><p>申请人 ${esc(item.reporter_name)} · 对方 ${esc(item.respondent_name)} · 受理人 ${esc(item.handler_name || "等待受理")}</p><p class="description-text">${esc(item.reason)}</p>${item.resolution ? `<p class="description-text">处理结果：${esc(item.resolution)}</p><p>处置：${decisions[item.decision]}</p>` : ""}${participant || item.can_handle ? '<button type="button" id="case-context">查看关联资料</button><div id="context-data"></div>' : ""}<p id="case-error" class="form-error" role="alert"></p></section><section class="card description-card"><h2>沟通与处理记录</h2>${item.actions.map((action) => `<article class="feedback-item"><p class="muted">${esc(action.actor_name)} · ${formatTime(action.created_at)}</p><p class="description-text">${esc(action.body)}</p>${(participant || item.can_handle) ? action.images.map((image) => `<a href="${image.url}" target="_blank" rel="noopener"><img class="evidence-image" src="${image.url}" alt="案件证据"></a>`).join("") : ""}${action.result.execution?.order_id ? `<p>${participant ? `<a href="#page=order&id=${action.result.execution.order_id}">关联订单</a>` : "关联订单已记录"} · ${action.result.execution.restore_stock === true ? "已恢复库存" : action.result.execution.restore_stock === false ? "库存按已消耗处理" : ""}</p>${action.result.execution.confirmation_plan ? `<p>后续确认安排：${esc(action.result.execution.confirmation_plan)}</p>` : ""}` : ""}</article>`).join("")}${item.status !== "RESOLVED" ? '<form id="case-comment"><label>补充说明<textarea name="body" maxlength="2000" required></textarea></label><label>补充证据图片<input type="file" name="images" multiple accept="image/png,image/jpeg,image/webp"></label><p class="form-error" role="alert"></p><button type="submit">提交补充说明</button></form>' : ""}</section>${item.can_handle ? `<section class="card description-card"><h2>客服处置</h2><form id="case-resolve"><label>处理方式<select name="decision" required><option value="">请选择</option>${options.map((key) => `<option value="${key}">${decisions[key]}</option>`).join("")}</select></label><label>处理依据与意见<textarea name="reason" maxlength="2000" required></textarea></label><label id="restore-field" hidden>退款后库存<select name="restore_stock"><option value="">请选择</option><option value="true">恢复本单全部数量</option><option value="false">保持消耗，不恢复</option></select></label><label id="plan-field" hidden>后续履约与手动确认安排<textarea name="confirmation_plan" maxlength="1000"></textarea></label><p class="form-error" role="alert"></p><button type="submit">执行处置并结案</button></form></section>` : ""}`;
  root.querySelector("#case-comment")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget, button = form.querySelector("button");
    if (button.disabled) return;
    button.disabled = true;
    try {
      const imageIds = await uploadEvidence(form.elements.images, context.signal);
      await caseApi.comment(item.id, { body: form.elements.body.value, image_ids: imageIds }, context.signal);
      if (!context.signal.aborted) context.navigate("case", { id: item.id });
    } catch (error) { if (error.name !== "AbortError") form.querySelector(".form-error").textContent = error.message; }
    finally { if (!context.signal.aborted) button.disabled = false; }
  }, { signal: context.signal });
  const resolve = root.querySelector("#case-resolve");
  resolve?.elements.decision.addEventListener("change", () => {
    const refund = resolve.elements.decision.value === "REFUND", resume = resolve.elements.decision.value === "CONTINUE";
    root.querySelector("#restore-field").hidden = !refund;
    root.querySelector("#plan-field").hidden = !resume;
    resolve.elements.restore_stock.required = refund;
    resolve.elements.confirmation_plan.required = resume;
  }, { signal: context.signal });
  resolve?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = resolve.querySelector("button"), decision = resolve.elements.decision.value;
    if (button.disabled) return;
    button.disabled = true;
    try {
      await caseApi.resolve(item.id, { version: item.version, decision, reason: resolve.elements.reason.value, ...(decision === "REFUND" ? { restore_stock: resolve.elements.restore_stock.value === "true" } : {}), ...(decision === "CONTINUE" ? { confirmation_plan: resolve.elements.confirmation_plan.value } : {}) }, context.signal);
      if (!context.signal.aborted) context.navigate("case", { id: item.id });
    } catch (error) { if (error.name !== "AbortError") resolve.querySelector(".form-error").textContent = error.message; }
    finally { if (!context.signal.aborted) button.disabled = false; }
  }, { signal: context.signal });
  let before;
  async function loadContext() {
    const button = root.querySelector("#case-context");
    button.disabled = true;
    try {
      const result = await caseApi.context(item.id, new URLSearchParams(before ? { before_id: before } : {}), context.signal);
      if (context.signal.aborted) return;
      const data = root.querySelector("#context-data");
      if (!before && result.order) data.innerHTML = `<p>订单 ${esc(result.order.order_no)} · ${esc(result.order.snapshot.title)} · 合计 ¥${formatMoney(result.order.total_cents)}</p><p>平台暂存 ¥${formatMoney(result.order.funds.balance_cents)} · 已退款 ¥${formatMoney(result.order.funds.refunded_cents)} · 已结算 ¥${formatMoney(result.order.funds.settled_cents)}</p>`;
      data.insertAdjacentHTML("beforeend", result.messages.map((message) => `<p class="description-text">${esc(message.sender_name)}：${esc(message.body)} <span class="muted">${formatTime(message.created_at)}</span></p>`).join("") || '<p class="muted">暂无关联聊天。</p>');
      before = result.messages[0]?.id;
      button.textContent = "查看更早聊天";
      button.hidden = !result.has_more;
    } catch (error) { if (error.name !== "AbortError") root.querySelector("#case-error").textContent = error.message; }
    finally { if (!context.signal.aborted) button.disabled = false; }
  }
  root.querySelector("#case-context")?.addEventListener("click", loadContext, { signal: context.signal });
}
