import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime
import altair as alt

# 1. 基礎防護與 SSL 修正
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="無人機資安終極儀表板", page_icon="🛡️", layout="wide")

JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"
RED_LIST = ["DJI", "大疆", "Autel", "道通", "Hubsan", "FIMI", "哈博森"]

# 2. 強化版日期轉換
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
        
        # --- 關鍵修正：自動欄位對應 ---
        mapping = {
            "申請單位": "廠商名稱",
            "報告日期": "有效日期" # 該資料集若無有效日期，暫以報告日期計算
        }
        for old_col, new_col in mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]

        # 補足缺失欄位
        for col in ['廠商名稱', '廠牌', '型式', '有效日期']:
            if col not in df.columns: df[col] = "不詳"
        
        # 日期運算
        today = datetime.now()
        df['西元日期'] = df['有效日期'].apply(safe_roc_to_datetime)
        df['剩餘天數'] = df['西元日期'].apply(lambda x: (x - today).days if x else 9999)
        
        def get_status(days):
            if days == 9999: return "無效期資料"
            if days < 0: return "🚫 已失效"
            if days < 90: return "⚠️ 預警 (90天內)"
            return "✅ 安全"
        df['資安狀態'] = df['剩餘天數'].apply(get_status)
        
        return df
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return pd.DataFrame()

# 3. 主介面
def main():
    st.title("🛡️ 無人機資安監控儀表板 (中揚資訊股份有限公司彙整)")
    df = load_and_fix_data()
    if df.empty: return

    # --- 左側選單：懶人快速功能 (保留並強化) ---
    st.sidebar.header("⚡ 懶人快速洞察")
    quick_mode = st.sidebar.radio(
        "選擇快查模式：",
        ["全部清單", "✅ 非敏感供應鏈 (本土)", "🚫 敏感供應鏈 (避坑)", "🏆 高資安等級 (Level 3)", "⏳ 效期預警模式"]
    )
    
    st.sidebar.divider()
    st.sidebar.metric("合格產品總數", len(df))
    
    # --- 核心邏輯過濾 ---
    f_df = df.copy()
    red_pattern = "|".join(RED_LIST)
    
    if quick_mode == "✅ 非紅供應鏈 (本土)":
        f_df = f_df[~f_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
    elif quick_mode == "🚫 紅色供應鏈 (避坑)":
        f_df = f_df[f_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        st.error("🚨 警告：此清單包含敏感供應鏈廠商。")
    elif quick_mode == "🏆 高資安等級 (Level 3)":
        mask = f_df.astype(str).apply(lambda x: x.str.contains("3", case=False)).any(axis=1)
        f_df = f_df[mask]
    elif quick_mode == "⏳ 效期預警模式":
        f_df = f_df[f_df['剩餘天數'] < 180].sort_values("剩餘天數")

    # --- 右側內容：Tabs 展開 ---
    tab1, tab2, tab3 = st.tabs(["🔍 設備快查", "⏳ 效期管理", "📊 統計分析"])

    with tab1:
        keyword = st.text_input("輸入關鍵字搜尋", placeholder="例如：雷虎、中光電...")
        if keyword:
            f_df = f_df[f_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)]
        st.dataframe(f_df, use_container_width=True)

    with tab2:
        st.subheader("資安認證倒數計時")
        # 只顯示關鍵欄位
        expiry_cols = ['廠商名稱', '廠牌', '型式', '有效日期', '剩餘天數', '資安狀態']
        avail_cols = [c for c in expiry_cols if c in f_df.columns]
        st.dataframe(f_df[avail_cols].sort_values("剩餘天數"), use_container_width=True)

    with tab3:
        st.subheader("產業分佈分析")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**廠商持有合格證排行**")
            counts = df['廠商名稱'].value_counts().reset_index().head(10)
            st.bar_chart(counts, x='廠商名稱', y='count')
        with c2:
            st.write("**資安健康度分佈**")
            status_df = df['資安狀態'].value_counts().reset_index()
            pie = alt.Chart(status_df).mark_arc().encode(theta='count', color='資安狀態')
            st.altair_chart(pie, use_container_width=True)

if __name__ == "__main__":
    main()
