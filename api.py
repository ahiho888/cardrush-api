import re, time
from fastapi import FastAPI, Query
from playwright.async_api import async_playwright

app = FastAPI()
PRICE_RE = re.compile(r"販売価格[^0-9]*([0-9][0-9,]*)\s*円")

CACHE_TTL = 6 * 60 * 60
_cache = {}  # url -> (price, ts)

_play = None
_browser = None

async def get_browser():
    global _play, _browser
    if _browser is None:
        _play = await async_playwright().start()
        _browser = await _play.chromium.launch(headless=True)
    return _browser

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/price")
async def price(url: str = Query(...)):
    now = time.time()
    if url in _cache:
        p, ts = _cache[url]
        if now - ts < CACHE_TTL:
            return {"ok": True, "url": url, "price": p, "cached": True}

    browser = await get_browser()
    ctx = await browser.new_context(locale="ja-JP")
    page = await ctx.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        html = await page.content()
        m = PRICE_RE.search(html)
        p = m.group(1).replace(",", "") if m else ""
        _cache[url] = (p, now)
        return {"ok": True, "url": url, "price": p, "cached": False}
    finally:
        await page.close()
        await ctx.close()