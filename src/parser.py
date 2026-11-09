import json
from datetime import date, timedelta
from pathlib import Path
from tqdm import tqdm
from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
    resolve_api_key,
)
from typing import Callable, Any
from dotenv import load_dotenv

START_DATE = date(2024, 4, 3)
END_DATE = date.today()
CHUNK_SIZE = 28

def generate_date_ranges(start_date: date, end_date: date, chunk_size: int):
    ranges = []
    current_start = start_date
    while current_start <= end_date:
        current_end = current_start + timedelta(days=chunk_size-1)
        current_end = min(current_end, end_date)
        ranges.append([current_start.isoformat(), current_end.isoformat()])
        current_start = current_end + timedelta(days=1)
    return ranges

def fetch_chunked_endpoint(
    fetch_fn: Callable[[str, str], Any],
    date_ranges: list[list[str]],
    desc: str = "Downloading data"
) -> list[dict]:

    all_data = []

    for start_str, end_str in tqdm(date_ranges, desc=desc):
        try:
            response = fetch_fn(start_str, end_str)
        except Exception as e:
            tqdm.write(f"ERROR FOR: {start_str} - {end_str}: {e}")
            continue
        if response:
                if isinstance(response, list):
                    all_data.extend(response)
                else:
                    all_data.append(response)

    return all_data

def save_to_json(
        data: Any,
        filepath: Path,
):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, mode='w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Saving data to: {filepath}")

if __name__ == "__main__":
    load_dotenv()

    RAW_DIR =  Path(__file__).resolve().parents[1] / 'data' / 'raw'
    print(f'Path to save data: {RAW_DIR}')

    api_key = resolve_api_key()

    with PersonalApiAuthenticator() as auth:
        token = auth.obtain_token(api_key)
    print(f'Authorization done')

    ranges = generate_date_ranges(START_DATE, END_DATE, CHUNK_SIZE)

    with GarminPersonalApiClient(token.access_token) as client:
        daily_data = fetch_chunked_endpoint(client.get_daily_summaries, ranges, desc="Daily summaries")
        save_to_json(daily_data, RAW_DIR / 'daily.json')

        daily_hrv = fetch_chunked_endpoint(client.get_daily_hrv_summaries, ranges, desc="Daily HRV")
        save_to_json(daily_hrv, RAW_DIR / 'daily_hrv.json')

        daily_sleep = fetch_chunked_endpoint(client.get_daily_sleep_summaries, ranges, desc="Daily sleep")
        save_to_json(daily_sleep, RAW_DIR / 'daily_sleep.json')