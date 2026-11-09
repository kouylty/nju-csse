import { productApi } from "../api.js";
import { escapeText as esc, formatMoney, parseMoney } from "../format.js";
import { toast } from "../ui.js";

export async function mount(root, params, context) {
  const options = await productApi.options(context.signal);
  let product = params.has("id") ? await productApi.detail(params.get("id"), context.signal) : null;
  if (product && !product.allowed_actions.includes("edit")) throw new Error("当前商品暂时不能编辑。");
  const draft = product || { title: "", description: "", price_cents: null, available_stock: 1,
    type: "GOODS", category: "", allow_post: false, allow_meet: true, free_shipping: true,
    postage_cents: 0, meeting_description: "", images: [] };
  let images = [...draft.images];
  root.innerHTML = `<div class="section-header"><h1>${product ? "编辑商品" : "发布商品"}</h1><a href="#page=sell">返回我的商品</a></div><form id="product-form" class="card edit-form"><label>商品名称<input name="title" maxlength="60" required value="${esc(draft.title)}"></label><div class="form-columns"><label>价格（元）<input name="price" inputmode="decimal" required value="${formatMoney(draft.price_cents)}"></label><label>可售库存<input name="available_stock" type="number" min="0" max="2147483647" step="1" required value="${draft.available_stock}"></label></div><div class="form-columns"><label>商品类型<select name="type"><option value="GOODS">物品</option><option value="SERVICE" ${draft.type === "SERVICE" ? "selected" : ""}>一次性交付服务</option></select></label><label>商品分类<select name="category" required><option value="">请选择分类</option>${options.categories.map((c) => `<option ${draft.category === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label></div><fieldset id="delivery-fields"><legend>交付方式</legend><label class="checkbox"><input type="checkbox" name="allow_post" ${draft.allow_post ? "checked" : ""}>支持邮寄</label><label class="checkbox"><input type="checkbox" name="allow_meet" ${draft.allow_meet ? "checked" : ""}>支持当面交付</label><div id="postage-fields"><label class="checkbox"><input type="checkbox" name="free_shipping" ${draft.free_shipping ? "checked" : ""}>邮寄包邮</label><label>每单邮费（元）<input name="postage" inputmode="decimal" value="${formatMoney(draft.postage_cents)}"></label></div><label>当面交付说明<input name="meeting_description" maxlength="500" value="${esc(draft.meeting_description)}" placeholder="例如：仙林校区当面交付，时间另行约定"></label></fieldset><p id="service-hint" class="hint" hidden>服务按一次性交付，库存表示可接单数量，无需邮费和收货地址。</p><label>商品图片<input id="product-images" type="file" accept="image/jpeg,image/png,image/webp" multiple></label><p class="hint">JPG、PNG、WebP，每张最多 5 MiB，最多六张。</p><div id="image-previews" class="image-previews"></div><label>商品描述<textarea name="description" maxlength="3000" rows="6" required>${esc(draft.description)}</textarea></label><p id="product-error" class="form-error" role="alert"></p><p id="upload-status" class="hint" role="status"></p><div class="actions"><button type="submit" name="intent" value="save" formnovalidate>保存${product?.status === "PUBLISHED" ? "修改" : "草稿"}</button><button type="submit" name="intent" value="submit">保存并提交审核</button></div></form>`;
  const form = root.querySelector("#product-form");
  if (product && product.status !== "DRAFT") form.querySelector("[value=save]").textContent = "保存修改";
  if (["PUBLISHED", "BLOCKED"].includes(product?.status)) form.querySelector("[value=submit]").remove();
  const errorElement = root.querySelector("#product-error");
  const buttons = () => form.querySelectorAll("button[type=submit]");
  const setBusy = (busy) => buttons().forEach((button) => { button.disabled = busy; });
  let uploading = false;

  function updateDelivery() {
    const service = form.elements.type.value === "SERVICE";
    root.querySelector("#delivery-fields").hidden = service;
    root.querySelector("#service-hint").hidden = !service;
    root.querySelector("#postage-fields").hidden = !form.elements.allow_post.checked;
    form.elements.postage.disabled = service || !form.elements.allow_post.checked || form.elements.free_shipping.checked;
    form.elements.meeting_description.disabled = service || !form.elements.allow_meet.checked;
  }

  function renderImages() {
    root.querySelector("#image-previews").innerHTML = images.map((image, index) => `<figure><img src="${image.url}" alt="商品图片 ${index + 1}"><button type="button" data-remove="${index}">移除图片 ${index + 1}</button></figure>`).join("");
  }
  root.querySelector("#image-previews").addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove]");
    if (button && !uploading) { images.splice(Number(button.dataset.remove), 1); renderImages(); }
  }, { signal: context.signal });
  form.addEventListener("change", updateDelivery, { signal: context.signal });
  root.querySelector("#product-images").addEventListener("change", async (event) => {
    const selected = [...event.target.files];
    event.target.value = "";
    if (images.length + selected.length > 6) { errorElement.textContent = "每件商品最多六张图片。"; return; }
    uploading = true;
    event.target.disabled = true;
    setBusy(true);
    errorElement.textContent = "";
    root.querySelector("#upload-status").textContent = "正在上传图片…";
    try {
      for (const file of selected) {
        images.push(await productApi.upload(file, context.signal));
        if (context.signal.aborted) return;
        renderImages();
      }
    } catch (error) { if (error.name !== "AbortError") errorElement.textContent = error.message; }
    finally {
      uploading = false;
      event.target.disabled = false;
      if (!context.signal.aborted) { setBusy(false); root.querySelector("#upload-status").textContent = ""; }
    }
  }, { signal: context.signal });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (uploading) return;
    const intent = event.submitter?.value || "save";
    setBusy(true);
    errorElement.textContent = "";
    try {
      const service = form.elements.type.value === "SERVICE";
      const post = !service && form.elements.allow_post.checked;
      const data = { title: form.elements.title.value, description: form.elements.description.value,
        category: form.elements.category.value, type: form.elements.type.value,
        price_cents: parseMoney(form.elements.price.value),
        available_stock: Number(form.elements.available_stock.value), allow_post: post,
        allow_meet: !service && form.elements.allow_meet.checked,
        free_shipping: service || !post || form.elements.free_shipping.checked,
        postage_cents: post && !form.elements.free_shipping.checked ? (parseMoney(form.elements.postage.value) ?? 0) : 0,
        meeting_description: service ? "" : form.elements.meeting_description.value,
        image_ids: images.map((image) => image.id) };
      product = product ? await productApi.update(product.id, { ...data, version: product.version }, context.signal)
        : await productApi.create(data, context.signal);
      if (intent === "submit" && product.status !== "PENDING") product = await productApi.submit(product.id, product.version, context.signal);
      if (context.signal.aborted) return;
      toast(product.status === "PENDING" ? "已提交审核。" : "商品已保存。");
      context.navigate("product", { id: product.id });
    } catch (error) { if (error.name !== "AbortError") errorElement.textContent = error.message; }
    finally { if (!context.signal.aborted) setBusy(false); }
  }, { signal: context.signal });
  updateDelivery();
  renderImages();
}
