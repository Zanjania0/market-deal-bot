import asyncio
import csv
from datetime import datetime
import json
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
    "TARGET_DEALS_COUNT": 100,
    "BASE_DOMAIN": "https://marketapp.org",
    "EXPORT_CSV": "discounts.csv",
    "EXPORT_HTML": "index.html",
    "EXPORT_JSON": "discounts.json",
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
    "GITHUB_REPOSITORY": os.getenv("GITHUB_REPOSITORY", ""),
}


def detect_rarity_badge(number_str: str) -> str:
    """شناسایی هوشمند شماره‌های رند و کمیاب"""
    try:
        num = int(re.sub(r"\D", "", str(number_str)))
    except ValueError:
        return ""

    s = str(num)
    if num < 100:
        return "👑 شماره دو رقمی (نایاب)"
    if num < 1000:
        return f"💎 شماره زیر ۱۰۰۰ (#{num})"
    if len(s) >= 3 and len(set(s)) == 1:
        return f"✨ شماره رند (#{s})"
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
        else "https://t.me"
    )


def calculate_arbitrage(price_per_day: float, discount_val: float) -> dict:
    """محاسبه‌گر حرفه‌ای سود و آربیتراژ"""
    if discount_val >= 100:
        discount_val = 99.0

    original_fair_price = price_per_day / (1.0 - (discount_val / 100.0))
    daily_profit = original_fair_price - price_per_day
    monthly_profit = daily_profit * 30.0
    roi_percent = (
        (daily_profit / price_per_day) * 100.0 if price_per_day > 0 else 0
    )

    return {
        "fair_price": round(original_fair_price, 3),
        "daily_profit": round(daily_profit, 3),
        "monthly_profit": round(monthly_profit, 2),
        "roi_percent": round(roi_percent, 1),
    }


