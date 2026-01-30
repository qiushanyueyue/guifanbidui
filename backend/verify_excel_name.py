from app.services.excel_loader import excel_loader
import pandas as pd

def verify_name_lookup():
    target_name = "地铁"
    
    print(f"Searching for Name containing: '{target_name}'")
    
    # Check raw dataframe
    print("\nChecking RAW dataframe for '50157':")
    EXCEL_PATH = "/Volumes/yue/Download/规范目录库（含网址）.xlsx"
    df = pd.read_excel(EXCEL_PATH)
    if '名称' in df.columns:
        results = df[df['名称'].str.contains("50157", na=False)]
        print(results[['名称', '网址']].to_string())
    else:
        print("Column '名称' not found in raw DF.")

if __name__ == "__main__":
    verify_name_lookup()
