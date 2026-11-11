import json
import time
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
import re

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
    filepath: Path | str | None = None,
    desc: str = "Downloading data"
) -> list[dict]:

    if filepath and Path(filepath).exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    else:
        all_data = []

    existing_dates = {item.get('calendarDate') for item in all_data if item.get('calendarDate')}

    for start_str, end_str in tqdm(date_ranges, desc=desc):
        if start_str in existing_dates or end_str in existing_dates:
            continue

        response = None
        for attempt in range(3):
            try:
                response = fetch_fn(start_str, end_str)
                break
            except Exception as e:
                if '429' in str(e):
                    tqdm.write(
                        f"API limit exceeded for {start_str} - {end_str}."
                        f"\nTrying again in a few seconds... (Attempt {attempt+1}/3)"
                    )
                    time.sleep(30)
                elif re.search(r'\b5\d{2}\b', str(e)):
                    tqdm.write(
                        f"Server error for {start_str} - {end_str}."
                        f"\nTrying again in a few seconds..."
                    )
                    time.sleep(5)
                else:
                    tqdm.write(f"Unexpected error for {start_str} - {end_str}: {e}")
                    break

        if response:
            if isinstance(response, list):
                items = response
            elif isinstance(response, dict):
                items = response.get('data') or response.get('hrvSummaries') or [response]
            else:
                items = [response]
            for item in items:
                c_date = item.get('calendarDate')
                if c_date and c_date not in existing_dates:
                    all_data.append(item)
                    existing_dates.add(c_date)
                elif not c_date:
                    all_data.append(item)

        time.sleep(0.3)

    all_data.sort(key=lambda x: x.get("calendarDate", ""))
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
        daily_data = fetch_chunked_endpoint(
            fetch_fn=client.get_daily_summaries,
            date_ranges=ranges,
            filepath=RAW_DIR / 'daily.json',
            desc="Daily summaries"
        )
        save_to_json(daily_data, RAW_DIR / 'daily.json')

        daily_hrv = fetch_chunked_endpoint(
            fetch_fn=client.get_daily_hrv_summaries,
            date_ranges=ranges,
            filepath=RAW_DIR / 'daily_hrv.json',
            desc="Daily HRV"
        )
        save_to_json(daily_hrv, RAW_DIR / 'daily_hrv.json')

        daily_sleep = fetch_chunked_endpoint(
            fetch_fn=client.get_daily_sleep_summaries,
            date_ranges=ranges,
            filepath=RAW_DIR / 'daily_sleep.json',
            desc="Daily sleep"
        )
        save_to_json(daily_sleep, RAW_DIR / 'daily_sleep.json')