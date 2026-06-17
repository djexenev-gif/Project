import asyncio
import logging
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

TOKEN = "8736773902:AAHghP2lzWA63PxsJkioKcpxoRNLvOg8NkA"

bot = Bot(token=TOKEN)
dp = Dispatcher()

DEX_API_BASE = "https://api.dexscreener.com"

SUPPORTED_CHAINS = {
    "solana",
    "ethereum",
    "bsc",
    "base",
    "arbitrum",
    "polygon",
    "avalanche",
    "optimism",
    "fantom",
}


async def ds_get_pairs_by_token(chain: str, token_address: str) -> Optional[dict]:
    """
    Берём пары по адресу токена:
    GET /latest/dex/tokens/{tokenAddress}[web:55][web:133]
    Потом фильтруем по chainId.
    """
    url = f"{DEX_API_BASE}/latest/dex/tokens/{token_address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            logging.info(f"DexScreener tokens status={resp.status} url={resp.url}")
            if resp.status != 200:
                return None
            data = await resp.json()
            pairs = data.get("pairs") or []
            pairs = [p for p in pairs if p.get("chainId") == chain]
            if not pairs:
                return None
            # берем самую "топовую" пару (первая в списке)
            p = pairs[0]
            buys = int(p.get("txns", {}).get("h24", {}).get("buys", 0))
            sells = int(p.get("txns", {}).get("h24", {}).get("sells", 0))
            return {
                "chainId": p.get("chainId"),
                "dexId": p.get("dexId"),
                "pairAddress": p.get("pairAddress"),
                "baseSymbol": p.get("baseToken", {}).get("symbol"),
                "baseName": p.get("baseToken", {}).get("name"),
                "baseAddress": p.get("baseToken", {}).get("address"),
                "priceUsd": float(p.get("priceUsd") or 0),
                "liquidityUsd": float(p.get("liquidity", {}).get("usd") or 0),
                "volume24h": float(p.get("volume", {}).get("h24") or 0),
                "fdv": float(p.get("fdv") or 0),
                "txns24h": buys + sells,
                "priceChange24h": float(p.get("priceChange", {}).get("h24") or 0),
                "url": f"https://dexscreener.com/{p.get('chainId')}/{p.get('pairAddress')}",
            }


def calc_risk(liq: float, vol24: float, fdv: float, txns24: int, change24: float) -> int:
    """
    Более мягкая эвристика риска:
    - для крупной ликвидности/каппы риск падает,
    - для топовых монет риск не будет 80–90 сразу.[web:55][web:120]
    """
    risk = 0

    # Ликвидность
    if liq < 5_000:
        risk += 35
    elif liq < 50_000:
        risk += 20
    elif liq < 250_000:
        risk += 10
    elif liq < 1_000_000:
        risk += 5
    # если ликвидность > 1M — ничего не добавляем (для норм альткоинов/мажоров)

    # Объём 24ч
    if vol24 < 20_000:
        risk += 25
    elif vol24 < 200_000:
        risk += 15
    elif vol24 < 1_000_000:
        risk += 8
    elif vol24 < 10_000_000:
        risk += 3

    # FDV / МКап
    if fdv < 10_000:
        risk += 15
    elif fdv < 100_000:
        risk += 10
    elif fdv < 1_000_000:
        risk += 5

    # Транзакции 24ч
    if txns24 < 100:
        risk += 15
    elif txns24 < 1_000:
        risk += 8
    elif txns24 < 10_000:
        risk += 3

    # Волатильность 24ч
    if abs(change24) > 80:
        risk += 20
    elif abs(change24) > 40:
        risk += 12
    elif abs(change24) > 20:
        risk += 6

    # Лёгкий "оверфит": если ликвидность и объём очень большие,
    # чуть снижаем суммарный риск, чтобы топовые монеты не были как скам.
    if liq > 5_000_000 and vol24 > 10_000_000:
        risk -= 15
    elif liq > 1_000_000 and vol24 > 5_000_000:
        risk -= 8

    return max(0, min(100, risk))


