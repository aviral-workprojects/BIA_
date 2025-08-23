"""
Data input/output operations for BIA application.
Handles loading and processing of curated datasets.
"""

import pandas as pd
import os
from typing import Dict, Any
import streamlit as st

@st.cache_data
def load_curated_data() -> Dict[str, pd.DataFrame]:
    """Load all curated data files"""
    
    data = {}
    
    # Define data files
    data_files = {
        'city_stats': 'data/curated/city_stats.csv',
        'facilities': 'data/curated/facilities.csv',
        'tariffs': 'data/curated/tariffs.csv',
        'costs': 'data/curated/costs.csv'
    }
    
    for key, filepath in data_files.items():
        try:
            if os.path.exists(filepath):
                data[key] = pd.read_csv(filepath)
            else:
                # Create empty dataframe with expected structure
                data[key] = create_empty_dataframe(key)
        except Exception as e:
            st.warning(f"Could not load {filepath}: {str(e)}")
            data[key] = create_empty_dataframe(key)
    
    return data

def create_empty_dataframe(data_type: str) -> pd.DataFrame:
    """Create empty dataframe with expected structure"""
    
    if data_type == 'city_stats':
        return pd.DataFrame(columns=[
            'city', 'population', 'waste_generation_tpd', 
            'organic_fraction', 'industrial_fraction', 'agricultural_fraction'
        ])
    
    elif data_type == 'facilities':
        return pd.DataFrame(columns=[
            'name', 'city', 'state', 'type', 'capacity_mw', 
            'status', 'lat', 'lon', 'source'
        ])
    
    elif data_type == 'tariffs':
        return pd.DataFrame(columns=[
            'city', 'state', 'tariff_residential', 'tariff_commercial', 
            'tariff_industrial', 'renewable_tariff'
        ])
    
    elif data_type == 'costs':
        return pd.DataFrame(columns=[
            'technology', 'capex_per_mw', 'opex_per_mwh', 
            'capacity_factor', 'lifetime_years'
        ])
    
    else:
        return pd.DataFrame()

def get_city_data(city: str) -> Dict[str, Any]:
    """Get data specific to a city"""
    
    curated_data = load_curated_data()
    
    city_info = {
        'city': city,
        'population': None,
        'waste_generation_tpd': None,
        'tariff': 4.5,  # Default tariff
        'facilities_count': 0
    }
    
    # Get city statistics
    city_stats = curated_data['city_stats']
    if not city_stats.empty:
        city_row = city_stats[city_stats['city'] == city]
        if not city_row.empty:
            city_info.update(city_row.iloc[0].to_dict())
    
    # Get tariff information
    tariffs = curated_data['tariffs']
    if not tariffs.empty:
        tariff_row = tariffs[tariffs['city'] == city]
        if not tariff_row.empty:
            city_info['tariff'] = tariff_row.iloc[0].get('renewable_tariff', 4.5)
    
    # Count facilities
    facilities = curated_data['facilities']
    if not facilities.empty:
        city_facilities = facilities[facilities['city'] == city]
        city_info['facilities_count'] = len(city_facilities)
    
    return city_info

def export_user_data(username: str, data: Dict[str, Any]) -> str:
    """Export user data to JSON format"""
    import json
    from datetime import datetime
    
    export_data = {
        'username': username,
        'export_timestamp': datetime.now().isoformat(),
        'data': data
    }
    
    return json.dumps(export_data, indent=2, default=str)
