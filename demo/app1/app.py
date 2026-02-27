import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime
import altair as alt

# 1. 基礎防護與環境設定
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="無人機資安監控儀表板", page_icon="🛡️", layout="wide")

JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"
RED_LIST = ["DJI", "大疆", "Autel", "道通", "Hubsan", "FIMI", "哈博森"]

# 2. 強化日期轉換函數
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
        
        # 自動欄位補強與映射 (對付政府資料亂跳的 Key)
        mapping = {"申請單位": "廠商名稱", "報告日期": "檢測日期"}
        for old_c, new_c in mapping.items():
            if old_c in df.columns: df[new_c] = df[old_c]
        
        # 預設關鍵欄位
        for col in ['廠商名稱', '廠牌', '型式', '有效日期']:
            if col not in df.columns: df[col] = "不詳"

        # 日期運算邏輯
        today = datetime.now()
        df['西元日期'] = df['有效日期'].apply(safe_roc_to_datetime)
        df['剩餘天數'] = df['西元日期'].apply(lambda x: (x - today).days if x else 9999)
        
        def get_status(days):
            if days == 9999: return "無日期資料"
            if days < 0: return "🚫 已過期"
            if days < 90: return "⚠️ 預警 (90天內)"
            return "✅ 安全"
        df['資安狀態'] = df['剩餘天數'].apply(get_status)
        
        return df
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return pd.DataFrame()

# 3. 主介面邏輯
def main():
    st.title("🛡️ 無人機資安監控儀表板 (BlueMagpie Edition)")
    
    # 確保 Session State 初始化
    if 'search_input' not in st.session_state:
        st.session_state.search_input = ""

    df = load_and_fix_data()
    if df.empty: return

    # --- 左側選單：懶人快速洞察 (增加一鍵清除功能) ---
    st.sidebar.header("⚡ 懶人快速洞察")
    
    quick_mode = st.sidebar.radio(
        "選擇快查模式：",
        ["全部清單", "✅ 非敏感供應鏈 (本土)", "🚫 敏感供應鏈 (避坑)", "🏆 高資安等級 (Level 3)", "⏳ 效期預警模式"],
        key="quick_mode"
    )
    
    if st.sidebar.button("🧹 清除所有搜尋條件"):
        st.session_state.search_input = ""
        st.rerun()

    st.sidebar.divider()
    st.sidebar.metric("合格產品總數", len(df))
    
    # --- 過濾核心邏輯 ---
    f_df = df.copy()
    red_pattern = "|".join(RED_LIST)
    
    # A. 執行懶人模式篩選
    if quick_mode == "✅ 非敏感供應鏈 (本土)":
        f_df = f_df[~f_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
    elif quick_mode == "🚫 敏感供應鏈 (避坑)":
        f_df = f_df[f_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
    elif quick_mode == "🏆 高資安等級 (Level 3)":
        f_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains("3", case=False)).any(axis=1)]
    elif quick_mode == "⏳ 效期預警模式":
        f_df = f_df[f_df['剩餘天數'] < 180].sort_values("剩餘天數")

    # B. 疊加關鍵字搜尋 (使用 session_state 保持狀態)
    st.subheader(f"🔍 模式：{quick_mode}")
    keyword = st.text_input("輸入關鍵字搜尋 (型號、廠商)", value=st.session_state.search_input, key="main_search")
    st.session_state.search_input = keyword

    if keyword:
        # 進行關鍵字搜尋
        keyword_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)]
        
        # 貼心檢查：如果懶人模式 + 關鍵字沒結果，但「全部資料」中有結果
        if keyword_df.empty:
            st.warning(f"💡 在『{quick_mode}』模式下找不到『{keyword}』。但在其他分類中可能存在，是否切換回全部清單？")
        else:
            f_df = keyword_df

    # --- 右側 Tabs ---
    tab1, tab2, tab3 = st.tabs(["🔍 設備快查", "⏳ 效期管理", "📊 產業分析"])

    with tab1:
        st.dataframe(f_df, use_container_width=True)

    with tab2:
        st.subheader("資安認證倒數計時")
        expiry_cols = ['廠商名稱', '廠牌', '型式', '有效日期', '剩餘天數', '資安狀態']
        avail_cols = [c for c in expiry_cols if c in f_df.columns]
        st.dataframe(f_df[avail_cols].sort_values("剩餘天數"), use_container_width=True)

    with tab3:
        st.subheader("產業分佈分析")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**前 10 大檢測合格廠商**")
            counts = df['廠商名稱'].value_counts().reset_index().head(10)
            st.bar_chart(counts, x='廠商名稱', y='count')
        with c2:
            st.write("**資安健康度 (全部資料)**")
            status_df = df['資安狀態'].value_counts().reset_index()
            pie = alt.Chart(status_df).mark_arc().encode(theta='count', color='資安狀態')
            st.altair_chart(pie, use_container_width=True)

if __name__ == "__main__":
    main()
