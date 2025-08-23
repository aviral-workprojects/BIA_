"""
Model evaluation functions for forecasting models.
Includes backtesting and performance metrics.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from bia_core.models import BaseModel

def calculate_mape(actual: List[float], predicted: List[float]) -> float:
    """Calculate Mean Absolute Percentage Error"""
    
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted arrays must have same length")
    
    if len(actual) == 0:
        return float('inf')
    
    # Handle zeros in actual values
    actual_array = np.array(actual)
    predicted_array = np.array(predicted)
    
    # Only consider non-zero actual values
    non_zero_mask = actual_array != 0
    
    if not non_zero_mask.any():
        # If all actual values are zero, use MAE instead
        return calculate_mae(actual, predicted)
    
    # Calculate MAPE only for non-zero values
    actual_nz = actual_array[non_zero_mask]
    predicted_nz = predicted_array[non_zero_mask]
    
    mape = np.mean(np.abs((actual_nz - predicted_nz) / actual_nz)) * 100
    
    return mape

def calculate_mae(actual: List[float], predicted: List[float]) -> float:
    """Calculate Mean Absolute Error"""
    
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted arrays must have same length")
    
    actual_array = np.array(actual)
    predicted_array = np.array(predicted)
    
    mae = np.mean(np.abs(actual_array - predicted_array))
    
    return mae

def calculate_rmse(actual: List[float], predicted: List[float]) -> float:
    """Calculate Root Mean Square Error"""
    
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted arrays must have same length")
    
    actual_array = np.array(actual)
    predicted_array = np.array(predicted)
    
    mse = np.mean((actual_array - predicted_array) ** 2)
    rmse = np.sqrt(mse)
    
    return rmse

def calculate_r2(actual: List[float], predicted: List[float]) -> float:
    """Calculate R-squared coefficient"""
    
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted arrays must have same length")
    
    actual_array = np.array(actual)
    predicted_array = np.array(predicted)
    
    # Calculate R-squared
    ss_res = np.sum((actual_array - predicted_array) ** 2)
    ss_tot = np.sum((actual_array - np.mean(actual_array)) ** 2)
    
    if ss_tot == 0:
        return 0.0  # Perfect fit if no variance in actual
    
    r2 = 1 - (ss_res / ss_tot)
    
    return r2

def backtest_model(model: BaseModel, features_df: pd.DataFrame, 
                   test_size: int = 7, min_train_size: int = 7) -> float:
    """
    Perform time series cross-validation backtesting
    
    Args:
        model: Fitted forecasting model
        features_df: Historical data
        test_size: Number of days to forecast in each test
        min_train_size: Minimum training size
    
    Returns:
        MAPE score from backtesting
    """
    
    if len(features_df) < min_train_size + test_size:
        return float('inf')
    
    all_actuals = []
    all_predictions = []
    
    # Sliding window backtesting
    max_train_end = len(features_df) - test_size
    
    for train_end in range(min_train_size, max_train_end + 1, test_size):
        # Split data
        train_data = features_df.iloc[:train_end].copy()
        test_data = features_df.iloc[train_end:train_end + test_size].copy()
        
        if len(test_data) == 0:
            continue
        
        try:
            # Fit model on training data
            model.fit(train_data)
            
            # Generate forecast
            forecast = model.predict(len(test_data))
            
            # Collect results
            actual_values = test_data['waste_tons'].tolist()
            all_actuals.extend(actual_values)
            all_predictions.extend(forecast[:len(actual_values)])
            
        except Exception as e:
            print(f"Backtest iteration failed: {e}")
            continue
    
    if len(all_actuals) == 0:
        return float('inf')
    
    # Calculate MAPE
    mape = calculate_mape(all_actuals, all_predictions)
    
    return mape

def evaluate_model_performance(model: BaseModel, features_df: pd.DataFrame,
                              test_split: float = 0.3) -> Dict[str, float]:
    """
    Comprehensive model evaluation
    
    Args:
        model: Forecasting model
        features_df: Historical data
        test_split: Fraction of data for testing
    
    Returns:
        Dictionary of performance metrics
    """
    
    if len(features_df) < 10:
        return {
            'mape': float('inf'),
            'mae': float('inf'),
            'rmse': float('inf'),
            'r2': 0.0,
            'data_points': len(features_df)
        }
    
    # Split data
    split_idx = int(len(features_df) * (1 - test_split))
    train_data = features_df.iloc[:split_idx].copy()
    test_data = features_df.iloc[split_idx:].copy()
    
    if len(test_data) == 0:
        return {
            'mape': float('inf'),
            'mae': float('inf'),
            'rmse': float('inf'),
            'r2': 0.0,
            'data_points': len(features_df)
        }
    
    try:
        # Fit model
        model.fit(train_data)
        
        # Generate predictions
        forecast = model.predict(len(test_data))
        actual = test_data['waste_tons'].tolist()
        
        # Calculate metrics
        mape = calculate_mape(actual, forecast)
        mae = calculate_mae(actual, forecast)
        rmse = calculate_rmse(actual, forecast)
        r2 = calculate_r2(actual, forecast)
        
        return {
            'mape': mape,
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'data_points': len(features_df),
            'test_points': len(test_data)
        }
        
    except Exception as e:
        print(f"Model evaluation failed: {e}")
        return {
            'mape': float('inf'),
            'mae': float('inf'),
            'rmse': float('inf'),
            'r2': 0.0,
            'data_points': len(features_df)
        }

def compare_models(models: List[BaseModel], features_df: pd.DataFrame) -> pd.DataFrame:
    """Compare performance of multiple models"""
    
    results = []
    
    for model in models:
        model_name = type(model).__name__
        
        try:
            # Evaluate model
            performance = evaluate_model_performance(model, features_df)
            
            # Add model info
            performance['model'] = model_name
            results.append(performance)
            
        except Exception as e:
            print(f"Failed to evaluate {model_name}: {e}")
            results.append({
                'model': model_name,
                'mape': float('inf'),
                'mae': float('inf'),
                'rmse': float('inf'),
                'r2': 0.0,
                'data_points': len(features_df)
            })
    
    # Create comparison dataframe
    comparison_df = pd.DataFrame(results)
    
    if not comparison_df.empty:
        comparison_df = comparison_df.sort_values('mape')
    
    return comparison_df

def forecast_confidence_interval(model: BaseModel, features_df: pd.DataFrame,
                               forecast_days: int, confidence_level: float = 0.95) -> Tuple[List[float], List[float], List[float]]:
    """
    Generate forecast with confidence intervals (simplified approach)
    
    Args:
        model: Fitted model
        features_df: Historical data
        forecast_days: Number of days to forecast
        confidence_level: Confidence level (e.g., 0.95 for 95%)
    
    Returns:
        Tuple of (forecast, lower_bound, upper_bound)
    """
    
    # Fit model
    model.fit(features_df)
    
    # Generate base forecast
    forecast = model.predict(forecast_days)
    
    # Calculate residuals for confidence interval estimation
    if len(features_df) >= 10:
        # Use recent data for residual calculation
        recent_data = features_df.tail(min(30, len(features_df)))
        
        # Simple residual-based confidence intervals
        predictions_for_residuals = []
        actuals_for_residuals = recent_data['waste_tons'].tolist()
        
        # Generate predictions for recent period
        for i in range(len(recent_data)):
            temp_train = recent_data.iloc[:max(1, i)].copy()
            if len(temp_train) > 0:
                temp_model = type(model)()
                temp_model.fit(temp_train)
                pred = temp_model.predict(1)
                predictions_for_residuals.append(pred[0] if pred else 0)
            else:
                predictions_for_residuals.append(0)
        
        # Calculate residual standard deviation
        residuals = np.array(actuals_for_residuals) - np.array(predictions_for_residuals)
        residual_std = np.std(residuals)
        
        # Z-score for confidence level
        from scipy import stats
        z_score = stats.norm.ppf((1 + confidence_level) / 2)
        
        # Calculate bounds
        margin = z_score * residual_std
        lower_bound = [max(0, f - margin) for f in forecast]
        upper_bound = [f + margin for f in forecast]
        
    else:
        # Use simple percentage bounds if insufficient data
        margin_pct = 0.2  # 20% margin
        lower_bound = [max(0, f * (1 - margin_pct)) for f in forecast]
        upper_bound = [f * (1 + margin_pct) for f in forecast]
    
    return forecast, lower_bound, upper_bound

def residual_analysis(model: BaseModel, features_df: pd.DataFrame) -> Dict[str, Any]:
    """Perform residual analysis for model diagnostics"""
    
    if len(features_df) < 10:
        return {'error': 'Insufficient data for residual analysis'}
    
    # Split data for out-of-sample residuals
    split_idx = int(len(features_df) * 0.7)
    train_data = features_df.iloc[:split_idx].copy()
    test_data = features_df.iloc[split_idx:].copy()
    
    try:
        # Fit model
        model.fit(train_data)
        
        # Generate predictions
        predictions = model.predict(len(test_data))
        actuals = test_data['waste_tons'].tolist()
        
        # Calculate residuals
        residuals = np.array(actuals) - np.array(predictions)
        
        # Residual statistics
        residual_stats = {
            'mean': np.mean(residuals),
            'std': np.std(residuals),
            'min': np.min(residuals),
            'max': np.max(residuals),
            'median': np.median(residuals),
            'skewness': float(np.mean(((residuals - np.mean(residuals)) / np.std(residuals)) ** 3)),
            'kurtosis': float(np.mean(((residuals - np.mean(residuals)) / np.std(residuals)) ** 4))
        }
        
        return {
            'residual_stats': residual_stats,
            'residuals': residuals.tolist(),
            'predictions': predictions,
            'actuals': actuals
        }
        
    except Exception as e:
        return {'error': f'Residual analysis failed: {e}'}
