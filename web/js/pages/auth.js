import { session } from "../session.js";
import { toast } from "../ui.js";

export function mount(root, params, context) {
  const registering = params.get("mode") === "register";
  const next = params.get("next") || "account";
  const destination = new URLSearchParams(next.includes("=") ? next : `page=${next}`);
  const target = ["admin", "account", "edit", "sell", "home", "product", "orders", "order", "chat", "notifications", "profile", "cases", "case", "case_new", "logs"].includes(destination.get("page")) ? destination.get("page") : "account";
  const targetParams = Object.fromEntries(destination);
  delete targetParams.page;
  const title = registering ? "创建余闲账号" : "欢迎回到余闲";
  root.innerHTML = `<div class="auth-layout"><section class="intro"><span class="eyebrow">校园里的好物流转</span><h1>让闲置有去处，<br>让喜欢有回应。</h1><p>使用同一个账号买好物、分享闲置，留下每一次认真交易的记录。</p></section><section class="card"><h1>${title}</h1><p class="muted">${registering ? "注册后即可使用买卖双方的功能。" : "登录你的账号，继续这份喜欢。"}</p><form id="auth-form"><label for="username">用户名</label><input id="username" name="username" autocomplete="username" minlength="3" maxlength="32" required><p class="hint">3—32 个字母、数字或 ._- 字符，支持中文。</p><label for="password">密码</label><input id="password" name="password" type="password" autocomplete="${registering ? "new-password" : "current-password"}" ${registering ? 'minlength="8"' : ""} maxlength="128" required>${registering ? '<p class="hint">8—128 个字符，请妥善保存。</p>' : ""}<p id="form-error" class="form-error" role="alert"></p><button class="wide" type="submit">${registering ? "注册并登录" : "登录"}</button></form><p class="form-switch">${registering ? "已有账号？" : "还没有账号？"} <a href="#page=auth&mode=${registering ? "login" : "register"}&next=${target}">${registering ? "前往登录" : "创建账号"}</a></p></section></div>`;
  const form = root.querySelector("#auth-form");
  root.querySelector(".form-switch a").hash = new URLSearchParams({
    page: "auth", mode: registering ? "login" : "register", next,
  }).toString();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const errorElement = form.querySelector("#form-error");
    button.disabled = true;
    errorElement.textContent = "";
    const credentials = Object.fromEntries(new FormData(form));
    try {
      if (registering) await session.register(credentials, context.signal);
      else await session.login(credentials, context.signal);
      if (context.signal.aborted) return;
      toast(registering ? "账号已建立，欢迎加入余闲。" : "登录成功。");
      context.navigate(target, targetParams, true);
    } catch (error) {
      if (error.name === "AbortError") return;
      errorElement.textContent = error.message || "连接未完成，请稍后重试。";
      if (error.code === "CSRF_FAILED") {
        try { await session.refresh(context.signal); }
        catch { errorElement.textContent = "会话刷新未完成，请重新加载页面。"; }
      }
    } finally {
      if (!context.signal.aborted) button.disabled = false;
    }
  }, { signal: context.signal });
  root.querySelector("#username").focus();
  return () => { form.querySelector("#password").value = ""; };
}
