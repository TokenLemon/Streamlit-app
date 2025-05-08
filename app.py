import streamlit as st
import pandas as pd
import os
import numpy as np
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

st.set_page_config(page_title="Employee Compensation Calculator", layout="wide")
st.title("Employee Compensation Calculator")

# Initialize session state for dataframes if not exists
if 'excel_df' not in st.session_state:
    st.session_state['excel_df'] = None
if 'sheets_df' not in st.session_state:
    st.session_state['sheets_df'] = None
if 'combined_df' not in st.session_state:
    st.session_state['combined_df'] = None

def get_google_sheet_data(sheet_id, range_name):
    """Get data from Google Sheets with improved data handling"""
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
            
            # Use a manual authentication flow for better compatibility
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            st.write("Please authorize this app by visiting this URL:")
            st.markdown(f"[Click here to authorize]({auth_url})")
            
            auth_code = st.text_input("Enter the authorization code you received:")
            
            if auth_code:
                try:
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                    
                    # Save credentials for next time
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                    
                    st.success("Authentication successful!")
                except Exception as e:
                    st.error(f"Authentication failed: {e}")
                    return None
            else:
                return None
    
    if not creds:
        return None
        
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
    data = values[1:] if len(values) > 1 else []
    
    if not data:
        st.error("No data rows found in the Google Sheet.")
        return None
        
    # Create DataFrame
    df = pd.DataFrame(data, columns=headers)
    
    # Process specific columns we know should be numeric
    numeric_columns = [
        'Base Salary', 'Annual Bonus', 'Benefits', 
        'Stock Options', 'Retirement Contribution', 'Total Compensation'
    ]
    
    # Clean and convert columns that should be numeric
    for col in df.columns:
        if any(numeric_name in col for numeric_name in numeric_columns):
            # Clean the column: remove any non-numeric characters except decimal points
            df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
            # Convert to float
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Replace NaN with 0
            df[col] = df[col].fillna(0)
    
    return df

# Create the main UI tabs
tab1, tab2, tab3 = st.tabs(["Excel Upload", "Google Sheets", "Combined Analysis"])

