from __future__ import annotations

import pandas as pd
import streamlit as st

from src.allocator import allocate
from src.classifier import classify_all
from src.csv_parser import CSVFormatError, parse_bytes


st.set_page_config(page_title="大阪大学経済学部 卒業要件チェッカー", page_icon="🎓", layout="wide")
st.markdown("""
<style>
.block-container{max-width:1120px;padding-top:2.2rem}.hero{padding:2rem;border-radius:24px;background:linear-gradient(135deg,#071f3d,#103f6f);color:white;margin-bottom:1.4rem}.hero h1{margin:0;font-size:2.15rem}.hero p{opacity:.84;margin:.55rem 0 0}.metric-card{padding:1.1rem 1.2rem;border:1px solid #e5e7eb;border-radius:16px;background:white}.ok{color:#087f5b}.warn{color:#b7791f}.bad{color:#c92a2a}.privacy{background:#edf7f4;padding:.8rem 1rem;border-radius:12px;color:#1f5e50}
</style>
<div class="hero"><h1>大阪大学経済学部<br>卒業要件チェッカー</h1><p>2023年度入学者用 · 成績CSVから単位の充足状況を確認</p></div>
""", unsafe_allow_html=True)
st.markdown('<div class="privacy">🔒 CSVは保存せず、この画面内だけで処理します。学籍番号も表示しません。</div>', unsafe_allow_html=True)
uploaded = st.file_uploader("KOAN等から取得した成績CSVを選択", type=["csv"], help="UTF-8 / CP932 / Shift_JIS に対応")

if uploaded:
    try:
        courses = classify_all(parse_bytes(uploaded.getvalue()))
        result = allocate(courses)
    except CSVFormatError as exc:
        st.error(str(exc))
        st.stop()

    color = "ok" if "達成" in result.status else ("warn" if result.provisional else "bad")
    st.markdown(f"## 卒業要件判定\n<div class='metric-card'><div class='{color}' style='font-size:1.5rem;font-weight:700'>{result.status}</div><div style='font-size:2.3rem;font-weight:800'>{result.graduation_credits:g} <span style='font-size:1rem;color:#64748b'>/ {result.requirement_total:g} 単位</span></div></div>", unsafe_allow_html=True)
    st.caption("要確認科目がある場合は、達成条件を満たしていても暫定判定になります。")

    st.subheader("区分別進捗")
    cols = st.columns(3)
    for index, item in enumerate(result.progress.values()):
        with cols[index % 3]:
            status = "達成" if item["met"] else f"あと {item['short']:g}"
            st.markdown(f"<div class='metric-card'><b>{item['label']}</b><div style='font-size:1.45rem;font-weight:750'>{item['earned']:g} / {item['required']:g}</div><span class={'ok' if item['met'] else 'bad'}>{status}</span></div>", unsafe_allow_html=True)

    if result.shortages:
        st.subheader("不足している卒業要件")
        for shortage in result.shortages: st.error(shortage)
    if result.transfers:
        with st.expander("単位振替の内訳", expanded=True):
            for transfer in result.transfers: st.write("•", transfer)

    rows = pd.DataFrame(result.rows())
    review = rows[rows["要確認"] == "Yes"]
    excluded = rows[rows["卒業算入"] == "No"]
    if not review.empty:
        st.subheader("要確認科目")
        st.warning("以下の科目は公式ルールとの対応を確定できないため、自動加算していません。")
        st.dataframe(review, use_container_width=True, hide_index=True)
    if not excluded.empty:
        with st.expander("卒業単位に算入されない科目"):
            st.dataframe(excluded, use_container_width=True, hide_index=True)
    with st.expander("全科目の判定履歴（元区分 → 最終算入先）", expanded=True):
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.download_button("判定履歴をCSVで保存", rows.to_csv(index=False).encode("utf-8-sig"), "判定履歴.csv", "text/csv")
else:
    st.info("CSVをアップロードすると、科目を自動分類して判定結果を表示します。")
    st.markdown("### 確認できること\n- 必修科目と各区分の充足状況\n- 余剰単位の振替先\n- 不足している科目・単位\n- 全科目の分類根拠と要確認項目")

st.divider()
st.caption("本ツールは大阪大学の公式システムではありません。判定結果は参考情報です。卒業要件の最終確認は大阪大学経済学部の学生便覧・卒業要件確認表・教務係等で確認してください。")
