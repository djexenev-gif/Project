import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib

DATA_CSV = "pairs_unique.csv"
MODEL_PATH = "risk_model.pkl"

# Сюда ты потом сам впишешь реальные pairAddress известных rug-pull токенов
MANUAL_RUG_PULLS = [
    # "So11111111111111111111111111111111111111112",
    # "9xSomeRugPullPairAddress...",
]


def compute_risk_score(df: pd.DataFrame) -> pd.Series:
    """
    Вычисляет риск по 100-балльной шкале на основе нескольких правил.
    0 = минимальный риск, 100 = максимальный.
    """

    num_cols = [
        "liquidity_usd",
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
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # базовый скор
    score = pd.Series(0.0, index=df.index)

    # 1) Ликвидность
    low_liq = df["liquidity_usd"] < 3000
    very_low_liq = df["liquidity_usd"] < 1000
    high_liq = df["liquidity_usd"] > 50000

    score += low_liq * 25
    score += very_low_liq * 15   # если совсем мало
    score -= high_liq * 10       # хорошая ликвидность снижает риск

    # 2) Падение цены
    big_drop_h6 = df["priceChange_h6"] < -50
    big_drop_h24 = df["priceChange_h24"] < -70

    score += big_drop_h6 * 20
    score += big_drop_h24 * 20

    # 3) Мало покупок и много продаж
    few_buys = (df["txns_m5_buys"] < 3) & (df["txns_h1_buys"] < 10)
    more_sells_now = df["txns_m5_sells"] > df["txns_m5_buys"]

    score += few_buys * 15
    score += (few_buys & more_sells_now) * 10

    # 4) Слабый интерес вообще (мало сделок)
    very_low_activity = (df["txns_h1_buys"] + df["txns_h1_sells"]) < 5
    score += very_low_activity * 10

    # 5) Слишком агрессивное движение (pump-like)
    big_pump_h1 = df["priceChange_h1"] > 200
    score += big_pump_h1 * 10

    # нормируем в 0–100
    score = score.clip(lower=0, upper=100)

    return score


def mark_manual_rugpulls(df: pd.DataFrame, risk_score: pd.Series) -> pd.Series:
    """
    Для заранее известных rug pull пар принудительно ставим риск 100.
    """
    if not MANUAL_RUG_PULLS:
        return risk_score

    mask = df["pairAddress"].isin(MANUAL_RUG_PULLS)
    risk_score.loc[mask] = 100.0
    return risk_score


def create_label_from_score(score: pd.Series) -> pd.Series:
    """
    Переводим 0–100 score в 3 класса риска: 0/1/2.
    0 = low, 1 = medium, 2 = high.
    """
    labels = pd.Series(1, index=score.index)  # default = medium
    labels[score < 33] = 0
    labels[score > 66] = 2
    return labels


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Строим X для модели.
    """
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

    for col in feature_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    X = df[feature_cols].copy()

    # обработка пропусков: заполняем медианами
    X = X.fillna(X.median(numeric_only=True))

    return X


def main():
    print("Читаю данные:", DATA_CSV)
    df = pd.read_csv(DATA_CSV)

    print("Всего пар:", len(df))

    # 1) считаем rule-based risk_score (0–100)
    risk_score = compute_risk_score(df)
    # 2) помечаем ручные rug-pull пары как 100
    risk_score = mark_manual_rugpulls(df, risk_score)

    # 3) строим классы по score
    y = create_label_from_score(risk_score)

    print("Примеры risk_score:")
    print(risk_score.describe())
    print("Распределение классов риска (0=low,1=medium,2=high):")
    print(y.value_counts())

    # 4) признаки
    X = build_features(df)

    # 5) train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 6) модель
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    print("Обучаю модель...")
    model.fit(X_train, y_train)

    # оценка
    y_pred = model.predict(X_test)
    print("Отчёт по качеству (classification_report):")
    print(classification_report(y_test, y_pred))

    # 7) сохраняем модель и, при желании, score
    joblib.dump(model, MODEL_PATH)
    print("Модель сохранена в:", MODEL_PATH)

    # Можно сохранить risk_score рядом для анализа/графиков
    df_out = df.copy()
    df_out["risk_score_rule_based"] = risk_score
    df_out["risk_class"] = y
    df_out.to_csv("pairs_with_risk_scores.csv", index=False)
    print("Файл с risk_score сохранён в: pairs_with_risk_scores.csv")

if __name__ == "__main__":
    main()
    