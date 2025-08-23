import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import json
from datetime import datetime, date
import warnings

# Import our modules
from auth_inmemory import AuthStore, add_user, validate_user, add_waste_log, get_user_logs
from bia_core.data_io import load_curated_data
from bia_core.schemas import UserProfile, WasteLog
from bia_core.features import create_forecast_features
from bia_core.models import DeterministicModel, SARIMAModel, ModelSelector
from bia_core.finance import FinanceCalculator
from bia_core.eval import calculate_mape, backtest_model
from bia_core.maps import create_facilities_map
from bia_core.utils import format_currency, format_number, validate_range

warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="BIA - Bio-energy Intelligence Application",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
SUPPORTED_CITIES = ["Ahmedabad", "Gandhinagar", "Indore", "Delhi", "Mumbai", "Pune", "Bengaluru", "Chennai"]
WASTE_TYPES = ["organic", "industrial", "agricultural"]

# Initialize auth store
auth_store = AuthStore()

def init_session_state():
    """Initialize session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None

def login_signup_page():
    """Handle login and signup"""
    st.title("🔋 BIA - Bio-energy Intelligence Application")
    st.markdown("### Welcome to the Bio-energy Intelligence Platform")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")
            
            if login_btn:
                if username and password:
                    user_profile = validate_user(username, password)
                    if user_profile:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_profile = user_profile
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")
        
        st.info("Demo user: **demo** / **demo123**")
    
    with tab2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="signup_username")
            new_password = st.text_input("Password", type="password", key="signup_password")
            entity_name = st.text_input("Entity Name")
            city = st.selectbox("City", SUPPORTED_CITIES)
            waste_type = st.selectbox("Waste Type", WASTE_TYPES)
            signup_btn = st.form_submit_button("Sign Up")
            
            if signup_btn:
                if all([new_username, new_password, entity_name, city, waste_type]):
                    if add_user(new_username, new_password, entity_name, city, waste_type):
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error("Username already exists")
                else:
                    st.error("Please fill in all fields")

def sidebar_controls():
    """Create sidebar controls for parameters"""
    st.sidebar.title("🔋 BIA Controls")
    
    # User info
    if st.session_state.user_profile:
        st.sidebar.write(f"**User:** {st.session_state.username}")
        st.sidebar.write(f"**Entity:** {st.session_state.user_profile.entity_name}")
        st.sidebar.write(f"**City:** {st.session_state.user_profile.city}")
        st.sidebar.write(f"**Waste Type:** {st.session_state.user_profile.waste_type}")
    
    st.sidebar.divider()
    
    # Parameter controls
    st.sidebar.subheader("Technical Parameters")
    
    yield_rate = st.sidebar.slider(
        "Yield Rate (kWh/ton)", 
        min_value=100.0, max_value=2000.0, value=800.0, step=50.0,
        help="Energy yield per ton of waste"
    )
    
    capacity_factor = st.sidebar.slider(
        "Capacity Factor (%)", 
        min_value=30.0, max_value=95.0, value=85.0, step=5.0,
        help="Plant capacity utilization factor"
    ) / 100
    
    st.sidebar.subheader("Financial Parameters")
    
    tariff = st.sidebar.slider(
        "Tariff (₹/kWh)", 
        min_value=2.0, max_value=8.0, value=4.5, step=0.1,
        help="Electricity selling price"
    )
    
    opex_per_ton = st.sidebar.slider(
        "OPEX per ton (₹)", 
        min_value=200.0, max_value=1000.0, value=500.0, step=50.0,
        help="Operating expenses per ton of waste"
    )
    
    fixed_opex = st.sidebar.number_input(
        "Fixed OPEX (₹ lakhs/year)", 
        min_value=0.0, max_value=100.0, value=10.0, step=1.0,
        help="Fixed annual operating expenses"
    ) * 100000  # Convert to rupees
    
    capex = st.sidebar.number_input(
        "CAPEX (₹ crores)", 
        min_value=1.0, max_value=100.0, value=25.0, step=1.0,
        help="Capital expenditure"
    ) * 10000000  # Convert to rupees
    
    discount_rate = st.sidebar.slider(
        "Discount Rate (%)", 
        min_value=5.0, max_value=20.0, value=12.0, step=0.5,
        help="Cost of capital"
    ) / 100
    
    horizon_years = st.sidebar.slider(
        "Project Horizon (years)", 
        min_value=10, max_value=30, value=20, step=1,
        help="Project lifetime"
    )
    
    st.sidebar.divider()
    
    # Logout button
    if st.sidebar.button("Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_profile = None
        st.rerun()
    
    return {
        'yield_rate': yield_rate,
        'capacity_factor': capacity_factor,
        'tariff': tariff,
        'opex_per_ton': opex_per_ton,
        'fixed_opex': fixed_opex,
        'capex': capex,
        'discount_rate': discount_rate,
        'horizon_years': horizon_years
    }

def waste_logging_section():
    """Waste logging interface"""
    st.subheader("📝 Log Waste")
    
    with st.form("waste_log_form"):
        col1, col2 = st.columns(2)
        with col1:
            waste_amount = st.number_input(
                "Waste Amount (tons)", 
                min_value=0.01, max_value=1000.0, value=1.0, step=0.1
            )
        with col2:
            log_date = st.date_input("Date", value=date.today())
        
        submit_btn = st.form_submit_button("Add Waste Log")
        
        if submit_btn:
            if waste_amount > 0:
                waste_log = WasteLog(
                    username=st.session_state.username,
                    date=log_date,
                    waste_tons=waste_amount
                )
                add_waste_log(waste_log)
                st.success(f"Added {waste_amount} tons of waste for {log_date}")
                st.rerun()
            else:
                st.error("Please enter a valid waste amount")

def entity_profile_tab():
    """Entity profile and logs"""
    st.header("🏢 Entity Profile")
    
    profile = st.session_state.user_profile
    
    # Profile information
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **Entity Name:** {profile.entity_name}  
        **City:** {profile.city}  
        **Waste Type:** {profile.waste_type}  
        **Username:** {st.session_state.username}
        """)
    
    with col2:
        waste_logging_section()
    
    # Waste logs
    st.subheader("📊 Waste Logs")
    logs = get_user_logs(st.session_state.username)
    
    if logs:
        df_logs = pd.DataFrame([{
            'Date': log.date,
            'Waste (tons)': log.waste_tons
        } for log in logs])
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Waste", f"{df_logs['Waste (tons)'].sum():.2f} tons")
        with col2:
            today_waste = df_logs[df_logs['Date'] == date.today()]['Waste (tons)'].sum()
            st.metric("Today's Waste", f"{today_waste:.2f} tons")
        with col3:
            st.metric("Total Logs", len(df_logs))
        
        # Logs table
        st.dataframe(df_logs, use_container_width=True)
        
        # Download logs
        csv = df_logs.to_csv(index=False)
        st.download_button(
            label="Download Logs CSV",
            data=csv,
            file_name=f"waste_logs_{st.session_state.username}.csv",
            mime="text/csv"
        )
    else:
        st.info("No waste logs found. Add some logs to get started!")

