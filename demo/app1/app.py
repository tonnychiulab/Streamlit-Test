import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime
import altair as alt

# 1. 基礎設定與 SSL 警告處理
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="無人機資安決策儀表板", page_icon="🛡️", layout="wide")

JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"
RED_LIST = ["DJI", "大疆", "Autel", "道通", "Hubsan", "FIMI", "哈博森"]

# 2. 日期轉換輔助函數 (民國年轉西元年)
def roc_to_datetime(roc_str):
    try:
        # 假設格式為 1141231 -> 2025-12-31
        roc_str = str(roc_str).strip()
        year = int(roc_str[:-4]) + 1911
        month = int(roc_str[-4:-2])
        day = int(roc_str[-2:])
        return datetime(year, month, day)
    except:
        return None

@st.cache_data(ttl=3600)
def load_and_process_data():
    try:
        response = requests.get(JSON_URL, verify=False, timeout=15)
        df = pd.DataFrame(response.json())
        df.columns = [col.strip() for col in df.columns]
        
        # 資料預處理：計算到期日與天數
        if "有效日期" in df.columns:
            df['西元到期日'] = df['有效日期'].apply(roc_to_datetime)
            today = datetime.now()
            df['剩餘天數'] = (df['西元到期日'] - today).dt.days
            
            # 定義狀態
            def get_status(days):
                if pd.isna(days): return "未知"
                if days < 0: return "🚫 已過期"
                if days < 90: return "⚠️ 預警 (90天內)"
                return "✅ 安全"
            df['資安狀態'] = df['剩餘天數'].apply(get_status)
            
        return df
    except Exception as e:
        st.error(f"資料處理失敗: {e}")
        return pd.DataFrame()

# 3. 主程式
def main():
    st.title("🛡️ 無人機資安監控儀表板 (BlueMagpie Edition)")
    df = load_and_process_data()
    if df.empty: return

    # --- 側邊欄 ---
    st.sidebar.header("⚡ 快速過濾")
    show_red_chain = st.sidebar.checkbox("顯示紅色供應鏈警示 ⚠️")
    
    # --- 分頁設計 ---
    tab1, tab2, tab3 = st.tabs(["🔍 設備快查", "⏳ 認證效期管理", "📊 產業分佈分析"])

    # --- Tab 1: 設備快查 ---
    with tab1:
        st.subheader("快速搜尋合格設備")
        keyword = st.text_input("輸入關鍵字 (型號、廠商)", placeholder="例如：雷虎...")
        
        display_df = df.copy()
        red_pattern = "|".join(RED_LIST)
        
        # 預設排除紅鏈，除非勾選顯示
        if not show_red_chain:
            display_df = display_df[~display_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        
        if keyword:
            mask = display_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
            display_df = display_df[mask]
        
        st.dataframe(display_df, use_container_width=True)

    # --- Tab 2: 認證效期管理 ---
    with tab2:
        st.subheader("資安認證倒數計時")
        st.info("根據台灣資安院規範，認證到期前三個月應啟動重新送測流程。")
        
        # 只顯示未來的、或是快過期的
        expiry_df = df[['廠商名稱', '廠牌', '型式', '有效日期', '剩餘天數', '資安狀態']].copy()
        expiry_df = expiry_df.sort_values(by="剩餘天數")
        
        # 使用 color-coding 顯示 (Streamlit 自動支援部分色塊)
        st.dataframe(
            expiry_df,
            column_config={
                "剩餘天數": st.column_config.NumberColumn("剩餘天數", format="%d 天"),
                "資安狀態": st.column_config.TextColumn("狀態")
            },
            use_container_width=True
        )

    # --- Tab 3: 產業分佈分析 ---
    with tab3:
        st.subheader("合格產品分佈統計")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.write("**廠商持有合格證數量排行**")
            brand_counts = df['廠商名稱'].value_counts().reset_index().head(10)
            st.bar_chart(brand_counts, x='index', y='count')

        with col_chart2:
            st.write("**資安等級分佈**")
            # 假設欄位名稱包含 '資安等級'
            level_col = '資安等級' if '資安等級' in df.columns else None
            if level_col:
                level_counts = df[level_col].value_counts().reset_index()
                chart = alt.Chart(level_counts).mark_arc().encode(
                    theta='count',
                    color='index'
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.write("目前資料集未提供獨立等級欄位")

if __name__ == "__main__":
    main()