# Tab 1: Excel File Upload
with tab1:
    st.header("Upload Excel File")
    uploaded_file = st.file_uploader("Upload Employee Data (Excel or CSV)", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        st.success("File successfully uploaded!")
        
        # Read the file based on its extension
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        if file_extension == ".csv":
            df = pd.read_csv(uploaded_file)
        else:  # Excel file
            df = pd.read_excel(uploaded_file)
            
        # Process numeric columns
        numeric_columns = [
            'Base Salary', 'Annual Bonus', 'Benefits', 
            'Stock Options', 'Retirement Contribution', 'Total Compensation'
        ]
        
        for col in df.columns:
            if any(numeric_name in col for numeric_name in numeric_columns):
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
                
        st.session_state['excel_df'] = df
        
        # Display the data
        st.subheader("Excel Data Preview")
        st.dataframe(df)
        
        # Show basic statistics
        if df is not None and not df.empty:
            st.subheader("Excel Data Statistics")
            st.write(f"Number of employees: {len(df)}")
            
            # Find numeric columns that might be compensation
            comp_cols = [col for col in df.columns if any(term in col for term in ['Salary', 'Bonus', 'Benefits', 'Stock', 'Retirement', 'Compensation'])]
            if comp_cols:
                comp_cols_numeric = [col for col in comp_cols if pd.api.types.is_numeric_dtype(df[col])]
                if comp_cols_numeric:
                    comp_sum = df[comp_cols_numeric].sum().sum()
                    st.write(f"Sum of all compensation values: ${comp_sum:,.2f}")

# Tab 2: Google Sheets Connection
with tab2:
    st.header("Connect to Google Sheets")
    
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
                sheets_df = get_google_sheet_data(sheet_id, sheet_range)
                if sheets_df is not None:
                    st.session_state['sheets_df'] = sheets_df
                    st.success("Successfully connected to Google Sheet!")
                    
                    # Display the data
                    st.subheader("Google Sheets Data Preview")
                    st.dataframe(sheets_df)
                    
                    # Show column data types to help debug
                    st.subheader("Column Data Types")
                    dtypes_df = pd.DataFrame({'Column': sheets_df.columns, 'Data Type': sheets_df.dtypes.astype(str)})
                    st.dataframe(dtypes_df)
                    
                    # Show basic statistics
                    if not sheets_df.empty:
                        st.subheader("Google Sheets Data Statistics")
                        st.write(f"Number of employees: {len(sheets_df)}")
                        
                        # Find numeric columns that might be compensation
                        comp_cols = [col for col in sheets_df.columns if any(term in col for term in ['Salary', 'Bonus', 'Benefits', 'Stock', 'Retirement', 'Compensation'])]
                        if comp_cols:
                            comp_cols_numeric = [col for col in comp_cols if pd.api.types.is_numeric_dtype(sheets_df[col])]
                            if comp_cols_numeric:
                                comp_sum = sheets_df[comp_cols_numeric].sum().sum()
                                st.write(f"Sum of all compensation values: ${comp_sum:,.2f}")
        else:
            st.error("Please enter a Google Sheet ID")

# Tab 3: Combined Analysis
with tab3:
    st.header("Combined Data Analysis")
    
    # Check if we have data from either source
    excel_df = st.session_state['excel_df']
    sheets_df = st.session_state['sheets_df']
    
    if excel_df is None and sheets_df is None:
        st.warning("Please upload an Excel file and/or connect to a Google Sheet first.")
    else:
        # Provide options for how to combine the data
        st.subheader("Data Combination Settings")
        
        if excel_df is not None and sheets_df is not None:
            combine_method = st.radio(
                "How would you like to combine the data?",
                ["Append (Stack records)", "Join/Merge on a key column"]
            )
            
            if combine_method == "Append (Stack records)":
                # Check if columns match
                excel_cols = set(excel_df.columns)
                sheets_cols = set(sheets_df.columns)
                
                if excel_cols != sheets_cols:
                    st.warning("Column names don't match exactly between Excel and Google Sheets.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("Excel columns:")
                        st.write(sorted(list(excel_cols)))
                    with col2:
                        st.write("Google Sheets columns:")
                        st.write(sorted(list(sheets_cols)))
                    
                    # Option to proceed anyway
                    proceed_anyway = st.checkbox("Proceed with combination anyway (only matching columns will be used)")
                    
                    if proceed_anyway:
                        # Find common columns
                        common_cols = excel_cols.intersection(sheets_cols)
                        st.write("Common columns to be used:", sorted(list(common_cols)))
                        
                        # Combine data using only common columns
                        combined_df = pd.concat([
                            excel_df[list(common_cols)], 
                            sheets_df[list(common_cols)]
                        ], ignore_index=True)
                        
                        st.session_state['combined_df'] = combined_df
                    else:
                        st.stop()
                else:
                    # Columns match, so we can simply append
                    combined_df = pd.concat([excel_df, sheets_df], ignore_index=True)
                    st.session_state['combined_df'] = combined_df
            
            elif combine_method == "Join/Merge on a key column":
                # Get common columns to select from
                common_cols = set(excel_df.columns).intersection(set(sheets_df.columns))
                
                if not common_cols:
                    st.error("No common columns found between Excel and Google Sheets data. Cannot perform join.")
                    st.stop()
                
                # Let user select key column for the join
                key_column = st.selectbox(
                    "Select column to join on:",
                    options=sorted(list(common_cols))
                )
                
                join_type = st.selectbox(
                    "Select join type:",
                    options=["inner", "outer", "left", "right"],
                    format_func=lambda x: {
                        "inner": "Inner join (only matching records)",
                        "outer": "Full outer join (all records from both sources)",
                        "left": "Left join (all Excel records, matching Google Sheets records)",
                        "right": "Right join (all Google Sheets records, matching Excel records)"
                    }.get(x)
                )
                
                # Check for duplicates in join key
                if excel_df[key_column].duplicated().any():
                    st.warning(f"Duplicate values found in Excel {key_column} column. Join may produce unexpected results.")
                
                if sheets_df[key_column].duplicated().any():
                    st.warning(f"Duplicate values found in Google Sheets {key_column} column. Join may produce unexpected results.")
                
                # Add suffixes to identify source
                combined_df = pd.merge(
                    excel_df, 
                    sheets_df, 
                    on=key_column, 
                    how=join_type,
                    suffixes=('_excel', '_sheets')
                )
                
                st.session_state['combined_df'] = combined_df
        else:
            # If we only have one source, use that
            if excel_df is not None:
                st.write("Only Excel data available. Using Excel data for analysis.")
                st.session_state['combined_df'] = excel_df
            else:
                st.write("Only Google Sheets data available. Using Google Sheets data for analysis.")
                st.session_state['combined_df'] = sheets_df
        
        # Now process the combined data for compensation calculation
        combined_df = st.session_state['combined_df']
        
        if combined_df is not None and not combined_df.empty:
            st.subheader("Combined Data Preview")
            st.dataframe(combined_df)
            
            # List all columns for the user to select
            st.subheader("Select Compensation Columns")
            
            # Suggest columns based on names
            comp_columns = [col for col in combined_df.columns if any(
                term in str(col) for term in ['Salary', 'Bonus', 'Benefits', 'Stock', 'Retirement', 'Compensation']
            )]
            
            # Let the user select compensation columns
            selected_columns = st.multiselect(
                "Select all columns to include in total compensation calculation",
                options=combined_df.columns,
                default=comp_columns
            )
            
            if selected_columns:
                # Make a copy to avoid modifying the original
                calc_df = combined_df.copy()
                
                # Ensure all selected columns are numeric
                for col in selected_columns:
                    if not pd.api.types.is_numeric_dtype(calc_df[col]):
                        st.warning(f"Converting column '{col}' to numeric. Original data may not be fully numeric.")
                        # Clean the column to ensure successful conversion
                        calc_df[col] = calc_df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
                    
                    calc_df[col] = pd.to_numeric(calc_df[col], errors='coerce')
                    calc_df[col] = calc_df[col].fillna(0)
                
                # Calculate total compensation
                calc_df['Calculated Total Compensation'] = calc_df[selected_columns].sum(axis=1)
                total_comp = calc_df['Calculated Total Compensation'].sum()
                
                # Display results with improved formatting
                st.subheader("Compensation Analysis")
                
                # Display options
                display_cols = st.multiselect(
                    "Select columns to display in results",
                    options=calc_df.columns,
                    default=['Employee ID', 'First Name', 'Last Name'] + selected_columns + ['Calculated Total Compensation']
                )
                
                if display_cols:
                    st.dataframe(calc_df[display_cols])
                else:
                    st.dataframe(calc_df)
                
                # Summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Compensation Cost", f"${total_comp:,.2f}")
                
                with col2:
                    # Optional: Show average compensation
                    avg_comp = total_comp / len(calc_df)
                    st.metric("Average Compensation per Employee", f"${avg_comp:,.2f}")
                    
                with col3:
                    # Show employee count
                    st.metric("Total Employee Count", f"{len(calc_df)}")
                
                # Optional: Add visualization
                st.subheader("Compensation Distribution")
                
                # Prepare data for chart (sum by component)
                chart_data = pd.DataFrame({
                    'Component': list(selected_columns) + ['Total'],
                    'Amount': [calc_df[col].sum() for col in selected_columns] + [total_comp]
                })
                
                # Display the data for the chart
                st.bar_chart(data=chart_data, x='Component', y='Amount')
                
                # Department-based analysis if Department column exists
                if 'Department' in calc_df.columns:
                    st.subheader("Compensation by Department")
                    dept_data = calc_df.groupby('Department')['Calculated Total Compensation'].agg(['sum', 'mean', 'count'])
                    dept_data.columns = ['Total Compensation', 'Average Compensation', 'Employee Count']
                    dept_data = dept_data.sort_values('Total Compensation', ascending=False)
                    st.dataframe(dept_data)
                    
                # Download processed data
                csv = calc_df.to_csv(index=False)
                st.download_button(
                    label="Download Combined Data",
                    data=csv,
                    file_name="combined_compensation_data.csv",
                    mime="text/csv"
                )