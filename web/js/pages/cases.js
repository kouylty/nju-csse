import { caseApi } from "../api.js";
import { caseCards } from "../case_ui.js";
import { pageLinks } from "../product_ui.js";
import { caseKinds, caseStates } from "../social_ui.js";

export async function mount(root, params, context, admin = false) {
  const query = new URLSearchParams({ status: params.get("status") || "", kind: params.get("kind") || "", offset: params.get("offset") || "0" });
  const result = await caseApi.list(query, admin, context.signal);
  const section = document.createElement("section");
  section.innerHTML = `<h1>${admin ? "案件处理" : "我的案件"}</h1><form class="card filter-form"><label>案件类型<select name="kind"><option value="">全部类型</option>${Object.entries(caseKinds).map(([key, value]) => `<option value="${key}" ${query.get("kind") === key ? "selected" : ""}>${value}</option>`).join("")}</select></label><label>案件状态<select name="status"><option value="">全部状态</option>${Object.entries(caseStates).map(([key, value]) => `<option value="${key}" ${query.get("status") === key ? "selected" : ""}>${value}</option>`).join("")}</select></label><button type="submit">查询案件</button></form><p class="form-error" role="alert"></p>${caseCards(result.items, admin)}${pageLinks(result, admin ? "admin" : "cases", admin ? new URLSearchParams({ ...Object.fromEntries(query), tab: "cases" }) : query)}`;
  if (!admin) root.replaceChildren();
  root.append(section);
  section.querySelector("form").addEventListener("submit", (event) => {
    event.preventDefault();
    context.navigate(admin ? "admin" : "cases", { ...Object.fromEntries(new FormData(event.currentTarget)), ...(admin ? { tab: "cases" } : {}) });
  }, { signal: context.signal });
  section.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-claim]");
    if (!button || button.disabled) return;
    button.disabled = true;
    try {
      const result = await caseApi.claim(button.dataset.claim, context.signal);
      if (!context.signal.aborted) context.navigate("case", { id: result.id });
    } catch (error) { if (error.name !== "AbortError") { section.querySelector(".form-error").textContent = error.message; button.disabled = false; } }
  }, { signal: context.signal });
}
