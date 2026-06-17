# SurplusIQ

> Employee-aware financial forecasting system that tracks attendance deductions, predicts monthly surplus, and automatically reallocates recovered funds to internal needs — reducing dependency on external loans.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Core Philosophy](#2-core-philosophy)
3. [Attendance & Salary Deduction Rule](#3-attendance--salary-deduction-rule)
4. [Budget Structure Per Project](#4-budget-structure-per-project)
5. [Data Requirements](#5-data-requirements)
6. [Surplus Calculator](#6-surplus-calculator)
7. [Loan Pressure Index (LPI)](#7-loan-pressure-index-lpi)
8. [4-Layer Prediction Pipeline](#8-4-layer-prediction-pipeline)
9. [ML API Prediction](#9-ml-api-prediction)
10. [Reallocation Engine](#10-reallocation-engine)
11. [Repository Structure](#11-repository-structure)
12. [Team Division](#12-team-division)
13. [Build Order](#13-build-order)
14. [Config Reference](#14-config-reference)
15. [Requirements](#15-requirements)

---

## 1. Project Overview

SurplusIQ is a financial management and forecasting system built for a project-based company. It solves one core problem:

**The company periodically needs to borrow from an external loan source. SurplusIQ identifies, predicts, and reallocates internal surplus funds so that external borrowing is reduced and eventually eliminated.**

Sources of internal surplus:
- Salary deductions from employee late-coming attendance rule
- Budget underspend across project categories
- HR cost deductions flowing in monthly from active projects

The system predicts next month's external loan requirement and proactively adjusts internal allocations (core team %, project funding) to minimise or avoid the loan entirely.

---

## 2. Core Philosophy

```
More active projects  →  more monthly HR deductions flowing in
                      →  higher internal surplus
                      →  less external loan needed

When loan pressure is high:
  →  reduce core team % from 5% to 3-4%
  →  recover extra funds internally
  →  avoid external borrowing
```

The system is self-correcting. It does not just report the problem — it adjusts allocations automatically based on predicted loan pressure.

---

## 3. Attendance & Salary Deduction Rule

### Rule

Each employee is allowed **7 late arrivals per month** at no penalty.
From the **8th late arrival onward**, each additional late day deducts **1 day** from effective attendance, directly reducing that month's salary.

### Formula

```
Penalty_Days         = max(0, late_count - 7)
Effective_Attendance = Total_Days_in_Month - Penalty_Days
Adjusted_Salary      = (Base_Salary / Total_Days) * Effective_Attendance
Deduction            = Base_Salary - Adjusted_Salary
```

### Examples

| Late Count | Penalty Days | Effective Attendance (30-day month) | Deduction |
|---|---|---|---|
| 5 | 0 | 30 days | ₹0 |
| 7 | 0 | 30 days | ₹0 |
| 8 | 1 | 29 days | 1/30 of base salary |
| 10 | 3 | 27 days | 3/30 of base salary |
| 12 | 5 | 25 days | 5/30 of base salary |

### Implementation (`person_a/attendance_module.py`)

```python
def calculate_effective_attendance(total_days, late_count, allowed_late=7):
    penalty = max(0, late_count - allowed_late)
    return total_days - penalty

def calculate_salary(base_salary, total_days, late_count, allowed_late=7):
    eff_att     = calculate_effective_attendance(total_days, late_count, allowed_late)
    adjusted    = (base_salary / total_days) * eff_att
    deduction   = base_salary - adjusted
    return adjusted, eff_att, deduction

def monthly_salary_cost(employee_df, total_days=30):
    """
    employee_df columns: employee_id, base_salary, late_count
    Returns: total adjusted salary cost, per-employee detail DataFrame
    """
    results = []
    for _, row in employee_df.iterrows():
        adj, eff, ded = calculate_salary(row['base_salary'], total_days, row['late_count'])
        results.append({
            'employee_id'        : row['employee_id'],
            'base_salary'        : row['base_salary'],
            'late_count'         : row['late_count'],
            'effective_attendance': eff,
            'adjusted_salary'    : adj,
            'deduction'          : ded
        })
    detail_df = pd.DataFrame(results)
    total_deductions = detail_df['deduction'].sum()
    return total_deductions, detail_df
```

Total deductions from this function feed directly into the Surplus Calculator.

---

## 4. Budget Structure Per Project

Every project follows a fixed split:

```
Total Project Budget = 100%
│
├── 85% → Project Fund
│   ├── Awareness Camp
│   ├── Flex
│   └── Staff
│
└── 15% → Overhead
    ├── Core Team   5%   ← ADJUSTABLE: reducible to 3-4% under loan pressure
    ├── Admin       5%   ← FIXED
    └── HR Cost     5%   ← FIXED: flows into company monthly expenses
```

### HR Cost Monthly Deduction Rule

```
Monthly_HR_Deduction (per project) = (Project_Budget × 0.05) / Duration_in_Months
```

This amount is subtracted from the company's total monthly expenses.
The remaining balance (expenses not covered by HR deductions + surplus) determines how much external loan is needed.

### Core Team Adjustment Lever

| Loan Pressure | Core Team % | Extra Recovery |
|---|---|---|
| GREEN  (LPI < 0.25) | 5% | ₹0 extra |
| YELLOW (LPI < 0.50) | 5% | ₹0 extra |
| ORANGE (LPI < 0.75) | 4% | 1% of total budget recovered |
| RED    (LPI ≥ 0.75) | 3% | 2% of total budget recovered |

### Implementation (`person_b/allocation_engine.py`)

```python
def get_adjusted_budget(total_budget, lpi):
    core_pct    = get_core_team_pct(lpi)   # from shared/loan_pressure.py
    admin_pct   = 0.05
    hr_pct      = 0.05
    project_pct = 1 - core_pct - admin_pct - hr_pct

    return {
        'project_fund': total_budget * project_pct,   # 85-87%
        'core_team'   : total_budget * core_pct,       # 3-5%
        'admin'       : total_budget * admin_pct,       # 5%
        'hr_cost'     : total_budget * hr_pct           # 5%
    }
```

---

## 5. Data Requirements

### Required CSV Files

#### `data/raw/attendance.csv`
```
employee_id, date, late_count, base_salary
```

#### `data/raw/revenue.csv`
```
date, revenue
```
Date format: `YYYY-MM-01` (monthly, first of month)

#### `data/raw/expenses.csv`
```
date, project_id, category, budgeted_amount, actual_amount
```
Category values: `awareness_camp`, `flex`, `staff`, `core_team`, `admin`, `hr_cost`

#### `data/raw/projects.csv`
```
project_id, project_name, start_date, end_date, total_budget, duration_months, status
```
Status values: `active`, `completed`, `pipeline`

#### `data/raw/loans.csv`
```
date, loan_amount_requested, loan_amount_received, repaid_amount, outstanding_balance, source
```

#### `data/raw/project_pipeline.csv`
```
expected_start_date, estimated_budget, estimated_duration_months, probability
```
Probability values: `confirmed`, `likely`, `tentative`

### Loading Data

```python
import pandas as pd

def load_series(filepath, date_col='date', value_col=None):
    df = pd.read_csv(filepath, parse_dates=[date_col], index_col=date_col)
    df = df.asfreq('MS')   # MS = Month Start — required for time-series models
    return df[value_col] if value_col else df
```

### Data Priority

| Priority | File | Purpose |
|---|---|---|
| Must have | attendance.csv | Salary deductions |
| Must have | expenses.csv | Cost variance + surplus |
| Must have | loans.csv | Training target variable |
| Must have | projects.csv | HR deduction calculation |
| Must have | revenue.csv | Total inflow baseline |
| Nice to have | project_pipeline.csv | Future loan forecasting |

---

## 6. Surplus Calculator

### Formula

```
Monthly_Surplus = Salary_Deductions + Cost_Underspend - Cost_Overspend
```

Where:
- `Salary_Deductions` = sum of all attendance-based deductions (from attendance module)
- `Cost_Underspend`   = `max(0, budgeted_cost - actual_cost)` — money saved vs plan
- `Cost_Overspend`    = `max(0, actual_cost - budgeted_cost)` — money spent over plan

### Implementation (`person_a/surplus_calculator.py`)

```python
def compute_monthly_surplus(salary_deductions, budgeted_cost, actual_cost):
    underspend = max(0, budgeted_cost - actual_cost)
    overspend  = max(0, actual_cost  - budgeted_cost)
    surplus    = salary_deductions + underspend - overspend
    return surplus

def compute_project_hr_deductions(projects_df):
    """
    projects_df columns: project_id, total_budget, duration_months, status
    Returns total monthly HR deductions from all active projects
    """
    active = projects_df[projects_df['status'] == 'active']
    active = active.copy()
    active['monthly_hr'] = (active['total_budget'] * 0.05) / active['duration_months']
    return active['monthly_hr'].sum()
```

Output is written to `data/processed/monthly_surplus.csv` — the handoff file between Person A and Person B.

---

## 7. Loan Pressure Index (LPI)

LPI is a composite score from 0.0 to 1.0 measuring how urgently the company needs to reduce external loan dependency.

### Components

| Component | Weight | What it measures |
|---|---|---|
| Loan Utilization | 30% | Outstanding balance vs max loan limit |
| Loan Frequency | 20% | How often loans are taken (last 3 months) |
| Surplus Coverage | 30% | Can internal funds cover expenses without loan |
| Repayment Stress | 20% | Is outstanding balance growing or shrinking |

### Implementation (`shared/loan_pressure.py`)

```python
def calculate_loan_pressure(
    outstanding_balance,
    max_loan_limit,
    loans_taken_last_3_months,
    monthly_surplus,
    monthly_expenses,
    active_project_hr_deductions
):
    utilization      = outstanding_balance / max_loan_limit
    frequency        = min(loans_taken_last_3_months / 3, 1.0)
    internal_funds   = monthly_surplus + active_project_hr_deductions
    coverage         = 1 - min(internal_funds / monthly_expenses, 1.0)
    repayment_stress = min(max(0, outstanding_balance / max_loan_limit), 1.0)

    lpi = (
        0.30 * utilization     +
        0.20 * frequency       +
        0.30 * coverage        +
        0.20 * repayment_stress
    )
    return round(lpi, 3)

def get_pressure_band(lpi):
    if lpi < 0.25:
        return "GREEN",  "No action needed — self sufficient"
    elif lpi < 0.50:
        return "YELLOW", "Mild pressure — monitor closely"
    elif lpi < 0.75:
        return "ORANGE", "High pressure — reduce core team to 4%"
    else:
        return "RED",    "Critical — reduce core team to 3%, accelerate projects"

def get_core_team_pct(lpi):
    if lpi < 0.50:
        return 0.05
    elif lpi < 0.75:
        return 0.04
    else:
        return 0.03

def lpi_trend(lpi_history: list):
    if len(lpi_history) < 2:
        return "INSUFFICIENT DATA"
    delta = lpi_history[-1] - lpi_history[-2]
    if delta < -0.05:
        return "IMPROVING"
    elif delta > 0.05:
        return "WORSENING"
    else:
        return "STABLE"
```

---

## 8. 4-Layer Prediction Pipeline

All four layers run sequentially. Each layer feeds the next.

```
Layer 1: Predict active project count next month   (seasonal trend)
              ↓
Layer 2: Predict total monthly surplus             (from all sources)
              ↓
Layer 3: Predict external loan required            (expenses - surplus)
              ↓
Layer 4: Compute LPI + trigger core team lever
```

### Layer 1 — Project Count Prediction

```python
def predict_project_count(history: list, month_number: int) -> dict:
    """
    history      = list of monthly project counts (12+ values)
    month_number = 1-12 (the month being predicted)
    """
    return {
        'month_number'       : month_number,
        'last_month_count'   : history[-1],
        'rolling_3m_avg'     : sum(history[-3:]) / 3,
        'same_month_last_yr' : history[-12] if len(history) >= 12 else history[-1]
    }
```

### Layer 2 — Monthly Surplus Prediction

```python
def predict_monthly_surplus(
    predicted_project_count,
    avg_project_budget,
    avg_project_duration,
    predicted_attendance_deductions,
    predicted_cost_variance
):
    hr_per_project   = (avg_project_budget * 0.05) / avg_project_duration
    total_hr         = predicted_project_count * hr_per_project

    predicted_surplus = (
        total_hr                          +
        predicted_attendance_deductions   +
        predicted_cost_variance
    )
    return predicted_surplus
```

### Layer 3 — Loan Requirement Prediction

```python
def predict_loan_required(
    predicted_total_expenses,
    predicted_surplus,
    predicted_revenue,
    core_team_pct
):
    internal_funds    = predicted_surplus + predicted_revenue
    raw_loan          = predicted_total_expenses - internal_funds
    core_team_saving  = predicted_total_expenses * (0.05 - core_team_pct)
    adjusted_loan     = max(0, raw_loan - core_team_saving)

    return {
        'raw_loan_required'     : raw_loan,
        'core_team_saving'      : core_team_saving,
        'adjusted_loan_required': adjusted_loan,
        'loan_avoidable'        : raw_loan <= 0
    }
```

### Layer 4 — Full Pipeline Orchestrator

```python
def full_prediction_pipeline(month_number, history, config):

    # Layer 1 — project count
    proj_features = predict_project_count(history['projects'], month_number)
    proj_count    = proj_features['rolling_3m_avg']

    # Layer 2 — surplus
    surplus = predict_monthly_surplus(
        proj_count,
        config['avg_project_budget'],
        config['avg_project_duration'],
        history['avg_attendance_deduction'],
        history['avg_cost_variance']
    )

    # Layer 3 — first pass loan (assume 5% core team)
    loan_result = predict_loan_required(
        history['avg_monthly_expenses'],
        surplus,
        history['avg_revenue'],
        core_team_pct=0.05
    )

    # Layer 4 — LPI + lever
    lpi          = calculate_loan_pressure(
        history['outstanding_balance'],
        config['max_loan_limit'],
        history['loans_last_3m'],
        surplus,
        history['avg_monthly_expenses'],
        surplus
    )
    band, msg    = get_pressure_band(lpi)
    core_pct     = get_core_team_pct(lpi)

    # Recompute loan with adjusted core team %
    final_loan   = predict_loan_required(
        history['avg_monthly_expenses'],
        surplus,
        history['avg_revenue'],
        core_team_pct=core_pct
    )

    return {
        'predicted_project_count'         : proj_count,
        'predicted_surplus'               : surplus,
        'lpi'                             : lpi,
        'pressure_band'                   : band,
        'pressure_message'                : msg,
        'core_team_pct'                   : core_pct,
        'predicted_loan_required'         : final_loan['adjusted_loan_required'],
        'loan_avoidable'                  : final_loan['loan_avoidable'],
        'projects_to_zero_loan'           : compute_projects_to_zero_loan(
                                                final_loan['adjusted_loan_required'],
                                                config['avg_project_budget'],
                                                config['avg_project_duration']
                                            )
    }

def compute_projects_to_zero_loan(loan_required, avg_budget, avg_duration):
    if loan_required <= 0:
        return 0
    hr_per_project = (avg_budget * 0.05) / avg_duration
    return round(loan_required / hr_per_project + 0.5)   # ceiling
```

---

## 9. ML API Prediction

Since the company currently has only 1 year (12 months) of data, training a local Linear Regression model is unreliable (minimum 30+ data points needed per feature). The ML API approach sidesteps this constraint entirely.

### Why ML API over local model

| Factor | Local Linear Regression | ML API (Claude) |
|---|---|---|
| Min data needed | 30+ points (10× features) | Works with 3-4 months |
| Retraining | Manual, every month | None — just send new data |
| Explainability | Coefficients only | Natural language reasoning |
| Allocation advice | Separate rule engine | Built into the response |
| Setup complexity | Medium | Minimal |

### Adaptive Upgrade Path (as data grows)

```python
def choose_model(monthly_data):
    n = len(monthly_data)
    if n < 24:
        return "ML_API"                  # current phase — 12 months
    elif n < 36:
        return "ARIMA"                   # no seasonality yet
    else:
        return "SARIMA"                  # full seasonal model (m=12)
```

### API Call (`person_a/prediction_model.py`)

```python
import anthropic
import json

client = anthropic.Anthropic()   # key handled by environment

def api_predict(history: dict, config: dict, month_number: int) -> dict:
    prompt = f"""
    You are a financial prediction assistant for a project-based company.

    Historical data (last 12 months):
    - Monthly project counts      : {history['projects']}
    - Monthly surplus values      : {history['surplus']}
    - Monthly loan amounts taken  : {history['loans']}
    - Monthly expenses            : {history['expenses']}
    - Attendance deductions       : {history['attendance_deductions']}

    Company config:
    - Average project budget      : {config['avg_project_budget']}
    - Average project duration    : {config['avg_project_duration']} months
    - HR cost rule                : 5% of budget divided by duration = monthly deduction
    - Core team range             : 3-5% (reducible under loan pressure)
    - Max loan limit              : {config['max_loan_limit']}
    - Outstanding loan balance    : {history['outstanding_balance']}

    Predict for month number {month_number}:
    1. expected_project_count
    2. expected_monthly_surplus
    3. expected_loan_required
    4. loan_pressure_index (0.0 to 1.0)
    5. recommended_core_team_pct (0.03, 0.04, or 0.05)
    6. projects_needed_to_avoid_loan
    7. reasoning (2-3 lines)

    Respond in JSON only. No preamble. No markdown.
    """

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response.content[0].text)
```

---

## 10. Reallocation Engine

### Priority Tiers

| Priority | Destination | Rule |
|---|---|---|
| 1 — FIRST | Emergency Reserve | Top up to `RESERVE_TARGET` before anything else |
| 2 — SECOND | External Loan Repayment | 50% of remaining after reserve |
| 3 — THIRD | Active Project Funding | Remaining split by project weight |
| 4 — FOURTH | R&D / Discretionary | Only if surplus remains after above |

### Implementation (`person_b/allocation_engine.py`)

```python
def allocate_surplus(predicted_surplus, priorities, current_reserve, reserve_target):
    allocation = {}
    remaining  = predicted_surplus

    # Priority 1: Emergency Reserve
    reserve_gap              = max(0, reserve_target - current_reserve)
    allocation['reserve']    = min(remaining, reserve_gap)
    remaining               -= allocation['reserve']

    # Priority 2: Loan Repayment
    loan_fraction            = priorities.get('loan_fraction', 0.5)
    allocation['loan']       = remaining * loan_fraction
    remaining               -= allocation['loan']

    # Priority 3 & 4: Projects
    for project, weight in priorities.get('projects', {}).items():
        allocation[project]  = remaining * weight

    return allocation
```

---

## 11. Repository Structure

```
surplusiq/
│
├── data/
│   ├── raw/
│   │   ├── attendance.csv
│   │   ├── revenue.csv
│   │   ├── expenses.csv
│   │   ├── projects.csv
│   │   ├── loans.csv
│   │   └── project_pipeline.csv
│   └── processed/
│       └── monthly_surplus.csv        ← Person A output / Person B input
│
├── person_a/                          ← Data & Prediction Engine
│   ├── data_cleaning.py               ← load, clean, handle missing values
│   ├── attendance_module.py           ← salary deduction logic
│   ├── surplus_calculator.py          ← compute monthly surplus
│   └── prediction_model.py           ← 4-layer pipeline + ML API call
│
├── person_b/                          ← Allocation & Reporting Engine
│   ├── allocation_engine.py           ← priority-based reallocation
│   ├── loan_tracker.py                ← running loan balance + reduction timeline
│   └── dashboard.py                   ← charts, tables, monthly reports
│
├── shared/
│   ├── loan_pressure.py               ← LPI calculation + pressure bands + lever
│   ├── config.py                      ← all constants and weights
│   └── utils.py                       ← shared helper functions
│
├── main.py                            ← runs full pipeline end to end
├── requirements.txt
└── README.md
```

### Data Flow

```
attendance.csv   ──┐
revenue.csv      ──┤──→  data_cleaning.py
expenses.csv     ──┤           │
projects.csv     ──┘           ↓
                     attendance_module.py
                     surplus_calculator.py
                               │
                               ↓
                       monthly_surplus.csv
                               │
                    ┌──────────┴───────────┐
                    ↓                      ↓
           prediction_model.py    allocation_engine.py
           (4-layer pipeline)     (priority reallocation)
           (ML API call)                   │
                    │                      ↓
                    └──────────┬───────────┘
                               ↓
                          dashboard.py
                   (reports + loan tracker)
```

---

## 12. Team Division

### Person A — Data & Prediction Engine

| File | Responsibility |
|---|---|
| `data_cleaning.py` | Load all CSVs, parse dates (`asfreq('MS')`), handle missing values |
| `attendance_module.py` | Deduction logic, `monthly_salary_cost()`, per-employee detail output |
| `surplus_calculator.py` | Combine deductions + HR deductions + cost variance → `monthly_surplus.csv` |
| `prediction_model.py` | 4-layer prediction pipeline, ML API call, output `predicted_surplus` + full prediction dict |

### Person B — Allocation & Reporting Engine

| File | Responsibility |
|---|---|
| `allocation_engine.py` | `allocate_surplus()`, `get_adjusted_budget()`, reads `monthly_surplus.csv` |
| `loan_tracker.py` | Running loan balance, projects-to-zero-loan counter, repayment timeline |
| `dashboard.py` | Monthly bar charts (allocation), LPI gauge, loan balance line chart, summary tables |
| `config.py` (shared) | Maintained jointly — all constants agreed on before coding starts |

### Integration Point

```python
# Person A writes:
# data/processed/monthly_surplus.csv
# columns: date, actual_surplus, predicted_surplus, lpi, core_team_pct, predicted_loan

# Person B reads:
df          = pd.read_csv('data/processed/monthly_surplus.csv')
latest      = df.iloc[-1]
prediction  = {
    'predicted_surplus' : latest['predicted_surplus'],
    'lpi'               : latest['lpi'],
    'core_team_pct'     : latest['core_team_pct'],
    'predicted_loan'    : latest['predicted_loan']
}
plan = allocate_surplus(prediction['predicted_surplus'], priorities, current_reserve, RESERVE_TARGET)
```

### Git Workflow

- `main` — stable, tested code only. Never push broken code here.
- `person-a` — Person A's development branch
- `person-b` — Person B's development branch
- Merge to `main` via pull request once each module passes basic tests

---

## 13. Build Order

Follow this order to avoid integration blockers:

| Step | Person | Task | Output |
|---|---|---|---|
| 1 | Both | Agree on CSV column names in `config.py` | Shared data contract |
| 2 | A | `data_cleaning.py` — load and validate all CSVs | Clean DataFrames |
| 3 | A | `attendance_module.py` — deduction logic | `monthly_salary_cost()` |
| 4 | A | `surplus_calculator.py` — combine all surplus sources | `monthly_surplus.csv` |
| 5 | B | `shared/loan_pressure.py` — LPI + pressure bands + lever | `calculate_loan_pressure()` |
| 6 | B | `allocation_engine.py` — priority allocator | `allocate_surplus()` |
| 7 | A | `prediction_model.py` — 4-layer pipeline + ML API | Full prediction dict |
| 8 | B | `loan_tracker.py` — running balance + timeline | Loan reduction tracker |
| 9 | B | `dashboard.py` — charts and summary tables | Monthly report output |
| 10 | Both | `main.py` — wire all modules end to end | Full working pipeline |

---

## 14. Config Reference

`shared/config.py` — both developers coordinate on these values before coding starts.

```python
# ── Attendance ──────────────────────────────────────────
ALLOWED_LATE_DAYS       = 7
WORKING_DAYS_PER_MONTH  = 30

# ── Budget Split ────────────────────────────────────────
HR_COST_PCT             = 0.05    # fixed
ADMIN_PCT               = 0.05    # fixed
CORE_TEAM_PCT_DEFAULT   = 0.05    # adjustable: 0.03 / 0.04 / 0.05
PROJECT_FUND_PCT        = 0.85    # when core team at full 5%

# ── Loan Pressure ───────────────────────────────────────
MAX_LOAN_LIMIT          = 500000  # update to company's actual limit
RESERVE_TARGET          = 100000  # minimum emergency reserve

# ── Reallocation Priorities ─────────────────────────────
LOAN_REPAYMENT_FRACTION = 0.5     # 50% of post-reserve surplus → loan repayment
PROJECT_WEIGHTS         = {
    'project_alpha': 0.30,
    'project_beta' : 0.20,
}

# ── Prediction ──────────────────────────────────────────
AVG_PROJECT_BUDGET      = 200000  # update with real average
AVG_PROJECT_DURATION    = 6       # months

# ── Model Selection ─────────────────────────────────────
# Automatically chosen based on data size (see prediction_model.py)
# < 24 months  → ML API
# 24-36 months → ARIMA
# 36+ months   → SARIMA (m=12)
```

---

## 15. Requirements

### Python packages (`requirements.txt`)

```
pandas
numpy
scikit-learn
statsmodels
prophet
matplotlib
seaborn
anthropic
python-dotenv
```

### Install

```bash
pip install -r requirements.txt
```

### Environment Variables (`.env`)

```
ANTHROPIC_API_KEY=your_key_here
```

```python
# In prediction_model.py
from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic()   # picks up key from environment automatically
```

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Forecasting model | ML API (Claude) now, SARIMA later | Only 12 months of data — insufficient for local model training |
| Minimum data for Linear Regression | 30+ points (10× features) | With 4-5 features, need 40-50 months — not yet available |
| Attendance threshold | 7 allowed late days | Hardcoded in `config.py` as `ALLOWED_LATE_DAYS` |
| Core team range | 3–5% (adjustable) | 1-2% recovery under loan pressure without affecting project quality |
| Reallocation priority | Reserve → Loan → Projects | Stability first, then debt reduction, then growth |
| Repo structure | Single repo, two branches | Cleaner integration, shared `config.py` and `shared/` modules |
| Handoff file | `monthly_surplus.csv` | Clean separation between Person A (compute) and Person B (allocate) |
| LPI weights | Utilization 30%, Coverage 30%, Frequency 20%, Repayment 20% | Debt level and coverage are most actionable signals |

---

*SurplusIQ — making the company self-sufficient, one recovered rupee at a time.*
