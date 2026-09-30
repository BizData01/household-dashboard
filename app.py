import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
st.set_page_config(page_title="가계부 대시보드", page_icon="💰", layout="wide")

SHEET_ID = "1IisJb1FIs32KOAma1T-8L4meWDGiokYv-9fkqRSoW2g"
SHEET_GID = 1379534029

@st.cache_data(ttl=300)  # 5분마다 자동 갱신
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"], format="%Y.%m.%d")
    df["수입"] = pd.to_numeric(df["수입"], errors="coerce").fillna(0).astype(int)
    df["지출"] = pd.to_numeric(df["지출"], errors="coerce").fillna(0).astype(int)
    df["잔액"] = pd.to_numeric(df["잔액"], errors="coerce").fillna(0).astype(int)
    df["월"] = df["날짜"].dt.to_period("M").astype(str)
    return df


# --- 데이터 로드 ---
try:
    df = load_data()
except Exception as e:
    st.error(f"Google Sheets 연결 실패: {e}")
    st.info("Google Sheet이 공개(링크가 있는 모든 사용자) 설정인지 확인하세요.")
    st.stop()

# --- Sidebar ---
st.sidebar.title("🔍 필터")

if st.sidebar.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

months = ["전체"] + sorted(df["월"].unique().tolist())
selected_month = st.sidebar.selectbox("월 선택", months)

all_cats = sorted(df["분류"].unique().tolist())
selected_cat = st.sidebar.multiselect("분류 선택", all_cats)

filtered = df.copy()
if selected_month != "전체":
    filtered = filtered[filtered["월"] == selected_month]
if selected_cat:
    filtered = filtered[filtered["분류"].isin(selected_cat)]

# --- Header ---
st.title("💰 가계부 대시보드")
st.caption(
    f"데이터: {df['날짜'].min().strftime('%Y.%m.%d')} ~ {df['날짜'].max().strftime('%Y.%m.%d')}"
    f"  |  총 {len(df)}건  |  🔁 5분마다 자동 갱신"
)

# --- KPI ---
expense_df = filtered[filtered["지출"] > 0]

total_income = filtered["수입"].sum()
total_expense = filtered["지출"].sum()
net = total_income - total_expense
save_rate = (net / total_income * 100) if total_income > 0 else 0
current_balance = filtered["잔액"].iloc[-1] if not filtered.empty else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("총 수입", f"₩{total_income:,.0f}")
c2.metric("총 지출", f"₩{total_expense:,.0f}")
c3.metric("순 저축", f"₩{net:,.0f}", delta=f"{save_rate:.1f}%")
c4.metric("저축률", f"{save_rate:.1f}%")
c5.metric("현재 잔액", f"₩{current_balance:,.0f}")

st.divider()

# --- Row 1: 월별 수입/지출 & 잔액 추이 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 월별 수입 / 지출")
    monthly = df.groupby("월")[["수입", "지출"]].sum().reset_index()
    fig = go.Figure()
    fig.add_bar(x=monthly["월"], y=monthly["수입"], name="수입", marker_color="#4CAF50")
    fig.add_bar(x=monthly["월"], y=monthly["지출"], name="지출", marker_color="#F44336")
    fig.update_layout(barmode="group", height=350, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📈 잔액 추이")
    fig2 = px.line(df, x="날짜", y="잔액", markers=True, color_discrete_sequence=["#2196F3"])
    fig2.update_layout(height=350, margin=dict(t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

# --- Row 2: 분류별 지출 & 결제방법 ---
col3, col4 = st.columns(2)

with col3:
    st.subheader("🥧 분류별 지출")
    cat_exp = expense_df.groupby("분류")["지출"].sum().reset_index().sort_values("지출", ascending=False)
    fig3 = px.pie(cat_exp, names="분류", values="지출", hole=0.4,
                  color_discrete_sequence=px.colors.qualitative.Set3)
    fig3.update_layout(height=380, margin=dict(t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("💳 결제방법별 지출")
    pay_exp = expense_df.groupby("결제방법")["지출"].sum().reset_index().sort_values("지출", ascending=False)
    fig4 = px.bar(pay_exp, x="지출", y="결제방법", orientation="h",
                  color="지출", color_continuous_scale="Blues")
    fig4.update_layout(height=380, margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)

# --- Row 3: 분류별 지출 누적 바 ---
st.subheader("📋 월별 분류 지출 누적")
cat_bar = expense_df.groupby(["월", "분류"])["지출"].sum().reset_index()
fig5 = px.bar(cat_bar, x="월", y="지출", color="분류", barmode="stack",
              color_discrete_sequence=px.colors.qualitative.Pastel)
fig5.update_layout(height=350, margin=dict(t=10, b=10))
st.plotly_chart(fig5, use_container_width=True)

# --- 거래 내역 테이블 ---
st.subheader("📄 거래 내역")
display_df = filtered[["날짜", "항목", "분류", "수입", "지출", "잔액", "결제방법", "메모"]].copy()
display_df["날짜"] = display_df["날짜"].dt.strftime("%Y.%m.%d")
display_df["수입"] = display_df["수입"].apply(lambda x: f"₩{x:,.0f}" if x > 0 else "-")
display_df["지출"] = display_df["지출"].apply(lambda x: f"₩{x:,.0f}" if x > 0 else "-")
display_df["잔액"] = display_df["잔액"].apply(lambda x: f"₩{x:,.0f}")
st.dataframe(display_df, use_container_width=True, hide_index=True)
