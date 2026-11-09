import { productApi } from "../api.js";
import { cards, pageLinks, statusNames } from "../product_ui.js";

export async function mount(root, params, context) {
  const query = new URLSearchParams(params);
  query.delete("page");
  const result = await productApi.mine(query, context.signal);
  const stockTabs = '<a href="#page=sell&status=PUBLISHED&availability=available">在售</a><a href="#page=sell&status=PUBLISHED&availability=sold_out">售罄</a>';
  root.innerHTML = `<div class="section-header"><h1>我的商品</h1><a class="button" href="#page=edit">发布商品</a></div><nav class="tabs"><a href="#page=sell">全部</a>${Object.entries(statusNames).map(([key, name]) => `<a class="${params.get("status") === key ? "active" : ""}" href="#page=sell&status=${key}">${name}</a>`).join("")}${stockTabs}</nav>${cards(result.items)}${pageLinks(result, "sell", params)}`;
}
