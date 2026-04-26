from decimal import Decimal, InvalidOperation

from .utils import stream_csv

MAX_DETAILS = 1000  # prevent huge payloads


def normalize_amount(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


def normalize_status(value):
    if not value:
        return None
    return value.strip().upper()


def reconcile(file_a, file_b):

    A_map = {}
    seen_in_b = set()

    missing_in_a = []
    missing_in_b = []
    amount_mismatch = []
    status_mismatch = []

    # =========================
    # LOAD FILE A INTO MEMORY
    # =========================
    for row in stream_csv(file_a):
        tx_id = row.get("transaction_id")
        if not tx_id:
            continue

        A_map[tx_id] = {
            "amount": normalize_amount(row.get("amount")),
            "status": normalize_status(row.get("status")),
        }

    # =========================
    # STREAM FILE B
    # =========================
    for row in stream_csv(file_b):
        tx_id = row.get("transaction_id")
        if not tx_id:
            continue

        seen_in_b.add(tx_id)

        b_amount = normalize_amount(row.get("amount"))
        b_status = normalize_status(row.get("status"))

        a = A_map.get(tx_id)

        if not a:
            if len(missing_in_a) < MAX_DETAILS:
                missing_in_a.append(tx_id)
            continue

        if a["amount"] != b_amount:
            if len(amount_mismatch) < MAX_DETAILS:
                amount_mismatch.append(tx_id)

        if a["status"] != b_status:
            if len(status_mismatch) < MAX_DETAILS:
                status_mismatch.append(tx_id)

    # =========================
    # FIND MISSING IN B
    # =========================
    for tx_id in A_map.keys():
        if tx_id not in seen_in_b:
            if len(missing_in_b) < MAX_DETAILS:
                missing_in_b.append(tx_id)

    # =========================
    # RESULT
    # =========================
    return {
        "summary": {
            "missing_in_a": len(missing_in_a),
            "missing_in_b": len(missing_in_b),
            "amount_mismatch": len(amount_mismatch),
            "status_mismatch": len(status_mismatch),
        },
        "details": {
            "missing_in_a": missing_in_a,
            "missing_in_b": missing_in_b,
            "amount_mismatch": amount_mismatch,
            "status_mismatch": status_mismatch,
        },
    }
