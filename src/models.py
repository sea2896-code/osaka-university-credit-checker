from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Course:
    name: str
    credits: float
    detail: str = ""
    subcategory: str = ""
    year: str = ""
    term: str = ""
    grade: str = ""
    passed: str = ""
    source_row: int = 0
    category: str = "unknown"
    language: str = ""
    reason: str = ""
    needs_review: bool = False


@dataclass
class Allocation:
    course: Course
    destination: str
    credits: float
    eligible: bool
    reason: str

    def to_row(self) -> dict[str, Any]:
        return {
            "科目名": self.course.name,
            "単位": self.course.credits,
            "元の科目詳細区分": self.course.detail,
            "元の科目小区分": self.course.subcategory,
            "最終算入先": self.destination,
            "算入単位": self.credits,
            "卒業算入": "Yes" if self.eligible else "No",
            "理由": self.reason,
            "要確認": "Yes" if self.course.needs_review else "No",
        }


@dataclass
class Result:
    status: str
    provisional: bool
    graduation_credits: float
    requirement_total: float
    progress: dict[str, dict[str, Any]]
    shortages: list[str]
    transfers: list[str]
    allocations: list[Allocation] = field(default_factory=list)

    def rows(self) -> list[dict[str, Any]]:
        return [allocation.to_row() for allocation in self.allocations]
