import { productApi } from "../api.js";
import { escapeText as esc, formatMoney, parseMoney } from "../format.js";
import { cards, pageLinks } from "../product_ui.js";

export async function mount(root, params, context) {
  const query = new URLSearchParams(params);
  query.delete("page");
  const [options, result] = await Promise.all([productApi.options(context.signal), productApi.search(query, context.signal)]);
  root.innerHTML = `<div class="section-header"><div><span class="eyebrow">校园里的好物流转</span><h1>发现好物</h1></div><a class="button" href="#page=edit">发布闲置</a></div><form id="search-form" class="card filter-form"><label>关键词<input name="q" value="${esc(params.get("q") || "")}" placeholder="搜索名称或描述"></label><label>分类<select name="category"><option value="">全部分类</option>${options.categories.map((c) => `<option ${params.get("category") === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label><label>类型<select name="type"><option value="">全部类型</option><option value="GOODS" ${params.get("type") === "GOODS" ? "selected" : ""}>物品</option><option value="SERVICE" ${params.get("type") === "SERVICE" ? "selected" : ""}>服务</option></select></label><label>最低价（元）<input name="min_price" inputmode="decimal" value="${params.has("min_price_cents") ? formatMoney(params.get("min_price_cents")) : ""}"></label><label>最高价（元）<input name="max_price" inputmode="decimal" value="${params.has("max_price_cents") ? formatMoney(params.get("max_price_cents")) : ""}"></label><label>库存状态<select name="availability">${[["available", "在售"], ["sold_out", "售罄"], ["all", "全部"]].map(([value, text]) => `<option value="${value}" ${params.get("availability") === value ? "selected" : ""}>${text}</option>`).join("")}</select></label><label>排序<select name="sort">${[["latest", "最新发布"], ["price_asc", "价格从低到高"], ["price_desc", "价格从高到低"]].map(([value, text]) => `<option value="${value}" ${params.get("sort") === value ? "selected" : ""}>${text}</option>`).join("")}</select></label><button type="submit">查询商品</button><p id="search-error" class="form-error" role="alert"></p></form>${cards(result.items)}${pageLinks(result, "home", params)}`;
  root.querySelector("#search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    try {
      const values = Object.fromEntries(new FormData(event.currentTarget));
      for (const field of ["min_price", "max_price"]) {
        const cents = parseMoney(values[field]);
        delete values[field];
        if (cents !== null) values[`${field}_cents`] = cents;
      }
      if (values.min_price_cents !== undefined && values.max_price_cents !== undefined && values.min_price_cents > values.max_price_cents) throw new Error("最低价格不能超过最高价格。");
      context.navigate("home", Object.fromEntries(Object.entries(values).filter(([, value]) => value !== "")));
    } catch (error) { root.querySelector("#search-error").textContent = error.message; }
  }, { signal: context.signal });
}
