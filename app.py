from flask import Flask, request, jsonify
import joblib
import pandas as pd
import requests
import math
import time

DEX_API_BASE = "https://api.dexscreener.com/latest/dex/pairs"
MODEL_PATH = "risk_model.pkl"

model = joblib.load(MODEL_PATH)
app = Flask(__name__)


def build_features_from_pair(pair: dict) -> pd.DataFrame:
    feature_cols = [
        "liquidity_usd",
        "fdv",
        "marketCap",
        "priceUsd",
        "priceChange_m5",
        "priceChange_h1",
        "priceChange_h6",
        "priceChange_h24",
        "txns_m5_buys",
        "txns_m5_sells",
        "txns_h1_buys",
        "txns_h1_sells",
    ]

    txns = pair.get("txns") or {}
    m5 = txns.get("m5") or {}
    h1 = txns.get("h1") or {}
    liq = pair.get("liquidity") or {}
    pc = pair.get("priceChange") or {}

    row = {
        "liquidity_usd": liq.get("usd"),
        "fdv": pair.get("fdv"),
        "marketCap": pair.get("marketCap"),
        "priceUsd": pair.get("priceUsd"),
        "priceChange_m5": pc.get("m5"),
        "priceChange_h1": pc.get("h1"),
        "priceChange_h6": pc.get("h6"),
        "priceChange_h24": pc.get("h24"),
        "txns_m5_buys": m5.get("buys"),
        "txns_m5_sells": m5.get("sells"),
        "txns_h1_buys": h1.get("buys"),
        "txns_h1_sells": h1.get("sells"),
    }

    df = pd.DataFrame([row])
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.fillna(df.median(numeric_only=True))

    return df[feature_cols]


def fetch_pair_by_address(chain: str, pair_address: str) -> dict | None:
    url = f"{DEX_API_BASE}/{chain}/{pair_address}"
    try:
        resp = requests.get(url, timeout=10)
    except Exception as e:
        print("DEX API request error:", e)
        return None

    print("DEX API status:", resp.status_code)
    if resp.status_code != 200:
        print("DEX API body:", resp.text[:300])
        return None

    data = resp.json()
    pairs = data.get("pairs") or []
    if not pairs:
        print("DEX API: pairs empty or null")
        return None
    return pairs[0]


