// Stage 4 smoke test: capture screenshots for visual verification.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const OUT_DIR = "/tmp/sm-stage4-shots";

async function ensureDir(dir) {
  await fs.promises.mkdir(dir, { recursive: true });
}

async function shot(page, name) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log(`screenshot: ${file}`);
}

async function run() {
  await ensureDir(OUT_DIR);
  const browser = await chromium.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.on("pageerror", (err) => console.error("pageerror:", err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      console.error("console.error:", msg.text());
    }
  });

  // 1. Settings page — verify reference context window section.
  await page.goto("http://127.0.0.1:5174/settings", { waitUntil: "networkidle" });
  await page.waitForSelector("text=Reference context window", { timeout: 15000 });
  const windowInput = page.locator('input[type="text"]').first();
  await windowInput.waitFor({ timeout: 15000 });
  await shot(page, "01-settings-default");

  // Edit and save.
  await windowInput.fill("64000");
  await shot(page, "02-settings-edited");
  const saveButton = page.locator("button", { hasText: "Save" }).first();
  await saveButton.click();
  await page.waitForTimeout(800);
  await shot(page, "03-settings-saved");

  // Reset for the list test.
  await windowInput.fill("128000");
  await saveButton.click();
  await page.waitForTimeout(800);

  // 2. Skills list — verify UsageCell column and sort toggle.
  await page.goto("http://127.0.0.1:5174/skills/use", { waitUntil: "networkidle" });
  await page.waitForSelector(".skill-card", { timeout: 15000 });
  await page.waitForTimeout(800);
  await shot(page, "04-skills-list-default");

  // Toggle sort.
  const sortToggle = page.locator('button[aria-label="Sort list by estimated context usage"]');
  if ((await sortToggle.count()) === 0) {
    const fallback = page.locator('button:has-text("按占用率排序"), button:has-text("Sort by usage")').first();
    await fallback.waitFor({ timeout: 15000 });
    await fallback.click();
  } else {
    await sortToggle.click();
  }
  await page.waitForTimeout(400);
  await shot(page, "05-skills-list-sorted");

  // 3. Skill detail drawer — open first card and screenshot.
  const firstCard = page.locator(".skill-card").first();
  await firstCard.click();
  await page.waitForTimeout(800);
  await shot(page, "06-skill-detail");

  await browser.close();
  console.log("DONE");
}

run().catch((err) => {
  console.error("smoke failed:", err);
  process.exit(1);
});