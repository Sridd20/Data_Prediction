import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.fund_pressure import get_core_team_pct
from shared import config

def get_adjusted_budget(total_budget, fpi):
    core_pct    = get_core_team_pct(fpi)
    admin_pct   = config.ADMIN_PCT
    hr_pct      = config.HR_COST_PCT
    project_pct = 1.0 - core_pct - admin_pct - hr_pct

    return {
        'project_fund': total_budget * project_pct,   # 85-87%
        'core_team'   : total_budget * core_pct,       # 3-5%
        'admin'       : total_budget * admin_pct,       # 5%
        'hr_cost'     : total_budget * hr_pct           # 5%
    }

def allocate_surplus(predicted_surplus, priorities, current_reserve, reserve_target):
    allocation = {}
    remaining  = predicted_surplus

    # Priority 1: Emergency Reserve
    reserve_gap              = max(0, reserve_target - current_reserve)
    allocation['reserve']    = min(remaining, reserve_gap)
    remaining               -= allocation['reserve']

    # Priority 2: Fund Repayment
    fund_fraction            = priorities.get('fund_fraction', config.FUND_REPAYMENT_FRACTION)
    allocation['fund']       = remaining * fund_fraction
    remaining               -= allocation['fund']

    # Priority 3 & 4: Projects
    project_weights = priorities.get('projects', config.PROJECT_WEIGHTS)
    for project, weight in project_weights.items():
        allocation[project]  = remaining * weight

    return allocation