@app.route("/", methods=["GET"])
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>CryptoGuard AI – Meme Coin Risk</title>
        <style>
            * { box-sizing: border-box; }

            body {
                margin: 0;
                padding: 40px 16px;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: radial-gradient(circle at top, #111827 0, #020617 55%, #000000 100%);
                color: #e5e7eb;
            }

            .card {
                max-width: 600px;
                margin: 0 auto;
                padding: 24px 24px 28px;
                background: rgba(15, 23, 42, 0.92);
                border-radius: 16px;
                box-shadow:
                    0 18px 45px rgba(0, 0, 0, 0.6),
                    0 0 0 1px rgba(148, 163, 184, 0.15);
                backdrop-filter: blur(12px);
            }

            h1 {
                margin: 0 0 12px;
                font-size: 24px;
                letter-spacing: 0.03em;
                color: #f9fafb;
            }

            p {
                margin: 0 0 20px;
                font-size: 14px;
                color: #9ca3af;
            }

            label {
                display: block;
                margin: 10px 0 4px;
                font-size: 13px;
                color: #d1d5db;
            }

            input {
                width: 100%;
                padding: 9px 11px;
                border-radius: 10px;
                border: 1px solid #4b5563;
                background: #020617;
                color: #e5e7eb;
                font-size: 14px;
                outline: none;
                transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
            }

            input::placeholder { color: #6b7280; }

            input:focus {
                border-color: #38bdf8;
                box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.5);
                background: #020617;
            }

            .button-row { margin-top: 18px; }

            button {
                width: 100%;
                padding: 11px 14px;
                border-radius: 999px;
                border: none;
                font-size: 15px;
                font-weight: 600;
                letter-spacing: 0.03em;
                text-transform: uppercase;
                cursor: pointer;
                color: #0b1120;
                background: linear-gradient(135deg, #22c55e, #a3e635);
                box-shadow:
                    0 12px 25px rgba(34, 197, 94, 0.35),
                    0 0 0 1px rgba(190, 242, 100, 0.1);
                transition:
                    transform 0.12s ease,
                    box-shadow 0.12s ease,
                    filter 0.12s ease,
                    background-position 0.2s ease;
                background-size: 130% 130%;
                background-position: 0% 50%;
            }

            button:hover {
                transform: translateY(-1px);
                box-shadow:
                    0 16px 32px rgba(34, 197, 94, 0.45),
                    0 0 0 1px rgba(190, 242, 100, 0.16);
                filter: brightness(1.03);
                background-position: 100% 50%;
            }

            button:active {
                transform: translateY(0);
                box-shadow:
                    0 10px 20px rgba(34, 197, 94, 0.4),
                    0 0 0 1px rgba(190, 242, 100, 0.22);
                filter: brightness(0.97);
            }

            .result {
                margin-top: 18px;
                padding: 12px 14px;
                border-radius: 12px;
                font-size: 14px;
                line-height: 1.4;
                border: 1px solid transparent;
            }

            .low {
                background: rgba(22, 163, 74, 0.18);
                border-color: rgba(34, 197, 94, 0.5);
                color: #bbf7d0;
            }

            .medium {
                background: rgba(234, 179, 8, 0.18);
                border-color: rgba(234, 179, 8, 0.6);
                color: #fef3c7;
            }

            .high {
                background: rgba(239, 68, 68, 0.2);
                border-color: rgba(248, 113, 113, 0.7);
                color: #fee2e2;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>CryptoGuard AI – Meme Coin Risk</h1>
            <p>Оценка риска по ликвидности, капитализации, волатильности, активности, возрасту и сигналу ML‑модели.</p>

            <label>Chain ID (например, solana):</label>
            <input id="chainId" value="solana">

            <label>Pair Address:</label>
            <input id="pairAddress" placeholder="вставь адрес пары">

            <div class="button-row">
                <button onclick="analyze()">Analyze</button>
            </div>

            <div id="result" class="result" style="display:none;"></div>
        </div>

        <script>
            async function analyze() {
                const chainId = document.getElementById('chainId').value.trim();
                const pairAddress = document.getElementById('pairAddress').value.trim();
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.className = 'result';
                resultDiv.textContent = 'Analyzing...';

                if (!pairAddress) {
                    resultDiv.textContent = 'Введите pairAddress.';
                    return;
                }

                try {
                    const resp = await fetch('/api/predict', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ chainId, pairAddress })
                    });
                    const data = await resp.json();
                    if (!resp.ok) {
                        resultDiv.textContent = 'Error: ' + (data.error || resp.statusText);
                        return;
                    }

                    const cls = data.risk_class;
                    const score = (data.risk_score_model || 0).toFixed(1);

                    let label = '';
                    let css = 'result ';
                    if (cls === 2) {
                        label = 'High risk';
                        css += 'high';
                    } else if (cls === 1) {
                        label = 'Medium risk';
                        css += 'medium';
                    } else {
                        label = 'Low risk';
                        css += 'low';
                    }

                    resultDiv.className = css;
                    resultDiv.textContent = `${label} (${score}/100).`;

                } catch (e) {
                    resultDiv.textContent = 'Error: ' + e;
                }
            }
        </script>
    </body>
    </html>
    """


@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.json or {}
    chain = data.get("chainId", "solana").strip()
    pair_address = (data.get("pairAddress") or "").strip()

    if not pair_address:
        return jsonify({"error": "pairAddress is required"}), 400

    pair = fetch_pair_by_address(chain, pair_address)
    if not pair:
        return jsonify({"error": "pair not found or API error"}), 404

    X = build_features_from_pair(pair)
    feat = X.to_dict(orient="records")[0]

    proba = model.predict_proba(X)[0]
    if len(proba) == 3:
        p_high = float(proba[2])
    else:
        p_high = float(proba[-1])

    print("=== DEBUG ===")
    print("Pair:", chain, pair_address)
    print("Features:", feat)
    print("Proba:", proba, "p_high:", p_high)
    print("=============")

    liq = float(feat["liquidity_usd"])
    fdv = float(feat["fdv"])
    mcap = float(feat["marketCap"])
    pc_m5 = float(feat["priceChange_m5"])
    pc_h1 = float(feat["priceChange_h1"])
    pc_h6 = float(feat["priceChange_h6"])
    pc_h24 = float(feat["priceChange_h24"])
    tx_m5 = float(feat["txns_m5_buys"] + feat["txns_m5_sells"])
    tx_h1 = float(feat["txns_h1_buys"] + feat["txns_h1_sells"])

    now_ms = int(time.time() * 1000)
    created_ms = int(pair.get("pairCreatedAt") or now_ms)
    age_days = max(0.0, (now_ms - created_ms) / (1000 * 60 * 60 * 24))

    # 1) Liquidity risk
    if liq >= 5_000_000:
        liquidity_risk = 5.0
    elif liq <= 1_000:
        liquidity_risk = 100.0
    else:
        x = (math.log10(liq) - math.log10(1_000)) / (math.log10(5_000_000) - math.log10(1_000))
        liquidity_risk = (1.0 - max(0.0, min(1.0, x))) * 95.0 + 5.0

    # 2) Size risk
    size_val = max(fdv, mcap)
    if size_val >= 5_000_000_000:
        size_risk = 5.0
    elif size_val <= 1_000_000:
        size_risk = 100.0
    else:
        x = (math.log10(size_val) - math.log10(1_000_000)) / (math.log10(5_000_000_000) - math.log10(1_000_000))
        size_risk = (1.0 - max(0.0, min(1.0, x))) * 95.0 + 5.0

    # 3) Activity risk
    if tx_h1 >= 5000:
        activity_risk = 5.0
    elif tx_h1 <= 5:
        activity_risk = 100.0
    else:
        x = (tx_h1 - 5) / (5000 - 5)
        activity_risk = (1.0 - max(0.0, min(1.0, x))) * 95.0 + 5.0

    # 4) Volatility risk
    def vol_component(pct_change: float) -> float:
        base_low = -5.0
        base_high = 5.0
        max_down = -80.0
        max_up = 400.0
        if base_low <= pct_change <= base_high:
            return 20.0
        if pct_change < base_low:
            x = (pct_change - base_low) / (max_down - base_low)
            x = max(-1.0, min(0.0, x))
            return 20.0 + abs(x) * 80.0
        else:
            x = (pct_change - base_high) / (max_up - base_high)
            x = max(0.0, min(1.0, x))
            return 20.0 + x * 80.0

    vol_m5 = vol_component(pc_m5)
    vol_h1 = vol_component(pc_h1)
    vol_h24 = vol_component(pc_h24)

    volatility_risk = max(vol_m5 * 1.1, vol_h1 * 1.0, vol_h24 * 0.9)
    volatility_risk = max(20.0, min(100.0, volatility_risk))

    # 5) Imbalance risk
    if tx_m5 > 0:
        imbalance = (feat["txns_m5_buys"] - feat["txns_m5_sells"]) / tx_m5
    else:
        imbalance = 0.0
    imbalance_risk = min(100.0, 20.0 + abs(imbalance) * 80.0)

    # 6) Age risk
    # новая монета (часы/дни) = высокий риск, 1+ год = очень низкий
    if age_days <= 1:
        age_risk = 100.0
    elif age_days >= 365:
        age_risk = 5.0
    else:
        x = (age_days - 1.0) / (365.0 - 1.0)
        age_risk = 100.0 - x * 95.0  # от 100 до 5

    # 7) Фундаментальный риск
    fundamental_risk = (
        0.20 * liquidity_risk +
        0.20 * size_risk +
        0.18 * activity_risk +
        0.18 * volatility_risk +
        0.12 * age_risk +
        0.12 * imbalance_risk
    )

    model_risk = p_high * 100.0
    combined_risk_raw = 0.6 * fundamental_risk + 0.4 * model_risk

    base_liq = liq
    base_size = size_val

    # blue‑chip / устоявшийся крупный токен (SOL, ETH, BTC, старый PEPE и т.п.)
    is_blue_chip_like = (
        base_liq >= 20_000_000 and
        base_size >= 10_000_000_000 and
        tx_h1 >= 5000 and
        abs(pc_h24) < 15 and
        age_days >= 365
    )

    # сильный устоявшийся мем (FDV/мкап 1B+, возраст 180+ дней)
    is_big_old_meme = (
        base_size >= 1_000_000_000 and
        age_days >= 180 and
        base_liq >= 5_000_000
    )

    # 8) Коррекция для blue‑chip и старых крупных мемов:
    # хотим, чтобы у них было где‑то 15–35, а не 40+
    if is_blue_chip_like:
        combined_risk_raw = combined_risk_raw * 0.4
    elif is_big_old_meme:
        combined_risk_raw = combined_risk_raw * 0.55

    # 9) Мягкий пол для всего, что не blue‑chip и не большой старый мем
    if not (is_blue_chip_like or is_big_old_meme):
        combined_risk_raw = max(combined_risk_raw, 30.0)

    # 10) Новые/шитовые профили: лиq < 500k или size < 50M или возраст < 30 дней
    if base_liq < 500_000 or base_size < 50_000_000 or age_days < 30:
        vol_factor = (volatility_risk - 20.0) / 80.0
        act_factor = (100.0 - activity_risk) / 95.0
        memeness = max(0.0, min(1.0, 0.7 * vol_factor + 0.3 * (1.0 - act_factor)))
        meme_floor = 55.0 + memeness * 35.0   # 55..90
        combined_risk_raw = max(combined_risk_raw, meme_floor)

    # 11) Финальный скор 10–100
    min_score = 10.0
    risk_score = min_score + (combined_risk_raw / 100.0) * (100.0 - min_score)
    risk_score = max(10.0, min(100.0, risk_score))

    # 12) Классы
    if risk_score >= 70:
        pred_class = 2
    elif risk_score >= 45:
        pred_class = 1
    else:
        pred_class = 0

    return jsonify({
        "pairAddress": pair_address,
        "chainId": chain,
        "risk_class": int(pred_class),
        "risk_score_model": float(risk_score)
    })


if __name__ == "__main__":
    app.run(debug=True)