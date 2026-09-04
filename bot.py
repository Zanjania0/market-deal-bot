import asyncio
import csv
from datetime import datetime
import os
import re
import time
from typing import Any, Dict, List, Set
import urllib.parse
import urllib.request
from playwright.async_api import async_playwright

# ==========================================
# ⚙️ تنظیمات اپلیکیشن
# ==========================================
CONFIG = {
    "TARGET_URL": (
        "https://marketapp.org/rent/?tab=market&sort_by=price_per_day_asc"
        "&subtab=gifts&view=grid&min_price=0.01&max_price=0.02"
    ),
    "MIN_DISCOUNT_PERCENT": 50.0,
    "TARGET_DEALS_COUNT": 100,  # افزایش ظرفیت به ۱۰۰ مورد
    "BASE_DOMAIN": "https://marketapp.org",
    "EXPORT_CSV": "discounts.csv",
    "EXPORT_TXT": "discounts.txt",
    "TELEGRAM_BOT_TOKEN": os.getenv(
        "TELEGRAM_BOT_TOKEN", "توکن_ربات_شما_اینجا"
    ),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", "آیدی_عددی_شما_اینجا"),
}


# ==========================================
# 💎 الگوریتم تشخیص شماره‌های رند و کمیاب
# ==========================================
def detect_rarity_badge(number_str: str) -> str:
    try:
        num = int(re.sub(r"\D", "", str(number_str)))
    except ValueError:
        return ""

    s = str(num)
    if num < 100:
        return "👑 شماره دو رقمی (فوق نایاب)"
    if num < 1000:
        return f"💎 شماره زیر ۱۰۰۰ (#{num})"
    if len(s) >= 3 and len(set(s)) == 1:
        return f"✨ شماره رند یکدست (#{s})"
    if s in [
        "123",
        "1234",
        "12345",
        "6969",
        "777",
        "888",
        "999",
        "10000",
        "50000",
        "100000",
    ]:
        return f"🎯 الگوی خاص (#{s})"
    if len(s) == 4 and s == s[::-1]:
        return f"🔁 شماره متقارن (#{s})"
    return ""