def generate_marketapp_html(deals: List[Dict[str, Any]]):
    """تولید وب‌سایت مدرن GitHub Pages با تم اختصاصی MarketApp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    deals_json = json.dumps(deals, ensure_ascii=False)

    max_discount = max([d.get("discount_num", 0) for d in deals] or [0])
    rare_count = sum(1 for d in deals if d.get("rarity"))
    max_roi = max(
        [d.get("arbitrage", {}).get("roi_percent", 0) for d in deals] or [0]
    )

    html_template = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MarketApp Gift Sniper | داشبورد تخفیف و آربیتراژ</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;700;900&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Vazirmatn', sans-serif;
            background-color: #0b0f19;
            color: #f3f4f6;
        }
        .glass {
            background: rgba(17, 24, 39, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .card-hover:hover {
            transform: translateY(-4px);
            border-color: rgba(59, 130, 246, 0.4);
            box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.2);
        }
    </style>
</head>
<body class="min-h-screen pb-16">
    <!-- هدر سایت -->
    <header class="sticky top-0 z-50 glass border-b border-gray-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-xl font-bold shadow-lg shadow-blue-500/30">
                    🎁
                </div>
                <div>
                    <h1 class="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-300">MarketApp Gift Sniper</h1>
                    <p class="text-xs text-gray-400">داشبورد هوشمند شکار تخفیف و آربیتراژ</p>
                </div>
            </div>
            <div class="text-left">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    بروزرسانی زنده
                </span>
                <p class="text-[11px] text-gray-400 mt-1">__TIMESTAMP__</p>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <!-- داشبورد آماری -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="glass p-5 rounded-2xl">
                <p class="text-xs text-gray-400 mb-1">تعداد گیفت‌های تخفیف‌دار</p>
                <p class="text-2xl font-black text-blue-400">__TOTAL_COUNT__ <span class="text-sm font-normal text-gray-400">مورد</span></p>
            </div>
            <div class="glass p-5 rounded-2xl">
                <p class="text-xs text-gray-400 mb-1">بیشترین درصد تخفیف</p>
                <p class="text-2xl font-black text-rose-400">-__MAX_DISCOUNT__%</p>
            </div>
            <div class="glass p-5 rounded-2xl">
                <p class="text-xs text-gray-400 mb-1">موارد کمیاب و خاص</p>
                <p class="text-2xl font-black text-amber-400">__RARE_COUNT__ <span class="text-sm font-normal text-gray-400">گیفت</span></p>
            </div>
            <div class="glass p-5 rounded-2xl">
                <p class="text-xs text-gray-400 mb-1">بیشترین بازدهی سود (ROI)</p>
                <p class="text-2xl font-black text-emerald-400">+__MAX_ROI__%</p>
            </div>
        </div>

        <!-- نوار فیلتر و جستجو -->
        <div class="glass p-4 rounded-2xl mb-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="relative w-full md:w-80">
                <i class="fa-solid fa-magnifying-glass absolute right-4 top-3.5 text-gray-400 text-sm"></i>
                <input type="text" id="searchInput" placeholder="جستجوی نام گیفت یا شماره..." 
                       class="w-full bg-gray-900/80 border border-gray-700/60 rounded-xl pr-11 pl-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition">
            </div>

            <div class="flex flex-wrap items-center gap-2 w-full md:w-auto">
                <button onclick="filterDeals('all')" class="filter-btn active px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 text-white transition">همه (__TOTAL_COUNT__)</button>
                <button onclick="filterDeals('rare')" class="filter-btn px-4 py-2 rounded-xl text-xs font-semibold bg-gray-800 text-gray-300 hover:bg-gray-700 transition">💎 فقط کمیاب‌ها</button>
                <button onclick="filterDeals('mega')" class="filter-btn px-4 py-2 rounded-xl text-xs font-semibold bg-gray-800 text-gray-300 hover:bg-gray-700 transition">🚨 بالای ۷۰٪ تخفیف</button>
                <button onclick="filterDeals('roi')" class="filter-btn px-4 py-2 rounded-xl text-xs font-semibold bg-gray-800 text-gray-300 hover:bg-gray-700 transition">💰 سود بالای ۲۰۰٪</button>
            </div>
        </div>

        <!-- گرید کارت‌های گیفت -->
        <div id="dealsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5"></div>
    </main>

    <script>
        const DEALS = __DEALS_JSON__;
        let currentFilter = 'all';

        function renderCards(items) {
            const container = document.getElementById('dealsGrid');
            if (items.length === 0) {
                container.innerHTML = '<div class="col-span-full py-16 text-center text-gray-400">موردی با این مشخصات یافت نشد.</div>';
                return;
            }

            container.innerHTML = items.map((deal) => {
                const rarityBadge = deal.rarity ? '<span class="absolute top-3 left-3 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">' + deal.rarity + '</span>' : '';
                return `
                <div class="glass rounded-2xl overflow-hidden card-hover transition duration-200 border border-gray-800/80 flex flex-col justify-between">
                    <div>
                        <div class="relative bg-gradient-to-b from-gray-800/50 to-transparent p-6 flex items-center justify-center min-h-[190px]">
                            <span class="absolute top-3 right-3 px-2.5 py-1 rounded-lg text-xs font-extrabold bg-rose-500/90 text-white shadow-lg shadow-rose-500/30">
                                ${deal.discount}
                            </span>
                            ${rarityBadge}
                            <img src="${deal.image_url}" alt="${deal.name}" class="w-28 h-28 object-contain filter drop-shadow-[0_8px_16px_rgba(0,0,0,0.5)] transform hover:scale-110 transition duration-300" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>

                        <div class="p-5">
                            <div class="flex items-center justify-between mb-2">
                                <h3 class="font-bold text-base text-white truncate">${deal.name}</h3>
                                <span class="text-xs text-gray-400 bg-gray-800/60 px-2 py-0.5 rounded-md">${deal.days_range} روز</span>
                            </div>

                            <div class="my-3 p-3 rounded-xl bg-gray-900/60 border border-gray-800">
                                <div class="flex items-center justify-between text-xs mb-1.5">
                                    <span class="text-gray-400">قیمت اجاره:</span>
                                    <span class="font-bold text-blue-400">${deal.price_per_day} TON <span class="text-[10px] text-gray-500">/روز</span></span>
                                </div>
                                <div class="flex items-center justify-between text-xs mb-1.5">
                                    <span class="text-gray-400">کف قیمت بازار:</span>
                                    <span class="text-gray-300 line-through">${deal.arbitrage.fair_price} TON</span>
                                </div>
                                <div class="flex items-center justify-between text-xs pt-1.5 border-t border-gray-800">
                                    <span class="text-emerald-400 font-medium">سود تخمینی ماهانه:</span>
                                    <span class="font-black text-emerald-400">+${deal.arbitrage.monthly_profit} TON (${deal.arbitrage.roi_percent}% ROI)</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="px-5 pb-5 pt-0 grid grid-cols-2 gap-2">
                        <a href="${deal.market_link}" target="_blank" class="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition shadow-lg shadow-blue-600/20">
                            <i class="fa-solid fa-cart-shopping text-xs"></i> اجاره
                        </a>
                        <a href="${deal.tg_link}" target="_blank" class="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-bold transition">
                            <i class="fa-brands fa-telegram text-xs"></i> تلگرام
                        </a>
                    </div>
                </div>
                `;
            }).join('');
        }

        function filterDeals(type) {
            currentFilter = type;
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white');
                btn.classList.add('bg-gray-800', 'text-gray-300');
            });
            event.target.classList.remove('bg-gray-800', 'text-gray-300');
            event.target.classList.add('bg-blue-600', 'text-white');
            applyFilters();
        }

        function applyFilters() {
            const query = document.getElementById('searchInput').value.trim().toLowerCase();
            let filtered = DEALS.filter(d => {
                const matchQuery = d.name.toLowerCase().includes(query) || d.number.includes(query);
                if (!matchQuery) return false;
                if (currentFilter === 'rare') return d.rarity !== '';
                if (currentFilter === 'mega') return d.discount_num >= 70;
                if (currentFilter === 'roi') return d.arbitrage.roi_percent >= 200;
                return true;
            });
            renderCards(filtered);
        }

        document.getElementById('searchInput').addEventListener('input', applyFilters);
        renderCards(DEALS);
    </script>
</body>
</html>"""

    html_content = (
        html_template.replace("__TIMESTAMP__", timestamp)
        .replace("__TOTAL_COUNT__", str(len(deals)))
        .replace("__MAX_DISCOUNT__", str(max_discount))
        .replace("__RARE_COUNT__", str(rare_count))
        .replace("__MAX_ROI__", str(max_roi))
        .replace("__DEALS_JSON__", deals_json)
    )

    with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)


