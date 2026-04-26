import csv
from io import TextIOWrapper


REQUIRED_COLUMNS = {"transaction_id", "amount", "status"}


def stream_csv(file_obj):
    """
    Stream CSV rows safely with validation.

    Features:
    - Binary → text conversion
    - Validates required columns
    - Cleans whitespace
    - Skips empty rows
    """

    text_stream = TextIOWrapper(file_obj, encoding="utf-8", newline="")
    reader = csv.DictReader(text_stream)

    # ✅ Validate headers FIRST (before processing rows)
    if not reader.fieldnames:
        raise ValueError("CSV file has no header row")

    headers = {h.strip() for h in reader.fieldnames if h}
    missing = REQUIRED_COLUMNS - headers

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ✅ Stream rows
    for row in reader:
        if not row:
            continue

        cleaned_row = {
            (key.strip() if key else key): (
                value.strip() if isinstance(value, str) else value
            )
            for key, value in row.items()
        }

        # Skip completely empty rows
        if not any(cleaned_row.values()):
            continue

        yield cleaned_row
        