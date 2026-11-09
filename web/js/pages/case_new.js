import { caseApi } from "../api.js";
import { uploadEvidence } from "../case_ui.js";
import { escapeText as esc } from "../format.js";
import { caseKinds } from "../social_ui.js";

export function mount(root, params, context) {
  const kind = params.get("kind"), target = Number(params.get("target"));
  root.innerHTML = `<section class="card"><h1>${caseKinds[kind] || "提交案件"}</h1><p>请说明具体情况。提交后可在“我的案件”查看进度、补充证据，与对方及管理员沟通。</p><form id="case-form"><label>原因说明<textarea name="reason" maxlength="2000" rows="5" required></textarea></label><label>证据图片（最多六张）<input type="file" name="images" multiple accept="image/png,image/jpeg,image/webp"></label><p class="hint">证据由案件双方及当前受理管理员查看。</p><p class="form-error" role="alert"></p><button type="submit">提交${esc(caseKinds[kind] || "申请")}</button></form></section>`;
  root.querySelector("form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget, button = form.querySelector("button");
    if (button.disabled) return;
    button.disabled = true;
    try {
      const imageIds = await uploadEvidence(form.elements.images, context.signal);
      const result = await caseApi.submit({ kind, target_id: target, reason: form.elements.reason.value, image_ids: imageIds }, context.signal);
      if (!context.signal.aborted) context.navigate("case", { id: result.id });
    } catch (error) { if (error.name !== "AbortError") form.querySelector(".form-error").textContent = error.message; }
    finally { if (!context.signal.aborted) button.disabled = false; }
  }, { signal: context.signal });
}
