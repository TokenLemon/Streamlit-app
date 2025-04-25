import streamlit as st
import pandas as pd
import os
import tempfile
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle

# Google Sheets API scope t
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

st.title("Employee Compensation Calculator")

# Create sidebar for data source selection
st.sidebar.title("Data Source")
data_source = st.sidebar.radio(
    "Choose your data source:",
    ("Upload File", "Google Sheets")
)

def get_google_sheet_data(sheet_id, range_name):
    """Get data from Google Sheets"""
    # Check if we have stored credentials
    creds = None
    token_path = "token.pickle"
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Look for credentials file
            if not os.path.exists('credentials.json'):
                st.error("Missing credentials.json file. Please upload your Google OAuth credentials.")
                uploaded_creds = st.file_uploader("Upload your credentials.json file", type=['json'])
                if uploaded_creds:
                    with open('credentials.json', 'wb') as f:
                        f.write(uploaded_creds.getbuffer())
                    st.success("Credentials saved! Please reload the app.")
                    st.stop()
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8501)
        
        # Save credentials for next time
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    # Build the service
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    
    # Call the Sheets API
    result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
    values = result.get('values', [])
    
    if not values:
        st.error("No data found in the Google Sheet.")
        return None
    
    # Convert to DataFrame (first row is header)
    headers = values[0]
    data = values[1:]
    return pd.DataFrame(data, columns=headers)

# Handle Google Sheets
if data_source == "Google Sheets":
    st.subheader("Connect to Google Sheets")
    
    # Package requirements note
    st.info("Make sure to install the required packages with: `pip install google-auth google-auth-oauthlib google-api-python-client`")
    
    # Input for Google Sheet ID
    sheet_id = st.text_input(
        "Google Sheet ID", 
        help="The ID is the part of the URL after 'spreadsheets/d/' and before '/edit'"
    )
    
    sheet_range = st.text_input(
        "Sheet Range", 
        value="Sheet1!A1:Z1000",
        help="Example: Sheet1!A1:Z1000"
    )
    
    if st.button("Connect to Google Sheet"):
        if sheet_id:
            with st.spinner("Connecting to Google Sheets..."):
                df = get_google_sheet_data(sheet_id, sheet_range)
                if df is not None:
                    st.session_state['df'] = df
                    st.success("Successfully connected to Google Sheet!")
        else:
            st.error("Please enter a Google Sheet ID")

# Handle file upload
elif data_source == "Upload File":
    uploaded_file = st.file_uploader("Upload Employee Data (Excel or CSV)", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        st.success("File successfully uploaded!")
        
        # Read the file based on its extension
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        if file_extension == ".csv":
            df = pd.read_csv(uploaded_file)
        else:  # Excel file
            df = pd.read_excel(uploaded_file)
            
        st.session_state['df'] = df

# Process data if available
if 'df' in st.session_state:
    df = st.session_state['df']
    
    # Display the uploaded data
    st.subheader("Employee Data")
    st.dataframe(df)
    
    # Find columns that might contain compensation data
    possible_comp_columns = []
    for col in df.columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ['salary', 'wage', 'pay', 'bonus', 'benefit', 'compensation', 'total']):
            possible_comp_columns.append(col)
    
    # Let the user select compensation columns
    st.subheader("Select Compensation Components")
    selected_columns = st.multiselect(
        "Select all columns to include in total compensation calculation",
        options=df.columns,
        default=possible_comp_columns
    )
    
    if selected_columns:
        # Convert selected columns to numeric, ignoring errors
        for col in selected_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # Calculate total compensation
        df['Total Compensation'] = df[selected_columns].sum(axis=1)
        total_comp = df['Total Compensation'].sum()
        
        # Display results
        st.subheader("Compensation Analysis")
        st.dataframe(df)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Compensation Cost", f"${total_comp:,.2f}")
        
        with col2:
            # Optional: Show average compensation
            avg_comp = total_comp / len(df)
            st.metric("Average Compensation per Employee", f"${avg_comp:,.2f}")
        
        # Download processed data
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Processed Data",
            data=csv,
            file_name="processed_compensation_data.csv",
            mime="text/csv"
        )
else:
    if data_source == "Upload File":
        st.info("Please upload an employee data file to begin analysis")
        
        # Show example file format
        st.subheader("Expected File Format")
        st.write("Your file should contain columns for employee information and compensation data.")
        st.write("Example columns: Employee ID, Name, Department, Salary, Bonus, Benefits")
        
        # Create sample data
        sample_data = {
            'Employee ID': ['001', '002', '003'],
            'Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'Department': ['Engineering', 'Marketing', 'Finance'],
            'Salary': [75000, 65000, 80000],
            'Bonus': [5000, 3000, 7000],
            'Benefits': [12000, 10000, 13000]
        }
        sample_df = pd.DataFrame(sample_data)
        st.dataframe(sample_df)
    elif data_source == "Google Sheets":
        st.info("Please connect to a Google Sheet to begin analysis")
        st.write("Your Google Sheet should have a similar structure to the example below:")
        
        sample_data = {
            'Employee ID': ['001', '002', '003'],
            'Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'Department': ['Engineering', 'Marketing', 'Finance'],
            'Salary': [75000, 65000, 80000],
            'Bonus': [5000, 3000, 7000],
            'Benefits': [12000, 10000, 13000]
        }
        sample_df = pd.DataFrame(sample_data)
        st.dataframe(sample_df)
