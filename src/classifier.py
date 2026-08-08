from __future__ import annotations

import re

from .csv_parser import normalize
from .models import Course


LANGUAGES = ("ドイツ語", "フランス語", "ロシア語", "中国語")


def _language(text: str) -> str:
    return next((lang for lang in LANGUAGES if lang in text), "")


def classify(course: Course) -> Course:
    name, detail, sub = map(normalize, (course.name, course.detail, course.subcategory))
    text = detail + sub + name

    if normalize(course.passed) != "合":
        course.category, course.reason = "excluded", "合否が「合」ではないため"
    elif "随意科目" in text:
        course.category, course.reason = "excluded", "随意科目は卒業単位に算入しないため"
    elif "教職教育科目" in detail or "教職教育科目" in sub:
        course.category, course.reason = "excluded", "教職教育科目は卒業単位に算入しないため"
    elif "選択(教職)" in sub or "選択科目(教職)" in sub:
        course.category, course.reason = "free_direct", "2023年度学生便覧の選択科目（教職）"
    elif "学問への扉" in sub:
        course.category, course.reason = "doorway", "科目小区分が学問への扉"
    elif "基盤教養教育科目" in sub:
        course.category, course.reason = "basic_liberal", "科目小区分が基盤教養教育科目"
    elif "情報教育科目" in sub:
        course.category, course.reason = "information", "科目小区分が情報教育科目"
    elif "健康・スポーツ教育科目" in sub:
        course.category, course.reason = "health_sports", "科目小区分が健康・スポーツ教育科目"
    elif "高度教養教育科目" in sub:
        course.category, course.reason = "advanced_liberal", "科目小区分が高度教養教育科目"
    elif "第1外国語" in sub:
        if "総合英語" in name:
            course.category = "first_general"
        elif "実践英語" in name:
            course.category = "first_practical"
        else:
            course.category, course.needs_review = "unknown", True
        course.reason = "第1外国語の科目構成で判定"
    elif "第2外国語" in sub:
        course.category, course.language = "second_language", _language(text)
        course.reason = f"第2外国語（{course.language or '言語不明'}）"
        course.needs_review = not bool(course.language)
    elif "グローバル理解" in sub:
        course.category, course.language = "global_understanding", _language(text)
        course.reason = f"グローバル理解（{course.language or '言語不明'}）"
        course.needs_review = not bool(course.language)
    elif "高度国際性涵養教育科目" in sub:
        course.category, course.reason = "advanced_international", "高度国際性涵養教育科目へ優先充当"
    elif "専門基礎教育科目" in sub:
        course.category, course.reason = "professional_foundation", "専門基礎教育科目"
    elif "専門セミナー" in sub:
        course.category, course.reason = "professional_seminar", "必修の専門セミナー"
    elif "研究セミナー" in sub and "選択" not in sub:
        course.category, course.reason = "research_seminar", "必修の研究セミナー"
    elif "選択必修1" in sub:
        course.category, course.reason = "elective_required_1", "科目小区分が選択必修1"
    elif "選択必修2" in sub:
        course.category, course.reason = "elective_required_2", "科目小区分が選択必修2"
    elif sub == "選択" or "専門教育系科目" in detail and "選択" in sub:
        course.category, course.reason = "professional_elective", "専門教育科目の選択科目"
    elif "アドヴァンスト・セミナー" in text or "アドヴァンストセミナー" in text:
        course.category, course.reason = "free_direct", "公式確認表で自由選択に算入可能"
    elif "他学部" in detail:
        course.category, course.reason, course.needs_review = "unknown", "他学部科目は算入可否の確認が必要", True
    else:
        course.category, course.reason, course.needs_review = "unknown", "公式ルールとの対応を確定できない", True
    return course


def classify_all(courses: list[Course]) -> list[Course]:
    return [classify(course) for course in courses]
