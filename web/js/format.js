export function escapeText(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

export function formatTime(value) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

export function roleName(role) {
  return role === "ADMIN" ? "管理员" : "普通用户";
}

export function formatMoney(cents) {
  if (cents === null) return "";
  const value = BigInt(cents);
  return `${value / 100n}.${String(value % 100n).padStart(2, "0")}`;
}

export function parseMoney(value) {
  const text = value.trim();
  if (!text) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(text)) throw new Error("金额最多填写两位小数。");
  const [whole, fraction = ""] = text.split(".");
  const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
  if (cents > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error("金额超出支持范围。");
  return Number(cents);
}
