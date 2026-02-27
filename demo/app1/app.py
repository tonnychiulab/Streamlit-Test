import streamlit as st
import pandas as pd
import requests
import urllib3

# 1. 處理政府網站 SSL 憑證問題
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="無人機資安查詢 - 避坑專用版", page_icon="🛡️", layout="wide")

JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"

# 定義敏感供應鏈清單 (紅色供應鏈)
RED_LIST = ["DJI", "大疆", "Autel", "道通", "Hubsan", "FIMI", "哈博森", "SwellPro"]

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
    st.title("🛸 台灣無人機資安檢測查詢系統")
    
    df = load_data()
    if df.empty: return

    # --- 左側側邊欄：懶人快速搜機制 ---
    st.sidebar.header("⚡ 懶人快速洞察")
    
    # 使用按鈕或 Radio 建立快速導航
    mode = st.sidebar.radio(
        "選擇檢視模式：",
        ["📋 全部清單", "✅ 非紅供應鏈 (本土/安全)", "🚫 紅色供應鏈 (避坑警示)", "🏆 高資安等級 (Level 3)", "⏳ 認證即將到期"],
        index=0
    )

    st.sidebar.divider()
    st.sidebar.metric("目前合格總數", len(df))
    
    # --- 主畫面過濾邏輯 ---
    filtered_df = df.copy()
    red_pattern = "|".join(RED_LIST)

    # 1. 模式過濾
    if mode == "🚫 紅色供應鏈 (避坑警示)":
        if "廠牌" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        st.error("🚨 警告：以下廠商屬敏感供應鏈（Red Supply Chain）。在規劃公部門或關鍵設施專案時，請務必避開以符合規範。")
    
    elif mode == "✅ 非紅供應鏈 (本土/安全)":
        if "廠牌" in filtered_df.columns:
            filtered_df = filtered_df[~filtered_df["廠牌"].str.contains(red_pattern, case=False, na=False)]
        st.success("💪 目前顯示為排除敏感供應鏈後的「安全名單」。")
        
    elif mode == "🏆 高資安等級 (Level 3)":
        # 如果沒有專屬欄位，就用全域模糊搜尋
        keyword_l3 = "3"
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(keyword_l3, case=False)).any(axis=1)
        filtered_df = filtered_df[mask]
        st.info("ℹ️ 正在篩選包含 '3' 或 'Level 3' 關鍵字的檢測紀錄。")

    elif mode == "⏳ 認證即將到期":
        if "有效日期" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["有效日期"].str.startswith("114", na=False)]

    # 2. 進階關鍵字搜尋
    st.subheader("🔍 進階搜尋")
    keyword = st.text_input("輸入關鍵字 (廠商、型號或備註)", placeholder="例如：雷虎、中光電...")
    
    if keyword:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
        filtered_df = filtered_df[mask]

    # --- 顯示結果 ---
    st.subheader(f"{mode} 結果 ({len(filtered_df)} 筆)")
    
    if not filtered_df.empty:
        # 自動隱藏不必要的欄位或調整顯示
        st.dataframe(filtered_df, use_container_width=True)
        
        # 下載按鈕
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載此篩選結果 (CSV)", csv_data, "drone_security_list.csv", "text/csv")
    else:
        st.info("此分類下目前無符合條件的資料。")

    st.divider()
    st.caption("🛡️ 系統由資訊安全部門維護 | 排除清單參考：DJI, Autel, Hubsan 等紅鏈品牌。")

if __name__ == "__main__":
    main()
