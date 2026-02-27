import streamlit as st
import pandas as pd
import requests
import urllib3

# 1. 處理 SSL 憑證問題
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="無人機資安查詢系統 - 資安長專用版", page_icon="🛡️", layout="wide")

JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"

# 定義敏感供應鏈名單 (可根據最新禁令清單持續擴充)
RED_LIST_BRANDS = ["DJI", "大疆", "Autel", "道通", "Hubsan", "FIMI", "哈博森"]

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

    # --- 側邊欄：懶人快速搜機制 (新增紅色供應鏈警示) ---
    st.sidebar.header("⚡ 懶人快速洞察")
    
    quick_filter = st.sidebar.radio(
        "選擇檢視模式：",
        ["全部清單", "非紅供應鏈 (本土優先)", "紅色供應鏈 (風險警示) ⚠️", "高資安等級 (Level 3)", "認證即將到期"],
        index=0
    )

    st.sidebar.divider()
    st.sidebar.metric("目前合格總數", len(df))
    
    # --- 主畫面：搜尋與篩選 ---
    st.subheader("🔍 進階搜尋")
    col1, col2 = st.columns([2, 1])
    with col1:
        keyword = st.text_input("輸入關鍵字 (廠商、型號)", placeholder="輸入關鍵字...")
    with col2:
        levels = ["全部"] + sorted(df["資安等級"].unique().tolist()) if "資安等級" in df.columns else ["全部"]
        selected_level = st.selectbox("資安等級篩選", levels)

    # --- 核心過濾邏輯 ---
    filtered_df = df.copy()
    red_pattern = "|".join(RED_LIST_BRANDS)

    # 處理懶人包模式
    if quick_filter == "紅色供應鏈 (風險警示) ⚠️":
        # 僅顯示紅色清單品牌
        filtered_df = filtered_df[filtered_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        st.error("🚨 警告：以下顯示之產品屬敏感供應鏈品牌。若用於政府採購或關鍵基礎設施，請務必確認合規性。")
    
    elif quick_filter == "非紅供應鏈 (本土優先)":
        # 排除紅色清單品牌
        filtered_df = filtered_df[~filtered_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        st.success("✅ 目前顯示為排除敏感供應鏈後的產品清單。")
        
    elif quick_filter == "高資安等級 (Level 3)":
        filtered_df = filtered_df[filtered_df["資安等級"].str.contains("3", na=False)]
    
    elif quick_filter == "認證即將到期":
        # 篩選 114 年到期之產品
        if "有效日期" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["有效日期"].str.startswith("114", na=False)]

    # 疊加搜尋與等級條件
    if keyword:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    if selected_level != "全部":
        filtered_df = filtered_df[filtered_df["資安等級"] == selected_level]

    # --- 顯示結果 ---
    st.subheader(f"📋 {quick_filter} 結果 ({len(filtered_df)} 筆)")
    
    if not filtered_df.empty:
        # 針對結果進行排序，讓最新的報告排前面
        if "報告日期" in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by="報告日期", ascending=False)

        st.dataframe(
            filtered_df, 
            use_container_width=True,
            column_config={
                "有效日期": st.column_config.TextColumn("有效日期"),
                "資安等級": st.column_config.TextColumn("資安等級"),
                "廠牌": st.column_config.TextColumn("廠牌"),
            }
        )
        
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載此篩選結果 (CSV)", csv_data, "drone_security_report.csv", "text/csv")
    else:
        st.info("查無符合條件的產品。")

    st.divider()
    st.caption("⚠️ 技術說明：本工具由 Bear Magpie Intelligence 安全團隊維護，旨在輔助資安合規評估。")

if __name__ == "__main__":
    main()
