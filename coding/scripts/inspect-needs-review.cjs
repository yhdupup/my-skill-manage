const { chromium } = require("playwright");

async function run() {
  const browser = await chromium.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto("http://127.0.0.1:5174/skills/review", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "/tmp/sm-stage4-shots/needs-review-page.png", fullPage: true });
  console.log("screenshot saved");

  // Get the heading and any introductory text
  const heading = await page.locator("h1, h2").allTextContents();
  console.log("headings:", heading);

  const subtitle = await page.locator(".subtitle, [class*='subtitle'], p").allTextContents();
  console.log("subtitles:", subtitle.slice(0, 5));

  await browser.close();
}

run().catch(e => { console.error(e); process.exit(1); });