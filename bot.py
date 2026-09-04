import asyncio
from datetime import datetime
import os
import re
import time
from typing import Any, Dict, List, Set
import urllib.parse
import urllib.request
from playwright.async_api import async_playwright

CONFIG = {
    "TARGET_URL": "https://marketapp.org/rent/?tab=market&sort_by=price_per_day_asc&subtab=gifts&view=grid&min_price=0.01&max_price=0.02",
    "MIN_DISCOUNT_PERCENT": 50.0,
    "TARGET_DEALS_COUNT": 50,
    "BASE_DOMAIN": "https://marketapp.org",
    # خواندن توکن‌ها از محیط سرور یا تنظیم دستی
    "TELEGRAM_BOT_TOKEN": os.getenv(
        "TELEGRAM_BOT_TOKEN", "توکن_ربات_شما_اینجا"
    ),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", "آیدی_عددی_شما_اینجا"),
}


def send_telegram_final_list(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("⚠️ اطلاعات تلگرام تنظیم نشده است.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"🔥 <b>لیست {len(deals)} گیفت با ۵۰٪ تخفیف یا بالاتر</b>\n"
        f"📅 <i>تاریخ بررسی: {timestamp} (GitHub Cloud)</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    messages = []
    current_msg = header

    for idx, d in enumerate(deals, 1):
        item_text = (
            f"<b>{idx}. {d['name']}</b>\n"
            f"🏷️ تخفیف: <code>{d['discount']}</code> | 💰 {d['price_per_day']} TON/روز\n"
            f"🔗 <a href='{d['tg_link']}'>لینک تلگرام</a> | "
            f"<a href='{d['market_link']}'>لینک مارکت</a>\n\n"
        )
        if len(current_msg) + len(item_text) > 3800:
            messages.append(current_msg)
            current_msg = item_text
        else:
            current_msg += item_text

    if current_msg:
        messages.append(current_msg)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for msg in messages:
        payload = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload)
            with urllib.request.urlopen(req, timeout=15) as response:
                pass
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ خطا در ارسال پیام به تلگرام: {e}")


def generate_tg_nft_link(name: str, number: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", name)
    slug = "".join(w.capitalize() for w in words)
    clean_num = re.sub(r"\D", "", str(number))
    return (
        f"https://t.me/nft/{slug}-{clean_num}"
        if slug and clean_num
        else "نامشخص"
    )


async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()

    async with async_playwright() as p:
        # در سرور گیت‌هاب حتما headless=True باشد
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("🌐 در حال بارگذاری MarketApp روی سرور...")
        await page.goto(
            CONFIG["TARGET_URL"], wait_until="domcontentloaded", timeout=60000
        )
        await page.wait_for_timeout(4000)

        scroll_step = 0
        while len(deals_found) < CONFIG["TARGET_DEALS_COUNT"]:
            cards = await page.locator("a[href*='/nft/']").all()

            for card in cards:
                if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]:
                    break

                try:
                    href = await card.get_attribute("href")
                    if not href:
                        continue

                    full_link = (
                        href
                        if href.startswith("http")
                        else f"{CONFIG['BASE_DOMAIN']}{href if href.startswith('/') else '/' + href}"
                    )
                    if full_link in seen_links:
                        continue

                    text = await card.inner_text()
                    if not text.strip():
                        continue

                    discount_match = re.search(r"-(\d+(?:\.\d+)?)%", text)
                    if discount_match:
                        discount_val = float(discount_match.group(1))

                        if discount_val >= CONFIG["MIN_DISCOUNT_PERCENT"]:
                            num_match = re.search(r"#(\d+)", text)
                            item_num = (
                                num_match.group(1) if num_match else "0"
                            )

                            days_match = re.search(
                                r"Days:\s*(\d+\s*–\s*\d+)", text
                            )
                            days_range = (
                                days_match.group(1)
                                if days_match
                                else "1 – 180"
                            )

                            lines = [
                                l.strip()
                                for l in text.split("\n")
                                if l.strip()
                            ]
                            name_candidates = [
                                l
                                for l in lines
                                if not l.startswith("Days:")
                                and not l.startswith("-")
                                and not l.startswith("#")
                                and l.lower() not in ["per day", "min. price"]
                                and not re.match(r"^\d+(\.\d+)?$", l)
                            ]

                            gift_name = (
                                name_candidates[0]
                                if name_candidates
                                else "NFT Gift"
                            )
                            tg_link = generate_tg_nft_link(gift_name, item_num)

                            deal = {
                                "name": f"{gift_name} #{item_num}",
                                "discount": f"-{discount_val}%",
                                "price_per_day": "0.01",
                                "days_range": days_range,
                                "tg_link": tg_link,
                                "market_link": full_link,
                            }
                            seen_links.add(full_link)
                            deals_found.append(deal)
                            print(
                                f"🎯 [{len(deals_found)}/{CONFIG['TARGET_DEALS_COUNT']}] {deal['name']} ({deal['discount']})"
                            )
                    else:
                        seen_links.add(full_link)
                except Exception:
                    continue

            if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]:
                break

            scroll_step += 1
            await page.evaluate("window.scrollBy(0, window.innerHeight * 2.5);")
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(1000)

            if scroll_step % 8 == 0:
                await page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                await page.wait_for_timeout(1800)

        await browser.close()
        send_telegram_final_list(deals_found)


if __name__ == "__main__":
    asyncio.run(main())
