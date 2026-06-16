from datetime import datetime
import calendar


dt=datetime.now()
month = calendar.monthrange(dt.year,dt.month)[1]

print(month)
def eff_att(late_count,month):
    return month- max(0,late_count-7)
    
def adj_sal(base_sal):
    return ((base_sal/month)*eff_att(late_count,month))

late_count=8
base_salary=31762   

print(adj_sal(base_salary))