def forecast_tab(params):
    """Waste trend and forecast"""
    st.header("📈 Waste Trend & Forecast")
    
    logs = get_user_logs(st.session_state.username)
    
    if not logs or len(logs) < 2:
        st.warning("Need at least 2 waste logs to generate forecasts")
        return
    
    # Prepare data
    df_logs = pd.DataFrame([{
        'date': log.date,
        'waste_tons': log.waste_tons
    } for log in logs])
    
    df_logs = df_logs.sort_values('date')
    df_logs['cumulative_waste'] = df_logs['waste_tons'].cumsum()
    
    # Create forecast features
    forecast_features = create_forecast_features(df_logs)
    
    # Initialize models
    det_model = DeterministicModel()
    sarima_model = SARIMAModel()
    
    # Fit models
    det_model.fit(forecast_features)
    sarima_model.fit(forecast_features)
    
    # Generate forecasts
    forecast_days = 30
    det_forecast = det_model.predict(forecast_days)
    sarima_forecast = sarima_model.predict(forecast_days)
    
    # Model selection based on backtest
    model_selector = ModelSelector([det_model, sarima_model])
    best_model = model_selector.select_best_model(forecast_features)
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Historical trend
        fig_hist = px.line(df_logs, x='date', y='waste_tons', 
                          title="Historical Waste Logs")
        fig_hist.update_layout(xaxis_title="Date", yaxis_title="Waste (tons)")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Cumulative waste
        fig_cum = px.line(df_logs, x='date', y='cumulative_waste', 
                         title="Cumulative Waste")
        fig_cum.update_layout(xaxis_title="Date", yaxis_title="Cumulative Waste (tons)")
        st.plotly_chart(fig_cum, use_container_width=True)
    
    # Forecast comparison
    st.subheader("📊 Forecast Comparison")
    
    forecast_dates = pd.date_range(
        start=df_logs['date'].max() + pd.Timedelta(days=1),
        periods=forecast_days,
        freq='D'
    )
    
    forecast_df = pd.DataFrame({
        'Date': forecast_dates,
        'Deterministic': det_forecast,
        'SARIMA': sarima_forecast
    })
    
    fig_forecast = go.Figure()
    
    # Add historical data
    fig_forecast.add_trace(go.Scatter(
        x=df_logs['date'], y=df_logs['waste_tons'],
        mode='lines+markers', name='Historical',
        line=dict(color='blue')
    ))
    
    # Add forecasts
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df['Date'], y=forecast_df['Deterministic'],
        mode='lines', name='Deterministic Forecast',
        line=dict(color='red', dash='dash')
    ))
    
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df['Date'], y=forecast_df['SARIMA'],
        mode='lines', name='SARIMA Forecast',
        line=dict(color='green', dash='dot')
    ))
    
    fig_forecast.update_layout(
        title="Waste Forecast (30 days)",
        xaxis_title="Date",
        yaxis_title="Waste (tons)"
    )
    
    st.plotly_chart(fig_forecast, use_container_width=True)
    
    # Model performance
    st.subheader("🎯 Model Performance")
    
    if len(forecast_features) >= 10:  # Need sufficient data for backtest
        det_mape = backtest_model(det_model, forecast_features)
        sarima_mape = backtest_model(sarima_model, forecast_features)
        
        perf_df = pd.DataFrame({
            'Model': ['Deterministic', 'SARIMA'],
            'MAPE (%)': [det_mape, sarima_mape],
            'Selected': ['✓' if best_model == det_model else '✗',
                        '✓' if best_model == sarima_model else '✗']
        })
        
        st.dataframe(perf_df, use_container_width=True)
        
        st.info(f"**Best Model:** {type(best_model).__name__} (Lower MAPE is better)")
    else:
        st.info("Need more data points for model backtesting")

