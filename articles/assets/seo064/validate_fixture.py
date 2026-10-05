"""Validate this synthetic fixture in Python only; never execute M or Excel.

The expected CSV/JSON files were specified separately. This script reads the
original CSV bytes, derives results with Python's date/Decimal libraries, and
compares all expected fields and counts. It does not write any files.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import decimal
import hashlib
import io
import json
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parent
SOURCES = {
    "inspections_a.csv": {
        "fields": ["InspectionID", "InspectionDate", "Reading", "Unit", "Result"],
        "format": "dd/MM/yyyy", "python_format": "%d/%m/%Y", "culture": "en-GB",
    },
    "inspections_b.csv": {
        "fields": ["InspectionKey", "DateRecorded", "MeasuredValue", "LengthUnit", "Outcome"],
        "format": "MM/dd/yyyy", "python_format": "%m/%d/%Y", "culture": "en-US",
    },
}
RAW_KEYS = ["IDRaw", "DateRaw", "ReadingRaw", "UnitRaw", "SourceResultRaw"]


def read_csv(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO((BASE / name).read_text(encoding="utf-8"))))


def numeric_text(value: decimal.Decimal | None) -> str:
    return "" if value is None else format(value.normalize(), "f")


def main() -> None:
    raw_rows: list[dict[str, str | int]] = []
    byte_receipts = []
    for name, config in SOURCES.items():
        raw = (BASE / name).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"Unexpected BOM: {name}"
        raw.decode("utf-8", errors="strict")
        assert b"\r" not in raw and raw.endswith(b"\n"), f"Expected LF: {name}"
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        assert reader.fieldnames == config["fields"], f"Unexpected headers: {name}"
        rows = list(reader)
        assert len(rows) == 5, f"Unexpected data-record count: {name}"
        assert all(None not in row for row in rows), f"Extra CSV fields: {name}"
        byte_receipts.append({"file": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "data_rows": len(rows)})
        for row_index, row in enumerate(rows, 1):
            item: dict[str, str | int] = {
                "SourceFile": name, "SourceRow": row_index,
                "DateFormat": config["format"], "SourceCulture": config["culture"],
            }
            item.update({out: row[src] for out, src in zip(RAW_KEYS, config["fields"])})
            raw_rows.append(item)

    counts = collections.Counter(str(row["IDRaw"]).strip() for row in raw_rows if str(row["IDRaw"]).strip())
    derived = []
    for raw in raw_rows:
        name = str(raw["SourceFile"])
        inspection_id = str(raw["IDRaw"]).strip()
        try:
            date_value = dt.datetime.strptime(str(raw["DateRaw"]).strip(), SOURCES[name]["python_format"]).date().isoformat()
        except ValueError:
            date_value = ""
        reading_text = str(raw["ReadingRaw"]).strip()
        # Numeric cultures in this fixture both use dot decimals. This limited
        # checker does not reimplement general Power Query culture parsing.
        try:
            if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", reading_text):
                raise decimal.InvalidOperation
            reading = decimal.Decimal(reading_text)
        except decimal.InvalidOperation:
            reading = None
        unit = str(raw["UnitRaw"]).strip().lower()
        result = str(raw["SourceResultRaw"]).strip()
        reading_mm = None if reading is None or unit not in {"mm", "cm"} else reading * (10 if unit == "cm" else 1)
        issues = []
        if not inspection_id: issues.append("missing_id")
        if not date_value: issues.append("invalid_date")
        if reading is None: issues.append("invalid_reading")
        if not unit: issues.append("missing_unit")
        if unit and unit not in {"mm", "cm"}: issues.append("unsupported_unit")
        if not result: issues.append("missing_source_result")
        if result and result not in {"Pass", "Fail"}: issues.append("unsupported_source_result")
        if counts[inspection_id] > 1: issues.append("duplicate_id")
        item = {key: str(value) for key, value in raw.items()}
        item.update({"InspectionID": inspection_id, "InspectionDate": date_value,
                     "ReadingNumber": numeric_text(reading), "Unit": unit,
                     "SourceResult": result, "ReadingMM": numeric_text(reading_mm),
                     "IDOccurrences": str(counts[inspection_id]), "Issues": ";".join(issues),
                     "RowState": "review" if issues else "ready_for_demo"})
        derived.append(item)
    derived.sort(key=lambda row: (row["SourceFile"], int(row["SourceRow"])))
    expected = read_csv("expected-normalized.csv")
    assert derived == expected, "Full row/field comparison differs from expected-normalized.csv"

    summary = json.loads((BASE / "expected-reconciliation.json").read_text(encoding="utf-8"))
    assert len(raw_rows) == len(derived) == summary["input_rows"] == summary["normalized_rows"] == 10
    assert summary["rows_removed"] == 0
    ready = sum(row["RowState"] == "ready_for_demo" for row in derived)
    review = sum(row["RowState"] == "review" for row in derived)
    assert (ready, review) == (summary["ready_for_demo_rows"], summary["review_rows"]) == (2, 8)
    assert ready + review == len(derived)
    result_counts = collections.Counter(row["SourceResult"] or "blank" for row in derived)
    assert dict(result_counts) == summary["source_result_label_counts"]
    issue_counts = collections.Counter(code for row in derived for code in row["Issues"].split(";") if code)
    assert dict(issue_counts) == summary["issue_occurrences"]
    per_source = []
    for name in SOURCES:
        subset = [row for row in derived if row["SourceFile"] == name]
        entry = {"SourceFile": name, "ExpectedInputRows": 5, "OutputRows": len(subset),
                 "ReadyRows": sum(row["RowState"] == "ready_for_demo" for row in subset),
                 "ReviewRows": sum(row["RowState"] == "review" for row in subset),
                 "PassLabels": sum(row["SourceResult"] == "Pass" for row in subset),
                 "FailLabels": sum(row["SourceResult"] == "Fail" for row in subset),
                 "BlankResultLabels": sum(row["SourceResult"] == "" for row in subset)}
        entry["RowReconciles"] = entry["OutputRows"] == entry["ExpectedInputRows"] == entry["ReadyRows"] + entry["ReviewRows"]
        per_source.append(entry)
    assert per_source == summary["per_source"]
    expected_recon = read_csv("expected-reconciliation.csv")
    serialized_recon = [{k: (str(v).lower() if isinstance(v, bool) else str(v)) for k, v in row.items()} for row in per_source]
    assert serialized_recon == expected_recon

    # Independent spot checks for the two deliberately ambiguous date strings,
    # raw leading zeros, unit conversion, retained duplicates and error overlap.
    lookup = {(row["SourceFile"], int(row["SourceRow"])): row for row in derived}
    assert lookup[("inspections_a.csv", 2)]["InspectionDate"] == "2026-02-01"
    assert lookup[("inspections_b.csv", 2)]["InspectionDate"] == "2026-01-02"
    assert lookup[("inspections_a.csv", 2)]["ReadingMM"] == "12.5"
    assert lookup[("inspections_b.csv", 1)]["ReadingMM"] == "12.5"
    assert len({(row["SourceFile"], row["SourceRow"]) for row in derived}) == 10
    assert sum(row["InspectionID"] == "00123" for row in derived) == 2
    assert all(not row["InspectionID"] or row["InspectionID"].startswith("00") for row in derived)
    assert lookup[("inspections_b.csv", 5)]["Issues"] == "invalid_date;missing_source_result"
    assert sum(issue_counts.values()) == 9 != review
    assert lookup[("inspections_b.csv", 4)]["ReadingMM"] == ""

    print(json.dumps({"checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                      "execution_engine": "Python standard library only", "validation_passed": True,
                      "input_file_receipts": byte_receipts, "input_rows": 10, "normalized_rows": 10,
                      "ready_for_demo_rows": ready, "review_rows": review, "rows_removed": 0,
                      "all_expected_rows_and_fields_match": True, "all_expected_reconciliation_counts_match": True,
                      "preserved_leading_zero_ids": True, "date_locale_spot_checks_passed": True,
                      "unit_conversion_spot_checks_passed": True, "source_lineage_unique_and_preserved": True,
                      "duplicate_rows_preserved": True, "issue_overlap_preserved": True,
                      "m_engine_executed": False, "power_query_execution_verified": False,
                      "excel_execution_verified": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
