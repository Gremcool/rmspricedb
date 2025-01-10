import streamlit as st
import pandas as pd
from time import time

# Set up session state to store uploaded files and search query
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# Profiling utility for performance optimization
def profile(func):
    """Decorator to measure function execution time."""
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

# Function to style DataFrame with fixed column width
@profile
def style_headers_fixed_width(df, cell_width=100):
    """
    Apply styles to the DataFrame with a fixed cell width.
    
    Parameters:
    - df: The input DataFrame.
    - cell_width: Fixed width for columns (in pixels).
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
                (f"width", f"{cell_width}px"),
                (f"max-width", f"{cell_width}px"),
            ]},
            {"selector": "td", "props": [
                ("text-align", "left"),
                ("padding", "2px 5px"),
                (f"width", f"{cell_width}px"),
                (f"max-width", f"{cell_width}px"),
                ("overflow", "hidden"),
                ("text-overflow", "ellipsis"),
            ]},
        ]
    )

# Search and highlight matches
@profile
def search_and_highlight(data, query):
    """Filter the data and highlight rows containing the search query."""
    if data is not None and query:
        filtered_data = data[data.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)]
        if not filtered_data.empty:
            # Highlight cells matching the query
            def highlight(value):
                return f"background-color: yellow" if query.lower() in str(value).lower() else ""
            
            return filtered_data.style.applymap(highlight)
    return None

# Admin Page: Upload files
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

# Main Page: Search and display results
def main_page():
    st.title("Search Price Lists")
    st.sidebar.header("Search Controls")

    # Predictive search bar
    search_query = st.text_input("Search Price Lists", st.session_state.search_query, key="search")
    st.session_state.search_query = search_query

    # Clear search button
    if st.button("Clear Search"):
        st.session_state.search_query = ""

    # Display search results
    if st.session_state.search_query:
        st.subheader("Search Results")
        for file_name, data in st.session_state.uploaded_files.items():
            st.markdown(f"### {file_name}")
            result = search_and_highlight(data, st.session_state.search_query)
            if result is not None:
                st.write(result.to_html(), unsafe_allow_html=True)
            else:
                st.write(f"No matches found in {file_name}.")

    # Display uploaded files with fixed column width
    if st.session_state.uploaded_files:
        st.subheader("Uploaded Files")
        for file_name, data in st.session_state.uploaded_files.items():
            st.markdown(f"### {file_name}")
            column_width = st.slider(f"Set column width for {file_name}", 50, 200, 100)
            styled_df = style_headers_fixed_width(data, column_width)
            st.write(styled_df.to_html(), unsafe_allow_html=True)

# Navigation menu
page = st.sidebar.selectbox("Choose a page", ["Main", "Admin"], index=0)
if page == "Admin":
    admin_page()
else:
    main_page()
