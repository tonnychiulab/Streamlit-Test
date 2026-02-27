import streamlit as st
import pandas as pd
import requests
import urllib3

# 1. 處理政府網站 SSL 憑證過舊的問題
# 針對特定錯誤 (Missing Subject Key Identifier) 關閉驗證並隱藏警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與風格
st.set_page_config(page_title="台灣無人機資安檢測查詢系統", page_icon="🛸", layout="wide")

# JSON 資料來源 URL
JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"

@st.cache_data(ttl=3600)  # 緩存一小時，確保效能並減輕政府伺服器負擔
def load_data():
    try:
        # 使用 verify=False 跳過 SSL 憑證驗證
        response = requests.get(JSON_URL, verify=False, timeout=15)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        
        # 欄位清理：去除空白字元
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"資料載入失敗：{str(e)}")
        return pd.DataFrame()

def main():
    st.title("🛸 台灣無人機資安檢測合格清單查詢")
    st.markdown("本系統即時同步 [政府資料開放平台](https://data.gov.tw/dataset/174663) 的合格廠商與型號清單。")

    # 載入資料
    df = load_data()

    if df.empty:
        st.warning("目前無法載入資料，請確認網路連線或稍後再試。")
        return

    # 側邊欄統計
    st.sidebar.header("📊 數據統計")
    st.sidebar.metric("目前合格產品總數", len(df))
    
    # 建立搜尋區塊
    st.subheader("🔍 快速篩選")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        keyword = st.text_input("輸入關鍵字 (支援廠商名稱、產品型號或名稱)", "")
    
    with col2:
        # 動態抓取現有的資安等級
        if "資安等級" in df.columns:
            levels = ["全部"] + sorted(df["資安等級"].unique().tolist())
            selected_level = st.selectbox("資安等級", levels)
        else:
            selected_level = "全部"

    # 執行過濾邏輯
    filtered_df = df.copy()

    if keyword:
        # 進行模糊搜尋
        mask = df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
        filtered_df = filtered_df[mask]

    if selected_level != "全部":
        filtered_df = filtered_df[filtered_df["資安等級"] == selected_level]

    # 顯示結果表格
    st.subheader(f"📋 查詢結果 ({len(filtered_df)} 筆)")
    
    if not filtered_df.empty:
        st.dataframe(
            filtered_df, 
            use_container_width=True,
            column_config={
                "有效日期": st.column_config.TextColumn("有效日期"),
                "資安等級": st.column_config.BadgeColumn("資安等級"),
                "廠商名稱": st.column_config.TextColumn("廠商名稱", width="medium"),
            }
        )
        
        # 提供搜尋結果下載
        csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載搜尋結果 (CSV)",
            data=csv_data,
            file_name="drone_security_list.csv",
            mime="text/csv",
        )
    else:
        st.info("查無符合條件的產品，請嘗試簡化搜尋關鍵字。")

    # 頁尾資訊
    st.divider()
    st.caption("⚠️ 技術提醒：由於政府開放資料平台部分網域 SSL 憑證規範較舊，本系統目前採用跳過驗證方式讀取資料。建議僅用於公開資訊查詢，不涉及機密傳輸。")

if __name__ == "__main__":
    main()
