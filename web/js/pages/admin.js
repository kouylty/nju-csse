import { adminApi, socialApi } from "../api.js";
import { escapeText, formatTime, roleName } from "../format.js";
import { cards, pageLinks, statusNames } from "../product_ui.js";
import * as cases from "./cases.js";
import * as logs from "./logs.js";

const tabs = '<nav class="tabs"><a href="#page=admin">账号管理</a><a href="#page=admin&tab=products">商品审核</a><a href="#page=admin&tab=todos">管理待办</a><a href="#page=admin&tab=cases">案件处理</a><a href="#page=admin&tab=logs">操作日志</a></nav>';

export async function mount(root, params, context) {
  if (["cases", "logs", "todos"].includes(params.get("tab"))) {
    root.innerHTML = tabs;
    if (params.get("tab") === "cases") return cases.mount(root, params, context, true);
    if (params.get("tab") === "logs") return logs.mount(root, params, context, true);
    const result = await socialApi.todos(context.signal);
    root.insertAdjacentHTML("beforeend", `<h1>管理待办</h1><div class="summary-grid"><a class="card" href="#page=admin&tab=products"><h2>待审核商品</h2><p>${result.pending_products}</p></a><a class="card" href="#page=admin&tab=cases&kind=REPORTS&status=ACTIVE"><h2>待处理举报</h2><p>${result.pending_reports}</p></a><a class="card" href="#page=admin&tab=cases&kind=DISPUTE&status=ACTIVE"><h2>待处理纠纷</h2><p>${result.pending_disputes}</p></a></div><p class="hint">案件待办包含待受理和处理中记录。</p>`);
    return;
  }
  if (params.get("tab") === "products") return mountProducts(root, params, context);
  const offset = Math.max(0, Number.parseInt(params.get("offset"), 10) || 0);
  const result = await adminApi.users(offset, context.signal);
  root.innerHTML = `${tabs}<section class="card"><div class="section-header"><h1>账号管理</h1><span class="muted">共 ${result.total} 个账号</span></div><div class="table-wrap"><table><thead><tr><th>账号编号</th><th>用户名</th><th>身份</th><th>建立时间</th></tr></thead><tbody>${result.items.map((user) => `<tr><td>${user.id}</td><td>${escapeText(user.username)}</td><td>${roleName(user.role)}</td><td>${escapeText(formatTime(user.created_at))}</td></tr>`).join("")}</tbody></table></div><div class="pagination">${offset > 0 ? `<a class="button secondary" href="#page=admin&offset=${Math.max(0, offset - 25)}">上一页</a>` : ""}${offset + 25 < result.total ? `<a class="button secondary" href="#page=admin&offset=${offset + 25}">下一页</a>` : ""}</div></section>`;
}

async function mountProducts(root, params, context) {
  const status = params.has("status") ? params.get("status") : "PENDING";
  const query = new URLSearchParams({ status, offset: params.get("offset") || "0" });
  const result = await adminApi.products(query, context.signal);
  root.innerHTML = `${tabs}<div class="section-header"><h1>商品审核</h1><span class="muted">共 ${result.total} 件</span></div><form id="admin-filter" class="card filter-form"><label>商品状态<select name="status"><option value="">全部状态</option>${Object.entries(statusNames).filter(([key]) => key !== "DRAFT").map(([key, name]) => `<option value="${key}" ${key === status ? "selected" : ""}>${name}</option>`).join("")}</select></label><button type="submit">查询</button></form>${cards(result.items)}${pageLinks(result, "admin", new URLSearchParams({ tab: "products", status }))}`;
  root.querySelector("#admin-filter").addEventListener("submit", (event) => {
    event.preventDefault();
    context.navigate("admin", { tab: "products", status: new FormData(event.currentTarget).get("status") });
  }, { signal: context.signal });
}
