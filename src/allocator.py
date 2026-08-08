from __future__ import annotations

import re
from collections import defaultdict
from copy import deepcopy

from .graduation_rules import load_rules
from .csv_parser import normalize
from .models import Allocation, Course, Result


LABELS = {
    "doorway": "学問への扉", "basic_liberal": "基盤教養", "information": "情報教育",
    "health_sports": "健康・スポーツ", "advanced_liberal": "高度教養",
    "first_language": "第1外国語", "second_language": "第2外国語",
    "global_understanding": "グローバル理解", "advanced_international": "高度国際性涵養",
    "professional_foundation": "専門基礎", "professional_required": "専門必修",
    "elective_required_1": "選択必修1", "elective_required_2": "選択必修2",
    "professional_elective": "専門選択", "free_elective": "自由選択",
}


def _total(courses: list[Course]) -> float:
    return round(sum(c.credits for c in courses), 6)


def _take(courses: list[Course], amount: float, destination: str, allocations: list[Allocation], reason: str) -> tuple[float, list[Course]]:
    remaining, leftovers = amount, []
    for course in courses:
        used = min(course.credits, max(remaining, 0))
        if used:
            allocations.append(Allocation(course, destination, used, True, reason))
            remaining -= used
        extra = course.credits - used
        if extra > 0:
            clone = deepcopy(course)
            clone.credits = extra
            leftovers.append(clone)
    return amount - remaining, leftovers


def _second_language_complete(courses: list[Course]) -> bool:
    names = [re.sub(r"\s+", "", c.name).upper() for c in courses]
    initial_one = any("初級I" in n and "初級II" not in n for n in names)
    initial_two = any("初級II" in n for n in names)
    intermediate = sum(1 for n in names if "中級" in n)
    return initial_one and initial_two and intermediate >= 2 and _total(courses) >= 4


