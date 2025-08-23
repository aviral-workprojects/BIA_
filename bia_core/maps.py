"""
Mapping functionality for bioenergy facilities.
"""

import folium
import pandas as pd
from typing import Dict, Any, Optional, List
import streamlit as st

# Default map coordinates for supported cities
CITY_COORDINATES = {
    'Ahmedabad': [23.0225, 72.5714],
    'Gandhinagar': [23.2156, 72.6369],
    'Indore': [22.7196, 75.8577],
    'Delhi': [28.7041, 77.1025],
    'Mumbai': [19.0760, 72.8777],
    'Pune': [18.5204, 73.8567],
    'Bengaluru': [12.9716, 77.5946],
    'Chennai': [13.0827, 80.2707]
}

def create_facilities_map(facilities_df: pd.DataFrame, city: str, 
                         zoom_start: int = 10) -> folium.Map:
    """
    Create interactive map with bioenergy facilities
    
    Args:
        facilities_df: DataFrame with facility data
        city: City name for map centering
        zoom_start: Initial zoom level
    
    Returns:
        Folium map object
    """
    
    # Get city coordinates
    if city in CITY_COORDINATES:
        center_coords = CITY_COORDINATES[city]
    else:
        # Default to India center if city not found
        center_coords = [20.5937, 78.9629]
    
    # Create base map
    m = folium.Map(
        location=center_coords,
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )
    
    # Add facilities as markers
    if not facilities_df.empty:
        for idx, facility in facilities_df.iterrows():
            try:
                # Determine marker color based on status
                status = facility.get('status', 'unknown').lower()
                if status == 'operational':
                    color = 'green'
                    icon = 'play'
                elif status == 'under_construction':
                    color = 'orange'
                    icon = 'cog'
                elif status == 'planned':
                    color = 'blue'
                    icon = 'clock'
                else:
                    color = 'gray'
                    icon = 'question'
                
                # Create popup content
                popup_content = create_facility_popup(facility)
                
                # Add marker
                folium.Marker(
                    location=[facility['lat'], facility['lon']],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=facility['name'],
                    icon=folium.Icon(
                        color=color,
                        icon=icon,
                        prefix='fa'
                    )
                ).add_to(m)
                
            except Exception as e:
                print(f"Error adding facility marker: {e}")
                continue
    
    # Add city marker
    folium.Marker(
        location=center_coords,
        popup=f"{city} City Center",
        tooltip=f"{city}",
        icon=folium.Icon(
            color='red',
            icon='home',
            prefix='fa'
        )
    ).add_to(m)
    
    # Add legend
    add_map_legend(m)
    
    return m

def create_facility_popup(facility: pd.Series) -> str:
    """Create HTML popup content for facility marker"""
    
    # Format capacity
    capacity = facility.get('capacity_mw', 0)
    if capacity > 0:
        capacity_str = f"{capacity:.1f} MW"
    else:
        capacity_str = "Not specified"
    
    # Create popup HTML
    popup_html = f"""
    <div style="width: 250px;">
        <h4 style="margin: 0 0 10px 0; color: #2E8B57;">
            {facility.get('name', 'Unknown Facility')}
        </h4>
        
        <table style="width: 100%; font-size: 12px;">
            <tr>
                <td><strong>Type:</strong></td>
                <td>{facility.get('type', 'Unknown')}</td>
            </tr>
            <tr>
                <td><strong>Capacity:</strong></td>
                <td>{capacity_str}</td>
            </tr>
            <tr>
                <td><strong>Status:</strong></td>
                <td style="color: {get_status_color(facility.get('status', 'unknown'))};">
                    {format_status(facility.get('status', 'unknown'))}
                </td>
            </tr>
            <tr>
                <td><strong>Location:</strong></td>
                <td>{facility.get('city', '')}, {facility.get('state', '')}</td>
            </tr>
            <tr>
                <td><strong>Source:</strong></td>
                <td style="font-size: 10px;">{facility.get('source', 'Unknown')}</td>
            </tr>
        </table>
        
        <div style="margin-top: 10px; font-size: 10px; color: #666;">
            Coordinates: {facility.get('lat', 0):.4f}, {facility.get('lon', 0):.4f}
        </div>
    </div>
    """
    
    return popup_html

def get_status_color(status: str) -> str:
    """Get color for facility status"""
    status_colors = {
        'operational': '#28a745',
        'under_construction': '#fd7e14',
        'planned': '#007bff',
        'unknown': '#6c757d'
    }
    
    return status_colors.get(status.lower(), '#6c757d')

