from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from src.allocator import allocate
from src.classifier import classify_all
from src.csv_parser import CSVFormatError, parse_bytes
from src.ui_helpers import overall_display, remaining_credits, should_show_fourth_year_message


st.set_page_config(page_title="阪大 経済 単位チェッカー", page_icon="🎓", layout="wide")


@st.dialog("KOANからのCSVダウンロード手順")
def show_koan_steps() -> None:
    st.caption("KOANで、以下の順番に操作してください。")
    st.markdown("""
    <div class="dialog-steps">
      <div class="dialog-step"><span>🔐</span><div><small>STEP 1</small><b>KOANにログインします</b><p>阪大生のみログイン可能なKOANにアクセスします。</p></div></div>
      <div class="dialog-step"><span>📊</span><div><small>STEP 2</small><b>「成績」アイコンをクリックします</b></div></div>
      <div class="dialog-step"><span>⚙️</span><div><small>STEP 3</small><b>表示範囲を「過去を含めた全成績」にします</b></div></div>
      <div class="dialog-step"><span>⬇️</span><div><small>STEP 4</small><b>「CSVに出力する」をクリックします</b></div></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
:root{--navy:#172554;--blue:#4f7cff;--pink:#ff6fae;--yellow:#ffd95a;--mint:#b9efd8;--ink:#1e293b;--muted:#64748b;--line:#e6eaf2}
.stApp{background:radial-gradient(circle at 8% 0,#fff2f7 0,transparent 27rem),radial-gradient(circle at 95% 8%,#edf4ff 0,transparent 30rem),#fbfcff;color:var(--ink)}
.block-container{max-width:1040px;padding-top:.8rem;padding-bottom:3rem}
.hero{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1rem 1.35rem;border:1px solid rgba(79,124,255,.14);border-radius:22px;background:rgba(255,255,255,.9);box-shadow:0 10px 30px rgba(30,41,59,.06);margin-bottom:1rem}
.hero-main{display:flex;align-items:center;gap:.65rem}.hero-icon{font-size:1.8rem}.hero h1{margin:0;color:var(--navy);font-size:clamp(1.45rem,3vw,2rem);line-height:1.1;letter-spacing:-.035em;font-weight:900}.hero p{color:var(--muted);font-size:.84rem;margin:.25rem 0 0;font-weight:650}.year-badge{flex:none;padding:.45rem .72rem;border-radius:999px;background:#fff0f6;color:#b83b72;font-size:.75rem;font-weight:850}
.section-card,.metric-card,.privacy-card,.notice-card,.steps-card{padding:1.35rem;border:1px solid var(--line);border-radius:24px;background:rgba(255,255,255,.94);box-shadow:0 12px 35px rgba(30,41,59,.055);margin-bottom:1rem}
.card-kicker{font-size:.76rem;letter-spacing:.08em;color:var(--blue);font-weight:850;text-transform:uppercase;margin-bottom:.35rem}
.card-title{font-size:1.25rem;color:var(--navy);font-weight:850;line-height:1.35;margin-bottom:.35rem}
.card-copy{color:var(--muted);font-size:.92rem;line-height:1.7}
.privacy-card{background:#effbf6;border-color:#cdeede;color:#28604a;font-size:.88rem;line-height:1.65}
.steps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin-top:1rem}
.step{min-height:150px;padding:1rem;border-radius:18px;background:#f8faff;border:1px solid #e7ecff}
.step:nth-child(2){background:#fff6fa;border-color:#ffe2ee}.step:nth-child(3){background:#fffbea;border-color:#fff0ae}.step:nth-child(4){background:#effbf6;border-color:#d4f2e4}
.step-icon{font-size:1.65rem}.step-label{margin:.5rem 0 .15rem;color:var(--blue);font-size:.7rem;font-weight:900;letter-spacing:.08em}.step b{display:block;color:var(--navy);font-size:.9rem;line-height:1.4}.step p{color:var(--muted);font-size:.76rem;line-height:1.45;margin:.35rem 0 0}
.dialog-steps{display:grid;gap:.65rem}.dialog-step{display:flex;align-items:flex-start;gap:.8rem;padding:.85rem;border-radius:16px;background:#f8faff;border:1px solid #e7ecff}.dialog-step:nth-child(2){background:#fff6fa;border-color:#ffe2ee}.dialog-step:nth-child(3){background:#fffbea;border-color:#fff0ae}.dialog-step:nth-child(4){background:#effbf6;border-color:#d4f2e4}.dialog-step>span{font-size:1.5rem}.dialog-step small{display:block;color:var(--blue);font-size:.67rem;font-weight:900;letter-spacing:.08em}.dialog-step b{display:block;color:var(--navy);font-size:.9rem;margin-top:.12rem}.dialog-step p{color:var(--muted);font-size:.76rem;margin:.25rem 0 0}
.result-card{position:relative;overflow:hidden;padding:1.65rem 1.8rem;border-radius:28px;background:linear-gradient(135deg,#172554 0%,#263b7c 68%,#4f7cff 100%);color:white;box-shadow:0 20px 42px rgba(23,37,84,.18);margin:1.4rem 0 1rem}
.result-card.success{background:linear-gradient(135deg,#12634a,#239a70)}.result-card.near{background:linear-gradient(135deg,#6b3dbd,#ff6fae)}
.result-label{font-size:.75rem;letter-spacing:.1em;font-weight:800;opacity:.72}.result-title{font-size:clamp(1.65rem,3vw,2.45rem);font-weight:900;margin:.35rem 0}.remaining-wrap{display:flex;align-items:end;gap:.55rem;margin:.65rem 0}.remaining-number{font-size:clamp(4rem,8vw,6.8rem);line-height:.8;font-weight:950;letter-spacing:-.06em}.remaining-unit{font-weight:800;font-size:1rem;padding-bottom:.35rem}.result-copy{opacity:.88;font-weight:650}.result-meta{display:flex;gap:.55rem;flex-wrap:wrap;margin-top:1rem}.pill{padding:.4rem .7rem;border-radius:999px;background:rgba(255,255,255,.14);font-size:.78rem;font-weight:750}
.progress-shell{height:12px;border-radius:999px;background:#e8ecf7;overflow:hidden;margin:.75rem 0 .45rem}.progress-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--blue),#75a7ff)}
.progress-card{padding:1.05rem 1.1rem;border:1px solid var(--line);border-radius:20px;background:white;margin-bottom:.75rem}.progress-top{display:flex;justify-content:space-between;gap:.7rem;align-items:start}.progress-name{font-weight:850;color:var(--navy)}.status-tag{white-space:nowrap;padding:.26rem .55rem;border-radius:999px;background:#eef2ff;color:#4059a9;font-size:.7rem;font-weight:850}.status-tag.ok{background:#e5f8ef;color:#167a57}.status-tag.short{background:#fff1f6;color:#b83b72}.progress-value{font-size:1.55rem;font-weight:900;color:var(--navy);margin-top:.35rem}.progress-value small{font-size:.75rem;color:var(--muted);font-weight:700}.progress-foot{display:flex;justify-content:space-between;color:var(--muted);font-size:.75rem}.bubble{display:inline-block;padding:.7rem 1rem;border-radius:16px 16px 16px 4px;background:#fff4c7;color:#765d08;font-weight:750;margin:0 0 1rem}
.notice-card{background:#fffaf0;border-color:#f5e4b4;color:#6d5a23}.notice-card b{color:#4e421d}.filename{padding:.65rem .8rem;border-radius:12px;background:#eef3ff;color:#314a91;font-weight:750;font-size:.86rem;margin-bottom:.75rem}
div[data-testid="stFileUploader"]{padding:1rem;border:2px dashed #b9c9ff;border-radius:20px;background:#f7f9ff}div[data-testid="stFileUploader"] section{background:transparent;border:0}
.stDownloadButton button,.stButton button{border:0!important;border-radius:999px!important;background:linear-gradient(90deg,var(--blue),#6f8fff)!important;color:white!important;font-weight:800!important;box-shadow:0 8px 20px rgba(79,124,255,.2)}
.st-key-upload_card{padding:1.35rem!important;border:1px solid var(--line)!important;border-radius:24px!important;background:#fff!important;box-shadow:0 12px 35px rgba(30,41,59,.055);margin-bottom:1rem}.st-key-upload_card .section-card{padding:0;border:0;box-shadow:none;margin-bottom:.75rem}.st-key-upload_card .privacy-card{margin-bottom:0}
.st-key-koan_help button{background:#fff!important;color:var(--navy)!important;border:1px solid #dce3f2!important;box-shadow:0 7px 18px rgba(30,41,59,.07)!important}.st-key-koan_help button:hover{border-color:#aebeff!important;color:var(--blue)!important}
div[data-testid="stExpander"]{border:1px solid var(--line);border-radius:18px;background:white;overflow:hidden;margin-bottom:.65rem}
@media(max-width:900px){.steps{grid-template-columns:1fr}.step{min-height:auto}.block-container{padding-left:1rem;padding-right:1rem}}
@media(max-width:560px){.hero{align-items:flex-start;padding:.85rem 1rem}.year-badge{font-size:.67rem}.hero-icon{font-size:1.45rem}.hero p{font-size:.76rem}}
</style>
<div class="hero"><div class="hero-main"><span class="hero-icon">🎓</span><div><h1>阪大 経済 単位チェッカー</h1><p>あなたの卒業までの道のりを、サクッと可視化。</p></div></div><span class="year-badge">2023年度入学者向け</span></div>
""", unsafe_allow_html=True)

