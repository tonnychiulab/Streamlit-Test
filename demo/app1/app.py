import streamlit as st
import pandas as pd
import requests

# 設定網頁標題與圖示
st.set_page_config(page_title="台灣無人機資安檢測查詢系統", page_icon="🛸", layout="wide")

# JSON 資料來源 URL
JSON_URL = "https://quality.data.gov.tw/dq_download_json.php?nid=174663&md5_url=12c13680f07f84091e72fcc351447baf"

@st.cache_data(ttl=3600)  # 緩存 1 小時，避免頻繁請求政府伺服器
def load_data():
    try:
        response = requests.get(JSON_URL)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        # 清理欄位名稱（去除可能存在的空白）
        df.columns = [col.strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"資料載入失敗：{e}")
        return pd.DataFrame()

# 主程式邏輯
def main():
    st.title("🛸 台灣無人機資安檢測合格清單查詢")
    st.markdown("本系統直接串接 [政府資料開放平台](https://data.gov.tw/dataset/174663) 資料，提供即時的合格廠商與型號查詢。")

    # 載入資料
    df = load_data()

    if df.empty:
        st.warning("目前無法取得資料，請檢查網路連線或稍後再試。")
        return

    # 側邊欄：統計資訊
    st.sidebar.header("📊 快速統計")
    st.sidebar.metric("合格產品總數", len(df))
    
    # 搜尋功能
    st.subheader("🔍 條件篩選")
    col1, col2 = st.columns(2)
    
    with col1:
        keyword = st.text_input("關鍵字搜尋 (廠商、產品名稱或型號)", "")
    
    with col2:
        # 動態取得資安等級清單
        levels = ["全部"] + sorted(df["資安等級"].unique().tolist()) if "資安等級" in df.columns else ["全部"]
        selected_level = st.selectbox("資安等級篩選", levels)

    # 資料過濾邏輯
    filtered_df = df.copy()

    if keyword:
        # 在所有欄位中搜尋關鍵字
        mask = df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
        filtered_df = filtered_df[mask]

    if selected_level != "全部":
        filtered_df = filtered_df[filtered_df["資安等級"] == selected_level]

    # 顯示結果
    st.subheader(f"📋 查詢結果 ({len(filtered_df)} 筆)")
    
    if not filtered_df.empty:
        # 使用 Streamlit 的 Dataframe 顯示，支援排序與搜尋
        st.dataframe(
            filtered_df, 
            use_container_width=True,
            column_config={
                "有效日期": st.column_config.TextColumn("有效日期"),
                "資安等級": st.column_config.BadgeColumn("資安等級")
            }
        )
        
        # 下載按鈕
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載此搜尋結果為 CSV",
            data=csv,
            file_name="drone_security_search_results.csv",
            mime="text/csv",
        )
    else:
        st.info("找不到符合條件的資料，請嘗試調整搜尋詞。")

    # 底部提醒
    st.divider()
    st.caption("資料來源：政府資料開放平台 (ID: 174663) | 本系統僅供參考，正式資訊請以相關主管機關公告為準。")

if __name__ == "__main__":
    main()