def format_status(status: str) -> str:
    """Format status string for display"""
    if status.lower() == 'under_construction':
        return 'Under Construction'
    elif status.lower() == 'operational':
        return 'Operational'
    elif status.lower() == 'planned':
        return 'Planned'
    else:
        return 'Unknown'

def add_map_legend(map_obj: folium.Map):
    """Add legend to the map"""
    
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 180px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h5 style="margin: 0 0 10px 0;">Facility Status</h5>
    <p style="margin: 5px 0;"><i class="fa fa-circle" style="color:green"></i> Operational</p>
    <p style="margin: 5px 0;"><i class="fa fa-circle" style="color:orange"></i> Under Construction</p>
    <p style="margin: 5px 0;"><i class="fa fa-circle" style="color:blue"></i> Planned</p>
    <p style="margin: 5px 0;"><i class="fa fa-circle" style="color:red"></i> City Center</p>
    </div>
    '''
    
    map_obj.get_root().html.add_child(folium.Element(legend_html))

def create_heat_map(facilities_df: pd.DataFrame, city: str) -> folium.Map:
    """Create heat map of facility density"""
    
    from folium.plugins import HeatMap
    
    # Get city coordinates
    center_coords = CITY_COORDINATES.get(city, [20.5937, 78.9629])
    
    # Create base map
    m = folium.Map(
        location=center_coords,
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    if not facilities_df.empty:
        # Prepare heat map data
        heat_data = []
        for idx, facility in facilities_df.iterrows():
            try:
                # Weight by capacity if available
                weight = facility.get('capacity_mw', 1)
                heat_data.append([
                    facility['lat'], 
                    facility['lon'], 
                    weight
                ])
            except:
                continue
        
        # Add heat map layer
        if heat_data:
            HeatMap(heat_data).add_to(m)
    
    return m

def get_facility_statistics(facilities_df: pd.DataFrame) -> Dict[str, Any]:
    """Get statistics about facilities"""
    
    if facilities_df.empty:
        return {
            'total_facilities': 0,
            'total_capacity_mw': 0,
            'operational_count': 0,
            'planned_count': 0,
            'under_construction_count': 0,
            'avg_capacity_mw': 0,
            'facility_types': {}
        }
    
    # Basic statistics
    total_facilities = len(facilities_df)
    total_capacity = facilities_df['capacity_mw'].sum()
    avg_capacity = facilities_df['capacity_mw'].mean()
    
    # Status counts
    status_counts = facilities_df['status'].value_counts().to_dict()
    operational_count = status_counts.get('operational', 0)
    planned_count = status_counts.get('planned', 0)
    under_construction_count = status_counts.get('under_construction', 0)
    
    # Facility types
    type_counts = facilities_df['type'].value_counts().to_dict()
    
    return {
        'total_facilities': total_facilities,
        'total_capacity_mw': total_capacity,
        'operational_count': operational_count,
        'planned_count': planned_count,
        'under_construction_count': under_construction_count,
        'avg_capacity_mw': avg_capacity,
        'facility_types': type_counts
    }

def filter_facilities_by_criteria(facilities_df: pd.DataFrame, 
                                criteria: Dict[str, Any]) -> pd.DataFrame:
    """Filter facilities based on criteria"""
    
    filtered_df = facilities_df.copy()
    
    # Filter by status
    if 'status' in criteria and criteria['status']:
        filtered_df = filtered_df[filtered_df['status'].isin(criteria['status'])]
    
    # Filter by type
    if 'type' in criteria and criteria['type']:
        filtered_df = filtered_df[filtered_df['type'].isin(criteria['type'])]
    
    # Filter by capacity range
    if 'min_capacity' in criteria:
        filtered_df = filtered_df[filtered_df['capacity_mw'] >= criteria['min_capacity']]
    
    if 'max_capacity' in criteria:
        filtered_df = filtered_df[filtered_df['capacity_mw'] <= criteria['max_capacity']]
    
    return filtered_df

@st.cache_data
def load_facility_data_for_city(city: str) -> pd.DataFrame:
    """Load facility data for specific city with caching"""
    
    from bia_core.data_io import load_curated_data
    
    try:
        curated_data = load_curated_data()
        facilities = curated_data.get('facilities', pd.DataFrame())
        
        if not facilities.empty:
            city_facilities = facilities[facilities['city'] == city].copy()
            return city_facilities
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error loading facility data for {city}: {e}")
        return pd.DataFrame()
