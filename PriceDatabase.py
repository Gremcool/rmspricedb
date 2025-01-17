import streamlit as st
import pandas as pd
import random
import requests
from io import BytesIO

# GitHub repository URL where Excel files are stored
GITHUB_REPO_URL = "https://github.com/Gremcool/gremcool/tree/main/excel_files"

# Raw GitHub content base URL
GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/excel_files"

# Logo URL from GitHub
LOGO_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/assets/logo.png"

# List of filenames to load from the GitHub repository
EXCEL_FILE_NAMES = [
    "FINAL MASTER LIST AS OF 24 JULY 2024.xlsx",
    "First Draft PriceList.xlsx",
    "SA Price List.xlsx",  # Add all your file names here
]

# Function to fetch Excel files from GitHub
def load_files_from_github():
    files = {}
    for file_name in EXCEL_FILE_NAMES:
        file_url = f"{GITHUB_RAW_BASE_URL}/{file_name}"
        response = requests.get(file_url)
        if response.status_code == 200:
            file_data = pd.read_excel(BytesIO(response.content))
            files[file_name] = file_data
        else:
            st.warning(f"Failed to load {file_name} from GitHub. Please check the URL.")
    return files

# Function to style DataFrame and highlight matches
def highlight_matches(data, query):
    return data.style.applymap(
        lambda val: "background-color: yellow" if query.lower() in str(val).lower() else ""
    ).set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "black"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                ],
            }
        ]
    )

# Function to search across files and highlight results
def search_across_files(query, files):
    result = {}
    for file_name, data in files.items():
        matches = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1)]
        if not matches.empty:
            result[file_name] = highlight_matches(matches, query)
    return result

# Function to add a styled sidebar with logo and file download options
def add_sidebar(files):
    # Add logo to sidebar
    st.sidebar.markdown(
        f"""
        <style>
            /* Sidebar background color */
            section[data-testid="stSidebar"] {{
                background-color: black;
                color: white;
            }}

            /* Logo container styling */
            .logo-container {{
                text-align: center;
                margin-bottom: 20px;
            }}

            .logo {{
                max-width: 100%;
                height: auto;
                width: 150px; /* Adjust the size of the logo */
            }}

            /* Download section styling */
            .download-section {{
                background-color: #1e1e1e; /* Dark background for the section */
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}

            /* Button styling */
            .download-btn {{
                background-color: blue; /* Default button color */
                color: white;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                text-decoration: none;
                display: block;
                margin-top: 10px;
                transition: background-color 0.3s ease;
            }}

            .download-btn:hover {{
                background-color: red; /* Color when hovered */
            }}
        </style>

        <div class="logo-container">
            <img src="{LOGO_URL}" class="logo" alt="Logo">
        </div>

        <div class="download-section">
            <h4>Download Full Excel Files</h4>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Add download buttons for each file
    for file_name, data in files.items():
        towrite = BytesIO()
        data.to_excel(towrite, index=False, sheet_name="Sheet1")
        towrite.seek(0)
        st.sidebar.markdown(
            f"""
            <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{towrite.getvalue().decode('latin1')}" download="{file_name}.xlsx" class="download-btn">
                {file_name}
            </a>
            """,
            unsafe_allow_html=True
        )

# Main function for the app
def main():
    # Add a header banner
    st.markdown(
        """
        <style>
            .header-banner {
                background-color: #4CAF50;
                padding: 20px;
                border-radius: 5px;
                text-align: center;
                color: white;
                font-size: 24px;
            }
        </style>
        <div class="header-banner">
            Welcome to the RMS Price List Viewer!
        </div>
        """,
        unsafe_allow_html=True
    )

    st.title("RMS Price List")

    # Load files from GitHub
    uploaded_files = load_files_from_github()

    # Add the sidebar for downloads and logo
    add_sidebar(uploaded_files)

    # Predictive search bar
    search_query = st.text_input("Enter product you want to search:")
    if st.button("Clear Search"):
        search_query = ""

    # Display search results or all files
    if search_query:
        st.header("Search Results")
        search_results = search_across_files(search_query, uploaded_files)
        if search_results:
            for file_name, styled_data in search_results.items():
                title_bg_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                st.markdown(f"<div style='background-color: {title_bg_color}; padding: 10px; border-radius: 5px; color: white;'>{file_name}</div>", unsafe_allow_html=True)
                st.write(styled_data)
        else:
            st.write("No matches found.")
    else:
        st.header("All Files")
        for file_name, data in uploaded_files.items():
            title_bg_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            st.markdown(f"<div style='background-color: {title_bg_color}; padding: 10px; border-radius: 5px; color: white;'>{file_name}</div>", unsafe_allow_html=True)
            st.write(data.head())  # Show preview of the data

if __name__ == "__main__":
    main()
