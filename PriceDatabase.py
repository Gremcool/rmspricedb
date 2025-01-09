import streamlit as st
import pandas as pd
import os
import uuid

# Directory to store uploaded files
UPLOAD_DIR = "uploads"
LOGO_DIR = "logos"

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)

# Function to save uploaded files to server storage
def save_uploaded_file(uploaded_file, folder):
    unique_filename = f"{uuid.uuid4()}_{uploaded_file.name}"
    file_path = os.path.join(folder, unique_filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# Function to load all Excel files from the upload directory
def load_excel_files():
    excel_files = {}
    for file_name in os.listdir(UPLOAD_DIR):
        if file_name.endswith(".xlsx"):
            file_path = os.path.join(UPLOAD_DIR, file_name)
            try:
                excel_files[file_name] = pd.read_excel(file_path)
            except Exception as e:
                st.error(f"Error loading file {file_name}: {e}")
    return excel_files

# Function to load the logo
def load_logo():
    logo_files = os.listdir(LOGO_DIR)
    return os.path.join(LOGO_DIR, logo_files[0]) if logo_files else None

# Function to style the DataFrame with fixed column width
def style_headers_fixed_width(df, cell_width=100):
    return df.style.set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "black"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                    (f"width", f"{cell_width}px"),
                    (f"max-width", f"{cell_width}px"),
                    ("overflow", "hidden"),
                    ("text-overflow", "ellipsis"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("text-align", "left"),
                    (f"width", f"{cell_width}px"),
                    (f"max-width", f"{cell_width}px"),
                    ("overflow", "hidden"),
                    ("text-overflow", "ellipsis"),
                ],
            },
        ]
    )

# Display table with fixed width
def display_table_with_fixed_width(data, column_width):
    styled_df = style_headers_fixed_width(data, cell_width=column_width)
    st.markdown(styled_df.to_html(), unsafe_allow_html=True)

# Define the admin page
def admin_page():
    st.title("Admin Page")
    st.sidebar.header("Admin Controls")

    # Upload RMS logo
    logo = st.sidebar.file_uploader("Upload RMS Logo", type=["png", "jpg", "jpeg"], key="logo")
    if logo:
        logo_path = save_uploaded_file(logo, LOGO_DIR)
        st.success(f"Logo uploaded to {logo_path}")

    # Upload Excel files
    st.header("Upload Excel Files")
    uploaded_files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True, key="excel")
    if uploaded_files:
        for file in uploaded_files:
            file_path = save_uploaded_file(file, UPLOAD_DIR)
            st.success(f"File uploaded to {file_path}")

# Define the main page
def main_page():
    st.title("Main Panel")
    
    # Display the logo
    logo_path = load_logo()
    if logo_path:
        st.image(logo_path, width=150)
    
    # Load and display uploaded Excel files
    excel_files = load_excel_files()
    if excel_files:
        for file_name, data in excel_files.items():
            st.subheader(file_name)
            
            # Allow column width adjustment
            column_width = st.slider(f"Set column width for {file_name}", 50, 200, 100)
            display_table_with_fixed_width(data, column_width)
    else:
        st.info("No Excel files uploaded yet.")

# Navigation menu with Main Page as default
page = st.sidebar.selectbox("Choose a page", ["Main", "Admin"], index=0)
if page == "Admin":
    admin_page()
else:
    main_page()