def energy_finance_tab(params):
    """Energy and finance calculations"""
    st.header("⚡ Energy & Finance")
    
    logs = get_user_logs(st.session_state.username)
    
    if not logs:
        st.warning("No waste logs found. Add some logs to see energy and finance projections.")
        return
    
    # Calculate totals
    total_waste = sum(log.waste_tons for log in logs)
    today_waste = sum(log.waste_tons for log in logs if log.date == date.today())
    
    # Energy calculations
    gross_electricity = total_waste * params['yield_rate'] * params['capacity_factor']
    estimated_daily_electricity = today_waste * params['yield_rate'] * params['capacity_factor']
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Gross Electricity Generated", 
            f"{format_number(gross_electricity)} kWh",
            help="Total electricity from all logged waste"
        )
    
    with col2:
        st.metric(
            "Today's Est. Electricity", 
            f"{format_number(estimated_daily_electricity)} kWh",
            help="Estimated electricity from today's waste"
        )
    
    with col3:
        revenue_potential = gross_electricity * params['tariff']
        st.metric(
            "Revenue Potential", 
            f"₹{format_number(revenue_potential)}",
            help="Revenue from gross electricity"
        )
    
    # Financial projections
    st.subheader("💰 Financial Projections")
    
    # Initialize finance calculator
    calc = FinanceCalculator(
        yield_rate=params['yield_rate'],
        capacity_factor=params['capacity_factor'],
        tariff=params['tariff'],
        opex_per_ton=params['opex_per_ton'],
        fixed_opex=params['fixed_opex'],
        capex=params['capex'],
        discount_rate=params['discount_rate']
    )
    
    # Calculate average daily waste for projections
    if logs:
        avg_daily_waste = total_waste / len(set(log.date for log in logs))
    else:
        avg_daily_waste = 1.0  # Default
    
    # Generate cashflows
    cashflows = calc.calculate_cashflows(avg_daily_waste, params['horizon_years'])
    
    # Create cashflow chart
    years = list(range(1, params['horizon_years'] + 1))
    
    fig_cf = go.Figure()
    
    fig_cf.add_trace(go.Bar(
        x=years, y=[cf['revenue'] for cf in cashflows],
        name='Revenue', marker_color='green'
    ))
    
    fig_cf.add_trace(go.Bar(
        x=years, y=[-cf['opex'] for cf in cashflows],
        name='OPEX', marker_color='red'
    ))
    
    fig_cf.add_trace(go.Scatter(
        x=years, y=[cf['ncf'] for cf in cashflows],
        mode='lines+markers', name='Net Cash Flow',
        line=dict(color='blue', width=3)
    ))
    
    fig_cf.update_layout(
        title="Annual Cashflows",
        xaxis_title="Year",
        yaxis_title="Amount (₹)",
        barmode='relative'
    )
    
    st.plotly_chart(fig_cf, use_container_width=True)
    
    # Export cashflows
    cf_df = pd.DataFrame([{
        'Year': i+1,
        'Waste (tons)': cf['waste_tons'],
        'Electricity (kWh)': cf['electricity_kwh'],
        'Revenue (₹)': cf['revenue'],
        'OPEX (₹)': cf['opex'],
        'Net Cash Flow (₹)': cf['ncf']
    } for i, cf in enumerate(cashflows)])
    
    st.subheader("📋 Annual Cashflow Table")
    st.dataframe(cf_df, use_container_width=True)
    
    # Download button
    csv = cf_df.to_csv(index=False)
    st.download_button(
        label="Download Cashflows CSV",
        data=csv,
        file_name=f"cashflows_{st.session_state.username}.csv",
        mime="text/csv"
    )

