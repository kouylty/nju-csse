import { escapeText as esc, formatMoney } from "./format.js";

export const statusNames = {
  DRAFT: "草稿", PENDING: "待审核", REJECTED: "审核驳回", PUBLISHED: "已发布",
  OFFLINE: "主动下架", BLOCKED: "违规下架",
};

export function cards(items) {
  if (!items.length) return '<p class="card muted">暂时没有匹配的好物。</p>';
  return `<div class="product-grid">${items.map((p) => `<article class="card product-card"><a href="#page=product&id=${p.id}">${p.images[0] ? `<img src="${p.images[0].url}" alt="${esc(p.title || "商品图片")}">` : '<div class="image-placeholder">暂无图片</div>'}<div class="product-summary"><span class="tag">${statusNames[p.status]}${p.status === "PUBLISHED" && p.availability === "sold_out" ? " · 售罄" : ""}</span><h2>${esc(p.title || "未命名商品")}</h2><p class="money">${p.price_cents === null ? "未填价格" : `¥${formatMoney(p.price_cents)}`}</p><p class="muted">${esc(p.seller_name)} · ${p.type === "SERVICE" ? "服务" : "物品"} · 库存 ${p.available_stock}</p></div></a></article>`).join("")}</div>`;
}

export function pageLinks(result, page, params) {
  const offset = result.offset, size = result.limit;
  function url(next) {
    const query = new URLSearchParams(params);
    query.set("page", page);
    query.set("offset", next);
    return `#${query}`;
  }
  return `<div class="pagination"><span class="muted">共 ${result.total} 件</span>${offset > 0 ? `<a class="button secondary" href="${esc(url(Math.max(0, offset - size)))}">上一页</a>` : ""}${offset + size < result.total ? `<a class="button secondary" href="${esc(url(offset + size))}">下一页</a>` : ""}</div>`;
}
