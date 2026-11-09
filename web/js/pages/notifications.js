import { socialApi } from "../api.js";
import { escapeText as esc, formatTime } from "../format.js";
import { pageLinks } from "../product_ui.js";

export async function mount(root, params, context) {
  const query = new URLSearchParams({ offset: params.get("offset") || "0", unread: params.get("unread") || "false" });
  const result = await socialApi.notifications(query, context.signal);
  const pages = { PRODUCT: "product", ORDER: "order", CASE: "case", CONVERSATION: "chat" };
  root.innerHTML = `<h1>站内通知</h1><p>未读 ${result.unread_count} 条</p><nav class="tabs"><a href="#page=notifications">全部通知</a><a href="#page=notifications&unread=true">只看未读</a></nav>${result.items.map((item) => `<article class="card feedback-item"><h2>${esc(item.title)}${item.read_at ? "" : " · 未读"}</h2><p class="description-text">${esc(item.body)}</p><p class="muted">${formatTime(item.created_at)}</p><div class="actions"><a href="#page=${pages[item.object_type]}&id=${item.object_id}">查看相关内容</a>${item.read_at ? "" : `<button type="button" data-read="${item.id}">标为已读</button>`}</div></article>`).join("") || '<p class="card muted">暂无通知。</p>'}${pageLinks(result, "notifications", params)}<p id="notice-error" class="form-error" role="alert"></p>`;
  root.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-read]");
    if (!button || button.disabled) return;
    button.disabled = true;
    try { await socialApi.read(button.dataset.read, context.signal); if (!context.signal.aborted) context.navigate("notifications", Object.fromEntries(query)); }
    catch (error) { if (error.name !== "AbortError") { root.querySelector("#notice-error").textContent = error.message; button.disabled = false; } }
  }, { signal: context.signal });
}
