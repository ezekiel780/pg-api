"""
utils.py — low-level CSV streaming helper for the reconciliation pipeline.

Public API: stream_csv(file_obj) -> Generator[dict, None, None]
"""

import csv
import io
import logging
from typing import Generator, IO

logger = logging.getLogger(__name__)

# Columns every uploaded CSV must contain.
REQUIRED_COLUMNS = {"transaction_id", "amount", "status"}

# Raise the single-cell size limit from Python's default 128 KB to 1 MB.
# Financial systems sometimes export long description or reference fields.
# Without this, a large cell raises _csv.Error and kills the entire job.
csv.field_size_limit(1_024 * 1_024)


def stream_csv(
    file_obj: IO[bytes],
    encoding: str = "utf-8-sig",
) -> Generator[dict, None, None]:
    """
    Stream a CSV file one row at a time, yielding each row as a clean dict.

    Memory profile: O(1) — one row held in memory at a time regardless of
    file size. Suitable for 1M+ row files inside a Celery worker.

    Args:
        file_obj: Binary-mode file-like object (opened with mode="rb").
                  Accepts Django InMemoryUploadedFile, TemporaryUploadedFile,
                  or any plain file handle from open(..., "rb").
        encoding: File encoding. Default is "utf-8-sig" which transparently
                  strips the UTF-8 BOM that Microsoft Excel prepends to every
                  CSV it exports. Using plain "utf-8" causes the first header
                  to arrive as "\ufefftransaction_id", silently failing the
                  REQUIRED_COLUMNS check for all Excel-exported uploads.

    Yields:
        dict: One row per iteration with stripped keys and values.

    Raises:
        ValueError: Empty file, missing header, or missing required columns.
        UnicodeDecodeError: File cannot be decoded with the given encoding.
    """
    # ------------------------------------------------------------------
    # Binary → text bridge
    #
    # tasks.py opens files with open(path, "rb") — binary mode.
    # csv.DictReader needs a text-mode iterable.
    # TextIOWrapper bridges the two without reading the whole file into RAM.
    #
    # CRITICAL — detach() in the finally block:
    # TextIOWrapper takes ownership of the underlying binary stream.
    # When the wrapper is GC'd, its __del__ calls close() on the binary
    # file handle the caller still owns, causing:
    #   ValueError: I/O operation on closed file
    # on any read after iteration ends.
    # text_stream.detach() releases ownership so the caller's handle stays open.
    # ------------------------------------------------------------------
    text_stream = io.TextIOWrapper(file_obj, encoding=encoding, newline="")

    try:
        reader = csv.DictReader(text_stream)

        # DictReader is lazy — fieldnames is None until the first row is
        # consumed.  Accessing .fieldnames triggers the header read.
        raw_headers = reader.fieldnames

        if not raw_headers:
            raise ValueError(
                "CSV file is empty or has no header row. "
                "Ensure the first line contains column names."
            )

        # FIX: Strip whitespace from the actual fieldnames list and reassign.
        # The original code built a stripped set only for the missing-column
        # check, leaving reader.fieldnames unstripped. Every downstream
        # row["transaction_id"] call would get None back because the real
        # key was " transaction_id " (with spaces).
        reader.fieldnames = [h.strip() for h in raw_headers if h]

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"CSV is missing required column(s): {', '.join(sorted(missing))}. "
                f"Columns found: {', '.join(reader.fieldnames)}"
            )

        # ------------------------------------------------------------------
        # Row streaming
        # ------------------------------------------------------------------
        for line_num, row in enumerate(reader, start=2):  # line 1 = header
            # FIX: Filter rows with a None key.
            # DictReader places overflow values (more columns than headers)
            # under a None key. Yielding those rows causes KeyError in callers.
            if None in row:
                logger.warning(
                    "Skipping malformed row at line %d — extra columns detected. "
                    "Row preview: %s",
                    line_num,
                    {k: v for k, v in row.items() if k is not None},
                )
                continue

            # Strip all string values — prevents false mismatches from
            # trailing spaces exported by different financial systems.
            cleaned = {
                k: (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
            }

            # Skip entirely blank rows (e.g. trailing newlines at end of file)
            if not any(cleaned.values()):
                continue

            # FIX: Guard against blank transaction_id.
            # Without this, a row with no ID gets yielded and the caller
            # does A_map[""] = row, silently overwriting every previous
            # blank-ID row with no error raised.
            tx_id = cleaned.get("transaction_id", "")
            if not tx_id:
                logger.warning(
                    "Skipping row at line %d — empty transaction_id", line_num
                )
                continue

            yield cleaned

    finally:
        # Detach releases ownership of the binary stream so the caller's
        # file handle stays valid after this generator is exhausted or closed.
        text_stream.detach()
        