import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import config
from shared.fund_pressure import get_pressure_band
from person_b.allocation_engine import allocate_surplus
from person_b.fund_tracker import FundTracker, compute_projects_to_zero_fund

def generate_dashboard(surplus_csv_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        df = pd.read_csv(surplus_csv_path, parse_dates=['date'])
    except FileNotFoundError:
        print(f"Error: Could not find {surplus_csv_path}")
        return

    tracker = FundTracker(config.MAX_FUND_LIMIT)
    current_reserve = 50000 # Dummy initial reserve
    
    allocations_list = []
    
    # Process history
    for _, row in df.iterrows():
        # Ensure we handle columns gracefully if they are missing
        predicted_surplus = row.get('predicted_surplus', 0)
        
        priorities = {
            'fund_fraction': config.FUND_REPAYMENT_FRACTION,
            'projects': config.PROJECT_WEIGHTS
        }
        alloc = allocate_surplus(predicted_surplus, priorities, current_reserve, config.RESERVE_TARGET)
        
        # Update reserve based on allocation
        current_reserve += alloc.get('reserve', 0)
        
        # Update fund
        tracker.make_payment(alloc.get('fund', 0), row['date'])
        
        alloc_record = alloc.copy()
        alloc_record['date'] = row['date']
        allocations_list.append(alloc_record)

    alloc_df = pd.DataFrame(allocations_list)
    
    # Get latest info
    latest = df.iloc[-1]
    prediction  = {
        'predicted_surplus' : latest.get('predicted_surplus', 0),
        'fpi'               : latest.get('fpi', 0.0),
        'core_team_pct'     : latest.get('core_team_pct', config.CORE_TEAM_PCT_DEFAULT),
        'predicted_fund'    : latest.get('predicted_fund', 0)
    }
    
    band, msg = get_pressure_band(prediction['fpi'])
    
    # 1. Allocation Bar Chart (Most recent month)
    latest_alloc = alloc_df.iloc[-1].drop('date', errors='ignore')
    plt.figure(figsize=(8, 6))
    latest_alloc.plot(kind='bar', color=['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974'])
    plt.title("Current Month Surplus Allocation")
    plt.ylabel("Amount")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latest_allocation.png"))
    plt.close()

    # 2. External Fund Balance Line Chart
    history_df = pd.DataFrame(tracker.history)
    plt.figure(figsize=(8, 6))
    if not history_df.empty:
        plt.plot(history_df['date'], history_df['balance'], marker='o', linestyle='-', color='#C44E52')
    plt.title("External Fund Balance Over Time")
    plt.xlabel("Date")
    plt.ylabel("Balance")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "fund_balance.png"))
    plt.close()
    
    # 3. Summary Report
    months_left = tracker.estimate_months_remaining()
    projects_needed = compute_projects_to_zero_fund(prediction['predicted_fund'])
    
    date_str = latest['date'].strftime('%Y-%m-%d') if hasattr(latest['date'], 'strftime') else latest['date']
    
    print("\n" + "="*40)
    print("           MONTHLY REPORT")
    print("="*40)
    print(f"Date: {date_str}")
    print("-" * 40)
    print(f"Predicted Surplus    : Rs.{prediction['predicted_surplus']:,.2f}")
    print(f"Predicted Fund Reqd  : Rs.{prediction['predicted_fund']:,.2f}")
    print("-" * 40)
    print(f"Fund Pressure Index  : {prediction['fpi']:.3f} [{band}]")
    print(f"Status               : {msg}")
    print(f"Recommended Core Team: {prediction['core_team_pct'] * 100:.0f}%")
    print("-" * 40)
    print(f"Current Reserve      : Rs.{current_reserve:,.2f} / Rs.{config.RESERVE_TARGET:,.2f}")
    print(f"Current Fund Balance : Rs.{tracker.get_balance():,.2f}")
    if months_left:
        print(f"Est. Months to Payoff: {months_left:.1f}")
    if projects_needed > 0:
        print(f"New Projects Needed  : {projects_needed} (to zero out fund)")
    print("="*40 + "\n")

if __name__ == "__main__":
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'monthly_surplus.csv')
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    generate_dashboard(csv_path, out_dir)
