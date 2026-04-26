import logging
from decimal import Decimal, InvalidOperation
from typing import IO

from .utils import stream_csv

logger = logging.getLogger(__name__)
DETAILS_CAP = int(10_000)


def _normalize_amount(raw: str) -> Decimal:
    """
    Convert a raw amount string to a Decimal for exact numeric comparison.

    Why Decimal and not float:
      float("100.10") == float("100.1") is True — floats silently equate
      values that should be distinct in financial reconciliation.
      "100.00" != "100.0" as strings — raw string comparison produces false
      mismatches when two systems serialise the same value differently.
      Decimal gives exact, unambiguous comparison with no rounding surprises.

    Returns Decimal("0") and logs a warning if the value cannot be parsed
    so a single malformed amount field doesn't kill the entire job.
    """
    try:
        return Decimal(raw.strip().replace(",", ""))  # handle "1,000.00"
    except (InvalidOperation, AttributeError):
        logger.warning("Could not parse amount value: %r — treating as 0", raw)
        return Decimal("0")


def reconcile(file_a: IO[bytes], file_b: IO[bytes]) -> dict:
    """
    Compare two CSV transaction files and return a structured report.

    Memory strategy — O(N) peak, not O(2N):
      The original implementation loaded both files into memory simultaneously
      (A_map and B_map fully populated before any comparison), which used
      ~400-500 MB for a 1M-row pair — dangerously close to the 1 GB Celery
      worker ceiling set in settings.py.

      This version:
        1. Streams file_a into A_map (one dict, O(N) memory).
        2. Streams file_b row-by-row, comparing each row against A_map and
           building a seen_in_b set of visited IDs.
        3. After file_b is exhausted, anything in A_map not in seen_in_b is
           missing_in_b — no second dict needed.

      Peak memory: one full dict (A_map) + one lightweight set (seen_in_b)
      + a small rolling window of B rows = ~200-250 MB for 1M rows.

    Args:
        file_a: Binary file handle for source-system A CSV.
        file_b: Binary file handle for source-system B CSV.

    Returns:
        {
            "summary": {
                "total_a": int,
                "total_b": int,
                "missing_in_a": int,
                "missing_in_b": int,
                "amount_mismatch": int,
                "status_mismatch": int,
                "details_capped": bool,   # True if any list hit DETAILS_CAP
            },
            "details": {
                "missing_in_a":    [tx_id, ...],   # capped at DETAILS_CAP
                "missing_in_b":    [tx_id, ...],
                "amount_mismatch": [tx_id, ...],
                "status_mismatch": [tx_id, ...],
            }
        }
    """
    # ------------------------------------------------------------------
    A_map: dict[str, dict] = {}

    for row in stream_csv(file_a):
        tx_id = row["transaction_id"]

        if tx_id in A_map:
            logger.warning(
                "Duplicate transaction_id in file_a: %r — keeping first occurrence",
                tx_id,
            )
            continue

        A_map[tx_id] = {
            "amount": _normalize_amount(row["amount"]),
            # FIX: Normalise status to uppercase — "success" != "SUCCESS"
            # is a false mismatch.
            "status": row["status"].upper(),
        }

    total_a = len(A_map)
    logger.info("Loaded file_a: %d transactions", total_a)

    seen_in_b: set[str] = set()

    count_missing_in_a   = 0
    count_amount_mismatch = 0
    count_status_mismatch = 0
    total_b              = 0
    missing_in_a:    list[str] = []
    amount_mismatch: list[str] = []
    status_mismatch: list[str] = []
    details_capped = False

    def _append_capped(lst: list, value: str) -> None:
        """Append value to lst unless DETAILS_CAP is already reached."""
        nonlocal details_capped
        if len(lst) < DETAILS_CAP:
            lst.append(value)
        else:
            details_capped = True

    for row in stream_csv(file_b):
        tx_id = row["transaction_id"]
        total_b += 1

        if tx_id in seen_in_b:
            logger.warning(
                "Duplicate transaction_id in file_b: %r — skipping duplicate",
                tx_id,
            )
            continue

        seen_in_b.add(tx_id)
        a = A_map.get(tx_id)

        if a is None:
            # Present in B, missing in A
            count_missing_in_a += 1
            _append_capped(missing_in_a, tx_id)
            continue

        # Both files have this ID — compare normalised values
        b_amount = _normalize_amount(row["amount"])
        b_status = row["status"].upper()

        if a["amount"] != b_amount:
            count_amount_mismatch += 1
            _append_capped(amount_mismatch, tx_id)

        if a["status"] != b_status:
            count_status_mismatch += 1
            _append_capped(status_mismatch, tx_id)

    logger.info("Streamed file_b: %d transactions", total_b)

    # ------------------------------------------------------------------
    # Phase 3 — IDs in A not seen in B are missing_in_b.
    # O(N) set difference; no second file pass needed.
    # ------------------------------------------------------------------
    missing_in_b_ids = [tx_id for tx_id in A_map if tx_id not in seen_in_b]
    count_missing_in_b = len(missing_in_b_ids)

    # Cap the list before storing
    missing_in_b: list[str] = []
    for tx_id in missing_in_b_ids:
        _append_capped(missing_in_b, tx_id)

    if details_capped:
        logger.warning(
            "One or more discrepancy lists exceeded DETAILS_CAP=%d. "
            "Summary counts are accurate; detail lists are truncated.",
            DETAILS_CAP,
        )

    return {
        "summary": {
            "total_a":         total_a,
            "total_b":         total_b,
            "missing_in_a":    count_missing_in_a,
            "missing_in_b":    count_missing_in_b,
            "amount_mismatch": count_amount_mismatch,
            "status_mismatch": count_status_mismatch,
            "details_capped":  details_capped,
        },
        "details": {
            "missing_in_a":    missing_in_a,
            "missing_in_b":    missing_in_b,
            "amount_mismatch": amount_mismatch,
            "status_mismatch": status_mismatch,
        },
    }
