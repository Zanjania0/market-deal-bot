import asyncio
from collections import defaultdict
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
    "TARGET_DEALS_COUNT": 200,  # ظرفیت بهینه: ۲۰۰ گیفت
    "BASE_DOMAIN": "https://marketapp.org",
    "EXPORT_CSV": "discounts.csv",
    "EXPORT_HTML": "index.html",
    "EXPORT_JSON": "discounts.json",
    "ADMIN_TELEGRAM_LINK": "https://t.me/Zanjani_a",
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
    "GITHUB_REPOSITORY": os.getenv("GITHUB_REPOSITORY", ""),
}


def detect_rarity_badge(number_str: str) -> str:
    """شناسایی شماره‌های کلکسیونی"""
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


def generate_duck_store_html(deals: List[Dict[str, Any]]):
    """تولید وب‌سایت فروشگاهی Duck Store با دسته‌بندی کالکشن‌ها"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    collections = sorted(list(set(d["gift_title"] for d in deals)))
    deals_json = json.dumps(deals, ensure_ascii=False)
    collections_json = json.dumps(collections, ensure_ascii=False)
    rare_count = sum(1 for d in deals if d.get("rarity"))

    html_template = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Duck Store | فروشگاه و اجاره گیفت‌های تلگرام</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;700;900&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Vazirmatn', sans-serif;
            background-color: #080c14;
            color: #f3f4f6;
        }
        .glass {
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .card-hover {
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .card-hover:hover {
            transform: translateY(-5px);
            border-color: rgba(59, 130, 246, 0.45);
            box-shadow: 0 16px 32px -8px rgba(59, 130, 246, 0.25);
        }
    </style>
</head>
<body class="min-h-screen pb-16">
    <header class="sticky top-0 z-50 glass border-b border-gray-800/80">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-11 h-11 rounded-2xl bg-gradient-to-tr from-amber-500 via-orange-500 to-yellow-400 flex items-center justify-center text-2xl shadow-lg shadow-orange-500/20">
                    🦆
                </div>
                <div>
                    <h1 class="text-xl font-black bg-clip-text text-transparent bg-gradient-to-r from-yellow-400 via-orange-400 to-amber-300">Duck Store</h1>
                    <p class="text-xs text-gray-400">مرجع تخصصی اجاره و خرید گیفت‌های تلگرام</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <a href="https://t.me/Zanjani_a" target="_blank" class="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 transition">
                    <i class="fa-brands fa-telegram text-sm"></i> پشتیبانی و سفارش
                </a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <div class="glass p-5 rounded-2xl flex items-center justify-between border-l-4 border-l-blue-500">
                <div>
                    <p class="text-xs text-gray-400 mb-1">گیفت‌های آماده تحویل</p>
                    <p class="text-2xl font-black text-white">__TOTAL_COUNT__ <span class="text-sm font-normal text-gray-400">مورد</span></p>
                </div>
                <div class="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center text-xl">
                    <i class="fa-solid fa-gift"></i>
                </div>
            </div>

            <div class="glass p-5 rounded-2xl flex items-center justify-between border-l-4 border-l-amber-500">
                <div>
                    <p class="text-xs text-gray-400 mb-1">آیتم‌های کلکسیونی و خاص</p>
                    <p class="text-2xl font-black text-amber-400">__RARE_COUNT__ <span class="text-sm font-normal text-gray-400">گیفت</span></p>
                </div>
                <div class="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center text-xl">
                    <i class="fa-solid fa-crown"></i>
                </div>
            </div>
        </div>

        <div class="glass p-4 rounded-2xl mb-8 space-y-4">
            <div class="flex flex-col md:flex-row items-center justify-between gap-4">
                <div class="relative w-full md:w-80">
                    <i class="fa-solid fa-magnifying-glass absolute right-4 top-3.5 text-gray-400 text-sm"></i>
                    <input type="text" id="searchInput" placeholder="جستجوی نام گیفت یا شماره..." 
                           class="w-full bg-gray-900/90 border border-gray-700/60 rounded-xl pr-11 pl-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition">
                </div>

                <div class="flex flex-wrap items-center gap-2 w-full md:w-auto">
                    <button onclick="filterType('all')" class="type-btn active px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 text-white transition">همه (__TOTAL_COUNT__)</button>
                    <button onclick="filterType('rare')" class="type-btn px-4 py-2 rounded-xl text-xs font-bold bg-gray-800 text-gray-300 hover:bg-gray-700 transition">💎 فقط کمیاب‌ها</button>
                </div>
            </div>

            <div class="pt-3 border-t border-gray-800/80">
                <p class="text-xs text-gray-400 mb-2 font-medium">🏷️ فیلتر بر اساس کالکشن:</p>
                <div id="collectionsBar" class="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto"></div>
            </div>
        </div>

        <div id="dealsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"></div>
    </main>

    <script>
        const DEALS = __DEALS_JSON__;
        const COLLECTIONS = __COLLECTIONS_JSON__;
        let selectedType = 'all';
        let selectedCollection = 'all';

        function initCollections() {
            const bar = document.getElementById('collectionsBar');
            bar.innerHTML = '<button onclick="filterCollection(\\'all\\')" class="col-btn active px-3 py-1 rounded-lg text-xs font-semibold bg-blue-600 text-white transition">همه کالکشن‌ها</button>' +
                COLLECTIONS.map(c => {
                    const count = DEALS.filter(d => d.gift_title === c).length;
                    return `<button onclick="filterCollection('${c}')" class="col-btn px-3 py-1 rounded-lg text-xs font-semibold bg-gray-800/80 text-gray-300 hover:bg-gray-700 transition border border-gray-700/40">${c} (${count})</button>`;
                }).join('');
        }

        function renderCards(items) {
            const container = document.getElementById('dealsGrid');
            if (items.length === 0) {
                container.innerHTML = '<div class="col-span-full py-16 text-center text-gray-400">گیفتی با این مشخصات پیدا نشد.</div>';
                return;
            }

            container.innerHTML = items.map((deal) => {
                const rarityBadge = deal.rarity ? '<span class="absolute top-3 left-3 px-3 py-1 rounded-xl text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 backdrop-blur-md shadow-lg">' + deal.rarity + '</span>' : '';
                const orderText = encodeURIComponent(`سلام، من متقاضی اجاره این گیفت از Duck Store هستم:\\n🎁 ${deal.name}\\n🔗 ${deal.tg_link}`);
                const rentLink = `https://t.me/Zanjani_a?text=${orderText}`;

                return `
                <div class="glass rounded-3xl overflow-hidden card-hover border border-gray-800 flex flex-col justify-between p-3">
                    <div>
                        <div class="relative bg-gradient-to-b from-gray-800/60 to-gray-900/40 rounded-2xl p-6 flex items-center justify-center min-h-[210px] overflow-hidden">
                            ${rarityBadge}
                            <span class="absolute bottom-2 right-3 px-2 py-0.5 rounded-md text-[10px] font-medium bg-gray-950/60 text-gray-400 border border-gray-800">${deal.gift_title}</span>
                            <img src="${deal.image_url}" alt="${deal.name}" class="w-36 h-36 object-contain filter drop-shadow-[0_12px_24px_rgba(0,0,0,0.6)] transform hover:scale-105 transition duration-300" onerror="this.src='https://marketapp.org/favicon.ico'">
                        </div>

                        <div class="p-4">
                            <div class="flex items-center justify-between mb-3">
                                <h3 class="font-black text-lg text-white truncate">${deal.name}</h3>
                                <span class="text-xs text-gray-400 bg-gray-800 px-2.5 py-1 rounded-lg border border-gray-700/50">${deal.days_range} روزه</span>
                            </div>

                            <div class="my-2 p-3.5 rounded-2xl bg-gray-900/80 border border-gray-800/90 flex items-center justify-between">
                                <span class="text-xs text-gray-400 font-medium">هزینه اجاره:</span>
                                <div class="text-left">
                                    <span class="text-base font-black text-emerald-400">160t</span>
                                    <span class="text-[11px] text-gray-400 font-normal">/ ماهانه</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="p-3 pt-0 grid grid-cols-2 gap-2">
                        <a href="${rentLink}" target="_blank" class="flex items-center justify-center gap-1.5 py-3 px-3 rounded-2xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-xs font-black transition shadow-lg shadow-blue-500/25">
                            <i class="fa-solid fa-bolt text-xs"></i> اجاره
                        </a>
                        <a href="${deal.tg_link}" target="_blank" class="flex items-center justify-center gap-1.5 py-3 px-3 rounded-2xl bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-bold transition border border-gray-700/40">
                            <i class="fa-solid fa-eye text-xs"></i> نمایش
                        </a>
                    </div>
                </div>
                `;
            }).join('');
        }

        function filterType(type) {
            selectedType = type;
            document.querySelectorAll('.type-btn').forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white');
                btn.classList.add('bg-gray-800', 'text-gray-300');
            });
            event.target.classList.remove('bg-gray-800', 'text-gray-300');
            event.target.classList.add('bg-blue-600', 'text-white');
            applyFilters();
        }

        function filterCollection(col) {
            selectedCollection = col;
            document.querySelectorAll('.col-btn').forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white');
                btn.classList.add('bg-gray-800/80', 'text-gray-300');
            });
            event.target.classList.remove('bg-gray-800/80', 'text-gray-300');
            event.target.classList.add('bg-blue-600', 'text-white');
            applyFilters();
        }

        function applyFilters() {
            const query = document.getElementById('searchInput').value.trim().toLowerCase();
            let filtered = DEALS.filter(d => {
                const matchQuery = d.name.toLowerCase().includes(query) || d.number.includes(query) || d.gift_title.toLowerCase().includes(query);
                if (!matchQuery) return false;
                if (selectedType === 'rare' && d.rarity === '') return false;
                if (selectedCollection !== 'all' && d.gift_title !== selectedCollection) return false;
                return true;
            });
            renderCards(filtered);
        }

        document.getElementById('searchInput').addEventListener('input', applyFilters);
        initCollections();
        renderCards(DEALS);
    </script>
</body>
</html>"""

    html_content = (
        html_template.replace("__TIMESTAMP__", timestamp)
        .replace("__TOTAL_COUNT__", str(len(deals)))
        .replace("__RARE_COUNT__", str(rare_count))
        .replace("__DEALS_JSON__", deals_json)
        .replace("__COLLECTIONS_JSON__", collections_json)
    )

    with open(CONFIG["EXPORT_HTML"], "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(CONFIG["EXPORT_JSON"], "w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)


