import { escapeText } from "./format.js";

let toastTimer;

export function toast(message) {
  const element = document.querySelector("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove("show"), 3000);
}

export function showError(root, message) {
  root.innerHTML = `<section class="card"><h1>暂时无法打开</h1><p class="form-error">${escapeText(message)}</p><button type="button" id="reload">重新加载</button></section>`;
  root.querySelector("#reload").addEventListener("click", () => location.reload());
}

export function renderNavigation(user, onLogout) {
  const element = document.querySelector("#navigation");
  element.innerHTML = user
    ? `<a href="#page=home">逛逛好物</a><a href="#page=sell">我的商品</a><a href="#page=orders&direction=buy">我的购买</a><a href="#page=orders&direction=sell">出售订单</a><a href="#page=chat">消息</a><a href="#page=notifications">通知</a><a href="#page=account">${escapeText(user.username)}</a>${user.role === "ADMIN" ? '<a href="#page=admin">账号管理</a><a href="#page=admin&tab=products">商品审核</a>' : ""}<button class="link" type="button" id="logout">退出登录</button>`
    : '<a href="#page=home">逛逛好物</a><a href="#page=auth">登录 / 注册</a>';
  element.querySelector("#logout")?.addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    try {
      await onLogout();
    } catch (error) {
      toast(error.message || "连接未完成，请稍后重试。");
      const button = element.querySelector("#logout");
      if (button) button.disabled = false;
    }
  });
}
