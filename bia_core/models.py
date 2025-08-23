"""
Forecasting models for waste prediction.
Includes deterministic and SARIMA models with model selection.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
import warnings
from datetime import datetime, timedelta

# Try to import statsmodels, fallback if not available
try:
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

class BaseModel:
    """Base class for forecasting models"""
    
    def __init__(self):
        self.is_fitted = False
        self.model_params = {}
        self.last_mape = float('inf')
    
    def fit(self, features_df: pd.DataFrame):
        """Fit the model to historical data"""
        raise NotImplementedError
    
    def predict(self, forecast_days: int) -> List[float]:
        """Generate forecast for specified number of days"""
        raise NotImplementedError
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'name': self.__class__.__name__,
            'is_fitted': self.is_fitted,
            'parameters': self.model_params,
            'last_mape': self.last_mape
        }

class DeterministicModel(BaseModel):
    """Simple deterministic growth model"""
    
    def __init__(self, default_growth_rate: float = 0.002):
        super().__init__()
        self.default_growth_rate = default_growth_rate
        self.base_value = 0
        self.growth_rate = default_growth_rate
    
    def fit(self, features_df: pd.DataFrame):
        """Fit deterministic model"""
        
        if features_df.empty or 'waste_tons' not in features_df.columns:
            self.base_value = 1.0
            self.growth_rate = self.default_growth_rate
            self.is_fitted = True
            return
        
        # Calculate base value (recent average)
        recent_data = features_df['waste_tons'].tail(7)  # Last 7 days
        self.base_value = recent_data.mean() if len(recent_data) > 0 else 1.0
        
        # Calculate growth rate
        if len(features_df) >= 14:
            # Compare first and second half
            mid_point = len(features_df) // 2
            first_half_avg = features_df['waste_tons'][:mid_point].mean()
            second_half_avg = features_df['waste_tons'][mid_point:].mean()
            
            if first_half_avg > 0:
                total_periods = len(features_df) - mid_point
                total_growth = (second_half_avg / first_half_avg) - 1
                self.growth_rate = (1 + total_growth) ** (1/total_periods) - 1
                
                # Cap growth rate
                self.growth_rate = max(-0.01, min(0.01, self.growth_rate))
            else:
                self.growth_rate = self.default_growth_rate
        else:
            self.growth_rate = self.default_growth_rate
        
        self.model_params = {
            'base_value': self.base_value,
            'growth_rate': self.growth_rate
        }
        
        self.is_fitted = True
    
    def predict(self, forecast_days: int) -> List[float]:
        """Generate deterministic forecast"""
        
        if not self.is_fitted:
            return [1.0] * forecast_days
        
        forecast = []
        for t in range(1, forecast_days + 1):
            value = self.base_value * ((1 + self.growth_rate) ** t)
            forecast.append(max(0, value))  # Ensure non-negative
        
        return forecast

class SARIMAModel(BaseModel):
    """SARIMA time series model"""
    
    def __init__(self, order=(1,1,1), seasonal_order=(0,1,1,12)):
        super().__init__()
        self.order = order
        self.seasonal_order = seasonal_order
        self.model = None
        self.fitted_model = None
        self.base_forecast = None
    
    def fit(self, features_df: pd.DataFrame):
        """Fit SARIMA model"""
        
        if not STATSMODELS_AVAILABLE:
            # Fallback to deterministic if statsmodels not available
            self.base_forecast = DeterministicModel()
            self.base_forecast.fit(features_df)
            self.is_fitted = True
            return
        
        if features_df.empty or len(features_df) < 10:
            # Need sufficient data for SARIMA
            self.base_forecast = DeterministicModel()
            self.base_forecast.fit(features_df)
            self.is_fitted = True
            return
        
        try:
            # Prepare time series data
            ts_data = features_df.set_index('date')['waste_tons']
            ts_data = ts_data.asfreq('D', fill_value=0)
            
            # Handle zero variance
            if ts_data.std() == 0:
                self.base_forecast = DeterministicModel()
                self.base_forecast.fit(features_df)
                self.is_fitted = True
                return
            
            # Fit SARIMA model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                self.model = SARIMAX(
                    ts_data,
                    order=self.order,
                    seasonal_order=self.seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
                
                self.fitted_model = self.model.fit(disp=False)
                
                self.model_params = {
                    'order': self.order,
                    'seasonal_order': self.seasonal_order,
                    'aic': self.fitted_model.aic,
                    'bic': self.fitted_model.bic
                }
                
                self.is_fitted = True
                
        except Exception as e:
            # Fallback to deterministic model
            print(f"SARIMA fitting failed: {e}")
            self.base_forecast = DeterministicModel()
            self.base_forecast.fit(features_df)
            self.is_fitted = True
    
    def predict(self, forecast_days: int) -> List[float]:
        """Generate SARIMA forecast"""
        
        if not self.is_fitted:
            return [1.0] * forecast_days
        
        # Use fallback model if SARIMA failed
        if self.base_forecast is not None:
            return self.base_forecast.predict(forecast_days)
        
        if self.fitted_model is None:
            return [1.0] * forecast_days
        
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                forecast_result = self.fitted_model.forecast(steps=forecast_days)
                forecast = forecast_result.tolist()
                
                # Ensure non-negative values
                forecast = [max(0, value) for value in forecast]
                
                return forecast
                
        except Exception as e:
            print(f"SARIMA prediction failed: {e}")
            # Return simple linear forecast
            return [1.0] * forecast_days

class ModelSelector:
    """Select best model based on performance"""
    
    def __init__(self, models: List[BaseModel]):
        self.models = models
        self.best_model = None
        self.performance_scores = {}
    
    def select_best_model(self, features_df: pd.DataFrame) -> BaseModel:
        """Select best performing model"""
        
        if len(self.models) == 0:
            return DeterministicModel()
        
        if len(features_df) < 10:
            # Insufficient data for proper evaluation
            return self.models[0]
        
        from bia_core.eval import backtest_model
        
        best_score = float('inf')
        best_model = self.models[0]
        
        for model in self.models:
            try:
                # Fit model
                model.fit(features_df)
                
                # Calculate backtest score
                score = backtest_model(model, features_df)
                self.performance_scores[type(model).__name__] = score
                
                if score < best_score:
                    best_score = score
                    best_model = model
                    
            except Exception as e:
                print(f"Model evaluation failed for {type(model).__name__}: {e}")
                self.performance_scores[type(model).__name__] = float('inf')
        
        self.best_model = best_model
        return best_model
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get performance summary for all models"""
        return self.performance_scores.copy()

def create_ensemble_forecast(models: List[BaseModel], features_df: pd.DataFrame, 
                           forecast_days: int, weights: Optional[List[float]] = None) -> List[float]:
    """Create ensemble forecast from multiple models"""
    
    if not models:
        return [1.0] * forecast_days
    
    if weights is None:
        weights = [1.0 / len(models)] * len(models)
    
    ensemble_forecast = [0.0] * forecast_days
    
    for model, weight in zip(models, weights):
        try:
            model.fit(features_df)
            model_forecast = model.predict(forecast_days)
            
            for i in range(forecast_days):
                ensemble_forecast[i] += weight * model_forecast[i]
                
        except Exception as e:
            print(f"Ensemble model failed: {type(model).__name__}: {e}")
    
    return ensemble_forecast