def npv_sensitivity_tab(params):
    """NPV calculations and sensitivity analysis"""
    st.header("💹 NPV & Sensitivity Analysis")
    
    logs = get_user_logs(st.session_state.username)
    
    if not logs:
        st.warning("No waste logs found. Add some logs to see NPV analysis.")
        return
    
    # Calculate average daily waste
    total_waste = sum(log.waste_tons for log in logs)
    avg_daily_waste = total_waste / len(set(log.date for log in logs))
    
    # Initialize finance calculator
    calc = FinanceCalculator(
        yield_rate=params['yield_rate'],
        capacity_factor=params['capacity_factor'],
        tariff=params['tariff'],
        opex_per_ton=params['opex_per_ton'],
        fixed_opex=params['fixed_opex'],
        capex=params['capex'],
        discount_rate=params['discount_rate']
    )
    
    # Calculate base case metrics
    npv = calc.calculate_npv(avg_daily_waste, params['horizon_years'])
    payback = calc.calculate_payback(avg_daily_waste, params['horizon_years'])
    roi = calc.calculate_roi(avg_daily_waste, params['horizon_years'])
    
    # CO2 savings calculation
    total_kwh = sum(log.waste_tons for log in logs) * params['yield_rate'] * params['capacity_factor']
    co2_savings = (total_kwh * 0.9) / 1000  # kg to tons
    trees_equivalent = 50 * co2_savings
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("NPV", f"₹{format_currency(npv)}")
    
    with col2:
        st.metric("Payback Period", f"{payback:.1f} years" if payback != float('inf') else "∞")
    
    with col3:
        st.metric("ROI", f"{roi:.1f}%")
    
    with col4:
        st.metric("CO₂ Savings", f"{co2_savings:.1f} tons")
    
    # Environmental impact
    st.subheader("🌱 Environmental Impact")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("CO₂ Savings", f"{co2_savings:.2f} tons")
    
    with col2:
        st.metric("Trees Equivalent", f"{trees_equivalent:.0f} trees")
    
    # Sensitivity Analysis
    st.subheader("📊 Sensitivity Analysis")
    
    # Parameters to analyze
    sensitivity_params = {
        'Yield Rate': ('yield_rate', params['yield_rate']),
        'Tariff': ('tariff', params['tariff']),
        'OPEX per ton': ('opex_per_ton', params['opex_per_ton']),
        'CAPEX': ('capex', params['capex']),
        'Discount Rate': ('discount_rate', params['discount_rate'])
    }
    
    # Calculate sensitivity
    sensitivity_results = []
    
    for param_name, (param_key, base_value) in sensitivity_params.items():
        # +15% case
        params_high = params.copy()
        params_high[param_key] = base_value * 1.15
        
        calc_high = FinanceCalculator(
            yield_rate=params_high['yield_rate'],
            capacity_factor=params_high['capacity_factor'],
            tariff=params_high['tariff'],
            opex_per_ton=params_high['opex_per_ton'],
            fixed_opex=params_high['fixed_opex'],
            capex=params_high['capex'],
            discount_rate=params_high['discount_rate']
        )
        
        npv_high = calc_high.calculate_npv(avg_daily_waste, params['horizon_years'])
        
        # -15% case
        params_low = params.copy()
        params_low[param_key] = base_value * 0.85
        
        calc_low = FinanceCalculator(
            yield_rate=params_low['yield_rate'],
            capacity_factor=params_low['capacity_factor'],
            tariff=params_low['tariff'],
            opex_per_ton=params_low['opex_per_ton'],
            fixed_opex=params_low['fixed_opex'],
            capex=params_low['capex'],
            discount_rate=params_low['discount_rate']
        )
        
        npv_low = calc_low.calculate_npv(avg_daily_waste, params['horizon_years'])
        
        # Calculate sensitivity
        npv_range = npv_high - npv_low
        
        sensitivity_results.append({
            'Parameter': param_name,
            'NPV Impact': npv_range,
            'NPV Low (-15%)': npv_low,
            'NPV High (+15%)': npv_high
        })
    
    # Sort by impact
    sensitivity_results.sort(key=lambda x: abs(x['NPV Impact']), reverse=True)
    
    # Create tornado chart
    fig_tornado = go.Figure()
    
    params_list = [r['Parameter'] for r in sensitivity_results]
    impacts = [r['NPV Impact'] for r in sensitivity_results]
    
    fig_tornado.add_trace(go.Bar(
        y=params_list,
        x=impacts,
        orientation='h',
        marker_color=['red' if x < 0 else 'green' for x in impacts]
    ))
    
    fig_tornado.update_layout(
        title="NPV Sensitivity Analysis (±15% parameter change)",
        xaxis_title="NPV Impact (₹)",
        yaxis_title="Parameter"
    )
    
    st.plotly_chart(fig_tornado, use_container_width=True)
    
    # Sensitivity table
    st.subheader("📋 Sensitivity Results")
    sens_df = pd.DataFrame(sensitivity_results)
    st.dataframe(sens_df, use_container_width=True)

