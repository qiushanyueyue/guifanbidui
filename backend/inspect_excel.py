import pandas as pd
import sys

try:
    file_path = "/Volumes/yue/Download/规范目录库（含网址）.xlsx"
    df = pd.read_excel(file_path, nrows=5)
    print("Columns:", df.columns.tolist())
    print("First 5 rows:")
    print(df.to_string())
except Exception as e:
    print(f"Error reading excel: {e}")
