from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path

from .models import Course


ENCODINGS = ("utf-8-sig", "cp932", "shift_jis")
REQUIRED_COLUMNS = ("科目詳細区分", "科目小区分", "開講科目名", "単位数", "合否")


class CSVFormatError(ValueError):
    pass


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"[\s\u3000]+", "", value).strip()


def decode_csv(data: bytes) -> tuple[str, str]:
    for encoding in ENCODINGS:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "�" not in text and normalize("科目詳細区分") in normalize(text):
            return text, encoding
    raise CSVFormatError("CSVの文字コードまたは形式を認識できませんでした")


def parse_bytes(data: bytes) -> list[Course]:
    text, _ = decode_csv(data)
    rows = list(csv.reader(io.StringIO(text)))
    header_index = -1
    header: list[str] = []
    for index, row in enumerate(rows):
        normalized = [normalize(cell) for cell in row]
        if all(any(required == cell for cell in normalized) for required in REQUIRED_COLUMNS):
            header_index, header = index, normalized
            break
    if header_index < 0:
        raise CSVFormatError("科目一覧のヘッダーを見つけられませんでした")

    aliases = {
        "科目詳細区分": "detail", "科目小区分": "subcategory", "開講科目名": "name",
        "単位数": "credits", "修得年度": "year", "修得学期": "term", "評語": "grade", "合否": "passed",
    }
    positions = {aliases[name]: header.index(name) for name in aliases if name in header}
    courses: list[Course] = []
    for source_row, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        def get(key: str) -> str:
            pos = positions.get(key, -1)
            return row[pos].strip() if 0 <= pos < len(row) else ""
        if not get("name"):
            continue
        try:
            credits = float(normalize(get("credits")).replace(",", ""))
        except ValueError:
            continue
        courses.append(Course(
            name=get("name").strip(), credits=credits, detail=get("detail"),
            subcategory=get("subcategory"), year=get("year"), term=get("term"),
            grade=get("grade"), passed=get("passed"), source_row=source_row,
        ))
    if not courses:
        raise CSVFormatError("科目データを読み取れませんでした")
    return courses


def parse_file(path: str | Path) -> list[Course]:
    return parse_bytes(Path(path).read_bytes())
