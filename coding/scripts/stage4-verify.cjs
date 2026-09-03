// Pull out text snippets to confirm components rendered correctly.
const { chromium } = require("playwright");

async function run() {
  const browser = await chromium.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // Settings page
  await page.goto("http://127.0.0.1:5174/settings", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  console.log("===== Settings =====");
  const headings = await page.locator("h2.settings-section__heading").allTextContents();
  console.log("section headings:", headings);
  const input = page.locator('input[inputmode="numeric"]').first();
  const inputValue = await input.inputValue();
  console.log("default window input value:", inputValue);
  const saveBtn = page.locator('button:has-text("保存"), button:has-text("Save")').first();
  const saveDisabled = await saveBtn.isDisabled();
  console.log("default save disabled:", saveDisabled);

  // Skills list
  await page.goto("http://127.0.0.1:5174/skills/use", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  console.log("\n===== Skills list =====");
  const usageCells = await page.locator(".usage-cell").count();
  console.log("usage-cell elements:", usageCells);
  const cellTexts = await page.locator(".usage-cell").allTextContents();
  console.log("usage-cell texts:", cellTexts.slice(0, 8));

  // State distribution
  const states = await page.evaluate(() => {
    const counts = { normal: 0, warning: 0, high: 0, unavailable: 0 };
    document.querySelectorAll(".usage-cell").forEach((el) => {
      for (const key of Object.keys(counts)) {
        if (el.className.includes(`usage-cell--${key}`)) counts[key] += 1;
      }
    });
    return counts;
  });
  console.log("state distribution:", states);

  // Sort toggle
  const sortBtn = page.locator('button[aria-label*="按预计上下文占用率排序列表"], button[aria-label="Sort list by estimated context usage"]');
  const sortLabel = await sortBtn.textContent();
  const pressed = await sortBtn.getAttribute("aria-pressed");
  console.log("sort toggle label:", sortLabel, "pressed:", pressed);

  // Click sort
  await sortBtn.click();
  await page.waitForTimeout(300);
  const pressedAfter = await sortBtn.getAttribute("aria-pressed");
  const labelAfter = await sortBtn.textContent();
  console.log("after click — pressed:", pressedAfter, "label:", labelAfter);

  // Get sorted order via the cells' parent row name.
  const sortedNames = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll(".skill-card"));
    return cards.map((card) => {
      const nameEl = card.querySelector(".skill-card__title, [data-card-name], strong");
      const usage = card.querySelector(".usage-cell");
      return {
          name: nameEl ? nameEl.textContent.trim() : "(unknown)",
          usage: usage ? usage.textContent.trim() : "(no usage)",
        };
    });
  });
  console.log("sorted order:", sortedNames);

  // Detail drawer
  console.log("\n===== Skill detail =====");
  const firstCard = page.locator(".skill-card").first();
  await firstCard.click();
  await page.waitForTimeout(800);
  const detailUsage = await page.locator(".usage-cell").first().textContent();
  console.log("detail usage cell:", detailUsage);
  const detailHeading = await page.locator(".skill-detail__section-heading, h3").allTextContents();
  console.log("detail headings:", detailHeading.slice(0, 6));

  await browser.close();
}

run().catch((e) => { console.error(e); process.exit(1); });