def facilities_map_tab():
    """Facilities mapping"""
    st.header("🗺️ Facilities Map")
    
    # Load facilities data
    try:
        facilities_data = load_curated_data()['facilities']
        user_city = st.session_state.user_profile.city
        
        # Filter facilities for user's city
        city_facilities = facilities_data[facilities_data['city'] == user_city]
        
        if len(city_facilities) > 0:
            # Create map
            facilities_map = create_facilities_map(city_facilities, user_city)
            
            # Display map
            map_data = st_folium(facilities_map, width=700, height=500)
            
            # Display facilities table
            st.subheader(f"🏭 Facilities in {user_city}")
            
            display_df = city_facilities[['name', 'type', 'capacity_mw', 'status', 'source']].copy()
            display_df.columns = ['Name', 'Type', 'Capacity (MW)', 'Status', 'Source']
            
            st.dataframe(display_df, use_container_width=True)
            
            # Summary statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Facilities", len(city_facilities))
            
            with col2:
                total_capacity = city_facilities['capacity_mw'].sum()
                st.metric("Total Capacity", f"{total_capacity:.1f} MW")
            
            with col3:
                operational_count = len(city_facilities[city_facilities['status'] == 'operational'])
                st.metric("Operational", operational_count)
            
        else:
            st.info(f"No verified facilities found in {user_city} in our current database.")
            st.markdown("**Note:** Our facility database is curated from verified sources and may not include all facilities.")
            
    except Exception as e:
        st.error(f"Error loading facilities data: {str(e)}")
        st.info("Please check if the facilities data file is available and properly formatted.")

