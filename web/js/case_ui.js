import { productApi } from "./api.js";
import { escapeText as esc } from "./format.js";

export async function uploadEvidence(input, signal) {
  if (input.files.length > 6) throw new Error("每次最多提交六张证据图片。");
  const ids = [];
  for (const file of input.files) ids.push((await productApi.upload(file, signal)).id);
  return ids;
}

export function caseCards(items, admin = false) {
  const kinds = { PRODUCT_REPORT: "商品举报", CHAT_REPORT: "聊天举报", DISPUTE: "订单纠纷" };
  const states = { OPEN: "待受理", PROCESSING: "处理中", RESOLVED: "已结案" };
  return items.map((item) => `<article class="card feedback-item"><h2>${kinds[item.kind]} · ${esc(item.product_title)}</h2><p>${states[item.status]} · ${esc(item.reporter_name)} / ${esc(item.respondent_name)}</p><p class="description-text">${esc(item.reason)}</p>${admin && item.status === "OPEN" ? `<button type="button" data-claim="${item.id}">受理案件</button>` : `<a href="#page=case&id=${item.id}">查看案件 #${item.id}</a>`}</article>`).join("") || '<p class="card muted">暂无对应案件。</p>';
}
