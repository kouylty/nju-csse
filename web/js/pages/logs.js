import { socialApi } from "../api.js";
import { escapeText as esc, formatTime } from "../format.js";
import { pageLinks } from "../product_ui.js";

export async function mount(root, params, context, admin = false) {
  const fields = { start: "开始日期", end: "结束日期", actor: "操作人用户名", product_id: "商品编号", order_no: "订单号", action: "操作类型" };
  const query = new URLSearchParams(Object.keys(fields).map((key) => [key, params.get(key) || ""]));
  query.set("offset", params.get("offset") || "0");
  const result = await socialApi.logs(query, admin, context.signal);
  const section = document.createElement("section");
  section.innerHTML = `<h1>${admin ? "操作日志" : "我的业务记录"}</h1><form class="card filter-form">${Object.entries(fields).map(([key, label]) => `<label>${label}<input name="${key}" type="${["start", "end"].includes(key) ? "date" : "text"}" value="${esc(query.get(key))}"></label>`).join("")}<button type="submit">查询记录</button></form><p class="hint">日期按 UTC 查询，包含结束日。</p>${result.items.map((item) => `<details class="card feedback-item"><summary>${formatTime(item.occurred_at)} · ${esc(item.actor_name || (item.actor_kind === "SYSTEM" ? "系统" : "本地管理命令"))} · ${esc(item.action)} · ${esc(item.object_type)} #${esc(item.object_id)}</summary><p class="description-text">变更前：${esc(JSON.stringify(item.before))}</p><p class="description-text">变更后：${esc(JSON.stringify(item.after))}</p></details>`).join("") || '<p class="card muted">暂无匹配记录。</p>'}${pageLinks(result, admin ? "admin" : "logs", new URLSearchParams({ ...Object.fromEntries(query), ...(admin ? { tab: "logs" } : {}) }))}`;
  if (!admin) root.replaceChildren();
  root.append(section);
  section.querySelector("form").addEventListener("submit", (event) => {
    event.preventDefault();
    context.navigate(admin ? "admin" : "logs", { ...Object.fromEntries(new FormData(event.currentTarget)), ...(admin ? { tab: "logs" } : {}) });
  }, { signal: context.signal });
}