def allocate(courses: list[Course], rules: dict | None = None) -> Result:
    rules = rules or load_rules()
    req = rules["requirements"]
    pools: dict[str, list[Course]] = defaultdict(list)
    allocations: list[Allocation] = []
    transfers: list[str] = []
    for course in courses:
        pools[course.category].append(course)

    for course in pools["excluded"]:
        allocations.append(Allocation(course, "算入対象外", 0, False, course.reason))
    for course in pools["unknown"]:
        allocations.append(Allocation(course, "要確認", 0, False, course.reason))

    values: dict[str, float] = {}
    free_candidates: list[Course] = list(pools["free_direct"])
    professional_elective_candidates: list[Course] = list(pools["professional_elective"])

    def required_pool(category: str, quota: float, overflow_to: str | None = None) -> None:
        used, overflow = _take(pools[category], quota, LABELS[category], allocations, f"{LABELS[category]}の卒業要件へ充当")
        values[category] = used
        if overflow:
            overflow_credits = _total(overflow)
            if overflow_to == "free":
                free_candidates.extend(overflow)
                transfers.append(f"{LABELS[category]}の余剰 {overflow_credits:g}単位 → 自由選択")
            elif overflow_to == "professional":
                professional_elective_candidates.extend(overflow)
                transfers.append(f"{LABELS[category]}の余剰 {overflow_credits:g}単位 → 専門選択")
            else:
                for c in overflow:
                    allocations.append(Allocation(c, "算入対象外", 0, False, f"{LABELS[category]}の超過分は自由選択へ算入不可"))

    required_pool("doorway", req["doorway"])
    required_pool("basic_liberal", req["basic_liberal"], "free")
    required_pool("information", req["information"])
    required_pool("health_sports", req["health_sports"])
    required_pool("advanced_liberal", req["advanced_liberal"], "free")

    # First language must be 6 credits of comprehensive English + 2 practical English.
    gen_used, gen_extra = _take(pools["first_general"], 6, LABELS["first_language"], allocations, "総合英語6単位へ充当")
    prac_used, prac_extra = _take(pools["first_practical"], 2, LABELS["first_language"], allocations, "実践英語2単位へ充当")
    values["first_language"] = gen_used + prac_used
    multilingual_extra = gen_extra + prac_extra

    # Choose one complete second language; global understanding must match it.
    by_language: dict[str, list[Course]] = defaultdict(list)
    global_by_language: dict[str, list[Course]] = defaultdict(list)
    for c in pools["second_language"]: by_language[c.language].append(c)
    for c in pools["global_understanding"]: global_by_language[c.language].append(c)
    selected_language = next((lang for lang in rules["second_languages"] if _second_language_complete(by_language[lang]) and _total(global_by_language[lang]) >= 4), "")
    second_used = global_used = 0.0
    if selected_language:
        second_used, second_extra = _take(by_language[selected_language], 4, LABELS["second_language"], allocations, f"{selected_language}の初級I・II・中級2科目")
        global_used, global_extra = _take(global_by_language[selected_language], 4, LABELS["global_understanding"], allocations, f"第2外国語と同じ{selected_language}")
        multilingual_extra += second_extra + global_extra
    values["second_language"], values["global_understanding"] = second_used, global_used
    for lang, lang_courses in by_language.items():
        if lang != selected_language:
            for c in lang_courses:
                allocations.append(Allocation(c, "要確認", 0, False, "第2外国語の所定構成または言語一致を確認できない"))
                c.needs_review = True
    for lang, lang_courses in global_by_language.items():
        if lang != selected_language:
            for c in lang_courses:
                allocations.append(Allocation(c, "要確認", 0, False, "第2外国語と同じ言語のグローバル理解ではない"))
                c.needs_review = True
    if multilingual_extra:
        free_candidates.extend(multilingual_extra)
        transfers.append(f"マルチリンガル教育の余剰 {_total(multilingual_extra):g}単位 → 自由選択")

    required_pool("advanced_international", req["advanced_international"], "free")
    required_pool("professional_foundation", req["professional_foundation"])

    # Required seminars, with capped overflow to professional electives.
    seminar_used, seminar_extra = _take(pools["professional_seminar"], 2, LABELS["professional_required"], allocations, "専門セミナー必修2単位")
    research_used, research_extra = _take(pools["research_seminar"], 4, LABELS["professional_required"], allocations, "研究セミナー必修4単位")
    values["professional_required"] = seminar_used + research_used
    for extra, cap, label in ((seminar_extra, 2, "専門セミナー"), (research_extra, 4, "研究セミナー")):
        used, rejected = _take(extra, cap, "専門選択", allocations, f"{label}の算入可能余剰")
        if used:
            # Already recorded in the destination, so it contributes directly below.
            values.setdefault("seminar_elective_overflow", 0)
            values["seminar_elective_overflow"] += used
            transfers.append(f"{label}の余剰 {used:g}単位 → 専門選択")
        for c in rejected:
            allocations.append(Allocation(c, "算入対象外", 0, False, f"{label}の算入上限を超過"))

    required_pool("elective_required_1", req["elective_required_1"], "professional")
    required_pool("elective_required_2", req["elective_required_2"], "professional")
    direct_prof_available = _total(professional_elective_candidates)
    prof_direct_used, prof_extra = _take(professional_elective_candidates, req["professional_elective"] - values.get("seminar_elective_overflow", 0), "専門選択", allocations, "専門選択22単位へ充当")
    values["professional_elective"] = prof_direct_used + values.get("seminar_elective_overflow", 0)
    if prof_extra:
        free_candidates.extend(prof_extra)
        transfers.append(f"専門教育科目の余剰 {_total(prof_extra):g}単位 → 自由選択")

    free_used, free_extra = _take(free_candidates, _total(free_candidates), LABELS["free_elective"], allocations, "公式資料で自由選択に算入可能")
    values["free_elective"] = free_used

    progress: dict[str, dict] = {}
    for key, minimum in req.items():
        earned = values.get(key, 0.0)
        progress[key] = {"label": LABELS[key], "earned": earned, "required": minimum, "met": earned >= minimum, "short": max(0, minimum - earned)}

    # Named-course requirements prevent category totals from masking missing mandatory subjects.
    normalized_names = {normalize(c.name) for c in courses if c.category != "excluded"}
    named_checks = {
        "basic_liberal": ["ミクロ経済学の考え方", "マクロ経済学の考え方"],
        "information": ["情報社会基礎"], "health_sports": ["スポーツ実習A"],
        "professional_foundation": ["解析学入門", "線形代数学入門"],
    }
    for key, required_names in named_checks.items():
        missing = [name for name in required_names if name not in normalized_names]
        if missing:
            progress[key]["met"] = False
            progress[key]["missing_courses"] = missing

    eligible_credits = round(sum(a.credits for a in allocations if a.eligible), 6)
    shortages = []
    for item in progress.values():
        if not item["met"]:
            message = f"{item['label']}：あと{item['short']:g}単位"
            if item.get("missing_courses"):
                message += "（必修: " + "、".join(item["missing_courses"]) + "）"
            shortages.append(message)
    if eligible_credits < rules["graduation_total"]:
        shortages.append(f"卒業算入総単位：あと{rules['graduation_total'] - eligible_credits:g}単位")
    provisional = any(c.needs_review for c in courses)
    achieved = not shortages and not provisional
    status = "卒業要件 達成" if achieved else ("暫定判定（要確認あり）" if provisional else "卒業要件 未達")
    return Result(status, provisional, eligible_credits, rules["graduation_total"], progress, shortages, transfers, allocations)
