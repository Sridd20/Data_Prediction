def calculate_fund_pressure(
    outstanding_balance,
    max_fund_limit,
    funds_taken_last_3_months,
    monthly_surplus,
    monthly_expenses,
    active_project_hr_deductions
):
    utilization      = outstanding_balance / max_fund_limit if max_fund_limit > 0 else 0
    frequency        = min(funds_taken_last_3_months / 3, 1.0)
    internal_funds   = monthly_surplus + active_project_hr_deductions
    
    if monthly_expenses > 0:
        coverage         = 1 - min(internal_funds / monthly_expenses, 1.0)
    else:
        coverage         = 0.0 if internal_funds >= 0 else 1.0
        
    repayment_stress = min(max(0, utilization), 1.0)

    fpi = (
        0.30 * utilization     +
        0.20 * frequency       +
        0.30 * coverage        +
        0.20 * repayment_stress
    )
    return round(fpi, 3)

def get_pressure_band(fpi):
    if fpi < 0.25:
        return "GREEN",  "No action needed — self sufficient"
    elif fpi < 0.50:
        return "YELLOW", "Mild pressure — monitor closely"
    elif fpi < 0.75:
        return "ORANGE", "High pressure — reduce core team to 4%"
    else:
        return "RED",    "Critical — reduce core team to 3%, accelerate projects"

def get_core_team_pct(fpi):
    if fpi < 0.50:
        return 0.05
    elif fpi < 0.75:
        return 0.04
    else:
        return 0.03

def fpi_trend(fpi_history: list):
    if len(fpi_history) < 2:
        return "INSUFFICIENT DATA"
    delta = fpi_history[-1] - fpi_history[-2]
    if delta < -0.05:
        return "IMPROVING"
    elif delta > 0.05:
        return "WORSENING"
    else:
        return "STABLE"