def generate_tg_nft_link(name: str, number: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", name)
    slug = "".join(w.capitalize() for w in words)
    clean_num = re.sub(r"\D", "", str(number))
    return (
        f"https://t.me/nft/{slug}-{clean_num}"
        if slug and clean_num
        else "نامشخص"
    )


# ==========================================
# 📤 ارسال پیام تفکیک‌شده به همراه لیست خالص لینک‌ها
# ==========================================
def send_telegram_package(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("⚠️ توکن یا چت‌آیدی تلگرام تنظیم نشده است.")
        return

    rare_deals = [d for d in deals if d["rarity"]]
    normal_deals = [d for d in deals if not d["rarity"]]

    discounts = [d["discount_num"] for d in deals]
    avg_discount = sum(discounts) / len(discounts) if discounts else 0
    max_discount = max(discounts) if discounts else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ۱. متن گزارش تفصیلی
    full_text = (
        f"📊 <b>گزارش تحلیلی گیفت‌های تخفیف‌دار MarketApp</b>\n"
        f"📅 <i>{timestamp}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>تعداد کل:</b> {len(deals)} مورد\n"
        f"💎 <b>موارد کمیاب/خاص:</b> {len(rare_deals)} مورد\n"
        f"🔥 <b>بیشترین تخفیف:</b> -{max_discount}%\n"
        f"📉 <b>میانگین تخفیف:</b> -{avg_discount:.1f}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if rare_deals:
        full_text += (
            f"💎 <b>━━━ موارد کمیاب و شماره‌های خاص ({len(rare_deals)} مورد) ━━━</b>\n\n"
        )
        for idx, d in enumerate(rare_deals, 1):
            hot_tag = "🚨 " if d["discount_num"] >= 70 else "⭐ "
            full_text += (
                f"<b>{idx}. {hot_tag}{d['name']}</b>\n"
                f"   🏆 <b>{d['rarity']}</b>\n"
                f"   🏷️ تخفیف: <code>{d['discount']}</code> | 💰 {d['price_per_day']} TON/روز\n"
                f"   🔗 <a href='{d['tg_link']}'>مشاهده در تلگرام</a> | "
                f"<a href='{d['market_link']}'>لینک مارکت</a>\n\n"
            )

    if normal_deals:
        full_text += (
            f"🎁 <b>━━━ سایر گیفت‌های تخفیف‌دار ({len(normal_deals)} مورد) ━━━</b>\n\n"
        )
        for idx, d in enumerate(normal_deals, 1):
            hot_tag = "🚨 " if d["discount_num"] >= 70 else "🔹 "
            full_text += (
                f"<b>{idx}. {hot_tag}{d['name']}</b>\n"
                f"   🏷️ تخفیف: <code>{d['discount']}</code> | 💰 {d['price_per_day']} TON/روز\n"
                f"   🔗 <a href='{d['tg_link']}'>تلگرام</a> | "
                f"<a href='{d['market_link']}'>مارکت‌اپ</a>\n\n"
            )

    # ۲. ساخت متن مجزا برای لیست خالص لینک‌های تلگرام
    links_text = (
        f"📋 <b>━━━ لیست فقط لینک‌های تلگرام ({len(deals)} مورد) ━━━</b>\n\n"
    )
    for idx, d in enumerate(deals, 1):
        links_text += f"{idx}. {d['tg_link']}\n"

    # ارسال تمام پیام‌ها با مدیریت سقف کاراکتر
    send_chunks_to_telegram(full_text, token, chat_id)
    time.sleep(1)
    send_chunks_to_telegram(links_text, token, chat_id)

    # ارسال فایل اکسل به عنوان ضمیمه
    send_telegram_csv_attachment(
        CONFIG["EXPORT_CSV"], token, chat_id, f"📊 فایل اکسل گزارش ({timestamp})"
    )


def send_chunks_to_telegram(text: str, token: str, chat_id: str):
    chunks = []
    current_chunk = ""
    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 > 3800:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"
        else:
            current_chunk += paragraph + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for part in chunks:
        payload = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": part,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload)
            with urllib.request.urlopen(req, timeout=15):
                pass
            time.sleep(0.4)
        except Exception as e:
            print(f"⚠️ خطا در ارسال پیام: {e}")


def send_telegram_csv_attachment(
    file_path: str, token: str, chat_id: str, caption: str
):
    if not os.path.exists(file_path):
        return

    boundary = "----MarketHunterBoundaryXYZ"
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="deals.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30):
            print("📎 فایل اکسل CSV نیز به تلگرام ارسال شد.")
    except Exception as e:
        print(f"⚠️ خطا در ارسال فایل اکسل: {e}")


# ==========================================
# 🚀 اجرای اصلی اسکرپر
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()

    print("\n" + "═" * 65)
    print("  🔥 MARKETAPP TELEGRAM NFT DEAL HUNTER PRO 🔥")
    print(f"  🎯 هدف: پیدا کردن {CONFIG['TARGET_DEALS_COUNT']} گیفت با تخفیف ≥ ۵۰٪")
    print("═" * 65 + "\n")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception:
            browser = await p.chromium.launch(headless=True, channel="chrome")

        page = await browser.new_page()
        print("🌐 در حال بارگذاری MarketApp...")
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
                            rarity = detect_rarity_badge(item_num)

                            deal = {
                                "name": f"{gift_name} #{item_num}",
                                "gift_title": gift_name,
                                "number": item_num,
                                "discount": f"-{discount_val}%",
                                "discount_num": discount_val,
                                "price_per_day": "0.01",
                                "tg_link": tg_link,
                                "market_link": full_link,
                                "rarity": rarity,
                            }

                            seen_links.add(full_link)
                            deals_found.append(deal)

                            rare_flag = (
                                f" | 💎 {rarity}" if rarity else ""
                            )
                            print(
                                f"🎯 [{len(deals_found)}/{CONFIG['TARGET_DEALS_COUNT']}] "
                                f"{deal['name']} ({deal['discount']}){rare_flag}"
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

        # ذخیره فایل CSV
        sorted_deals = sorted(
            deals_found, key=lambda x: (x["rarity"] == "", -x["discount_num"])
        )

        with open(
            CONFIG["EXPORT_CSV"], "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "ردیف",
                    "نام گیفت",
                    "شماره",
                    "تخفیف",
                    "کمیابی",
                    "قیمت روزانه",
                    "لینک تلگرام",
                    "لینک مارکت",
                ]
            )
            for idx, d in enumerate(sorted_deals, 1):
                writer.writerow(
                    [
                        idx,
                        d["gift_title"],
                        d["number"],
                        d["discount"],
                        d["rarity"] or "معمولی",
                        d["price_per_day"],
                        d["tg_link"],
                        d["market_link"],
                    ]
                )

        # ارسال پیام‌ها به تلگرام
        send_telegram_package(deals_found)


if __name__ == "__main__":
    asyncio.run(main())
