import { ApiError } from "./api.js";
import { session } from "./session.js";
import { showError } from "./ui.js";
import * as auth from "./pages/auth.js";
import * as account from "./pages/account.js";
import * as admin from "./pages/admin.js";
import * as home from "./pages/home.js";
import * as sell from "./pages/seller.js";
import * as edit from "./pages/product_edit.js";
import * as product from "./pages/product_detail.js";
import * as orders from "./pages/order_list.js";
import * as order from "./pages/order_detail.js";
import * as chat from "./pages/chat.js";
import * as notifications from "./pages/notifications.js";
import * as profile from "./pages/profile.js";
import * as cases from "./pages/cases.js";
import * as caseDetail from "./pages/case_detail.js";
import * as caseNew from "./pages/case_new.js";
import * as logs from "./pages/logs.js";

const pages = { auth, account, admin, home, sell, edit, product, orders, order, chat, notifications, profile, cases, case: caseDetail, case_new: caseNew, logs };

export function createRouter(root) {
  let controller;
  let dispose;
  let generation = 0;

  function navigate(page, params = {}, replace = false) {
    const hash = `#${new URLSearchParams({ page, ...params })}`;
    if (replace || location.hash === hash) {
      history.replaceState(null, "", hash);
      render();
    } else location.hash = hash;
  }

  async function render() {
    const current = ++generation;
    controller?.abort();
    dispose?.();
    dispose = undefined;
    const active = new AbortController();
    controller = active;
    const params = new URLSearchParams(location.hash.slice(1));
    const page = params.get("page") || "home";
    if (!["auth", "home", "product", ...(params.has("id") ? ["profile"] : [])].includes(page) && !session.current.user) {
      navigate("auth", { next: params.toString() || "page=account" }, true);
      return;
    }
    root.innerHTML = '<p class="muted">正在加载…</p>';
    try {
      const cleanup = await (pages[page] || account).mount(root, params, {
        signal: active.signal, navigate,
      });
      if (current === generation) dispose = cleanup;
      else cleanup?.();
    } catch (error) {
      if (error.name === "AbortError" || current !== generation) return;
      if (error instanceof ApiError && error.status === 401) {
        await session.refresh();
        navigate("auth", { next: params.toString() }, true);
      } else showError(root, error.message || "连接未完成，请稍后重试。");
    }
  }

  return {
    navigate,
    start() { window.addEventListener("hashchange", render); render(); },
  };
}
