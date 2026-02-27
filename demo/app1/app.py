import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime
import altair as alt

# 1. 基礎防護與環境設定 (處理 SSL 憑證問題)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="遙控無人機資安檢測合格清單 (中揚資訊彙整)", page_icon="🛡️", layout="wide")

# 政府資料開放平台來源
JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"
# 紅色供應鏈品牌清單 (避坑用)
RED_LIST = ["DJI", "大疆", "Autel", "道通", "Hubsan", "FIMI", "哈博森"]

# 2. 強化日期轉換 (處理民國年格式)
def safe_roc_to_datetime(roc_val):
    try:
        s = str(roc_val).strip()
        if len(s) < 6: return None
        year = int(s[:-4]) + 1911
        month = int(s[-4:-2])
        day = int(s[-2:])
        return datetime(year, month, day)
    except:
        return None

@st.cache_data(ttl=3600)
def load_and_fix_data():
    try:
        response = requests.get(JSON_URL, verify=False, timeout=15)
        df = pd.DataFrame(response.json())
        df.columns = [col.strip() for col in df.columns]
        
        # 欄位自動映射 (對齊政府 API 的 Key)
        mapping = {"申請單位": "廠商名稱", "報告日期": "檢測日期"}
        for old_c, new_c in mapping.items():
            if old_c in df.columns: df[new_c] = df[old_c]
        
        # 補齊必要欄位
        for col in ['廠商名稱', '廠牌', '型式', '有效日期']:
            if col not in df.columns: df[col] = "不詳"

        # 日期運算
        today = datetime.now()
        df['西元日期'] = df['有效日期'].apply(safe_roc_to_datetime)
        df['剩餘天數'] = df['西元日期'].apply(lambda x: (x - today).days if x else 9999)
        
        def get_status(days):
            if days == 9999: return "無效期資料"
            if days < 0: return "🚫 已過期"
            if days < 90: return "⚠️ 預警 (90天內)"
            return "✅ 安全"
        df['資安狀態'] = df['剩餘天數'].apply(get_status)
        
        return df
    except Exception as e:
        st.error(f"資料來源連線失敗: {e}")
        return pd.DataFrame()

# 3. 主介面邏輯
def main():
    # 更新標題：改為中揚資訊彙整版本
    st.title("🛡️ 遙控無人機資安檢測合格清單 (中揚資訊彙整)")
    
    if 'search_input' not in st.session_state:
        st.session_state.search_input = ""

    df = load_and_fix_data()
    if df.empty: return

    # --- 左側選單：懶人快速洞察 ---
    st.sidebar.header("⚡ 懶人快速洞察")
    
    quick_mode = st.sidebar.radio(
        "選擇快查模式：",
        ["全部清單", "✅ 非敏感供應鏈 (本土)", "🚫 敏感供應鏈 (避坑)", "🏆 高資安等級 (Level 3)", "⏳ 效期預警模式"],
        key="quick_mode"
    )
    
    if st.sidebar.button("🧹 清除搜尋條件"):
        st.session_state.search_input = ""
        st.rerun()

    st.sidebar.divider()
    st.sidebar.metric("合格產品總數", len(df))
    
    # --- 核心篩選邏輯 ---
    f_df = df.copy()
    red_pattern = "|".join(RED_LIST)
    
    if quick_mode == "✅ 非敏感供應鏈 (本土)":
        f_df = f_df[~f_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
    elif quick_mode == "🚫 敏感供應鏈 (避坑)":
        f_df = f_df[f_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        st.error("🚨 警告：目前顯示為敏感供應鏈品牌，採購前請確認合規性。")
    elif quick_mode == "🏆 高資安等級 (Level 3)":
        f_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains("3", case=False)).any(axis=1)]
    elif quick_mode == "⏳ 效期預警模式":
        f_df = f_df[f_df['剩餘天數'] < 180].sort_values("剩餘天數")

    # 關鍵字搜尋連動
    st.subheader(f"🔍 目前模式：{quick_mode}")
    keyword = st.text_input("搜尋型號或廠商名稱", value=st.session_state.search_input, key="main_search")
    st.session_state.search_input = keyword

    if keyword:
        keyword_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)]
        if keyword_df.empty:
            st.warning(f"💡 在目前的過濾條件下找不到『{keyword}』。")
        else:
            f_df = keyword_df

    # --- 功能分頁 ---
    tab1, tab2, tab3 = st.tabs(["🔍 設備清單", "⏳ 認證效期", "📊 數據統計"])

    with tab1:
        st.dataframe(f_df, use_container_width=True)

    with tab2:
        st.subheader("資安認證倒數與狀態")
        target_cols = ['廠商名稱', '廠牌', '型式', '有效日期', '剩餘天數', '資安狀態']
        avail_cols = [c for c in target_cols if c in f_df.columns]
        st.dataframe(f_df[avail_cols].sort_values("剩餘天數"), use_container_width=True)

    with tab3:
        st.subheader("產業合規分析")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**主要送測廠商 (Top 10)**")
            counts = df['廠商名稱'].value_counts().reset_index().head(10)
            st.bar_chart(counts, x='廠商名稱', y='count')
        with c2:
            st.write("**資安狀態分佈 (全部資料)**")
            status_df = df['資安狀態'].value_counts().reset_index()
            pie = alt.Chart(status_df).mark_arc().encode(theta='count', color='資安狀態')
            st.altair_chart(pie, use_container_width=True)

    st.divider()
    st.caption("由 Bear Magpie Intelligence 安全團隊維護 | 數據來源：政府開放資料平台")

if __name__ == "__main__":
    main()
