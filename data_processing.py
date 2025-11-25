# data_processing_mysql.py
import pandas as pd
import numpy as np

def load_and_clean(path_or_df):
    """Load CSV or DataFrame, drop columns that are all-NA, normalize and handle NaNs."""
    if isinstance(path_or_df, str):
        df = pd.read_csv(r"C:\Users\BalaGomathi\Downloads\traffic_stops - traffic_stops_with_vehicle_number.csv")
    else:
        df = path_or_df.copy()

    # Drop columns that contain only missing values
    df = df.dropna(axis=1, how='all')

    # normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # parse stop_date and stop_time
    if 'stop_date' in df.columns:
        df['stop_date'] = pd.to_datetime(df['stop_date'], errors='coerce').dt.date
    if 'stop_time' in df.columns:
        # keep time as string "HH:MM:SS" or as python time object
        df['stop_time'] = pd.to_datetime(df['stop_time'], errors='coerce').dt.time

    # driver_age: try to extract numeric from driver_age_raw if needed
    if 'driver_age' not in df.columns and 'driver_age_raw' in df.columns:
        df['driver_age'] = pd.to_numeric(df['driver_age_raw'], errors='coerce').astype('Int64')
    elif 'driver_age' in df.columns:
        df['driver_age'] = pd.to_numeric(df['driver_age'], errors='coerce').astype('Int64')

    # boolean-like columns normalization
    bool_cols = ['search_conducted', 'is_arrested', 'drugs_related_stop']
    for c in bool_cols:
        if c in df.columns:
            df[c] = df[c].map({
                'True': True, 'False': False,
                'true': True, 'false': False,
                '1': True, '0': False,
                1: True, 0: False,
                True: True, False: False
            }).astype('boolean')

    # simple violation normalization: map common keywords -> categories
    if 'violation_raw' in df.columns and 'violation' not in df.columns:
        def map_violation(s):
            if pd.isna(s): return None
            s0 = str(s).lower()
            if 'speed' in s0: return 'Speeding'
            if 'dui' in s0 or 'drunk' in s0: return 'DUI'
            if 'seat' in s0: return 'Seatbelt'
            if 'equipment' in s0: return 'Equipment'
            return s.strip().title()
        df['violation'] = df['violation_raw'].apply(map_violation)

    # fill categorical NaNs with 'Unknown' for a set of categorical columns
    cat_cols = ['country_name', 'driver_gender', 'driver_race', 'stop_outcome', 'stop_duration']
    for c in cat_cols:
        if c in df.columns:
            df[c] = df[c].fillna('Unknown')

    # add a needs_review flag when both date and time missing
    if 'stop_date' in df.columns and 'stop_time' in df.columns:
        df['needs_review'] = (df['stop_date'].isna() & df['stop_time'].isna()).astype('boolean')

    return df

if __name__ == "__main__":
    # tiny demo
    sample = pd.DataFrame([{
        'stop_date': '2025-11-15',
        'stop_time': '14:30',
        'country_name': 'CountryX',
        'driver_gender': 'Male',
        'driver_age_raw': '27',
        'driver_race': 'Unknown',
        'violation_raw': 'Speeding',
        'search_conducted': False,
        'search_type': None,
        'stop_outcome': 'Citation',
        'is_arrested': False,
        'stop_duration': '6-15 minutes',
        'drugs_related_stop': False,
        'vehicle_plate': 'TN09AB1234',
        'officer_id': 'OFCR001'
    }])
    cleaned = load_and_clean(sample)
    print(cleaned.to_dict(orient='records'))
