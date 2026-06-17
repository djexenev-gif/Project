import pandas as pd

RAW_CSV = "all_pairs.csv"
UNIQUE_CSV = "pairs_unique.csv"

def main():
    print("Читаю сырой файл:", RAW_CSV)

    df = pd.read_csv(
        RAW_CSV,
        on_bad_lines="skip",
        engine="python"
    )

    print("Всего строк (после skip):", len(df))
    print("Колонки:", list(df.columns))

    if "pairAddress" not in df.columns:
        raise ValueError("В файле нет колонки 'pairAddress' — проверь заголовок CSV")

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.sort_values("timestamp")
        df_unique = df.drop_duplicates(subset=["pairAddress"], keep="last")
    else:
        df_unique = df.drop_duplicates(subset=["pairAddress"], keep="first")

    print("Уникальных пар (по pairAddress):", len(df_unique))

    df_unique.to_csv(UNIQUE_CSV, index=False)
    print("Сохранено в:", UNIQUE_CSV)

if __name__ == "__main__":
    main()