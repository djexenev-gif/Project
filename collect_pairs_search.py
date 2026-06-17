import asyncio
import csv
import os
from typing import Dict, Any, List, Set

import aiohttp

DEX_API_BASE = "https://api.dexscreener.com"
ALL_PAIRS_CSV = "all_pairs.csv"

# Разные запросы, чтобы охватить много мемок
SEARCH_QUERIES = [
    # Базовые стейблы / пары
    "SOL/USDC",
    "SOL/USDT",
    "ETH/USDC",
    "ETH/USDT",
    "WETH/USDC",
    "WETH/USDT",
    "BTC/USDC",
    "BTC/USDT",

    "USDC",
    "USDT",
    "DAI",
    "WETH",
    "WBTC",

    # Классические мемы
    "DOGE",
    "SHIB",
    "PEPE",
    "FLOKI",
    "BONK",
    "WIF",
    "SAMO",
    "MOG",
    "HOGE",
    "SAFEMOON",
    "BABYDOGE",

    # Солана / Pump.fun вайб
    "SOL",
    "PUMP",
    "PUMP.FUN",
    "JUP",
    "RAY",
    "RAYDIUM",
    "ORCA",
    "PHOTON",
    "JITO",
    "DRIFT",
    "MOON",
    "LAMBO",
    "CAT",
    "DOG",
    "INU",
    "COIN",
    "MEME",
    "DEGEN",

    # Популярные форматки тикеров
    "/SOL",
    "/USDC",
    "/USDT",
    "/WETH",
    "/ETH",
    "/BTC",

    # Хайп/хомяк‑слова
    "100x",
    "10x",
    "1000x",
    "GEM",
    "GEMS",
    "MOONSHOT",
    "MOONER",
    "PONZI",
    "RUG",
    "RUGPULL",
    "SCAM",
    "DEGEN",
    "APE",
    "APED",
    "APING",
    "FOMO",
    "PUMP",
    "DUMP",
    "PUMP&DUMP",
    "PUMP AND DUMP",

    # Животные
    "CAT",
    "DOG",
    "INU",
    "SHIBA",
    "SHIB",
    "KITTY",
    "TIGER",
    "PANDA",
    "MONKEY",
    "APE",
    "GORILLA",
    "BANANA",
    "PEPE",
    "FROG",

    # Крипто‑слэнг / мем‑штуки
    "WAGMI",
    "NGMI",
    "GM",
    "GN",
    "REKT",
    "DEGEN",
    "BASED",
    "CLOWN",
    "CLOWN",
    "CLOWNCOIN",
    "CLOWN COIN",
    "ELON",
    "MUSK",
    "TRUMP",
    "BIDEN",
    "PRESIDENT",
    "KIM",
    "PUTIN",

    # Токены с явно мемными названиями
    "MEME",
    "MEMECOIN",
    "MEME COIN",
    "SHIT",
    "SHITCOIN",
    "SHIT COIN",
    "RUG",
    "RUGPULL",
    "SAFU",
    "NOTSAFU",
    "EXIT",
    "EXITSCAM",
    "CASINO",
    "LOTTO",
    "GAMBLE",
    "DEFLATIONARY",
    "HYPERDEFLATIONARY",

    # Базовые по сетям (Solana / Base / ETH)
    "SOLANA",
    "BASE",
    "ARBITRUM",
    "OPTIMISM",
    "BSC",
    "BNB",
    "POLYGON",
    "MATIC",

    # Форматы с разделителями
    "PEPE/USDC",
    "DOGE/USDC",
    "SHIB/USDC",
    "BONK/USDC",
    "WIF/USDC",
    "MEME/USDC",
    "DEGEN/USDC",
    "PEPE/SOL",
    "BONK/SOL",
    "DOGE/SOL",

    # Всякие «хайповые» сочетания
    "AI",
    "GPT",
    "BOT",
    "TRADING BOT",
    "SNIPER",
    "SNIPER BOT",
    "FRONTRUN",
    "ALPHA",
    "INSIDER",
    "INSIDER TRADING",
    "LAUNCH",
    "LAUNCHPAD",
    "FAIRLAUNCH",
    "FAIR LAUNCH",

    # Стёб/мусор
    "ZERO",
    "ZERO TAX",
    "0 TAX",
    "NO TAX",
    "TAXLESS",
    "REBASE",
    "REFLECTION",
    "YIELD",
    "STAKING",
]


