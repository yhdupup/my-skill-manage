// Inspect page structure to find selectors.
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

  await page.goto("http://127.0.0.1:5174/skills/use", { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);

  const url = page.url();
  console.log("URL:", url);
  // Click the Skills group in sidebar if collapsed.
  try {
    const sidebarSkills = page.locator('button:has-text("Skills")').first();
    if (await sidebarSkills.count() > 0) {
      const expanded = await sidebarSkills.getAttribute('aria-expanded');
      console.log("sidebar Skills aria-expanded:", expanded);
      if (expanded === 'false') {
        await sidebarSkills.click();
        await page.waitForTimeout(300);
      }
      // Click "In use" link.
      const inUseLink = page.locator('a:has-text("In use")').first();
      if (await inUseLink.count() > 0) {
        await inUseLink.click();
        await page.waitForTimeout(800);
      }
    }
  } catch (e) {
    console.error("sidebar nav error:", e.message);
  }
  console.log("URL-after-nav:", page.url());

  // dump body text (truncated)
  const body = await page.evaluate(() => document.body.innerText);
  console.log("BODY-LEN:", body.length);
  console.log("BODY-PREVIEW:", body.slice(0, 800));

  const allClasses = await page.evaluate(() => {
    const set = new Set();
    document.querySelectorAll("*").forEach((el) => {
      if (el.className && typeof el.className === "string") {
        el.className.split(/\s+/).forEach((c) => { if (c) set.add(c); });
      }
    });
    return Array.from(set);
  });
  console.log("RELEVANT:", allClasses.filter(c => c.includes("skill") || c.includes("usage") || c.includes("card") || c.includes("drawer") || c.includes("detail") || c.includes("grid") || c.includes("list")).join(", "));

  const body2 = await page.evaluate(() => document.body.innerText);
  console.log("FULL-BODY:", body2);

  await browser.close();
}

run().catch((e) => { console.error(e); process.exit(1); });