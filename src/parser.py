import json
from datetime import date, timedelta
from pathlib import Path
from tqdm import tqdm
from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
    resolve_api_key,
)

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