def audit_tab(params):
    """Audit trail with formulas and parameters"""
    st.header("🔍 Audit Trail")
    
    # LaTeX formulas
    st.subheader("📐 Mathematical Formulas")
    
    st.markdown("### Energy Calculations")
    st.latex(r"kWh_{year,t} = tons_{year,t} \times yield \times capacity\_factor")
    st.latex(r"tons_{year,t} = tpd_t \times 365")
    
    st.markdown("### Deterministic Forecast")
    st.latex(r"tpd_t = base\_tpd \times (1+g)^{(t-1)}")
    
    st.markdown("### Financial Calculations")
    st.latex(r"revenue_t = kWh_{year,t} \times tariff")
    st.latex(r"opex_t = tons_{year,t} \times opex\_per\_ton + fixed\_opex")
    st.latex(r"ncf_t = revenue_t - opex_t")
    
    st.markdown("### NPV Calculation")
    st.latex(r"NPV = -CAPEX + \sum_{t=1}^{horizon} \frac{ncf_t}{(1+r)^t}")
    
    st.markdown("### Environmental Impact")
    st.latex(r"CO_2\_savings = \frac{kWh \times 0.9}{1000} \text{ tons}")
    st.latex(r"Trees\_equivalent = 50 \times CO_2\_savings")
    
    # Parameter table
    st.subheader("⚙️ Current Parameters")
    
    param_data = {
        'Parameter': [
            'Yield Rate (kWh/ton)',
            'Capacity Factor (%)',
            'Tariff (₹/kWh)',
            'OPEX per ton (₹)',
            'Fixed OPEX (₹/year)',
            'CAPEX (₹)',
            'Discount Rate (%)',
            'Project Horizon (years)'
        ],
        'Value': [
            f"{params['yield_rate']:.1f}",
            f"{params['capacity_factor']*100:.1f}%",
            f"₹{params['tariff']:.2f}",
            f"₹{params['opex_per_ton']:.0f}",
            f"₹{params['fixed_opex']:,.0f}",
            f"₹{params['capex']:,.0f}",
            f"{params['discount_rate']*100:.1f}%",
            f"{params['horizon_years']} years"
        ],
        'Unit': [
            'kWh/ton',
            'Percentage',
            'INR per kWh',
            'INR per ton',
            'INR per year',
            'INR',
            'Percentage',
            'Years'
        ]
    }
    
    param_df = pd.DataFrame(param_data)
    st.dataframe(param_df, use_container_width=True)
    
    # Data provenance
    st.subheader("📊 Data Provenance")
    
    provenance_info = {
        "User Data": "In-memory storage during session",
        "Waste Logs": "User-entered data with auto-recorded timestamps",
        "City Data": "Curated from government and industry sources",
        "Facility Data": "Verified bioenergy facilities database",
        "Tariff Data": "State electricity regulatory commission rates",
        "Cost Parameters": "Industry benchmarks and user-adjustable"
    }
    
    for source, description in provenance_info.items():
        st.write(f"**{source}:** {description}")
    
    # Configuration export
    st.subheader("💾 Export Configuration")
    
    # Create run configuration
    run_config = {
        "timestamp": datetime.now().isoformat(),
        "user": st.session_state.username,
        "entity": st.session_state.user_profile.entity_name,
        "city": st.session_state.user_profile.city,
        "waste_type": st.session_state.user_profile.waste_type,
        "parameters": params,
        "total_logs": len(get_user_logs(st.session_state.username)),
        "application_version": "BIA v1.0"
    }
    
    config_json = json.dumps(run_config, indent=2, default=str)
    
    st.download_button(
        label="Download Run Configuration",
        data=config_json,
        file_name=f"bia_config_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )
    
    # Assumptions and limitations
    st.subheader("⚠️ Assumptions & Limitations")
    
    st.markdown("""
    **Key Assumptions:**
    - Constant yield rate and capacity factor over project lifetime
    - Linear waste growth for deterministic forecasting
    - Constant tariff rates (inflation not modeled)
    - No major policy or regulatory changes
    - Standard CO₂ emission factor (0.9 kg/kWh)
    
    **Limitations:**
    - Supports only 8 cities in current version
    - In-memory authentication (no data persistence)
    - Simplified financial modeling (no tax considerations)
    - SARIMA model assumes sufficient historical data
    - No detailed technical feasibility assessment
    """)

def main_dashboard():
    """Main dashboard with tabs"""
    st.title("🔋 BIA Dashboard")
    st.markdown(f"**Welcome, {st.session_state.user_profile.entity_name}!**")
    
    # Get parameters from sidebar
    params = sidebar_controls()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏢 Entity Profile",
        "📈 Waste Trend & Forecast", 
        "⚡ Energy & Finance",
        "💹 NPV & Sensitivity",
        "🗺️ Facilities Map",
        "🔍 Audit"
    ])
    
    with tab1:
        entity_profile_tab()
    
    with tab2:
        forecast_tab(params)
    
    with tab3:
        energy_finance_tab(params)
    
    with tab4:
        npv_sensitivity_tab(params)
    
    with tab5:
        facilities_map_tab()
    
    with tab6:
        audit_tab(params)

def main():
    """Main application"""
    init_session_state()
    
    if not st.session_state.logged_in:
        login_signup_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
