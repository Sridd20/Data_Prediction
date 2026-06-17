import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import config

class FundTracker:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.history = []

    def make_payment(self, amount, date):
        payment = min(self.balance, amount)
        self.balance -= payment
        self.history.append({'date': date, 'payment': payment, 'balance': self.balance})
        return payment

    def get_balance(self):
        return self.balance
        
    def estimate_months_remaining(self):
        if not self.history:
            return None
        
        total_paid = sum(h['payment'] for h in self.history)
        avg_payment = total_paid / len(self.history)
        
        if avg_payment <= 0:
            return None
            
        return self.balance / avg_payment

def compute_projects_to_zero_fund(fund_required, avg_budget=None, avg_duration=None):
    """
    Computes how many new projects would need to be started to offset the 
    required fund amount purely through their monthly HR deductions.
    """
    if avg_budget is None:
        avg_budget = config.AVG_PROJECT_BUDGET
    if avg_duration is None:
        avg_duration = config.AVG_PROJECT_DURATION

    if fund_required <= 0:
        return 0
        
    hr_per_project = (avg_budget * 0.05) / avg_duration
    
    # Using integer division with rounding up approach 
    # as described in the README `round(fund_required / hr_per_project + 0.5)`
    import math
    return math.ceil(fund_required / hr_per_project)
