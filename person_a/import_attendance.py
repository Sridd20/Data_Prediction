import pandas as pd
import re
import os
import sys
import argparse
from datetime import datetime

# Paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATTENDANCE_CSV = os.path.join(ROOT_DIR, 'data', 'raw', 'attendance.csv')
DEFAULT_BASE_SALARY = 30000

def parse_work_duration_report(file_path):
    print(f"Parsing {file_path}...")
    df = pd.read_excel(file_path, header=None)
    
    # Extract Date from row 2
    # Example format: "Nov 01 2025  To  Nov 29 2025"
    date_str = str(df.iloc[2, 1])
    match = re.search(r'([A-Za-z]{3}\s+\d{2}\s+\d{4})', date_str)
    if not match:
        raise ValueError(f"Could not parse date from string: {date_str}")
    
    start_date_str = match.group(1)
    # Parse to YYYY-MM-01 format
    dt = datetime.strptime(start_date_str, "%b %d %Y")
    report_date = dt.strftime("%Y-%m-01")
    
    # Extract Employees
    employees = []
    emp_rows = df[df[0] == 'Employee:']
    
    for _, row in emp_rows.iterrows():
        row_clean = row.dropna().tolist()
        if len(row_clean) < 3:
            continue
            
        emp_raw = str(row_clean[1])
        summary_raw = str(row_clean[2])
        
        # e.g., "THLL2408 : TITU S JAYAN"
        emp_id_match = re.search(r'([A-Za-z0-9]+)\s*:', emp_raw)
        emp_id = emp_id_match.group(1) if emp_id_match else emp_raw.split(':')[0].strip()
        
        # e.g., "... Late By Days: 2 ..."
        late_match = re.search(r'Late By Days:\s*(\d+)', summary_raw)
        late_count = int(late_match.group(1)) if late_match else 0
        
        # e.g., "... Absent: 22 ..."
        absent_match = re.search(r'Absent:\s*(\d+)', summary_raw)
        absent_count = int(absent_match.group(1)) if absent_match else 0
        
        # e.g., "... Leaves Taken: 0 ..."
        leaves_match = re.search(r'Leaves Taken:\s*(\d+)', summary_raw)
        sanctioned_leaves = int(leaves_match.group(1)) if leaves_match else 0
        
        employees.append({
            'employee_id': emp_id,
            'date': report_date,
            'late_count': late_count,
            'absent_count': absent_count,
            'sanctioned_leaves': sanctioned_leaves,
            'base_salary': DEFAULT_BASE_SALARY # Default, will be updated if history exists
        })
        
    return pd.DataFrame(employees)

def append_to_attendance_csv(new_df):
    if not os.path.exists(os.path.dirname(ATTENDANCE_CSV)):
        os.makedirs(os.path.dirname(ATTENDANCE_CSV))
        
    if os.path.exists(ATTENDANCE_CSV):
        existing_df = pd.read_csv(ATTENDANCE_CSV)
        
        # Try to pull latest base_salary for existing employees
        salary_map = existing_df.groupby('employee_id')['base_salary'].last().to_dict()
        new_df['base_salary'] = new_df['employee_id'].map(salary_map).fillna(DEFAULT_BASE_SALARY)
        
        # Append and avoid exact duplicates
        combined = pd.concat([existing_df, new_df]).drop_duplicates(subset=['employee_id', 'date'], keep='last')
        combined.to_csv(ATTENDANCE_CSV, index=False)
        print(f"Updated {ATTENDANCE_CSV} (Total records: {len(combined)})")
    else:
        new_df.to_csv(ATTENDANCE_CSV, index=False)
        print(f"Created {ATTENDANCE_CSV} with {len(new_df)} records.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Import Work Duration Report to attendance.csv")
    parser.add_argument("file", nargs="?", default=os.path.join(ROOT_DIR, 'data', 'processed', 'WorkDurationReport.xlsx'), help="Path to the Excel file")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
        
    parsed_df = parse_work_duration_report(args.file)
    print(f"Successfully extracted {len(parsed_df)} employee records for date {parsed_df['date'].iloc[0]}.")
    append_to_attendance_csv(parsed_df)
