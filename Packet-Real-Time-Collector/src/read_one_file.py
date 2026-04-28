import pyarrow.parquet as pq
import pandas as pd

path = r"data\date=2025-10-19\hour=19\part-00000-*.parquet"  # укажи точный файл
table = pq.read_table(path)
df = table.to_pandas()
print(df.head(20))