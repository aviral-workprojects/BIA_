# BIA - Bio-energy Intelligence Application

A Streamlit-based bioenergy intelligence platform for waste-to-energy analysis with forecasting, financial modeling, and facility mapping.

## Features

- **User Authentication**: Secure signup/login with bcrypt password hashing
- **Waste Logging**: Track waste generation with automatic date recording
- **Forecasting**: Deterministic and SARIMA models for waste prediction
- **Financial Analysis**: NPV, payback period, ROI calculations
- **Sensitivity Analysis**: Tornado charts for parameter impact assessment
- **Facility Mapping**: Interactive maps of bioenergy facilities
- **Audit Trail**: Complete mathematical formulas and parameter provenance

## Supported Cities

- Ahmedabad
- Gandhinagar  
- Indore
- Delhi
- Mumbai
- Pune
- Bengaluru
- Chennai

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install streamlit pandas numpy plotly statsmodels pydantic scikit-learn folium streamlit-folium pydeck python-dateutil bcrypt pyyaml matplotlib
   ```

2. **Run Application**
   ```bash
   streamlit run app.py
   ```

3. **Access Application**
   - Open your browser to `http://localhost:5000`
   - Demo login: **demo** / **demo123**

## Application Structure

