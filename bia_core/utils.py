"""
Utility functions for BIA application.
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union
import re
from datetime import datetime, date
import json

def format_currency(amount: float, currency: str = "₹") -> str:
    """Format currency with Indian number system"""
    
    if pd.isna(amount) or amount == 0:
        return f"{currency}0"
    
    # Convert to absolute value for formatting
    abs_amount = abs(amount)
    sign = "-" if amount < 0 else ""
    
    # Format based on magnitude
    if abs_amount >= 1e7:  # Crores
        formatted = f"{abs_amount/1e7:.1f} Cr"
    elif abs_amount >= 1e5:  # Lakhs
        formatted = f"{abs_amount/1e5:.1f} L"
    elif abs_amount >= 1e3:  # Thousands
        formatted = f"{abs_amount/1e3:.1f}K"
    else:
        formatted = f"{abs_amount:.0f}"
    
    return f"{sign}{currency}{formatted}"

def format_number(number: float, precision: int = 1) -> str:
    """Format large numbers with K, M, B suffixes"""
    
    if pd.isna(number) or number == 0:
        return "0"
    
    abs_number = abs(number)
    sign = "-" if number < 0 else ""
    
    if abs_number >= 1e9:
        return f"{sign}{abs_number/1e9:.{precision}f}B"
    elif abs_number >= 1e6:
        return f"{sign}{abs_number/1e6:.{precision}f}M"
    elif abs_number >= 1e3:
        return f"{sign}{abs_number/1e3:.{precision}f}K"
    else:
        return f"{sign}{abs_number:.{precision}f}"

def validate_range(value: float, min_val: float, max_val: float, 
                  param_name: str) -> bool:
    """Validate if value is within acceptable range"""
    
    if pd.isna(value):
        return False
    
    if value < min_val or value > max_val:
        return False
    
    return True

def clean_string(text: str) -> str:
    """Clean and normalize string input"""
    
    if not isinstance(text, str):
        return str(text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters (keep alphanumeric, spaces, hyphens, underscores)
    text = re.sub(r'[^\w\s\-]', '', text)
    
    return text

def safe_divide(numerator: float, denominator: float, 
               default: float = 0.0) -> float:
    """Safely divide two numbers, return default if division by zero"""
    
    if pd.isna(numerator) or pd.isna(denominator):
        return default
    
    if denominator == 0:
        return default
    
    return numerator / denominator

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    
    if pd.isna(old_value) or pd.isna(new_value):
        return 0.0
    
    if old_value == 0:
        return 100.0 if new_value > 0 else 0.0
    
    return ((new_value - old_value) / old_value) * 100

def interpolate_missing_values(series: pd.Series, method: str = 'linear') -> pd.Series:
    """Interpolate missing values in a pandas series"""
    
    if series.empty:
        return series
    
    if method == 'linear':
        return series.interpolate(method='linear')
    elif method == 'forward':
        return series.fillna(method='ffill')
    elif method == 'backward':
        return series.fillna(method='bfill')
    else:
        return series.fillna(0)

def create_date_range(start_date: Union[str, date], 
                     end_date: Union[str, date],
                     freq: str = 'D') -> pd.DatetimeIndex:
    """Create date range between two dates"""
    
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).date()
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).date()
    
    return pd.date_range(start=start_date, end=end_date, freq=freq)

def export_data_to_csv(data: Union[pd.DataFrame, Dict], 
                      filename: str = None) -> str:
    """Export data to CSV format"""
    
    if isinstance(data, dict):
        df = pd.DataFrame(data)
    else:
        df = data.copy()
    
    return df.to_csv(index=False)

def export_data_to_json(data: Any, filename: str = None) -> str:
    """Export data to JSON format"""
    
    if isinstance(data, pd.DataFrame):
        data_dict = data.to_dict(orient='records')
    else:
        data_dict = data
    
    return json.dumps(data_dict, indent=2, default=str)

def validate_email(email: str) -> bool:
    """Validate email format"""
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate Indian phone number format"""
    
    # Remove spaces and special characters
    clean_phone = re.sub(r'[^\d]', '', phone)
    
    # Check if it's 10 digits or 10 digits with country code
    if len(clean_phone) == 10:
        return clean_phone.startswith(('6', '7', '8', '9'))
    elif len(clean_phone) == 12:
        return clean_phone.startswith('91') and clean_phone[2:].startswith(('6', '7', '8', '9'))
    
    return False

