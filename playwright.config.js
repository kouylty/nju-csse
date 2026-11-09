import { defineConfig } from "@playwright/test";

const python = (process.env.PYTHON || "python").replaceAll("'", "'\\''");

export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: true,
  workers: 2,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5011",
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1365, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: `'${python}' -m scripts.stage_a_server --port 5011`,
    url: "http://127.0.0.1:5011/api/health",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
