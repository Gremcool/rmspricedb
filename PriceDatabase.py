import streamlit as st
import pandas as pd
import random

# Set up session state to store uploaded files and search query
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "uploaded_logo" not in st.session_state:
    st.session_state.uploaded_logo = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# Function to cache the uploaded files
def cache_uploaded_file(file, file_name):
    if file_name not in st.session_state.uploaded_files:
        st.session_state.uploaded_files[file_name] = pd.read_excel(file)

# Function to style the DataFrame with fixed column width
def style_headers_fixed_width(df, cell_width=100):
    """
    Apply styles to the DataFrame with a fixed cell width.

    Parameters:
    - df: The input DataFrame.
    - cell_width: The desired fixed width for columns, in pixels.
    """
    return df.style.set_table_styles(
        [
            # Style for table headers
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "black"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                    ("font-size", "12px"),
                    ("padding", "2px 5px"),
                    ("height", "15px"),
                    ("white-space", "nowrap"),
                    (f"width", f"{cell_width}px"),
                    (f"max-width", f"{cell_width}px"),
                    ("overflow", "hidden"),
                    ("text-overflow", "ellipsis"),
                ],
            },
            # Style for table cells
            {
                "selector": "td",
                "props": [
                    ("text-align", "left"),
                    ("padding", "2px 5px"),
                    ("height", "15px"),
                    ("white-space", "nowrap"),
                    (f"width", f"{cell_width}px"),
                    (f"max-width", f"{cell_width}px"),
                    ("overflow", "hidden"),
                    ("text-overflow", "ellipsis"),
                ],
            },
        ]
    )

# Display table with fixed width in Streamlit
def display_table_with_fixed_width(data, column_width):
    # Apply custom styles
    styled_df = style_headers_fixed_width(data, cell_width=column_width)
    st.markdown(styled_df.to_html(), unsafe_allow_html=True)

# Function to search across multiple Excel files
def search_across_files(query, files):
    """
    Search for a query across multiple DataFrames and return matches with file references.

    Parameters:
    - query: The search string.
    - files: Dictionary of file names and their corresponding DataFrames.

    Returns:
    - A DataFrame with rows containing the search query and a column indicating the source file.
    """
    result_df = pd.DataFrame()
    for file_name, data in files.items():
        matches = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1)]
        if not matches.empty:
            matches["Source File"] = file_name  # Add a column indicating the source file
            result_df = pd.concat([result_df, matches], ignore_index=True)
    return result_df

# Define the admin page
def admin_page():
    st.title("Admin Page")
    st.sidebar.header("Admin Controls")

    # Upload RMS logo
    logo = st.sidebar.file_uploader("Upload RMS Logo", type=["png", "jpg", "jpeg"], key="logo")
    if logo is not None:
        st.session_state.uploaded_logo = logo

    # Upload multiple Excel files
    st.header("Upload Excel Files")
    uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True, key="excel")
    if uploaded_files:
        for file in uploaded_files:
            file_name = file.name.split(".")[0]  # Use file name as header
            cache_uploaded_file(file, file_name)

# Define the main page
def main_page():
    # Apply custom styling for a polished design
    st.markdown(
        """
        <style>
        body {
            background-color: #eaf4fc;
            color: #333;
            font-family: 'Helvetica Neue', sans-serif;
        }
        .stApp {
            padding: 20px;
            border-radius: 10px;
        }
        .header {
            color: white;
            padding: 15px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
        }
        .pink-button {
            background-color: #ff69b4;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
        }
        .pink-button:hover {
            background-color: #ff1493;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Display logo if uploaded, aligned to top-left
    if st.session_state.uploaded_logo is not None:
        st.image(st.session_state.uploaded_logo, width=150, output_format="PNG")

    # Page title
    st.markdown("<div class='page-title'>Search Price Lists</div>", unsafe_allow_html=True)

    # Predictive search bar
    search_query = st.text_input("Enter your search query:", key="search")
    st.session_state.search_query = search_query

    # Clear search button
    if st.button("Clear Search"):
        st.session_state.search_query = ""

    # Display search results
    if st.session_state.search_query:
        st.markdown("<div class='search-results-header'>Search Results</div>", unsafe_allow_html=True)
        search_results = search_across_files(st.session_state.search_query, st.session_state.uploaded_files)
        if not search_results.empty:
            st.write(search_results)
        else:
            st.write("No matches found across the uploaded files.")

    # Display uploaded files as sections
    if st.session_state.uploaded_files:
        for file_name, data in st.session_state.uploaded_files.items():
            # Random background color generator for the title
            title_bg_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            
            st.markdown(f"<div class='header' style='background-color: {title_bg_color};'>{file_name}</div>", unsafe_allow_html=True)
            preview_data = data.head()
            display_table_with_fixed_width(preview_data, 100)

# Navigation menu with Main Page as default
page = st.sidebar.selectbox("Choose a page", ["Main", "Admin"], index=0)
if page == "Admin":
    admin_page()
else:
    main_page()