def calculate_working_days(start_date: date, end_date: date) -> int:
    """Calculate number of working days between two dates"""
    
    if start_date > end_date:
        return 0
    
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    working_days = len([d for d in date_range if d.weekday() < 5])  # Monday=0, Sunday=6
    
    return working_days

def round_to_significant_figures(number: float, sig_figs: int = 3) -> float:
    """Round number to specified significant figures"""
    
    if number == 0:
        return 0
    
    return round(number, -int(np.floor(np.log10(abs(number)))) + (sig_figs - 1))

def detect_outliers(series: pd.Series, method: str = 'iqr', 
                   threshold: float = 1.5) -> pd.Series:
    """Detect outliers in a pandas series"""
    
    if series.empty:
        return pd.Series([], dtype=bool)
    
    if method == 'iqr':
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        outliers = (series < lower_bound) | (series > upper_bound)
        
    elif method == 'zscore':
        z_scores = np.abs((series - series.mean()) / series.std())
        outliers = z_scores > threshold
        
    else:
        outliers = pd.Series([False] * len(series), index=series.index)
    
    return outliers

def create_summary_statistics(df: pd.DataFrame, 
                            columns: List[str] = None) -> pd.DataFrame:
    """Create summary statistics for dataframe columns"""
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    summary_stats = []
    
    for col in columns:
        if col in df.columns:
            stats = {
                'Column': col,
                'Count': df[col].count(),
                'Mean': df[col].mean(),
                'Std': df[col].std(),
                'Min': df[col].min(),
                '25%': df[col].quantile(0.25),
                '50%': df[col].median(),
                '75%': df[col].quantile(0.75),
                'Max': df[col].max(),
                'Missing': df[col].isna().sum(),
                'Outliers': detect_outliers(df[col]).sum()
            }
            summary_stats.append(stats)
    
    return pd.DataFrame(summary_stats)

def generate_color_palette(n_colors: int, palette: str = 'viridis') -> List[str]:
    """Generate color palette for visualizations"""
    
    import matplotlib.pyplot as plt
    
    if palette in plt.colormaps():
        cmap = plt.get_cmap(palette)
        colors = [cmap(i / (n_colors - 1)) for i in range(n_colors)]
        # Convert to hex
        hex_colors = ['#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255)) 
                     for r, g, b, a in colors]
        return hex_colors
    else:
        # Default colors
        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', 
                         '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', 
                         '#bcbd22', '#17becf']
        return (default_colors * (n_colors // len(default_colors) + 1))[:n_colors]

def log_performance(func_name: str, execution_time: float, 
                   data_size: int = None) -> Dict[str, Any]:
    """Log performance metrics for functions"""
    
    log_entry = {
        'function': func_name,
        'execution_time_seconds': execution_time,
        'timestamp': datetime.now().isoformat()
    }
    
    if data_size is not None:
        log_entry['data_size'] = data_size
        log_entry['performance_ratio'] = data_size / execution_time if execution_time > 0 else 0
    
    return log_entry

def create_backup_filename(base_name: str, extension: str = '.csv') -> str:
    """Create backup filename with timestamp"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    clean_base = clean_string(base_name)
    
    return f"{clean_base}_backup_{timestamp}{extension}"

class ConfigManager:
    """Simple configuration manager"""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        self.config = config_dict or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return self.config.copy()
    
    def from_dict(self, config_dict: Dict[str, Any]):
        """Import configuration from dictionary"""
        self.config = config_dict.copy()
