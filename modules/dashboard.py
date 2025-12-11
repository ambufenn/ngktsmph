# Household dashboard helpers (mocked computations)
import json, os
def household_summary(household):
    # read tokens and ledger to compute stats
    return {'total_kg':42.3, 'by_category':{'Plastik':20,'Kertas':10,'Logam':12}, 'estimated_co2_saved_kg':15.2, 'monthly_income':42000}
