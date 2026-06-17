import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import config

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATTENDANCE_CSV = os.path.join(ROOT_DIR, 'data', 'raw', 'attendance.csv')
LEAVE_BALANCES_CSV = os.path.join(ROOT_DIR, 'data', 'raw', 'leave_balances.csv')

def initialize_or_load_balances():
    if os.path.exists(LEAVE_BALANCES_CSV):
        return pd.read_csv(LEAVE_BALANCES_CSV).set_index('employee_id').to_dict('index')
    return {}

def save_balances(balances_dict):
    df = pd.DataFrame.from_dict(balances_dict, orient='index')
    df.index.name = 'employee_id'
    df.reset_index(inplace=True)
    df.to_csv(LEAVE_BALANCES_CSV, index=False)

def process_monthly_attendance(target_date):
    """
    Processes attendance for a specific month.
    target_date should be a string 'YYYY-MM-01'.
    Returns total salary deductions and a detailed DataFrame.
    """
    if not os.path.exists(ATTENDANCE_CSV):
        print(f"Error: {ATTENDANCE_CSV} not found.")
        return 0, pd.DataFrame()
        
    df = pd.read_csv(ATTENDANCE_CSV)
    df_month = df[df['date'] == target_date].copy()
    
    if df_month.empty:
        print(f"No records found for date {target_date}.")
        return 0, pd.DataFrame()

    import calendar
    from datetime import datetime
    
    # Calculate days in the target month
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    days_in_month = calendar.monthrange(dt.year, dt.month)[1]

    balances = initialize_or_load_balances()
    results = []
    
    for _, row in df_month.iterrows():
        emp = row['employee_id']
        late_count = row['late_count']
        absent_count = row.get('absent_count', 0)
        sanctioned_leaves = row.get('sanctioned_leaves', 0)
        base_salary = row['base_salary']
        
        # Initialize employee in balances if new
        if emp not in balances:
            balances[emp] = {'casual_leaves': 0, 'sick_leaves': config.SICK_LEAVES_PER_YEAR}
            
        # Accrue CL per month
        balances[emp]['casual_leaves'] += config.CASUAL_LEAVES_PER_MONTH
        
        # 1. Late Penalty
        late_penalty_days = max(0, late_count - config.ALLOWED_LATE_DAYS)
        
        # 2. Sanctioned Leaves processing (deduct from pool)
        leaves_to_deduct = sanctioned_leaves
        excessive_leaves = 0
        
        # Try to deduct from Casual Leaves first
        if balances[emp]['casual_leaves'] >= leaves_to_deduct:
            balances[emp]['casual_leaves'] -= leaves_to_deduct
            leaves_to_deduct = 0
        else:
            leaves_to_deduct -= balances[emp]['casual_leaves']
            balances[emp]['casual_leaves'] = 0
            
            # Then try Sick Leaves
            if balances[emp]['sick_leaves'] >= leaves_to_deduct:
                balances[emp]['sick_leaves'] -= leaves_to_deduct
                leaves_to_deduct = 0
            else:
                leaves_to_deduct -= balances[emp]['sick_leaves']
                balances[emp]['sick_leaves'] = 0
                
                # Any remaining sanctioned leaves become excessive (pay cut)
                excessive_leaves = leaves_to_deduct
                
        # Total Pay Cut Days
        total_pay_cut_days = late_penalty_days + absent_count + excessive_leaves
        
        # Deduction Amount
        daily_rate = base_salary / days_in_month
        deduction_amount = total_pay_cut_days * daily_rate
        adjusted_salary = base_salary - deduction_amount
        
        results.append({
            'employee_id': emp,
            'base_salary': base_salary,
            'late_count': late_count,
            'absent_count': absent_count,
            'sanctioned_leaves': sanctioned_leaves,
            'pay_cut_days': total_pay_cut_days,
            'adjusted_salary': adjusted_salary,
            'deduction': deduction_amount,
            'cl_balance': balances[emp]['casual_leaves'],
            'sl_balance': balances[emp]['sick_leaves']
        })

    # Save updated balances
    save_balances(balances)
    
    result_df = pd.DataFrame(results)
    total_deduction = result_df['deduction'].sum()
    
    return total_deduction, result_df

if __name__ == '__main__':
    # Test script for the latest month
    df = pd.read_csv(ATTENDANCE_CSV)
    latest_date = df['date'].max()
    print(f"Processing attendance for {latest_date}...")
    total_deduction, details = process_monthly_attendance(latest_date)
    print(f"Total Salary Deductions: Rs.{total_deduction:,.2f}")
    print("\nDetailed breakdown (first 5 employees):")
    print(details.head())
