import streamlit as st
import pandas as pd
import requests
import urllib3
from datetime import datetime

# 1. 處理 SSL 憑證問題
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="無人機資安檢測查詢系統", page_icon="🛸", layout="wide")

JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"

@st.cache_data(ttl=3600)
def load_data():
    try:
        response = requests.get(JSON_URL, verify=False, timeout=15)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"資料載入失敗：{str(e)}")
        return pd.DataFrame()

def main():
    st.title("🛸 台灣無人機資安檢測合格清單查詢")
    
    df = load_data()
    if df.empty: return

    # --- 側邊欄：懶人快速搜機制 ---
    st.sidebar.header("⚡ 懶人快速洞察")
    
    # 初始化篩選狀態
    quick_filter = st.sidebar.radio(
        "選擇檢視模式：",
        ["全部清單", "高資安等級 (Level 3)", "非紅供應鏈 (本土廠商)", "認證即將到期"],
        index=0
    )

    st.sidebar.divider()
    st.sidebar.metric("目前合格總數", len(df))
    
    # --- 主畫面：搜尋與篩選 ---
    st.subheader("🔍 進階搜尋")
    col1, col2 = st.columns([2, 1])
    with col1:
        keyword = st.text_input("輸入關鍵字 (廠商、型號)", placeholder="例如：雷虎、MiTAC...")
    with col2:
        levels = ["全部"] + sorted(df["資安等級"].unique().tolist()) if "資安等級" in df.columns else ["全部"]
        selected_level = st.selectbox("手動等級篩選", levels)

    # --- 過濾邏輯整合 ---
    filtered_df = df.copy()

    # A. 處理懶人包邏輯
    if quick_filter == "高資安等級 (Level 3)":
        filtered_df = filtered_df[filtered_df["資安等級"].str.contains("3", na=False)]
    
    elif quick_filter == "非紅供應鏈 (本土廠商)":
        # 排除常見非本土品牌 (如 DJI, Autel) 並保留關鍵台灣大廠
        red_brands = ["DJI", "Autel", "道通"]
        pattern = "|".join(red_brands)
        filtered_df = filtered_df[~filtered_df["廠牌"].str.contains(pattern, case=False, na=False)]
    
    elif quick_filter == "認證即將到期":
        # 簡單處理民國年日期 (例如 1141231 代表 2025/12/31)
        # 這裡篩選 114 年 (2025) 以前到期的
        if "有效日期" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["有效日期"].str.startswith("114", na=False)]

    # B. 疊加手動搜尋關鍵字
    if keyword:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
        filtered_df = filtered_df[mask]

    # C. 疊加等級篩選
    if selected_level != "全部":
        filtered_df = filtered_df[filtered_df["資安等級"] == selected_level]

    # --- 顯示結果 ---
    st.subheader(f"📋 {quick_filter} 結果 ({len(filtered_df)} 筆)")
    
    if not filtered_df.empty:
        st.dataframe(
            filtered_df, 
            use_container_width=True,
            column_config={
                "有效日期": st.column_config.TextColumn("有效日期"),
                "資安等級": st.column_config.TextColumn("資安等級"),
                "廠牌": st.column_config.TextColumn("廠牌", width="small"),
            }
        )
        
        # 下載按鈕
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載此清單 (CSV)", csv_data, "drone_list.csv", "text/csv")
    else:
        st.info("查無符合條件的產品。")

    st.divider()
    st.caption("⚠️ 資料來源：政府開放資料平台 (ID: 174663) | 本工具僅供資安專業評估參考。")

if __name__ == "__main__":
    main()