def send_telegram_package(deals: List[Dict[str, Any]]):
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    rare_deals = [d for d in deals if d["rarity"]]
    normal_deals = [d for d in deals if not d["rarity"]]
    discounts = [d["discount_num"] for d in deals]
    avg_discount = sum(discounts) / len(discounts) if discounts else 0
    max_discount = max(discounts) if discounts else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    gh_repo = CONFIG.get("GITHUB_REPOSITORY", "")
    pages_url = (
        f"https://{gh_repo.split('/')[0]}.github.io/{gh_repo.split('/')[1]}/"
        if "/" in gh_repo
        else "صفحه GitHub Pages شما"
    )

    full_text = (
        f"👑 <b>گزارش تحلیلی گیفت‌های تخفیف‌دار MarketApp</b>\n"
        f"📅 <i>{timestamp}</i>\n"
        f"🌐 <b>داشبورد گرافیکی آنلاین:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>تعداد کل:</b> {len(deals)} مورد\n"
        f"💎 <b>موارد کمیاب:</b> {len(rare_deals)} مورد\n"
        f"🔥 <b>بیشترین تخفیف:</b> -{max_discount}%\n"
        f"📉 <b>میانگین تخفیف:</b> -{avg_discount:.1f}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    if rare_deals:
        full_text += f"💎 <b>━━━ موارد کمیاب ({len(rare_deals)} مورد) ━━━</b>\n\n"
        for idx, d in enumerate(rare_deals, 1):
            full_text += (
                f"<b>{idx}. {d['name']}</b>\n"
                f"   🏆 <b>{d['rarity']}</b>\n"
                f"   🏷️ تخفیف: <code>{d['discount']}</code> | 💰 {d['price_per_day']} TON\n"
                f"   📈 <b>سود ماهانه:</b> +{d['arbitrage']['monthly_profit']} TON ({d['arbitrage']['roi_percent']}% ROI)\n"
                f"   🔗 <a href='{d['tg_link']}'>تلگرام</a> | <a href='{d['market_link']}'>مارکت‌اپ</a>\n\n"
            )

    links_text = (
        f"📋 <b>━━━ لیست فقط لینک‌های تلگرام ({len(deals)} مورد) ━━━</b>\n\n"
    )
    for idx, d in enumerate(deals, 1):
        links_text += f"{idx}. {d['tg_link']}\n"

    send_chunks_to_telegram(full_text, token, chat_id)
    time.sleep(1)
    send_chunks_to_telegram(links_text, token, chat_id)
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
        except Exception:
            pass


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
            pass
    except Exception:
        pass


# ==========================================
# 🚀 موتور اصلی اسکرپر
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()

    print("\n" + "═" * 65)
    print("  🔥 MARKETAPP TELEGRAM NFT DEAL HUNTER PRO 🔥")
    print(
        f"  🎯 هدف: استخراج ۱۰۰ گیفت تخفیف‌دار با محاسبه آربیتراژ و ساخت سایت"
    )
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
                            rarity = detect_rarity_badge(item_num)

                            img_el = card.locator("img").first
                            img_src = (
                                await img_el.get_attribute("src")
                                if await img_el.count() > 0
                                else "https://marketapp.org/favicon.ico"
                            )

                            price_per_day = 0.01
                            arbitrage = calculate_arbitrage(
                                price_per_day, discount_val
                            )

                            deal = {
                                "name": f"{gift_name} #{item_num}",
                                "gift_title": gift_name,
                                "number": item_num,
                                "discount": f"-{discount_val}%",
                                "discount_num": discount_val,
                                "price_per_day": price_per_day,
                                "days_range": days_range,
                                "tg_link": tg_link,
                                "market_link": full_link,
                                "image_url": img_src,
                                "rarity": rarity,
                                "arbitrage": arbitrage,
                            }

                            seen_links.add(full_link)
                            deals_found.append(deal)

                            rare_flag = (
                                f" | 💎 {rarity}" if rarity else ""
                            )
                            print(
                                f"🎯 [{len(deals_found)}/{CONFIG['TARGET_DEALS_COUNT']}] "
                                f"{deal['name']} ({deal['discount']}) | سود: +{arbitrage['monthly_profit']} TON{rare_flag}"
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

        # ساخت وب‌سایت
        generate_marketapp_html(deals_found)

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
                    "کف قیمت تخمینی",
                    "سود ماهانه (TON)",
                    "درصد بازدهی (ROI)",
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
                        d["arbitrage"]["fair_price"],
                        d["arbitrage"]["monthly_profit"],
                        f"{d['arbitrage']['roi_percent']}%",
                        d["tg_link"],
                        d["market_link"],
                    ]
                )

        print("\n✅ وب‌سایت و فایل‌های اکسل با موفقیت ایجاد شدند.")
        send_telegram_package(deals_found)


if __name__ == "__main__":
    asyncio.run(main())
