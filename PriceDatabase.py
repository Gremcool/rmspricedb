import streamlit as st
import pandas as pd
from time import time

# Set up session state to store uploaded files and search query
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# Add profiling utility
def profile(func):
    """Decorator for profiling function execution time."""
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        execution_time = time() - start_time
        st.write(f"⏱️ Execution time for {func.__name__}: {execution_time:.4f} seconds")
        return result
    return wrapper

# Function to cache the uploaded files
@profile
def cache_uploaded_file(file, file_name):
    if file_name not in st.session_state.uploaded_files:
        st.session_state.uploaded_files[file_name] = pd.read_excel(file)

# Function to style the DataFrame with fixed column width
@profile
def style_headers_fixed_width(df, cell_width=100):
    """
    Apply styles to the DataFrame with a fixed cell width.

    Parameters:
    - df: The input DataFrame.
    - cell_width: The desired fixed width for columns, in pixels.
    """
    return df.style.set_table_styles(
        [
            {"selector": "thead th", "props": [
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
            ]},
            {"selector": "td", "props": [
                ("text-align", "left"),
                ("padding", "2px 5px"),
                ("height", "15px"),
                ("white-space", "nowrap"),
                (f"width", f"{cell_width}px"),
                (f"max-width", f"{cell_width}px"),
                ("overflow", "hidden"),
                ("text-overflow", "ellipsis"),
            ]},
        ]
    )

# Optimize search and filtering
@profile
def search_and_highlight(data, query):
    """Filter the data and highlight rows containing the search query."""
    if data is not None and query:
        filtered_data = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)]
        return filtered_data if not filtered_data.empty else None
    return None

# Define the admin page
def admin_page():
    st.title("Admin Page")
    st.sidebar.header("Admin Controls")

    # Upload multiple Excel files
    st.header("Upload Excel Files")
    files = st.file_uploader(
        "Upload one or more Excel files", 
        type=["xlsx"], 
        accept_multiple_files=True, 
        key="excel"
    )
    if files:
        for file in files:
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
        .header {
            background-color: #2e86c1;
            color: white;
            padding: 15px;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Page title
    st.markdown("<div class='page-title'>Search Price Lists</div>", unsafe_allow_html=True)

    # Predictive search bar
    search_query = st.text_input("Search Price Lists", st.session_state.search_query, key="search")
    st.session_state.search_query = search_query

    # Clear search button
    if st.button("Clear Search"):
        st.session_state.search_query = ""

    # Display search results
    if st.session_state.search_query:
        st.markdown("<div class='header'>Search Results</div>", unsafe_allow_html=True)
        for file_name, data in st.session_state.uploaded_files.items():
            st.markdown(f"<div class='header'>{file_name}</div>", unsafe_allow_html=True)
            result = search_and_highlight(data, st.session_state.search_query)
            if result is not None:
                st.dataframe(result, use_container_width=True)
            else:
                st.write(f"No matches found in {file_name}.")

    # Display uploaded files as sections
    if st.session_state.uploaded_files:
        for file_name, data in st.session_state.uploaded_files.items():
            st.markdown(f"<div class='header'>{file_name}</div>", unsafe_allow_html=True)
            column_width = st.slider(f"Set column width for {file_name}", 50, 200, 100)
            styled_df = style_headers_fixed_width(data, column_width)
            st.write(styled_df.to_html(), unsafe_allow_html=True)

# Navigation menu with Main Page as default
page = st.sidebar.selectbox("Choose a page", ["Main", "Admin"], index=0)
if page == "Admin":
    admin_page()
else:
    main_page()
