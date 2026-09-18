// Headless browser walk used for REVIEW.md Appendix B.
//
// Requires Node and Playwright with Chromium installed:
//   npm install playwright && npx playwright install chromium
// Then, with the dev server running and fixtures seeded:
//   node docs/review/browser_walk.js [output-dir] [base-url]
//
// Registers a user through the real form, walks index, shop, item, cart and
// checkout, screenshots each page, and prints every request that failed
// (4xx/5xx) plus console errors. A clean run prints an empty failure list.
const { chromium } = require('playwright');

const out = process.argv[2] || '.';
const base = (process.argv[3] || 'http://127.0.0.1:8000').replace(/\/$/, '');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const failed = new Set();
  page.on('response', r => { if (r.status() >= 400) failed.add(r.status() + ' ' + r.url().replace(base, '')); });
  page.on('console', m => { if (m.type() === 'error') failed.add('console: ' + m.text().slice(0, 140)); });

  await page.goto(base + '/login_register/');
  const owners = await page.$$eval('button[type=submit]', bs => bs.map(b => ({ text: b.textContent.trim(), hasFormOwner: b.form !== null })));
  console.log('submit buttons on /login_register/:', JSON.stringify(owners));
  await page.fill('input[name=email] >> nth=1', 'browser@test.com');
  await page.fill('input[name=password] >> nth=1', 'browserpass');
  let posted = false;
  page.on('request', r => { if (r.method() === 'POST') posted = true; });
  await page.click('button:has-text("Register")');
  await page.waitForLoadState('networkidle');
  console.log('after clicking Register: url =', page.url(), '| POST sent =', posted);
  await page.screenshot({ path: out + '/1-login.png' });

  await page.goto(base + '/'); await page.waitForLoadState('networkidle');
  await page.screenshot({ path: out + '/2-index.png', fullPage: true });
  console.log('jQuery loaded:', await page.evaluate(() => typeof window.jQuery !== 'undefined'));

  await page.goto(base + '/shop/'); await page.waitForLoadState('networkidle');
  await page.screenshot({ path: out + '/3-shop.png', fullPage: true });

  await page.goto(base + '/item/?name=blue_shirt'); await page.waitForLoadState('networkidle');
  await page.screenshot({ path: out + '/4-item.png' });
  await page.selectOption('select[name=size]', 'M');
  await page.selectOption('select[name=quantity]', '3');
  await page.click('button:has-text("Add")'); await page.waitForLoadState('networkidle');
  console.log('after Add to cart landed on:', page.url());

  await page.goto(base + '/cart/'); await page.waitForLoadState('networkidle');
  await page.screenshot({ path: out + '/5-cart.png', fullPage: true });
  await page.click('button:has-text("X") >> nth=1', { force: true }); await page.waitForLoadState('networkidle');
  console.log('after clicking Remove X: url =', page.url(), '| rows still =', (await page.$$('td.name-pr')).length);

  await page.goto(base + '/checkout/'); await page.waitForLoadState('networkidle');
  await page.screenshot({ path: out + '/6-checkout.png', fullPage: true });
  page.once('dialog', d => d.accept());
  await page.fill('input[name=address]', '1 Test St');
  await page.click('button:has-text("Place Order")'); await page.waitForLoadState('networkidle');
  console.log('after Place Order landed on:', page.url());

  console.log('failed requests / console errors:');
  [...failed].forEach(f => console.log('  ', f));
  await browser.close();
})().catch(e => { console.error('ERR', e.message.split('\n')[0]); process.exit(1); });
