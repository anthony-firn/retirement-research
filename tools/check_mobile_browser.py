"""Check mobile layout and public offline behavior against a running local server; no tracker writes."""
import argparse
import asyncio
from playwright.async_api import async_playwright

async def check(base):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(locale="en-US", viewport={"width": 390, "height": 844})
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(base)
        await page.get_by_text("Start here: make my plan", exact=True).wait_for()
        await page.evaluate("navigator.serviceWorker.ready")
        await page.wait_for_function("navigator.serviceWorker.controller !== null")
        # A slow response from a page we left must not overwrite the new page or wire missing controls.
        async def delayed_error(route):
            await asyncio.sleep(0.3)
            await route.fulfill(status=503, json={"detail": "Simulated slow response"})
        await page.route("**/api/profiles", delayed_error)
        await page.route("**/api/battles", delayed_error)
        await page.evaluate("location.hash = '#/compare'")
        await page.locator("#c-cards").wait_for()
        await page.evaluate("location.hash = '#/'")
        await page.get_by_text("Start here: make my plan", exact=True).wait_for()
        await page.wait_for_timeout(500)
        await page.get_by_text("Start here: make my plan", exact=True).wait_for()
        await page.get_by_role("link", name="Research", exact=True).click()
        await page.get_by_role("heading", name="Retirement research, open to improvement").wait_for()
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        await page.get_by_text("Research history", exact=True).click()
        await page.get_by_role("heading", name="Research history", exact=True).wait_for()
        await page.wait_for_load_state("load")
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        await context.set_offline(True)
        await page.goto(base)
        await page.get_by_role("heading", name="Connect to your retirement tools").wait_for()
        await page.get_by_role("link", name="Read the research").click()
        await page.get_by_text("Reproduce and improve a search", exact=True).click()
        await page.get_by_role("heading", name="Reproduce and improve a search", exact=True).wait_for()
        await page.wait_for_load_state("load")
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        cached = await page.evaluate("""async () => {
          const all = []; for (const name of await caches.keys()) for (const req of await (await caches.open(name)).keys()) all.push(req.url);
          return all;
        }""")
        assert cached and not any("/api/" in url for url in cached), cached
        assert not errors, errors
        print(f"Mobile/offline checks passed; {len(cached)} public cached assets; no API responses cached.")
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8777")
    asyncio.run(check(parser.parse_args().url.rstrip("/")))
