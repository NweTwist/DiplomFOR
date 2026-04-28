import pyarrow.dataset as ds
import pandas as pd

def load_dataset(root="data"):
    dset = ds.dataset(root, format="parquet")
    table = dset.to_table()
    df = table.to_pandas()
    return df

if __name__ == "__main__":
    df = load_dataset("data")
    print("Rows:", len(df), "Columns:", list(df.columns))
    print("Head:\n", df.head(10))
    print("\nBy protocol+direction:\n", df.groupby(["protocol", "direction"]).size().sort_values(ascending=False).head(20))
    # Сохранить быстрый снимок в CSV
    df.head(1000).to_csv("data\\preview.csv", index=False, encoding="utf-8")
    print("\nSaved preview to data\\preview.csv")