"""
Financial calculations for bioenergy projects.
Includes NPV, payback, ROI, and cashflow analysis.
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from bia_core.schemas import FinancialParameters, CashflowItem, NPVResults
from bia_core import INR_CRORE, CO2_PER_KWH_KG

class FinanceCalculator:
    """Financial calculator for bioenergy projects"""
    
    def __init__(self, yield_rate: float, capacity_factor: float, tariff: float,
                 opex_per_ton: float, fixed_opex: float, capex: float, 
                 discount_rate: float):
        """
        Initialize finance calculator
        
        Args:
            yield_rate: Energy yield in kWh/ton
            capacity_factor: Plant capacity factor (0-1)
            tariff: Electricity tariff in ₹/kWh
            opex_per_ton: Variable OPEX in ₹/ton
            fixed_opex: Fixed OPEX in ₹/year
            capex: Capital expenditure in ₹
            discount_rate: Discount rate (0-1)
        """
        self.yield_rate = yield_rate
        self.capacity_factor = capacity_factor
        self.tariff = tariff
        self.opex_per_ton = opex_per_ton
        self.fixed_opex = fixed_opex
        self.capex = capex
        self.discount_rate = discount_rate
    
    def calculate_annual_metrics(self, daily_waste_tons: float, year: int, 
                               growth_rate: float = 0.02) -> Dict[str, float]:
        """Calculate annual metrics for a given year"""
        
        # Calculate waste for this year with growth
        annual_waste_tons = daily_waste_tons * 365 * ((1 + growth_rate) ** (year - 1))
        
        # Energy generation
        annual_kwh = annual_waste_tons * self.yield_rate * self.capacity_factor
        
        # Revenue
        annual_revenue = annual_kwh * self.tariff
        
        # Operating expenses
        variable_opex = annual_waste_tons * self.opex_per_ton
        total_opex = variable_opex + self.fixed_opex
        
        # Net cash flow
        ncf = annual_revenue - total_opex
        
        return {
            'year': year,
            'waste_tons': annual_waste_tons,
            'electricity_kwh': annual_kwh,
            'revenue': annual_revenue,
            'variable_opex': variable_opex,
            'fixed_opex': self.fixed_opex,
            'total_opex': total_opex,
            'ncf': ncf
        }
    
    def calculate_cashflows(self, daily_waste_tons: float, horizon_years: int,
                          growth_rate: float = 0.02) -> List[Dict[str, float]]:
        """Calculate cashflows for project horizon"""
        
        cashflows = []
        
        for year in range(1, horizon_years + 1):
            annual_metrics = self.calculate_annual_metrics(
                daily_waste_tons, year, growth_rate
            )
            
            cashflow_item = {
                'year': year,
                'waste_tons': annual_metrics['waste_tons'],
                'electricity_kwh': annual_metrics['electricity_kwh'],
                'revenue': annual_metrics['revenue'],
                'opex': annual_metrics['total_opex'],
                'ncf': annual_metrics['ncf']
            }
            
            cashflows.append(cashflow_item)
        
        return cashflows
    
    def calculate_npv(self, daily_waste_tons: float, horizon_years: int,
                      growth_rate: float = 0.02) -> float:
        """Calculate Net Present Value"""
        
        cashflows = self.calculate_cashflows(daily_waste_tons, horizon_years, growth_rate)
        
        # Calculate discounted cash flows
        npv = -self.capex  # Initial investment
        
        for cf in cashflows:
            year = cf['year']
            discounted_ncf = cf['ncf'] / ((1 + self.discount_rate) ** year)
            npv += discounted_ncf
        
        return npv
    
    def calculate_payback(self, daily_waste_tons: float, horizon_years: int,
                         growth_rate: float = 0.02) -> float:
        """Calculate payback period in years"""
        
        cashflows = self.calculate_cashflows(daily_waste_tons, horizon_years, growth_rate)
        
        cumulative_ncf = 0
        
        for cf in cashflows:
            cumulative_ncf += cf['ncf']
            
            if cumulative_ncf >= self.capex:
                # Linear interpolation for more precise payback
                prev_cumulative = cumulative_ncf - cf['ncf']
                remaining_recovery = self.capex - prev_cumulative
                year_fraction = remaining_recovery / cf['ncf']
                
                return cf['year'] - 1 + year_fraction
        
        return float('inf')  # Payback not achieved within horizon
    
    def calculate_roi(self, daily_waste_tons: float, horizon_years: int,
                      growth_rate: float = 0.02) -> float:
        """Calculate Return on Investment percentage"""
        
        cashflows = self.calculate_cashflows(daily_waste_tons, horizon_years, growth_rate)
        
        total_ncf = sum(cf['ncf'] for cf in cashflows)
        
        if self.capex > 0:
            roi = (total_ncf / self.capex) * 100
        else:
            roi = 0
        
        return roi
    
    def calculate_irr(self, daily_waste_tons: float, horizon_years: int,
                      growth_rate: float = 0.02) -> float:
        """Calculate Internal Rate of Return using approximation"""
        
        cashflows = self.calculate_cashflows(daily_waste_tons, horizon_years, growth_rate)
        
        # Simple IRR approximation
        total_ncf = sum(cf['ncf'] for cf in cashflows)
        avg_annual_ncf = total_ncf / horizon_years
        
        if self.capex > 0:
            irr_approx = (avg_annual_ncf / self.capex) * 100
        else:
            irr_approx = 0
        
        return max(0, irr_approx)
    
    def calculate_environmental_impact(self, daily_waste_tons: float, 
                                     horizon_years: int,
                                     growth_rate: float = 0.02) -> Dict[str, float]:
        """Calculate environmental impact metrics"""
        
        cashflows = self.calculate_cashflows(daily_waste_tons, horizon_years, growth_rate)
        
        # Total electricity generation
        total_kwh = sum(cf['electricity_kwh'] for cf in cashflows)
        
        # CO2 savings (kg CO2/kWh)
        co2_savings_kg = total_kwh * CO2_PER_KWH_KG
        co2_savings_tons = co2_savings_kg / 1000
        
        # Tree equivalent (1 tree = 20 kg CO2/year, project lifetime average)
        trees_equivalent = int(co2_savings_tons * 50)  # Conservative estimate
        
        return {
            'total_electricity_kwh': total_kwh,
            'co2_savings_kg': co2_savings_kg,
            'co2_savings_tons': co2_savings_tons,
            'trees_equivalent': trees_equivalent
        }
    
    def sensitivity_analysis(self, daily_waste_tons: float, horizon_years: int,
                           parameter_variations: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """Perform sensitivity analysis on key parameters"""
        
        results = {}
        base_npv = self.calculate_npv(daily_waste_tons, horizon_years)
        
        for param_name, variations in parameter_variations.items():
            npv_variations = []
            
            for variation in variations:
                # Create modified calculator
                modified_calc = self._create_modified_calculator(param_name, variation)
                modified_npv = modified_calc.calculate_npv(daily_waste_tons, horizon_years)
                npv_variations.append(modified_npv)
            
            results[param_name] = npv_variations
        
        return results
    
    def _create_modified_calculator(self, param_name: str, value: float) -> 'FinanceCalculator':
        """Create calculator with modified parameter"""
        
        params = {
            'yield_rate': self.yield_rate,
            'capacity_factor': self.capacity_factor,
            'tariff': self.tariff,
            'opex_per_ton': self.opex_per_ton,
            'fixed_opex': self.fixed_opex,
            'capex': self.capex,
            'discount_rate': self.discount_rate
        }
        
        if param_name in params:
            params[param_name] = value
        
        return FinanceCalculator(**params)
    
    def generate_financial_summary(self, daily_waste_tons: float, horizon_years: int,
                                 growth_rate: float = 0.02) -> Dict[str, Any]:
        """Generate comprehensive financial summary"""
        
        # Core metrics
        npv = self.calculate_npv(daily_waste_tons, horizon_years, growth_rate)
        payback = self.calculate_payback(daily_waste_tons, horizon_years, growth_rate)
        roi = self.calculate_roi(daily_waste_tons, horizon_years, growth_rate)
        irr = self.calculate_irr(daily_waste_tons, horizon_years, growth_rate)
        
        # Environmental impact
        env_impact = self.calculate_environmental_impact(daily_waste_tons, horizon_years, growth_rate)
        
        # Cashflow summary
        cashflows = self.calculate_cashflows(daily_waste_tons, horizon_years, growth_rate)
        total_revenue = sum(cf['revenue'] for cf in cashflows)
        total_opex = sum(cf['opex'] for cf in cashflows)
        
        return {
            'financial_metrics': {
                'npv': npv,
                'payback_years': payback,
                'roi_percent': roi,
                'irr_percent': irr,
                'total_revenue': total_revenue,
                'total_opex': total_opex,
                'total_ncf': total_revenue - total_opex
            },
            'environmental_impact': env_impact,
            'project_parameters': {
                'daily_waste_tons': daily_waste_tons,
                'horizon_years': horizon_years,
                'growth_rate': growth_rate,
                'capex': self.capex,
                'yield_rate': self.yield_rate,
                'capacity_factor': self.capacity_factor,
                'tariff': self.tariff
            }
        }
    
    def get_key_assumptions(self) -> Dict[str, Any]:
        """Get key financial assumptions"""
        
        return {
            'technical_assumptions': {
                'yield_rate_kwh_per_ton': self.yield_rate,
                'capacity_factor_percent': self.capacity_factor * 100,
                'plant_availability': '24/7 operation assumed'
            },
            'financial_assumptions': {
                'tariff_inr_per_kwh': self.tariff,
                'discount_rate_percent': self.discount_rate * 100,
                'inflation_rate': 'Not explicitly modeled',
                'tax_considerations': 'Not included in current model'
            },
            'operating_assumptions': {
                'opex_per_ton_inr': self.opex_per_ton,
                'fixed_opex_inr_per_year': self.fixed_opex,
                'escalation_rates': 'Constant real terms assumed'
            },
            'environmental_assumptions': {
                'co2_emission_factor': f'{CO2_PER_KWH_KG} kg CO2/kWh',
                'grid_displacement': 'Full grid electricity displacement assumed',
                'tree_equivalency': '1 tree = 20 kg CO2/year sequestration'
            }
        }
