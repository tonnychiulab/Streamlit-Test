import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime
import altair as alt

# 1. 基礎防護設定
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="無人機資安決策儀表板", page_icon="🛡️", layout="wide")

JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"
RED_LIST = ["DJI", "大疆", "Autel", "道通", "Hubsan", "FIMI", "哈博森"]

# 2. 強化版日期轉換 (處理各種奇怪格式)
def safe_roc_to_datetime(roc_val):
    try:
        s = str(roc_val).strip()
        if len(s) < 6: return None
        # 處理 1141231 這種格式
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
        df.columns = [col.strip() for col in df.columns] # 清除空白
        
        # 確保關鍵欄位一定存在 (即使是空值)
        essential_cols = ['廠商名稱', '廠牌', '型式', '有效日期']
        for col in essential_cols:
            if col not in df.columns:
                df[col] = "資料缺失"
        
        # 計算日期相關欄位
        today = datetime.now()
        df['西元到期日'] = df['有效日期'].apply(safe_roc_to_datetime)
        
        # 處理剩餘天數與狀態
        def calc_days(dt):
            return (dt - today).days if pd.notnull(dt) else 9999
        
        df['剩餘天數'] = df['西元到期日'].apply(calc_days)
        
        def get_status(days):
            if days == 9999: return "無日期資料"
            if days < 0: return "🚫 已過期"
            if days < 90: return "⚠️ 預警 (90天內)"
            return "✅ 安全"
        
        df['資安狀態'] = df['剩餘天數'].apply(get_status)
        return df
    except Exception as e:
        st.error(f"資料抓取失敗: {e}")
        return pd.DataFrame()

# 3. 主介面
def main():
    st.title("🛡️ 無人機資安監控儀表板 (BlueMagpie Edition)")
    df = load_and_fix_data()
    
    if df.empty:
        st.warning("暫時無法取得政府資料，請檢查網路。")
        return

    # 側邊欄：快速過濾
    st.sidebar.header("⚡ 快速篩選")
    show_red_chain = st.sidebar.checkbox("顯示紅色供應鏈標記 ⚠️")
    
    # 建立分頁
    tab1, tab2, tab3 = st.tabs(["🔍 設備快查", "⏳ 認證效期管理", "📊 產業分佈分析"])

    # --- Tab 1: 設備快查 (修正選取欄位的 Bug) ---
    with tab1:
        st.subheader("合格設備搜尋")
        keyword = st.text_input("輸入關鍵字 (廠商、型號)", key="search_bar")
        
        display_df = df.copy()
        red_pattern = "|".join(RED_LIST)
        
        # 紅鏈標記邏輯
        if not show_red_chain:
            # 排除紅鏈
            display_df = display_df[~display_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        
        if keyword:
            mask = display_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
            display_df = display_df[mask]
        
        st.dataframe(display_df, use_container_width=True)

    # --- Tab 2: 認證效期管理 (修正 KeyError) ---
    with tab2:
        st.subheader("資安認證倒數計時")
        # 安全地選取欄位，只選取存在的
        target_cols = ['廠商名稱', '廠牌', '型式', '有效日期', '剩餘天數', '資安狀態']
        cols_to_show = [c for c in target_cols if c in df.columns]
        
        expiry_df = df[cols_to_show].copy()
        expiry_df = expiry_df.sort_values(by="剩餘天數", ascending=True)
        
        st.dataframe(
            expiry_df,
            column_config={
                "剩餘天數": st.column_config.NumberColumn("剩餘天數", format="%d 天"),
                "資安狀態": st.column_config.TextColumn("狀態")
            },
            use_container_width=True
        )

    # --- Tab 3: 產業分析 ---
    with tab3:
        st.subheader("市場分析指標")
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.write("**前 10 大檢測合格廠商**")
            brand_counts = df['廠商名稱'].value_counts().reset_index().head(10)
            st.bar_chart(brand_counts, x='廠商名稱', y='count') # Streamlit 1.29+ 支援

        with col_c2:
            st.write("**資安風險分佈**")
            status_counts = df['資安狀態'].value_counts().reset_index()
            chart = alt.Chart(status_counts).mark_arc().encode(
                theta='count',
                color='資安狀態'
            )
            st.altair_chart(chart, use_container_width=True)

if __name__ == "__main__":
    main()
