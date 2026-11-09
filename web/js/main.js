import { createRouter } from "./router.js";
import { session } from "./session.js";
import { renderNavigation, showError } from "./ui.js";

const root = document.querySelector("#app");
const router = createRouter(root);

session.subscribe(({ user }) => renderNavigation(user, async () => {
  await session.logout();
  router.navigate("auth", {}, true);
}));

try {
  await session.refresh();
  router.start();
} catch (error) {
  showError(root, error.message || "连接未完成，请稍后重新加载。");
}
