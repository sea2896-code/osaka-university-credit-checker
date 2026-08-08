from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OverallDisplay:
    title: str
    message: str
    tone: str


def remaining_credits(graduation_credits: float, requirement_total: float) -> float:
    """Return the total-credit gap without changing the underlying allocation result."""
    return round(max(0.0, requirement_total - graduation_credits), 6)


def overall_display(remaining: float, provisional: bool = False) -> OverallDisplay:
    if remaining <= 0:
        message = "必要単位を満たしています。"
        if provisional:
            message += " 要確認科目があるため、判定は確定ではありません。"
        return OverallDisplay("卒業要件クリア！🎉", message, "success")
    if remaining <= 10:
        return OverallDisplay("あとちょっと！！", f"卒業まであと {remaining:g} 単位です。", "near")
    return OverallDisplay("未達🥹🥹", f"卒業まであと {remaining:g} 単位です。", "short")


def should_show_fourth_year_message(year: int | None, remaining: float) -> bool:
    return year == 4 and remaining > 0
