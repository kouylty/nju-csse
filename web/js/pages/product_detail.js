import { adminApi, productApi } from "../api.js";
import { escapeText as esc, formatMoney, formatTime } from "../format.js";
import { statusNames } from "../product_ui.js";
import { toast } from "../ui.js";
import { mountCheckout } from "../checkout.js";
import { mountProductSocial } from "../social_ui.js";

export async function mount(root, params, context) {
  const product = await productApi.detail(params.get("id"), context.signal);
  const actions = product.allowed_actions;
  const shipping = product.type === "SERVICE" ? "服务交付 · 邮费为零" : [product.allow_post ? (product.free_shipping ? "邮寄包邮" : `邮寄 · ¥${formatMoney(product.postage_cents)} / 单`) : "", product.allow_meet ? `当面交付 · ${product.meeting_description}` : ""].filter(Boolean).join("；");
  root.innerHTML = `<div class="breadcrumb"><a href="#page=home">逛逛好物</a><span>/</span><span>${esc(product.category)}</span></div><div class="product-detail-layout"><section class="gallery">${product.images.length ? product.images.map((image) => `<img src="${image.url}" alt="${esc(product.title || "商品图片")}">`).join("") : '<div class="image-placeholder">暂无图片</div>'}</section><section class="card"><span class="tag">${statusNames[product.status]}${product.status === "PUBLISHED" && !product.available_stock ? " · 售罄" : ""}</span><h1>${esc(product.title || "未命名商品")}</h1><p class="money">${product.price_cents === null ? "未填价格" : `¥${formatMoney(product.price_cents)}`}</p><p>卖家：<a href="#page=profile&id=${product.seller_id}">${esc(product.seller_name)}</a></p><p>${product.type === "SERVICE" ? "一次性交付服务" : "物品"} · 可售库存 ${product.available_stock}</p><p class="muted">${esc(shipping)}</p><div id="product-actions" class="actions">${actions.includes("edit") ? `<a class="button" href="#page=edit&id=${product.id}">编辑商品</a>` : ""}${[["submit", "提交审核"], ["take_down", "主动下架"], ["rectify", "提交整改复核"], ["approve", "审核通过"], ["reject", "驳回审核"], ["block", "违规下架"], ["reopen", "批准重新审核"]].filter(([key]) => actions.includes(key) || (actions.includes("review") && ["approve", "reject"].includes(key))).map(([key, label]) => `<button type="button" data-action="${key}">${label}</button>`).join("")}</div>${actions.some((a) => ["review", "block", "rectify"].includes(a)) ? '<label>处理或整改说明<textarea id="reason" rows="3" maxlength="1000" placeholder="驳回、违规下架和整改申请时须填写"></textarea></label>' : ""}<p id="action-error" class="form-error" role="alert"></p>${product.status === "PENDING" ? '<p class="hint">正在等待管理员审核，审核完成后可继续编辑。</p>' : ""}${product.moderation_reason ? `<p>下架说明：${esc(product.moderation_reason)}</p>` : ""}${product.rectification_note ? `<p>整改说明：${esc(product.rectification_note)}</p>` : ""}</section></div><section class="card description-card"><h2>关于这件好物</h2><p class="description-text">${esc(product.description || "尚未填写描述")}</p><h2>商品评价</h2><div id="product-evaluations"><p class="muted">暂无评价</p></div></section>${product.reviews?.length ? `<section class="card description-card"><h2>审核记录</h2>${product.reviews.map((review) => `<details><summary>${formatTime(review.submitted_at)} · ${{ PENDING: "待审核", APPROVED: "审核通过", REJECTED: "审核驳回" }[review.result]}</summary><p>${esc(review.reason || "暂无处理说明")}</p><p>提交名称：${esc(review.submitted.title)}</p><p class="description-text">${esc(review.submitted.description)}</p><p>提交价格：¥${formatMoney(review.submitted.price_cents)}</p></details>`).join("")}</section>` : ""}`;
  mountCheckout(root, product, context);
  root.querySelector("#product-actions").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const errorElement = root.querySelector("#action-error");
    const version = product.version, reason = root.querySelector("#reason")?.value || "";
    const handlers = {
      submit: () => productApi.submit(product.id, version, context.signal),
      take_down: () => productApi.takeDown(product.id, version, context.signal),
      rectify: () => productApi.rectify(product.id, { version, note: reason }, context.signal),
      approve: () => adminApi.review(product.id, { version, approve: true, reason }, context.signal),
      reject: () => adminApi.review(product.id, { version, approve: false, reason }, context.signal),
      block: () => adminApi.block(product.id, { version, reason }, context.signal),
      reopen: () => adminApi.reopen(product.id, version, context.signal),
    };
    root.querySelectorAll("#product-actions button").forEach((item) => { item.disabled = true; });
    try {
      await handlers[button.dataset.action]();
      if (context.signal.aborted) return;
      toast("处理完成。");
      context.navigate("product", { id: product.id });
    } catch (error) {
      if (error.name !== "AbortError") errorElement.textContent = error.message;
    } finally {
      if (!context.signal.aborted) root.querySelectorAll("#product-actions button").forEach((item) => { item.disabled = false; });
    }
  }, { signal: context.signal });
  await mountProductSocial(root, product, params, context);
}
