import streamlit as st
import pandas as pd
import os

st.title("Employee Compensation Cost Calculator")

# File uploader widget change
uploaded_file = st.file_uploader("Upload Employee Data (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file is not None:
    st.success("File successfully uploaded!")
    
    # Read the file based on its extension
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
    if file_extension == ".csv":
        df = pd.read_csv(uploaded_file)
    else:  # Excel file
        df = pd.read_excel(uploaded_file)
    
    # Display the uploaded data
    st.subheader("Uploaded Employee Data")
    st.dataframe(df)
    
    # Check if required columns exist
    required_columns = ['salary', 'bonus', 'benefits']  # Adjust these based on your expected file structure
    
    # Find columns that might contain compensation data
    possible_comp_columns = []
    for col in df.columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ['salary', 'wage', 'pay', 'bonus', 'benefit', 'compensation', 'total']):
            possible_comp_columns.append(col)
    
    # Let the user select compensation columns if we can't identify them automatically
    if not all(col.lower() in map(str.lower, df.columns) for col in required_columns):
        st.info("Please select the columns that contain compensation data:")
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
            
            st.metric("Total Compensation Cost", f"${total_comp:,.2f}")
            
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
        # If we have all the required columns
        numeric_columns = [col for col in required_columns if col.lower() in map(str.lower, df.columns)]
        for col in numeric_columns:
            matching_col = next(c for c in df.columns if c.lower() == col.lower())
            df[matching_col] = pd.to_numeric(df[matching_col], errors='coerce')
        
        df['Total Compensation'] = df[[c for c in df.columns if c.lower() in map(str.lower, required_columns)]].sum(axis=1)
        total_comp = df['Total Compensation'].sum()
        
        st.subheader("Compensation Analysis")
        st.dataframe(df)
        st.metric("Total Compensation Cost", f"${total_comp:,.2f}")
else:
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
