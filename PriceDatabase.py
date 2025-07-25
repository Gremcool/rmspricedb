import streamlit as st
import pandas as pd
import requests
import io
import plotly.express as px

# ---------------- CONFIG ------------------
st.set_page_config(page_title="RMS Price Database", layout="wide")
LOGO_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/assets/logo.jpg"
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/excel_files"

# Map of file labels to filenames
EXCEL_FILES = {
    "RMS Kigali": "Price Database Kigali.xlsx",
    "RMS Huye": "Price Database Huye.xlsx",
    "RMS Rubavu": "Price Database Rubavu.xlsx"
}

# --------------- UI HEADER ----------------
st.markdown(
    f"""
    <div style='display: flex; align-items: center; justify-content: space-between;'>
        <div>
            <h2 style='margin-bottom: 5px;'>💊 Rwanda Medical Supply Price Database</h2>
            <p style='font-size: 16px;'>Search across RMS locations for pricing and procurement data</p>
        </div>
        <img src="{LOGO_URL}" width="100">
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ---------------- FUNCTIONS ------------------

@st.cache_data
def load_excel_file_from_github(url):
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return pd.read_excel(io.BytesIO(response.content))

# ---------------- SEARCH ---------------------

search_term = st.text_input("🔍 Enter item to search (e.g. paracetamol):")

scroll_button = st.button("📊 View Price Chart")

results = {}
for label, file in EXCEL_FILES.items():
    file_url = f"{GITHUB_RAW_BASE_URL}/{file}"
    df = load_excel_file_from_github(file_url)
    if df is not None:
        df["source_file"] = label
        if search_term:
            mask = df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
            match_df = df[mask]
            if not match_df.empty:
                results[label] = match_df

# --------------- DISPLAY RESULTS -------------------

if search_term:
    if results:
        st.success(f"Results for **{search_term}**:")
        for label, df in results.items():
            st.markdown(f"### 📁 {label}")
            st.dataframe(df, use_container_width=True)

        # --------------- CHART -------------------
        price_data = []
        for label, df in results.items():
            for _, row in df.iterrows():
                if "Unit Price (USD)" in row and pd.notna(row["Unit Price (USD)"]):
                    price_data.append({
                        "Location": label,
                        "Item": str(row.get("Item Description", search_term)),
                        "Price": row["Unit Price (USD)"]
                    })

        if price_data:
            st.markdown('<div id="chart_section"></div>', unsafe_allow_html=True)
            chart_df = pd.DataFrame(price_data)

            fig = px.bar(
                chart_df,
                x="Location",
                y="Price",
                color="Location",
                hover_data=["Item"],
                title=f"💵 Price of '{search_term}' by RMS Location",
                text_auto=".2s"
            )
            fig.update_traces(marker_line_width=1.5)
            fig.update_layout(
                title_font_size=20,
                yaxis_title="Unit Price (USD)",
                xaxis_title="RMS Location",
                height=500,
                plot_bgcolor='white'
            )
            st.plotly_chart(fig, use_container_width=True)

            if scroll_button:
                st.markdown("""
                    <script>
                        document.getElementById("chart_section").scrollIntoView({ behavior: "smooth" });
                    </script>
                    """, unsafe_allow_html=True)
        else:
            st.warning("No price data available to display chart.")
    else:
        st.error("No results found. Try a different search term.")
else:
    st.info("Please enter an item to search above.")
