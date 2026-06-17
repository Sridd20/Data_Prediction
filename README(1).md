# Company Growth Prediction & Surplus Reallocation System

A data-driven financial management system that predicts revenue/costs/profit, tracks employee attendance with automatic salary deductions, computes monthly surplus funds, and intelligently reallocates them to reduce dependency on external loans.

> **Core Philosophy:** Rather than borrowing from Company B when funds run short, the system identifies recoverable money (salary deductions from late arrivals, budget underspend) and reroutes it where needed — making the company self-sufficient.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Attendance & Salary Deduction](#2-attendance--salary-deduction)
3. [Data Requirements](#3-data-requirements)
4. [Forecasting Model](#4-forecasting-model)
5. [Surplus Calculator](#5-surplus-calculator)
6. [Surplus Reallocation Engine](#6-surplus-reallocation-engine)
7. [Repository Structure](#7-repository-structure)
8. [Team Division of Work](#8-team-division-of-work)
9. [Full Data Flow](#9-full-data-flow)
10. [Setup & Installation](#10-setup--installation)
11. [Recommended Build Order](#11-recommended-build-order)
12. [Key Design Decisions](#12-key-design-decisions)

---

## 1. Project Overview

The system does four things:

- Predict future revenue, costs, and profit/loss using historical data
- Track employee attendance and automatically compute salary deductions
- Calculate monthly surplus funds from attendance deductions and cost underspend
- Intelligently reallocate surplus to internal needs (projects, reserves, loan repayment)

---

## 2. Attendance & Salary Deduction

### Rule

Each employee is allowed up to **7 late arrivals per month** at no penalty. From the 8th late arrival onward, each additional late day deducts 1 day from their effective attendance, which directly reduces their salary for that month.

### Formula

```
Penalty_Days         = max(0, late_count - 7)
Effective_Attendance = Total_Days_in_Month - Penalty_Days
Adjusted_Salary      = (Base_Salary / Total_Days) * Effective_Attendance
Deduction            = Base_Salary - Adjusted_Salary
```

### Example (30-day month)

| Late Count | Penalty Days | Effective Attendance | Salary Deducted    |
|------------|--------------|----------------------|--------------------|
| 5 days     | 0            | 30 days              | ₹0                 |
| 7 days     | 0            | 30 days              | ₹0                 |
| 8 days     | 1            | 29 days              | 1/30 of base salary|
| 10 days    | 3            | 27 days              | 3/30 of base salary|
| 12 days    | 5            | 25 days              | 5/30 of base salary|

### Python Implementation

```python
def calculate_effective_attendance(total_days, late_count, allowed_late=7):
    penalty = max(0, late_count - allowed_late)
    return total_days - penalty

def calculate_salary(base_salary, total_days, late_count, allowed_late=7):
    eff_att = calculate_effective_attendance(total_days, late_count, allowed_late)
    adjusted = (base_salary / total_days) * eff_att
    return adjusted, eff_att
```

Total salary deductions across all employees each month feeds into the Surplus Calculator as recovered funds.

---

## 3. Data Requirements

### Available Data

- 1 full year of daily/monthly company data (2025) — training baseline
- As new months pass, the model retrains on the growing dataset (adaptive)

### Required CSV Files

| File            | Key Columns                              | Notes                          |
|-----------------|------------------------------------------|--------------------------------|
| attendance.csv  | employee_id, date, late_count, base_salary | Daily or monthly aggregated  |
| revenue.csv     | date, revenue                            | Monthly, date as YYYY-MM-01    |
| costs.csv       | date, operating_cost, category           | Monthly, split by category     |

### CSV Format Example (`revenue.csv`)

```csv
date,revenue
2025-01-01,520000
2025-02-01,535000
2025-03-01,498000
```

### Loading Data

```python
import pandas as pd

df = pd.read_csv('data/raw/revenue.csv', parse_dates=['date'], index_col='date')
df = df.asfreq('MS')   # 'MS' = Month Start frequency — critical for SARIMA/Prophet
series = df['revenue']
```

> **Note on Data Quantity:** With only 12 months of data, SARIMA and LSTM are **not viable**. The chosen model is Multivariate Linear Regression — reliable with 12 data points and fully interpretable. The pipeline will auto-upgrade to SARIMA or Prophet once data exceeds 24 months.

---

## 4. Forecasting Model

### Model Comparison

| Model             | Min Data Needed   | Seasonality | Chosen?          | Reason                                      |
|-------------------|-------------------|-------------|------------------|---------------------------------------------|
| Linear Regression | ~6+ months        | No (month feature) | ✅ PRIMARY  | Works with 12 pts, interpretable, reliable  |
| ARIMA             | 24–36 months      | No          | ❌ (future)      | Needs more history                          |
| SARIMA            | 36+ months (m=12) | Yes         | 🔄 Future upgrade | Best at 36+ months of monthly data         |
| Prophet           | 24+ months        | Yes (auto)  | 🔄 Future upgrade | Needs 2+ full yearly cycles                |
| LSTM              | 100s of points    | Learned     | ❌               | Impractical with 12 months                 |

### Adaptive Upgrade Path

```python
if len(monthly_data) < 24:
    model = LinearRegression()              # current phase
elif len(monthly_data) < 36:
    model = ARIMA(order=(1,1,1))            # no seasonality yet
else:
    model = SARIMAX(order=(1,1,1),          # full seasonal model
                    seasonal_order=(1,1,1,12))
```

### Prediction Features

**Target:** next month's predicted surplus

| Feature                     | Description                                              |
|-----------------------------|----------------------------------------------------------|
| previous_month_surplus      | Lag-1 surplus — most predictive single feature           |
| total_salary_deductions     | Sum of all attendance-based deductions this month        |
| num_employees_over_threshold| Count of employees with 8+ late days                    |
| operating_cost_variance     | Actual cost minus budgeted cost (negative = underspend)  |
| revenue_vs_target           | Actual revenue minus revenue target                      |
| month_number                | 1–12 integer, captures within-year patterns              |

---

## 5. Surplus Calculator

### Definition

```
Monthly_Surplus = Salary_Deductions + Cost_Underspend - Cost_Overspend
```

Where:
- `Salary_Deductions` = sum of all individual employee deductions
- `Cost_Underspend` = `max(0, budgeted_cost - actual_cost)` — money saved vs plan
- `Cost_Overspend` = `max(0, actual_cost - budgeted_cost)` — money spent over plan

### Python Implementation

```python
def compute_monthly_surplus(salary_deductions, budgeted_cost, actual_cost):
    underspend = max(0, budgeted_cost - actual_cost)
    overspend  = max(0, actual_cost - budgeted_cost)
    surplus    = salary_deductions + underspend - overspend
    return surplus
```

---

## 6. Surplus Reallocation Engine

### Priority Tiers

| Priority | Destination          | Rule                                            |
|----------|----------------------|-------------------------------------------------|
| 1 — FIRST  | Emergency Reserve  | Top up to `reserve_target` before anything else |
| 2 — SECOND | Loan Repayment (Company B) | 50% of remaining after reserve          |
| 3 — THIRD  | Active Project Funding | Remaining split by project weight           |
| 4 — FOURTH | R&D / Discretionary | Only if surplus remains after above            |

### Python Implementation

```python
def allocate_surplus(predicted_surplus, priorities, current_reserve, reserve_target):
    allocation = {}
    remaining  = predicted_surplus

    # Priority 1: Emergency Reserve
    reserve_gap           = max(0, reserve_target - current_reserve)
    allocation['reserve'] = min(remaining, reserve_gap)
    remaining            -= allocation['reserve']

    # Priority 2: Loan Repayment
    loan_amount           = remaining * priorities.get('loan_fraction', 0.5)
    allocation['loan']    = loan_amount
    remaining            -= loan_amount

    # Priority 3 & 4: Projects (proportional to weight)
    for project, weight in priorities.get('projects', {}).items():
        allocation[project] = remaining * weight

    return allocation
```

### Config Values (`shared/config.py`)

```python
ALLOWED_LATE_DAYS       = 7
WORKING_DAYS_PER_MONTH  = 30
RESERVE_TARGET          = 100000    # minimum emergency reserve (adjust to company scale)
LOAN_REPAYMENT_FRACTION = 0.5       # 50% of post-reserve surplus goes to loan repayment
PROJECT_WEIGHTS         = {
    'project_alpha': 0.3,
    'project_beta' : 0.2,
}
```

---

## 7. Repository Structure

Single shared repository. Two developers (Person A and Person B) work in separate branches and merge into `main` when modules are tested.

```
company_surplus/
│
├── data/
│   ├── raw/
│   │   ├── attendance.csv
│   │   ├── revenue.csv
│   │   └── costs.csv
│   └── processed/
│       └── monthly_surplus.csv     ← Person A output / Person B input
│
├── person_a/                        ← Data & Prediction Engine
│   ├── data_cleaning.py             ← load, clean, handle missing values/outliers
│   ├── attendance_module.py         ← salary deduction logic
│   ├── surplus_calculator.py        ← compute monthly surplus
│   └── prediction_model.py          ← linear regression → predicted_surplus
│
├── person_b/                        ← Allocation & Reporting Engine
│   ├── allocation_engine.py         ← rule-based reallocation logic
│   ├── loan_tracker.py              ← track Company B loan reduction over time
│   └── dashboard.py                 ← charts/tables/monthly reports
│
├── shared/
│   ├── config.py                    ← all constants, thresholds, weights (both edit)
│   └── utils.py                     ← shared helper functions
│
├── main.py                          ← runs full pipeline end to end
├── requirements.txt
└── README.md
```

---

## 8. Team Division of Work

### Person A — Data & Prediction Engine

| File                  | Responsibility                                                               |
|-----------------------|------------------------------------------------------------------------------|
| data_cleaning.py      | Load CSVs, parse dates, handle missing values, flag anomalies                |
| attendance_module.py  | Implement deduction logic, `monthly_salary_cost()`, per-employee detail output |
| surplus_calculator.py | Combine deductions + cost variance → `monthly_surplus.csv`                  |
| prediction_model.py   | Engineer features, train Linear Regression, predict next month, output MAE/RMSE/MAPE |

### Person B — Allocation & Reporting Engine

| File                  | Responsibility                                                               |
|-----------------------|------------------------------------------------------------------------------|
| allocation_engine.py  | Implement `allocate_surplus()` with priority tiers, read from Person A output |
| loan_tracker.py       | Maintain running total of loan repayments, project when dependency reaches zero |
| dashboard.py          | Monthly bar charts (allocation), line chart (loan balance), summary tables   |
| config.py (shared)    | Define and maintain all constants — both developers coordinate here          |

### Integration Point

```python
# Person A writes:
# monthly_surplus.csv  →  date, actual_surplus, predicted_surplus

# Person B reads:
df = pd.read_csv('data/processed/monthly_surplus.csv')
predicted = df['predicted_surplus'].iloc[-1]
plan = allocate_surplus(predicted, priorities, current_reserve, RESERVE_TARGET)
```

### Git Workflow

- `main` — stable, tested code only. Never push broken code here.
- `person-a` — Person A's development branch
- `person-b` — Person B's development branch
- Merge to `main` via pull request once each module passes basic tests

---

## 9. Full Data Flow

```
attendance.csv  ──┐
revenue.csv     ──┤──→  data_cleaning.py
costs.csv       ──┘           │
                              ↓
                    attendance_module.py
                    (salary deductions)
                              │
                              ↓
                    surplus_calculator.py
                    (monthly_surplus.csv)
                              │
                    ┌─────────┴──────────┐
                    ↓                    ↓
           prediction_model.py    allocation_engine.py
           (predicted_surplus)    (reallocation plan)
                    │                    │
                    └──────────┬─────────┘
                               ↓
                         dashboard.py
                    (reports + loan tracker)
```

---

## 10. Setup & Installation

### Requirements (`requirements.txt`)

```
pandas
numpy
scikit-learn
statsmodels          # for future ARIMA/SARIMA upgrade
prophet              # for future Prophet upgrade
matplotlib
seaborn              # optional, for dashboard styling
```

### Install

```bash
pip install -r requirements.txt --break-system-packages
```

---

## 11. Recommended Build Order

| Step | Person | Task                                                      | Output                    |
|------|--------|-----------------------------------------------------------|---------------------------|
| 1    | Both   | Agree on CSV column names and formats in `config.py`      | Shared data contract      |
| 2    | A      | `data_cleaning.py` — load and validate CSVs               | Clean DataFrames          |
| 3    | A      | `attendance_module.py` — deduction logic                  | `monthly_salary_cost()`   |
| 4    | A      | `surplus_calculator.py` — combine deductions + cost variance | `monthly_surplus.csv`  |
| 5    | B      | `allocation_engine.py` — priority-based allocator         | `allocate_surplus()`      |
| 6    | A      | `prediction_model.py` — Linear Regression on surplus features | `predicted_surplus`   |
| 7    | B      | `loan_tracker.py` — running loan balance tracker          | Loan reduction timeline   |
| 8    | B      | `dashboard.py` — charts and summary tables                | Monthly report output     |
| 9    | Both   | `main.py` — wire all modules together end to end          | Full working pipeline     |

---

## 12. Key Design Decisions

| Decision | Detail |
|----------|--------|
| **Model choice** | Linear Regression (multivariate). Chosen because only 12 months of data is available. Upgrade path to SARIMA/Prophet is built into the architecture. |
| **Unsupervised learning** | Not used for core forecasting. May optionally add Isolation Forest for anomaly detection as a preprocessing step. |
| **Attendance threshold** | 7 allowed late days/month. The 8th onward triggers −1 effective attendance day per late day. Hardcoded in `config.py` as `ALLOWED_LATE_DAYS = 7`. |
| **Reallocation priority** | Reserve first → Loan repayment second (50% of remaining) → Projects third. Order is fixed in `allocation_engine.py`; weights are configurable in `config.py`. |
| **Repository** | Single shared repo, two branches (`person-a`, `person-b`), merge to `main` when stable. |
| **Data granularity** | Daily attendance data, monthly aggregation for forecasting. `monthly_surplus.csv` is the canonical handoff file between Person A and Person B. |

---

*Company Growth Prediction & Surplus Reallocation System*
