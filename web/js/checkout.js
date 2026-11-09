import { orderApi } from "./api.js";
import { escapeText, formatMoney } from "./format.js";
import { session } from "./session.js";

export function mountCheckout(root, product, context) {
  if (product.status !== "PUBLISHED" || product.type !== "GOODS" || !product.allow_meet
      || product.available_stock < 1 || session.current.user?.id === product.seller_id) return;
  const section = document.createElement("section");
  section.className = "checkout-panel";
  root.querySelector(".product-detail-layout .card").append(section);
  if (!session.current.user) {
    const next = new URLSearchParams({ page: "product", id: product.id });
    section.innerHTML = `<a class="button" href="#page=auth&next=${encodeURIComponent(next)}">登录后购买</a>`;
    return;
  }
  section.innerHTML = `
    <form id="checkout-form">
      <h2>确认购买</h2>
      <p class="hint">当面交付，邮费 ¥0.00。下单后为你保留库存十五分钟。</p>
      <label>购买数量<input name="quantity" type="number" min="1" max="${product.available_stock}" step="1" value="1" required></label>
      <p>应付合计：<strong id="checkout-total">¥${formatMoney(product.price_cents)}</strong></p>
      <p id="checkout-error" class="form-error" role="alert"></p>
      <div id="existing-order"></div>
      <button type="submit">提交订单，前往付款</button>
    </form>`;
  const form = section.querySelector("form");
  let intent = null;
  form.elements.quantity.addEventListener("input", () => {
    const quantity = Number(form.elements.quantity.value);
    const total = product.price_cents * quantity;
    section.querySelector("#checkout-total").textContent = Number.isSafeInteger(total) && quantity > 0
      ? `¥${formatMoney(total)}` : "请填写有效数量";
  }, { signal: context.signal });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    if (button.disabled) return;
    button.disabled = true;
    section.querySelector("#checkout-error").textContent = "";
    section.querySelector("#existing-order").replaceChildren();
    const data = { product_id: product.id, quantity: Number(form.elements.quantity.value),
      delivery_mode: "MEET", expected_unit_price_cents: product.price_cents, expected_postage_cents: 0 };
    const signature = JSON.stringify(data);
    if (intent?.signature !== signature) intent = { signature, key: crypto.randomUUID() };
    try {
      const result = await orderApi.place({ ...data, request_key: intent.key }, context.signal);
      if (!context.signal.aborted) context.navigate("order", { id: result.order.id });
    } catch (error) {
      if (error.name === "AbortError") return;
      section.querySelector("#checkout-error").textContent = error.message || "连接未完成，可使用相同内容再次提交。";
      const id = error.details?.order_id;
      if (Number.isSafeInteger(id) && id > 0) section.querySelector("#existing-order").innerHTML = `<a href="#page=order&id=${id}">${escapeText("查看已有订单")}</a>`;
    } finally { if (!context.signal.aborted) button.disabled = false; }
  }, { signal: context.signal });
}