def opinion_text(risk: int) -> str:
    if risk >= 80:
        return "Очень высокий риск. Похоже на чистую лотерею или потенциальный скам/слив."
    if risk >= 60:
        return "Высокий риск. Можно рассматривать только как спекуляцию маленьким объёмом."
    if risk >= 40:
        return "Средний риск. Типичное рисковое активо: может сильно вырасти, но и упасть также легко."
    if risk >= 20:
        return "Риск ниже среднего для волатильного рынка, но сохраняется возможность сильных движений."
    return "По этим метрикам риск выглядит относительно низким, но это не отменяет общую опасность крипты."


@dp.message(CommandStart())
async def start_handler(message: Message):
    chains_txt = ", ".join(sorted(SUPPORTED_CHAINS))
    await message.answer(
        "👋 Привет! Я бот, который по адресу контракта тянет данные с DexScreener "
        "и даёт примерную оценку риска токена.\n\n"
        "Формат:\n"
        "/analyze <chain> <CONTRACT_ADDRESS>\n\n"
        "Примеры:\n"
        "/analyze solana JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN\n"
        "/analyze ethereum 0x...\n"
        "/analyze bsc 0x...\n\n"
        f"Доступные сети сейчас: {chains_txt}\n\n"
        "Я не ограничиваюсь только мем‑коинами — можно кидать любые токены с DexScreener.\n"
        "Это не финансовый совет."
    )


@dp.message(Command("analyze"))
async def analyze_handler(message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        chains_txt = ", ".join(sorted(SUPPORTED_CHAINS))
        await message.answer(
            "Неверный формат.\n\n"
            "Правильно так:\n"
            "/analyze <chain> <CONTRACT_ADDRESS>\n\n"
            "Примеры:\n"
            "/analyze solana JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN\n"
            "/analyze ethereum 0x...\n\n"
            f"Поддерживаемые сети: {chains_txt}"
        )
        return

    chain = parts[1].lower().strip()
    token_address = parts[2].strip()

    if chain not in SUPPORTED_CHAINS:
        chains_txt = ", ".join(sorted(SUPPORTED_CHAINS))
        await message.answer(
            f"Эта сеть не поддерживается.\nСейчас доступны: {chains_txt}"
        )
        return

    await message.answer(f"Ищу пары для токена {token_address} в сети {chain} через DexScreener...")

    data = await ds_get_pairs_by_token(chain, token_address)
    if not data:
        await message.answer("Не нашёл пары для этого контракта на DexScreener. Проверь сеть и адрес.")
        return

    risk = calc_risk(
        data["liquidityUsd"],
        data["volume24h"],
        data["fdv"],
        int(data["txns24h"]),
        data["priceChange24h"],
    )
    opinion = opinion_text(risk)

    text = (
        f"🪙 {data['baseName']} ({data['baseSymbol']})\n"
        f"Сеть: {data['chainId']}\n"
        f"DEX: {data['dexId']}\n"
        f"Пара: {data['pairAddress']}\n"
        f"Контракт: {data['baseAddress']}\n\n"
        f"💵 Цена: {data['priceUsd']:.8f} $\n"
        f"💧 Ликвидность: {data['liquidityUsd']:.0f} $\n"
        f"📈 Объём 24ч: {data['volume24h']:.0f} $\n"
        f"🏦 FDV: {data['fdv']:.0f} $\n"
        f"🔄 Транзакций 24ч: {data['txns24h']}\n"
        f"📉 Изменение цены 24ч: {data['priceChange24h']:.2f}%\n\n"
        f"⚠️ Оценка риска: {risk}%\n\n"
        f"Моё мнение:\n{opinion}\n\n"
        f"Ссылка на пару: {data['url']}\n\n"
        "Это не финансовый совет. Делай свой ресёрч."
    )

    await message.answer(text)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())