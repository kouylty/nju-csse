import { escapeText, formatTime, roleName } from "../format.js";
import { session } from "../session.js";

export function mount(root) {
  const { user, expires_at: expiresAt } = session.current;
  root.innerHTML = `<section class="card account-card"><span class="eyebrow">我的余闲</span><h1>你好，${escapeText(user.username)}</h1><p class="muted">账号已登录，你可以在这里查看当前身份。</p><div class="actions"><a href="#page=profile">交易统计与评价</a><a href="#page=notifications">站内通知</a><a href="#page=cases">我的案件</a><a href="#page=logs">我的业务记录</a></div><dl><dt>用户名</dt><dd>${escapeText(user.username)}</dd><dt>账号身份</dt><dd>${roleName(user.role)}</dd><dt>登录有效期</dt><dd>${escapeText(formatTime(expiresAt))}</dd></dl>${user.role === "ADMIN" ? '<div class="actions"><a class="button" href="#page=admin">进入账号管理</a></div>' : '<p class="hint">同一个普通账号同时支持购买和出售。</p>'}</section>`;
}