with st.container(border=True, key="upload_card"):
    st.markdown("""<div class="section-card"><div class="card-kicker">START HERE</div><div class="card-title">① 成績CSVをアップロードしてください</div><div class="card-copy">KOANから出力した成績CSVを選択してください。ドラッグ＆ドロップ、またはファイル選択に対応しています。</div></div>""", unsafe_allow_html=True)
    uploaded = st.file_uploader("成績CSV", type=["csv"], help="UTF-8 / CP932 / Shift_JIS に対応", label_visibility="collapsed")
    if uploaded:
        st.markdown(f'<div class="filename">📄 選択中：{escape(uploaded.name)}</div>', unsafe_allow_html=True)
    st.markdown("""<div class="privacy-card">🔒 <b>プライバシーについて</b><br>アップロードしたCSVを恒久保存する処理は実装していません。判定処理のためにデータを一時的に読み込みます。学籍番号は画面上に表示しません。</div>""", unsafe_allow_html=True)
with st.container(key="koan_help"):
    if st.button("❓ KOANからのダウンロード方法がわからない方はこちら", use_container_width=True):
        show_koan_steps()

if uploaded:
    try:
        courses = classify_all(parse_bytes(uploaded.getvalue()))
        result = allocate(courses)
    except CSVFormatError as exc:
        st.error(str(exc))
        st.stop()

    remaining = remaining_credits(result.graduation_credits, result.requirement_total)
    display = overall_display(remaining, result.provisional)
    progress_percent = min(100.0, result.graduation_credits / result.requirement_total * 100) if result.requirement_total else 0
    st.markdown(f"""<div class="result-card {display.tone}"><div class="result-label">総合判定</div><div class="result-title">{display.title}</div><div class="remaining-wrap"><span class="remaining-number">{remaining:g}</span><span class="remaining-unit">残り単位</span></div><div class="result-copy">{display.message}</div><div class="progress-shell"><div class="progress-fill" style="width:{progress_percent:.1f}%"></div></div><div class="progress-foot" style="color:rgba(255,255,255,.75)"><span>取得 {result.graduation_credits:g} / 必要 {result.requirement_total:g} 単位</span><b>進捗率 {progress_percent:.1f}%</b></div><div class="result-meta"><span class="pill">既存判定：{escape(result.status)}</span>{'<span class="pill">要確認科目あり</span>' if result.provisional else ''}</div></div>""", unsafe_allow_html=True)
    if should_show_fourth_year_message(None, remaining):
        st.markdown('<div class="bubble">4年生、大丈夫そう？笑</div>', unsafe_allow_html=True)

    st.markdown('<div class="card-kicker">YOUR PROGRESS</div><div class="card-title">区分別進捗</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for index, item in enumerate(result.progress.values()):
        short = item["short"]
        percent = min(100.0, item["earned"] / item["required"] * 100) if item["required"] else 100
        if item["met"]:
            status, status_class = "OK", "ok"
        elif short <= 10:
            status, status_class = "あとちょっと！", ""
        else:
            status, status_class = "不足あり", "short"
        with cols[index % 2]:
            st.markdown(f"""<div class="progress-card"><div class="progress-top"><span class="progress-name">{escape(item['label'])}</span><span class="status-tag {status_class}">{status}</span></div><div class="progress-value">{item['earned']:g} <small>/ {item['required']:g} 単位</small></div><div class="progress-shell"><div class="progress-fill" style="width:{percent:.1f}%"></div></div><div class="progress-foot"><span>進捗 {percent:.1f}%</span><span>不足 {short:g} 単位</span></div></div>""", unsafe_allow_html=True)

    if result.shortages:
        with st.expander("不足している卒業要件", expanded=True):
            for shortage in result.shortages:
                st.write("・", shortage)
    if result.transfers:
        with st.expander("単位振替の内訳", expanded=True):
            for transfer in result.transfers:
                st.write("・", transfer)

    rows = pd.DataFrame(result.rows())
    review = rows[rows["要確認"] == "Yes"]
    excluded = rows[rows["卒業算入"] == "No"]
    if not review.empty:
        st.markdown("""<div class="notice-card">🧭 <b>要確認科目があります</b><br>この科目は自動判定できませんでした。自動加算はしていませんので、学生便覧等でご確認ください。</div>""", unsafe_allow_html=True)
        st.dataframe(review, use_container_width=True, hide_index=True)
    if not excluded.empty:
        with st.expander("卒業単位に算入されない科目"):
            st.dataframe(excluded, use_container_width=True, hide_index=True)
    with st.expander("全科目の判定履歴（元区分 → 最終算入先）", expanded=True):
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.download_button("判定履歴CSVをダウンロード", rows.to_csv(index=False).encode("utf-8-sig"), "判定履歴.csv", "text/csv")
else:
    st.markdown("""<div class="section-card"><div class="card-kicker">NEXT</div><div class="card-title">CSVをアップロードすると、この下に結果が表示されます。</div><div class="card-copy">総合判定から区分別進捗、詳細な判定履歴まで、上から順に確認できます。</div></div>""", unsafe_allow_html=True)

st.divider()
st.markdown("""<div class="notice-card">⚠️ <b>2023年度入学・大阪大学経済学部向け</b><br>本ツールは大阪大学公式のシステムではありません。判定結果は参考情報です。<br><br>卒業要件の最終確認は、大阪大学経済学部の学生便覧・卒業要件確認表・教務係等で確認してください。</div>""", unsafe_allow_html=True)
