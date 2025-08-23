"""
BIA Core - Bio-energy Intelligence Application Core Module

This module contains the core business logic for the BIA application including:
- Data models and schemas
- Forecasting models
- Financial calculations
- Mapping functionality
- Utility functions
"""

__version__ = "1.0.0"
__author__ = "BIA Development Team"

# Core constants
INR_CRORE = 1e7
CO2_PER_KWH_KG = 0.9
SUPPORTED_CITIES = [
    "Ahmedabad", "Gandhinagar", "Indore", "Delhi", 
    "Mumbai", "Pune", "Bengaluru", "Chennai"
]
WASTE_TYPES = ["organic", "industrial", "agricultural"]
