// Comprehensive v2 audit: verify current code can run v2's planned deletions.
const { chromium } = require("playwright");

async function run() {
  const browser = await chromium.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.on("pageerror", (err) => console.error("pageerror:", err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") console.error("console.error:", msg.text());
  });

  console.log("=== Navigate to each page ===");
  for (const path of [
    "/",
    "/overview",
    "/skills/use",
    "/skills/review",
    "/settings",
    "/scan-config",
    "/mcp/use",
    "/marketplace/skills",
    "/slash-commands/use",
  ]) {
    try {
      const response = await page.goto(`http://127.0.0.1:5174${path}`, { waitUntil: "networkidle", timeout: 8000 });
      const finalUrl = page.url();
      const status = response ? response.status() : "n/a";
      console.log(`  ${path} -> status=${status} url=${finalUrl}`);
    } catch (e) {
      console.log(`  ${path} -> ERROR ${e.message}`);
    }
  }

  console.log("\n=== Sidebar entries on /skills/use ===");
  await page.goto("http://127.0.0.1:5174/skills/use", { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const sidebarItems = await page.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="主导航"]');
    if (!aside) return null;
    const items = Array.from(aside.querySelectorAll('a, button')).map(el => ({
      tag: el.tagName.toLowerCase(),
      text: el.textContent.trim().slice(0, 30),
      href: el.getAttribute('href'),
    }));
    return items;
  });
  console.log(JSON.stringify(sidebarItems, null, 2));

  console.log("\n=== Sidebar footer (Refresh / Light / Language) ===");
  const footerButtons = await page.evaluate(() => {
    const aside = document.querySelector('aside[aria-label="主导航"]');
    if (!aside) return null;
    return Array.from(aside.querySelectorAll('button')).map(b => b.textContent.trim().slice(0, 30));
  });
  console.log(footerButtons);

  console.log("\n=== Settings page harness section ===");
  await page.goto("http://127.0.0.1:5174/settings", { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const settingsHeadings = await page.locator('h2.settings-section__heading').allTextContents();
  console.log(settingsHeadings);

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });