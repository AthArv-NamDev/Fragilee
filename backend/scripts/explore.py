import sys
import pandas as pd

path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/startup_data.csv"
df = pd.read_csv(path)

print("Shape (rows, columns):", df.shape)
print("\n--- Columns, type, missing values ---")
info = pd.DataFrame({"dtype": df.dtypes.astype(str), "missing": df.isna().sum()})
print(info.to_string())

print("\n--- Columns with 10 or fewer distinct values (label candidates) ---")
for col in df.columns:
    if df[col].nunique(dropna=True) <= 10:
        print(f"\n{col}:")
        print(df[col].value_counts(dropna=False).to_string())