FIELDNAMES = [
    "timestamp",
    "chainId",
    "dexId",
    "pairAddress",
    "baseToken_address",
    "baseToken_name",
    "baseToken_symbol",
    "quoteToken_address",
    "quoteToken_name",
    "quoteToken_symbol",
    "liquidity_usd",
    "fdv",
    "marketCap",
    "txns_m5_buys",
    "txns_m5_sells",
    "txns_h1_buys",
    "txns_h1_sells",
    "priceUsd",
    "priceChange_m5",
    "priceChange_h1",
    "priceChange_h6",
    "priceChange_h24",
    "pairCreatedAt_ms",
]

from datetime import datetime


def ensure_csv_exists():
    if not os.path.exists(ALL_PAIRS_CSV):
        with open(ALL_PAIRS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def load_existing_pairs() -> Set[str]:
    if not os.path.exists(ALL_PAIRS_CSV):
        return set()
    existing = set()
    with open(ALL_PAIRS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add(row["pairAddress"])
    return existing


async def fetch_search(session: aiohttp.ClientSession, query: str) -> List[Dict[str, Any]]:
    url = f"{DEX_API_BASE}/latest/dex/search"
    params = {"q": query}
    try:
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status != 200:
                print(f"[{query}] HTTP {resp.status}")
                return []
            data = await resp.json()
            pairs = data.get("pairs") or []
            print(f"[{query}] найдено пар: {len(pairs)}")
            return pairs
    except Exception as e:
        print(f"[{query}] ошибка запроса:", e)
        return []


def pair_to_row(pair: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}
    txns = pair.get("txns") or {}
    m5 = (txns.get("m5") or {})
    h1 = (txns.get("h1") or {})

    liquidity = pair.get("liquidity") or {}
    price_change = pair.get("priceChange") or {}

    row = {
        "timestamp": now_iso,
        "chainId": pair.get("chainId"),
        "dexId": pair.get("dexId"),
        "pairAddress": pair.get("pairAddress"),
        "baseToken_address": base.get("address"),
        "baseToken_name": base.get("name"),
        "baseToken_symbol": base.get("symbol"),
        "quoteToken_address": quote.get("address"),
        "quoteToken_name": quote.get("name"),
        "quoteToken_symbol": quote.get("symbol"),
        "liquidity_usd": (liquidity.get("usd") if liquidity else None),
        "fdv": pair.get("fdv"),
        "marketCap": pair.get("marketCap"),
        "txns_m5_buys": m5.get("buys"),
        "txns_m5_sells": m5.get("sells"),
        "txns_h1_buys": h1.get("buys"),
        "txns_h1_sells": h1.get("sells"),
        "priceUsd": pair.get("priceUsd"),
        "priceChange_m5": (price_change.get("m5") if price_change else None),
        "priceChange_h1": (price_change.get("h1") if price_change else None),
        "priceChange_h6": (price_change.get("h6") if price_change else None),
        "priceChange_h24": (price_change.get("h24") if price_change else None),
        "pairCreatedAt_ms": pair.get("pairCreatedAt"),
    }
    return row


async def main():
    ensure_csv_exists()
    existing = load_existing_pairs()
    print("Уже есть пар:", len(existing))

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_search(session, q) for q in SEARCH_QUERIES]
        results = await asyncio.gather(*tasks)

    now_iso = datetime.utcnow().isoformat()
    new_rows: List[Dict[str, Any]] = []

    for pairs in results:
        for pair in pairs:
            pa = pair.get("pairAddress")
            if not pa or pa in existing:
                continue
            existing.add(pa)
            new_rows.append(pair_to_row(pair, now_iso))

    if not new_rows:
        print("Новых пар нет (все уже были в all_pairs.csv).")
        return

    with open(ALL_PAIRS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        for r in new_rows:
            writer.writerow(r)

    print("Новых пар добавлено:", len(new_rows))
    print("Всего пар теперь:", len(existing))
    print("Файл:", ALL_PAIRS_CSV)


if __name__ == "__main__":
    asyncio.run(main())