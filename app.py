import streamlit as st
import pandas as pd
import os
import numpy as np

st.set_page_config(page_title="Employee Compensation Calculator", layout="wide")
st.title("Employee Compensation Calculator")

# Initialize session state for dataframes if not exists
if 'uploaded_files' not in st.session_state:
    st.session_state['uploaded_files'] = {}
if 'combined_df' not in st.session_state:
    st.session_state['combined_df'] = None

# Create the main UI tabs
tab1, tab2 = st.tabs(["File Upload", "Compensation Analysis"])

# Tab 1: File Upload
with tab1:
    st.header("Upload Files")
    
    # Option to name the upload source
    source_name = st.text_input("Source Name (e.g., Department or Year)", 
                                value="Source " + str(len(st.session_state['uploaded_files']) + 1))
    
    uploaded_file = st.file_uploader("Upload Employee Data (Excel or CSV)", type=["xlsx", "csv"])
    
    if uploaded_file is not None and st.button("Add to Analysis"):
        st.success(f"File '{uploaded_file.name}' successfully uploaded as '{source_name}'!")
        
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
        
        # Add to our collection
        st.session_state['uploaded_files'][source_name] = df
        
        # Display the data
        st.subheader(f"Preview: {source_name}")
        st.dataframe(df)
        
        # Show basic statistics
        if df is not None and not df.empty:
            st.write(f"Number of employees: {len(df)}")
            
            # Find numeric columns that might be compensation
            comp_cols = [col for col in df.columns if any(term in col for term in ['Salary', 'Bonus', 'Benefits', 'Stock', 'Retirement', 'Compensation'])]
            if comp_cols:
                comp_cols_numeric = [col for col in comp_cols if pd.api.types.is_numeric_dtype(df[col])]
                if comp_cols_numeric:
                    comp_sum = df[comp_cols_numeric].sum().sum()
                    st.write(f"Sum of all compensation values: ${comp_sum:,.2f}")
    
    # Display all uploaded files
    if st.session_state['uploaded_files']:
        st.subheader("Uploaded Sources")
        for name, df in st.session_state['uploaded_files'].items():
            with st.expander(f"{name} - {len(df)} records"):
                st.dataframe(df)
                if st.button(f"Remove {name}", key=f"remove_{name}"):
                    del st.session_state['uploaded_files'][name]
                    st.experimental_rerun()
        
        # Create combined dataframe
        if len(st.session_state['uploaded_files']) > 0:
            if st.button("Combine All Sources for Analysis"):
                dfs = list(st.session_state['uploaded_files'].values())
                # Check column compatibility
                all_columns = set(dfs[0].columns)
                for df in dfs[1:]:
                    if set(df.columns) != all_columns:
                        st.warning("Not all datasets have the same columns. Using only common columns.")
                        all_columns = all_columns.intersection(set(df.columns))
                
                # Filter to common columns before concatenating
                dfs_filtered = [df[list(all_columns)] for df in dfs]
                combined = pd.concat(dfs_filtered, ignore_index=True)
                st.session_state['combined_df'] = combined
                st.success(f"Combined {len(dfs)} sources with {len(combined)} total records!")

# Tab 2: Combined Analysis
with tab2:
    st.header("Compensation Analysis")
    
    # Check if we have data
    combined_df = st.session_state['combined_df']
    
    if combined_df is None:
        if len(st.session_state['uploaded_files']) == 0:
            st.warning("Please upload at least one file in the 'File Upload' tab.")
        else:
            st.warning("Please combine your uploaded sources in the 'File Upload' tab first.")
    else:
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