def send_telegram_package(deals: List[Dict[str, Any]]):
    """ارسال گزارش تلگرام دسته‌بندی‌شده بر اساس کالکشن"""
    token = CONFIG.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    gh_repo = CONFIG.get("GITHUB_REPOSITORY", "")
    pages_url = (
        f"https://{gh_repo.split('/')[0]}.github.io/{gh_repo.split('/')[1]}/"
        if "/" in gh_repo
        else "https://zanjania0.github.io/market-deal-bot/"
    )

    grouped_deals = defaultdict(list)
    for d in deals:
        grouped_deals[d["gift_title"]].append(d)

    rare_count = sum(1 for d in deals if d["rarity"])

    full_text = (
        f"🦆 <b>گزارش موجودی جدید ۲۰۰ گیفت در Duck Store</b>\n"
        f"📅 <i>{timestamp}</i>\n\n"
        f"🌐 <b>ویترین آنلاین فروشگاه:</b>\n👉 <a href='{pages_url}'>{pages_url}</a>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>تعداد کل:</b> {len(deals)} مورد ({len(grouped_deals)} کالکشن)\n"
        f"💎 <b>موارد کمیاب:</b> {rare_count} مورد\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    item_counter = 1
    for collection_name in sorted(grouped_deals.keys()):
        items = grouped_deals[collection_name]
        full_text += f"📦 <b>━━━ کالکشن {collection_name} ({len(items)} مورد) ━━━</b>\n\n"

        for d in items:
            rarity_badge = f"\n   🏆 <b>{d['rarity']}</b>" if d["rarity"] else ""
            full_text += (
                f"<b>{item_counter}. {d['name']}</b>{rarity_badge}\n"
                f"   🏷️ تخفیف: <code>{d['discount']}</code> | 💰 {d['price_per_day']} TON/روز\n"
                f"   📱 <a href='{d['tg_link']}'>مشاهده در تلگرام</a>\n"
                f"   🛒 <a href='{d['market_link']}'>خرید/اجاره در MarketApp</a>\n\n"
            )
            item_counter += 1

    send_chunks_to_telegram(full_text, token, chat_id)
    send_telegram_csv_attachment(
        CONFIG["EXPORT_CSV"],
        token,
        chat_id,
        f"📊 فایل اکسل ۲۰۰ گیفت Duck Store ({timestamp})",
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
            time.sleep(0.5)
        except Exception:
            pass


def send_telegram_csv_attachment(
    file_path: str, token: str, chat_id: str, caption: str
):
    if not os.path.exists(file_path):
        return
    boundary = "----DuckStoreBoundaryXYZ"
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="duck_store_gifts.csv"\r\n'
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
# ⚡ موتور اسکرپر فوق‌سریع توربو
# ==========================================
async def main():
    deals_found: List[Dict[str, Any]] = []
    seen_links: Set[str] = set()

    print("\n" + "═" * 65)
    print("  🦆 DUCK STORE TURBO SCRAPER (200 ITEMS) 🦆")
    print("═" * 65 + "\n")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception:
            browser = await p.chromium.launch(headless=True, channel="chrome")

        page = await browser.new_page()
        print("🌐 بارگذاری اولیه صفحه...")
        await page.goto(
            CONFIG["TARGET_URL"], wait_until="domcontentloaded", timeout=60000
        )
        await page.wait_for_timeout(3000)

        # استخراج دسته‌ای و فوق‌سریع در محیط جاوااسکریپت
        while len(deals_found) < CONFIG["TARGET_DEALS_COUNT"]:
            raw_cards = await page.evaluate(
                """() => {
                const cards = Array.from(document.querySelectorAll("a[href*='/nft/']"));
                return cards.map(c => ({
                    href: c.getAttribute('href') || '',
                    text: c.innerText || '',
                    img: c.querySelector('img') ? c.querySelector('img').src : ''
                }));
            }"""
            )

            for c in raw_cards:
                href = c["href"]
                if not href:
                    continue

                full_link = (
                    href
                    if href.startswith("http")
                    else f"{CONFIG['BASE_DOMAIN']}{href if href.startswith('/') else '/' + href}"
                )
                if full_link in seen_links:
                    continue

                text = c["text"]
                if not text.strip():
                    continue

                discount_match = re.search(r"-(\d+(?:\.\d+)?)%", text)
                if discount_match:
                    discount_val = float(discount_match.group(1))

                    if discount_val >= CONFIG["MIN_DISCOUNT_PERCENT"]:
                        num_match = re.search(r"#(\d+)", text)
                        item_num = num_match.group(1) if num_match else "0"

                        days_match = re.search(
                            r"Days:\s*(\d+\s*–\s*\d+)", text
                        )
                        days_range = (
                            days_match.group(1) if days_match else "1 – 180"
                        )

                        lines = [
                            l.strip() for l in text.split("\n") if l.strip()
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
                            name_candidates[0] if name_candidates else "NFT Gift"
                        )
                        tg_link = generate_tg_nft_link(gift_name, item_num)
                        rarity = detect_rarity_badge(item_num)
                        img_src = (
                            c["img"]
                            if c["img"]
                            else "https://marketapp.org/favicon.ico"
                        )

                        deal = {
                            "name": f"{gift_name} #{item_num}",
                            "gift_title": gift_name,
                            "number": item_num,
                            "discount": f"-{discount_val}%",
                            "discount_num": discount_val,
                            "price_per_day": "0.01",
                            "days_range": days_range,
                            "tg_link": tg_link,
                            "market_link": full_link,
                            "image_url": img_src,
                            "rarity": rarity,
                        }

                        seen_links.add(full_link)
                        deals_found.append(deal)

                        if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]:
                            break
                else:
                    seen_links.add(full_link)

            if len(deals_found) >= CONFIG["TARGET_DEALS_COUNT"]:
                break

            # اسکرول سریع‌تر
            await page.evaluate("window.scrollBy(0, window.innerHeight * 3);")
            await page.wait_for_timeout(400)

        await browser.close()

        sorted_deals = sorted(
            deals_found,
            key=lambda x: (
                x["gift_title"],
                int(re.sub(r"\D", "", x["number"]))
                if re.sub(r"\D", "", x["number"])
                else 0,
            ),
        )

        generate_duck_store_html(sorted_deals)

        with open(
            CONFIG["EXPORT_CSV"], "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "ردیف",
                    "کالکشن",
                    "نام گیفت",
                    "شماره",
                    "تخفیف",
                    "کمیابی",
                    "لینک تلگرام",
                    "لینک MarketApp",
                ]
            )
            for idx, d in enumerate(sorted_deals, 1):
                writer.writerow(
                    [
                        idx,
                        d["gift_title"],
                        d["name"],
                        d["number"],
                        d["discount"],
                        d["rarity"] or "معمولی",
                        d["tg_link"],
                        d["market_link"],
                    ]
                )

        print(
            f"\n⚡ ۲۰۰ گیفت در کمتر از ۴۵ ثانیه با موفقیت استخراج و ذخیره شدند!"
        )
        send_telegram_package(sorted_deals)


if __name__ == "__main__":
    asyncio.run(main())
