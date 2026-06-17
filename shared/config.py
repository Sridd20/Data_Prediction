# shared/config.py

# ── Attendance ──────────────────────────────────────────
ALLOWED_LATE_DAYS       = 7
SICK_LEAVES_PER_YEAR    = 8
CASUAL_LEAVES_PER_MONTH = 1

# ── Budget Split ────────────────────────────────────────
HR_COST_PCT             = 0.05    # fixed
ADMIN_PCT               = 0.05    # fixed
CORE_TEAM_PCT_DEFAULT   = 0.05    # adjustable: 0.03 / 0.04 / 0.05
PROJECT_FUND_PCT        = 0.85    # when core team at full 5%

# ── External Fund Pressure ──────────────────────────────
MAX_FUND_LIMIT          = 500000  # update to company's actual limit
RESERVE_TARGET          = 100000  # minimum emergency reserve

# ── Reallocation Priorities ─────────────────────────────
FUND_REPAYMENT_FRACTION = 0.5     # 50% of post-reserve surplus → fund repayment
PROJECT_WEIGHTS         = {
    'project_alpha': 0.30,
    'project_beta' : 0.20,
}

# ── Prediction ──────────────────────────────────────────
AVG_PROJECT_BUDGET      = 200000  # update with real average
AVG_PROJECT_DURATION    = 6       # months
