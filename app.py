# -*- coding: utf-8 -*-
import os
import random
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="로또 5게임 생성기", layout="centered")

EXCEL_FILENAME = "로또복권 번호모음1231.xlsx"
CSV_FILENAME = "lotto_5games_history.csv"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, EXCEL_FILENAME)
CSV_PATH = os.path.join(BASE_DIR, CSV_FILENAME)


@st.cache_data
def load_winning_numbers(excel_path: str) -> pd.DataFrame:
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"엑셀 파일이 서버에 없습니다: {EXCEL_FILENAME}")

    df = pd.read_excel(excel_path, engine="openpyxl")

    # 숫자형 컬럼 후보 탐색
    num_cols = []
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().mean() > 0.7:
            num_cols.append(c)

    if len(num_cols) < 6:
        raise ValueError(f"당첨번호로 보이는 숫자 컬럼이 6개 미만입니다. 후보: {num_cols}")

    # 보너스 컬럼 제외
    bonus_like = {"bonus", "보너스", "bns"}
    filtered = []
    for c in num_cols:
        cname = str(c).strip().lower()
        if any(k in cname for k in bonus_like):
            continue
        filtered.append(c)

    cols6 = filtered[:6] if len(filtered) >= 6 else num_cols[:6]

    win = df[cols6].copy()
    for c in win.columns:
        win[c] = pd.to_numeric(win[c], errors="coerce").astype("Int64")

    win = win.where((win >= 1) & (win <= 45))
    if win.notna().sum().sum() == 0:
        raise ValueError("엑셀에서 1~45 범위의 당첨번호를 찾지 못했습니다.")
    return win


def calc_frequency(win_df: pd.DataFrame) -> pd.Series:
    nums = win_df.stack(dropna=True).astype(int)
    freq = nums.value_counts().sort_index()
    return freq.reindex(range(1, 46), fill_value=0)


def build_pools(freq: pd.Series):
    top6 = freq.sort_values(ascending=False).head(6).index.tolist()
    bottom10 = freq.sort_values(ascending=True).head(10).index.tolist()
    mean_freq = freq.mean()
    mid_candidates = (freq - mean_freq).abs().sort_values(ascending=True).head(12).index.tolist()
    return top6, bottom10, mid_candidates


def gen_random_game():
    return tuple(sorted(random.sample(range(1, 46), 6)))


def gen_mix_game(fixed_numbers, fixed_count: int):
    fixed = random.sample(list(fixed_numbers), fixed_count)
    remaining_pool = [n for n in range(1, 46) if n not in fixed]
    rest = random.sample(remaining_pool, 6 - fixed_count)
    return tuple(sorted(fixed + rest))


def generate_5_games(top6, bottom10, mid_candidates):
    while True:
        games = [
            gen_random_game(),
            gen_random_game(),
            gen_mix_game(top6, 2),
            gen_mix_game(mid_candidates, 2),
            gen_mix_game(bottom10, 2),
        ]
        if len(set(games)) == 5:
            return games


def save_history(rows):
    df_out = pd.DataFrame(
        rows,
        columns=["created_at", "strategy", "n1", "n2", "n3", "n4", "n5", "n6"]
    )
    write_header = not os.path.exists(CSV_PATH)
    df_out.to_csv(CSV_PATH, mode="a", header=write_header, index=False, encoding="utf-8-sig")


# ---------------- UI ----------------
st.title("로또 6/45  |  5게임 생성기")
st.caption("버튼 한 번이면 5게임이 바로 생성됩니다.")

try:
    win = load_winning_numbers(EXCEL_PATH)
    freq = calc_frequency(win)
    top6, bottom10, mid_candidates = build_pools(freq)
except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
    st.stop()

with st.expander("빈도 기반 풀 보기", expanded=False):
    st.write("고빈도 TOP6:", top6)
    st.write("저빈도 BOTTOM10:", bottom10)
    st.write("중립 후보 12개:", mid_candidates)

save_toggle = st.checkbox("히스토리 저장", value=True)

if st.button("생성", type="primary", use_container_width=True):
    labels = [
        "RANDOM_1",
        "RANDOM_2",
        "HIGH_MIX",
        "MID_MIX",
        "LOW_MIX",
    ]
    games = generate_5_games(top6, bottom10, mid_candidates)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.subheader("이번 회차 5게임")
    for label, g in zip(labels, games):
        st.write(f"**{label}**")
        st.code("  ".join(map(str, g)))

    if save_toggle:
        rows = [[now, label, *g] for label, g in zip(labels, games)]
        save_history(rows)
        st.success("저장 완료!")

st.divider()

st.subheader("최근 히스토리(최대 50개)")
if os.path.exists(CSV_PATH):
    hist = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    st.dataframe(hist.tail(50), use_container_width=True)
else:
    st.info("아직 저장된 히스토리가 없습니다.")
