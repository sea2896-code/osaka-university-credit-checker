from src.allocator import allocate
from src.classifier import classify_all
from src.models import Course


def course(
    name: str,
    credits: float,
    subcategory: str,
    detail: str = "",
    passed: str = "合",
) -> Course:
    return Course(name=name, credits=credits, subcategory=subcategory, detail=detail, passed=passed)


def test_existing_classification_and_allocation_regression():
    courses = [
        course("扉科目", 2, "学問への扉"),
        course("ミクロ経済学の考え方", 5, "基盤教養教育科目"),
        course("マクロ経済学の考え方", 7, "基盤教養教育科目"),
        course("情報社会基礎", 2, "情報教育科目"),
        course("スポーツ実習A", 2, "健康・スポーツ教育科目"),
        course("高度教養", 2, "高度教養教育科目"),
        course("総合英語A", 6, "第1外国語"),
        course("実践英語A", 2, "第1外国語"),
        course("ドイツ語初級I", 1, "第2外国語"),
        course("ドイツ語初級II", 1, "第2外国語"),
        course("ドイツ語中級A", 1, "第2外国語"),
        course("ドイツ語中級B", 1, "第2外国語"),
        course("ドイツ語圏文化A", 4, "グローバル理解"),
        course("高度国際", 2, "高度国際性涵養教育科目"),
        course("解析学入門", 2, "専門基礎教育科目"),
        course("線形代数学入門", 2, "専門基礎教育科目"),
        course("専門セミナー", 2, "専門セミナー"),
        course("研究セミナー", 4, "研究セミナー"),
        course("選必1", 12, "選択必修1"),
        course("選必2", 28, "選択必修2"),
        course("専門選択", 22, "選択"),
        course("自由選択", 20, "選択科目(教職)"),
        course("不合格科目", 2, "選択", passed="否"),
        course("分類不能科目", 2, "その他"),
    ]

    result = allocate(classify_all(courses))

    assert result.graduation_credits == 130
    assert result.requirement_total == 130
    assert {key: item["earned"] for key, item in result.progress.items()} == {
        "doorway": 2,
        "basic_liberal": 10,
        "information": 2,
        "health_sports": 2,
        "advanced_liberal": 2,
        "first_language": 8,
        "second_language": 4,
        "global_understanding": 4,
        "advanced_international": 2,
        "professional_foundation": 4,
        "professional_required": 6,
        "elective_required_1": 12,
        "elective_required_2": 28,
        "professional_elective": 22,
        "free_elective": 22,
    }
    assert result.shortages == []
    assert result.transfers == ["基盤教養の余剰 2単位 → 自由選択"]
    assert result.provisional
    assert result.status == "暫定判定（要確認あり）"
    rows = result.rows()
    assert any(row["最終算入先"] == "要確認" and row["卒業算入"] == "No" for row in rows)
    assert any(row["最終算入先"] == "算入対象外" and row["卒業算入"] == "No" for row in rows)
