"""
Feature engineering for forecasting models.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime, timedelta

def create_forecast_features(df_logs: pd.DataFrame) -> pd.DataFrame:
    """Create features for forecasting models"""
    
    if df_logs.empty:
        return pd.DataFrame()
    
    # Ensure date column is datetime
    df = df_logs.copy()
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    # Aggregate by date (in case multiple logs per day)
    daily_data = df.groupby('date')['waste_tons'].sum().reset_index()
    
    # Fill missing dates
    if len(daily_data) > 1:
        date_range = pd.date_range(
            start=daily_data['date'].min(),
            end=daily_data['date'].max(),
            freq='D'
        )
        
        full_df = pd.DataFrame({'date': date_range})
        daily_data = full_df.merge(daily_data, on='date', how='left')
        daily_data['waste_tons'] = daily_data['waste_tons'].fillna(0)
    
    # Create time-based features
    daily_data['day_of_week'] = daily_data['date'].dt.dayofweek
    daily_data['day_of_month'] = daily_data['date'].dt.day
    daily_data['month'] = daily_data['date'].dt.month
    daily_data['quarter'] = daily_data['date'].dt.quarter
    
    # Create lag features
    for lag in [1, 7, 30]:
        if len(daily_data) > lag:
            daily_data[f'waste_lag_{lag}'] = daily_data['waste_tons'].shift(lag)
    
    # Rolling averages
    for window in [7, 14, 30]:
        if len(daily_data) >= window:
            daily_data[f'waste_ma_{window}'] = daily_data['waste_tons'].rolling(
                window=window, min_periods=1
            ).mean()
    
    # Trend features
    daily_data['days_since_start'] = (
        daily_data['date'] - daily_data['date'].min()
    ).dt.days
    
    # Growth rate (if enough data)
    if len(daily_data) > 7:
        daily_data['growth_rate_7d'] = (
            daily_data['waste_tons'] / daily_data['waste_tons'].shift(7) - 1
        ).fillna(0)
    
    # Cumulative features
    daily_data['cumulative_waste'] = daily_data['waste_tons'].cumsum()
    
    # Seasonality indicators
    daily_data['is_weekend'] = daily_data['day_of_week'].isin([5, 6]).astype(int)
    daily_data['is_month_start'] = (daily_data['day_of_month'] <= 5).astype(int)
    daily_data['is_month_end'] = (daily_data['day_of_month'] >= 25).astype(int)
    
    return daily_data

def prepare_sarima_data(features_df: pd.DataFrame) -> pd.Series:
    """Prepare data for SARIMA modeling"""
    
    if features_df.empty:
        return pd.Series()
    
    # Create time series with date index
    ts_data = features_df.set_index('date')['waste_tons']
    
    # Handle missing values
    ts_data = ts_data.fillna(method='ffill').fillna(0)
    
    return ts_data

def calculate_baseline_growth(features_df: pd.DataFrame) -> float:
    """Calculate baseline growth rate for deterministic model"""
    
    if len(features_df) < 7:
        return 0.02  # Default 2% growth
    
    # Calculate growth from first week to last week
    first_week_avg = features_df['waste_tons'][:7].mean()
    last_week_avg = features_df['waste_tons'][-7:].mean()
    
    if first_week_avg > 0:
        total_days = len(features_df)
        total_growth = (last_week_avg / first_week_avg) - 1
        daily_growth = (1 + total_growth) ** (1/total_days) - 1
        
        # Cap growth rate to reasonable bounds
        daily_growth = max(-0.01, min(0.01, daily_growth))
        
        return daily_growth
    
    return 0.002  # Default 0.2% daily growth

def extract_seasonality_patterns(features_df: pd.DataFrame) -> Dict[str, float]:
    """Extract seasonality patterns from historical data"""
    
    patterns = {
        'weekend_factor': 1.0,
        'month_start_factor': 1.0,
        'month_end_factor': 1.0,
        'quarterly_factors': [1.0, 1.0, 1.0, 1.0]
    }
    
    if len(features_df) < 30:
        return patterns
    
    # Weekend vs weekday pattern
    weekend_avg = features_df[features_df['is_weekend'] == 1]['waste_tons'].mean()
    weekday_avg = features_df[features_df['is_weekend'] == 0]['waste_tons'].mean()
    
    if weekday_avg > 0:
        patterns['weekend_factor'] = weekend_avg / weekday_avg
    
    # Month start/end patterns
    month_start_avg = features_df[features_df['is_month_start'] == 1]['waste_tons'].mean()
    month_end_avg = features_df[features_df['is_month_end'] == 1]['waste_tons'].mean()
    overall_avg = features_df['waste_tons'].mean()
    
    if overall_avg > 0:
        patterns['month_start_factor'] = month_start_avg / overall_avg
        patterns['month_end_factor'] = month_end_avg / overall_avg
    
    # Quarterly patterns
    for quarter in range(1, 5):
        quarter_data = features_df[features_df['quarter'] == quarter]['waste_tons']
        if len(quarter_data) > 0 and overall_avg > 0:
            patterns['quarterly_factors'][quarter-1] = quarter_data.mean() / overall_avg
    
    return patterns

def create_forecast_dates(last_date: pd.Timestamp, forecast_days: int) -> pd.DatetimeIndex:
    """Create forecast date range"""
    
    start_date = last_date + pd.Timedelta(days=1)
    end_date = start_date + pd.Timedelta(days=forecast_days-1)
    
    return pd.date_range(start=start_date, end=end_date, freq='D')

def validate_forecast_inputs(features_df: pd.DataFrame, forecast_days: int) -> bool:
    """Validate inputs for forecasting"""
    
    if features_df.empty:
        return False
    
    if forecast_days < 1 or forecast_days > 365:
        return False
    
    if 'waste_tons' not in features_df.columns:
        return False
    
    if features_df['waste_tons'].isna().all():
        return False
    
    return True
