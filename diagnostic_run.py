import pandas as pd
import numpy as np
import os
import zipfile
import pyproj
from pyproj import Transformer
import sys

# [TOOL] Root Directory Setup
ROOT_DIR = "/Users/heebonpark/Downloads/영업기회툴 운영계획/field-sales-assistant-main-0402"
os.chdir(ROOT_DIR)
sys.path.append(ROOT_DIR)

from src import utils

def run_diagnostic():
    print("--- 🩺 Field Sales Assistant Map Diagnostic ---")
    
    # 1. Environment Check
    print(f"Python Version: {sys.version}")
    print(f"Pandas Version: {pd.__version__}")
    print(f"Pyproj Version: {pyproj.__version__}")
    
    # 2. Transformer Test (EPSG:2097 -> WGS84)
    # Most Public Data uses Middle Point Coordinates (EPSG:2040ish or 2097ish or 5174-5186)
    transformers = [
        ("EPSG:2097 -> WGS84", Transformer.from_crs("EPSG:2097", "EPSG:4326", always_xy=True)),
        ("EPSG:5174 -> WGS84", Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)),
        ("EPSG:5181 -> WGS84", Transformer.from_crs("EPSG:5181", "EPSG:4326", always_xy=True)),
        ("EPSG:5186 -> WGS84", Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)),
    ]
    
    test_x, test_y = 194411, 444321 # Typical Seoul area coordinate in EPSG:5174/2097
    for name, tf in transformers:
        try:
            lon, lat = tf.transform(test_x, test_y)
            print(f"✅ {name}: ({test_x}, {test_y}) -> Lat: {lat:.5f}, Lon: {lon:.5f}")
        except Exception as e:
            print(f"❌ {name} failed: {e}")

    # 3. Data Sampling
    data_dir = "data"
    files = [f for f in os.listdir(data_dir) if f.endswith('.zip') or f.endswith('.csv')]
    if not files:
        print("❌ No data files found in 'data/' directory.")
        return

    sample_file = "LOCALDATA_NOWMON_CSV-3월.zip" if "LOCALDATA_NOWMON_CSV-3월.zip" in files else files[0]
    print(f"\n📂 Sampling file: {sample_file}")
    
    full_path = os.path.join(data_dir, sample_file)
    try:
        if sample_file.endswith('.zip'):
            with zipfile.ZipFile(full_path, 'r') as z:
                csv_files = [n for n in z.namelist() if n.endswith('.csv')]
                if not csv_files: sys.exit("No CSV in ZIP")
                with z.open(csv_files[0]) as f:
                    # Sample first 1000 rows
                    df = pd.read_csv(f, nrows=1000, encoding='cp949', on_bad_lines='skip')
        else:
            df = pd.read_csv(full_path, nrows=1000, encoding='cp949', on_bad_lines='skip')
            
        print(f"✅ Loaded {len(df)} rows.")
        print(f"📋 Columns: {list(df.columns)}")
        
        # 4. Check Coordinate Columns
        x_col = next((c for f in ['좌표정보(X)', '좌표정보(x)', 'X좌표'] for c in df.columns if f in c), None)
        y_col = next((c for f in ['좌표정보(Y)', '좌표정보(y)', 'Y좌표'] for c in df.columns if f in c), None)
        
        if x_col and y_col:
            print(f"✅ Found Coordinate Columns: {x_col}, {y_col}")
            df_coords = df.dropna(subset=[x_col, y_col])
            print(f"📍 Valid coordinate rows in sample: {len(df_coords)} / {len(df)}")
            
            # Test transform on first 5 rows
            for idx, row in df_coords.head(5).iterrows():
                x, y = row[x_col], row[y_col]
                res = utils.parse_coordinates_row(row, x_col, y_col)
                print(f"   [{idx}] X={x}, Y={y} -> Lat/Lon Result: {res}")
        else:
            print(f"❌ Could not find X/Y coordinate columns in {list(df.columns)}")

        # 5. Check Date Range (최종수정시점)
        mod_col = next((c for f in ['최종수정시점', '최종수정일', '수정일'] for c in df.columns if f in c), None)
        if mod_col:
            print(f"✅ Found Modification Date Column: {mod_col}")
            # Try to convert to datetime to see format
            dates = pd.to_datetime(df[mod_col], errors='coerce')
            print(f"📅 Date range in sample: {dates.min()} ~ {dates.max()}")
            now = pd.Timestamp.now()
            print(f"🕒 Current Time (Local): {now}")
            delta_days = (now - dates.max()).days if dates.max() is not pd.NaT else "N/A"
            print(f"⌛ Gap between latest record and now: {delta_days} days")
        else:
            print(f"❌ Could not find modification date column in {list(df.columns)}")

    except Exception as e:
        print(f"❌ Error during diagnostic: {e}")

if __name__ == "__main__":
    run_diagnostic()
