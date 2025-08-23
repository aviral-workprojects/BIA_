# BIA - Bio-energy Intelligence Application

## Overview

BIA (Bio-energy Intelligence Application) is a comprehensive Streamlit-based platform for bio-energy intelligence and waste-to-energy analysis. The application provides end-to-end capabilities for tracking waste generation, forecasting energy potential, performing financial analysis, and visualizing bioenergy facilities across major Indian cities. It serves as a decision-support tool for bioenergy stakeholders, enabling data-driven investment and operational decisions through integrated waste logging, predictive modeling, and financial evaluation capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit-based web application with reactive UI components
- **Layout**: Wide layout with expandable sidebar for navigation
- **State Management**: Session-based state management using Streamlit's built-in session state
- **Visualization**: Plotly for interactive charts and graphs, Folium for mapping functionality
- **User Interface**: Multi-page application structure with authentication, dashboard, forecasting, financial analysis, and mapping sections

### Backend Architecture
- **Core Module Structure**: Modular architecture with `bia_core` package containing business logic
- **Data Processing**: Pandas-based data manipulation and feature engineering
- **Authentication**: In-memory authentication using bcrypt for password hashing with thread-safe storage via Streamlit cache
- **Models**: Pluggable forecasting model architecture supporting deterministic and SARIMA models
- **Financial Engine**: Comprehensive financial calculator for NPV, ROI, and cashflow analysis
- **Validation**: Pydantic schemas for data validation and type safety

### Data Storage Solutions
- **Primary Storage**: In-memory storage using Streamlit's `@st.cache_resource` for thread-safe data persistence
- **User Data**: Thread-safe authentication store managing user profiles and waste logs
- **Curated Data**: CSV-based data storage for city statistics, facilities, tariffs, and cost parameters
- **Session Management**: Browser session-based state management for user authentication and application state

### Authentication and Authorization
- **Password Security**: bcrypt hashing algorithm for secure password storage
- **Session Management**: Streamlit session state for user authentication persistence
- **User Profiles**: Comprehensive user profile system with entity information and waste type classification
- **Demo Access**: Pre-configured demo user (demo/demo123) for immediate application testing

### Key Design Patterns
- **Model Abstraction**: Base model class with standardized fit/predict interface for forecasting models
- **Factory Pattern**: Model selector for choosing optimal forecasting approach based on data characteristics
- **Separation of Concerns**: Clear separation between data models, business logic, and presentation layers
- **Error Handling**: Comprehensive error handling with graceful fallbacks for missing dependencies

## External Dependencies

### Core Framework Dependencies
- **Streamlit**: Primary web application framework for UI and deployment
- **Pandas**: Data manipulation and analysis for time series processing
- **NumPy**: Numerical computations for financial calculations and forecasting
- **Plotly**: Interactive visualization library for charts, graphs, and financial analysis displays

### Forecasting and Analytics
- **Statsmodels**: Advanced time series modeling including SARIMA models (optional dependency with fallback)
- **Scikit-learn**: Machine learning utilities for model evaluation and data preprocessing
- **Python-dateutil**: Date parsing and manipulation for time series analysis

### Mapping and Visualization
- **Folium**: Interactive map generation for facility mapping
- **Streamlit-folium**: Streamlit integration for Folium maps
- **Pydeck**: Advanced geospatial visualization capabilities
- **Matplotlib**: Additional plotting capabilities for specialized visualizations

### Security and Data Validation
- **Bcrypt**: Cryptographic password hashing for user authentication
- **Pydantic**: Data validation and settings management with type annotations
- **PyYAML**: Configuration file parsing for application settings

### Geographic Coverage
- **Supported Cities**: Ahmedabad, Gandhinagar, Indore, Delhi, Mumbai, Pune, Bengaluru, Chennai
- **Waste Types**: Organic, industrial, and agricultural waste categories
- **Map Data**: Curated facility database with geographic coordinates and operational status

### Data Sources and Integrations
- **City Statistics**: Population, waste generation rates, and waste composition data
- **Facility Database**: Bioenergy facility locations, capacities, and operational status
- **Tariff Data**: Electricity pricing information for financial calculations
- **Cost Parameters**: Capital and operational expenditure benchmarks for project evaluation