import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import io
import random
from datetime import datetime
import numpy as np

# Import from Core
from core_2 import (
    generate_company_name, generate_materials, generate_master_data,
    generate_config_data, generate_transactions, calculate_allocations,
    generate_tp_adjustments, get_demo_scenario
)

# Plotly Imports
import plotly.graph_objects as go
import plotly.express as px

# Streamlit Flow Imports
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState

# Page Configuration
st.set_page_config(page_title="Global Company & Material Data Generator", layout="wide")

# Inject Custom Premium CSS (Aesthetics & WOW factor)
st.markdown("""
<style>
    /* Premium Google Web Font */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Sleek gradient background for header */
    .header-gradient {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        text-align: center;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    .header-gradient h1 {
        margin: 0 !important;
        padding-bottom: 0.5rem !important;
        font-weight: 700 !important;
        font-size: 2.5rem !important;
        background: linear-gradient(to right, #00e5ff, #12c2e9, #c471ed, #f64f59);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .header-gradient p {
        margin: 0 !important;
        font-size: 1.1rem !important;
        opacity: 0.8;
    }
    
    /* Glassmorphism Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-left: 5px solid #00c9ff;
        transition: all 0.3s ease-in-out;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(0, 229, 255, 0.1);
        border-left-color: #f64f59;
    }
    
    /* Styled buttons with micro-animations */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton>button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 4px 15px rgba(0, 229, 255, 0.25) !important;
    }
    
    /* Style headers */
    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
    }
    
    /* Custom container for Plotly charts */
    .chart-container {
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem;
        background: rgba(255, 255, 255, 0.02);
    }
</style>
""", unsafe_allow_html=True)

def build_flow_state(companies_df, tp_roles_df=None, transactions_df=None):
    nodes = []
    edges = []
    
    # Map granular OECD roles to visual lanes
    visual_category_map = {
        "Service Provider": "Service Provider",
        "Routine Manufacturer": "Contract Manufacturer",
        "Cost Plus Manufacturer": "Contract Manufacturer",
        "Commodity Trader": "Commodity Trader",
        "IP Principal": "IP Principal",
        "Distributor - TNMM": "Distributor",
        "Distributor - RPM": "Distributor"
    }

    # Segment configuration
    segment_configs = {
        "Commodity Trader": {"x": 50, "style": {'backgroundColor': '#e0f7fa', 'border': '2px solid #00acc1', 'color': 'black'}},
        "Contract Manufacturer": {"x": 350, "style": {'backgroundColor': '#e8f5e9', 'border': '2px solid #4caf50', 'color': 'black'}},
        "Service Provider": {"x": 350, "style": {'backgroundColor': '#f3e5f5', 'border': '2px solid #9c27b0', 'color': 'black'}},
        "IP Principal": {"x": 700, "style": {'backgroundColor': '#fff8e1', 'border': '2px solid #ffc107', 'color': 'black'}},
        "Distributor": {"x": 1050, "style": {'backgroundColor': '#e3f2fd', 'border': '2px solid #2196f3', 'color': 'black'}}
    }
    
    y_counters = {
        "Commodity Trader": 50,
        "Contract Manufacturer": 50,
        "Service Provider": 300,
        "IP Principal": 100,
        "Distributor": 50
    }
    
    # Role mapping
    roles_map = {}
    if tp_roles_df is not None:
        roles_map = dict(zip(tp_roles_df["Company Code"], tp_roles_df["TP Segment"]))

    for i, row in companies_df.iterrows():
        node_id = row["Company Code"]
        segment = roles_map.get(node_id, "Distributor - TNMM")
        
        # Get visual category for layout
        vis_cat = visual_category_map.get(segment, "Distributor")
        config = segment_configs.get(vis_cat, segment_configs["Distributor"])
        
        x = config["x"]
        y = y_counters[vis_cat]
        y_counters[vis_cat] += 150
        
        nodes.append(StreamlitFlowNode(
            id=node_id,
            pos=(x, y),
            data={'content': f"{row['Company Name']} ({row['Country Key']})\n{segment}"},
            style=config["style"],
            node_type='default',
            source_position='right',
            target_position='left'
        ))
    
    # Edges from transactions
    if transactions_df is not None and not transactions_df.empty:
        # Filter for IC transactions
        ic_flows = transactions_df[transactions_df["TypeOfSales"] == "IC"].groupby(["Company Code", "TradingPartner"]).size().reset_index()
        for _, row in ic_flows.iterrows():
            source = row["Company Code"]
            target = row["TradingPartner"]
            if source in [n.id for n in nodes] and target in [n.id for n in nodes]:
                edges.append(StreamlitFlowEdge(
                    id=f"{source}-{target}",
                    source=source,
                    target=target,
                    animated=True
                ))
            
    return StreamlitFlowState(nodes=nodes, edges=edges)

# 1. Load, cache and CLEAN data
@st.cache_data
def load_data():
    countries_df = pd.read_csv("data/All ISO, Countries, Currency, region.csv", sep=";")
    # Note: Renaming manual recommendation if mv fails: data/Cities_with_ISO.csv
    try:
        cities_df = pd.read_csv("data/Cities_with_ISO.csv", sep=",")
    except FileNotFoundError:
        cities_df = pd.read_csv("data/Citys_mit_ISO.csv", sep=",")
    
    countries_df['ISO3166-1-Alpha-3'] = countries_df['ISO3166-1-Alpha-3'].astype(str).str.strip()
    countries_df['Region Name'] = countries_df['Region Name'].astype(str).str.strip()
    countries_df['CLDR display name'] = countries_df['CLDR display name'].astype(str).str.strip()
    
    cities_df['ISO3166-1-Alpha-3'] = cities_df['ISO3166-1-Alpha-3'].astype(str).str.strip()
    cities_df['City'] = cities_df['City'].astype(str).str.strip()
    
    return countries_df, cities_df

try:
    countries_df, cities_df = load_data()
except FileNotFoundError:
    st.error("Please ensure that the CSV files are in the data directory.")
    st.stop()

# Cache for geocoding requests
@st.cache_data
def get_coordinates(city, country):
    if not city or not country or city == "Capital":
        return None, None
    geolocator = Nominatim(user_agent="company_generator_global_v7")
    try:
        location = geolocator.geocode(f"{city}, {country}")
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception:
        return None, None

def init_default_state():
    if 'company_data' not in st.session_state:
        demo_companies, demo_roles = get_demo_scenario()
        st.session_state['company_data'] = demo_companies
        st.session_state['tp_roles'] = demo_roles
        
        company_coords = {}
        map_coords = []
        for _, row in demo_companies.iterrows():
            if 'lat' in row and 'lon' in row:
                c_lat, c_lon = row['lat'], row['lon']
            else:
                c_lat, c_lon = get_coordinates(row['City'], row['Country Name'])
            
            if c_lat and c_lon:
                company_coords[row['Company Code']] = (c_lat, c_lon)
                map_coords.append({'lat': c_lat, 'lon': c_lon})
        st.session_state['company_coords'] = company_coords
        st.session_state['map_coords'] = map_coords
        
        df_mat_class, df_material = generate_materials(20)
        st.session_state['df_mat_class'] = df_mat_class
        st.session_state['df_material'] = df_material
        
        df_pnl, df_segments = generate_master_data()
        _, df_benchmark, _ = generate_config_data(demo_companies, df_segments)
        st.session_state['benchmark_data'] = df_benchmark

init_default_state()

st.markdown("<div class='header-gradient'><h1>Global Company & Material Data Generator</h1><p>Next-Generation Synthetic Data Generator for SAP PaPM Operational TP Demos</p></div>", unsafe_allow_html=True)

# Tab definitions
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Master Data & Map", "Material Configuration", "Export", "TP Network & Rules", "CIT Rates"])

with tab1:
    col1, col2, col3 = st.columns(3)

    with col1:
        regions = sorted(countries_df['Region Name'].dropna().unique().tolist())
        default_regions = ["Europe"] if "Europe" in regions else []
        selected_regions = st.multiselect("1. Select Region(s)", regions, default=default_regions)

    with col2:
        if selected_regions:
            filtered_countries = countries_df[countries_df['Region Name'].isin(selected_regions)]
        else:
            filtered_countries = pd.DataFrame(columns=countries_df.columns)

        all_country_names = sorted(filtered_countries['CLDR display name'].dropna().unique().tolist())
        default_countries = ["Germany", "United States", "Japan", "Brazil", "Australia"]
        selected_countries = st.multiselect("2. Select Country(ies)", all_country_names, default=[c for c in default_countries if c in all_country_names])

    with col3:
        countries_to_use = selected_countries if selected_countries else all_country_names

        if countries_to_use:
            selected_iso_codes = filtered_countries[filtered_countries['CLDR display name'].isin(countries_to_use)]['ISO3166-1-Alpha-3'].tolist()
            available_cities_df = cities_df[cities_df['ISO3166-1-Alpha-3'].isin(selected_iso_codes)]
            available_city_names = sorted(available_cities_df['City'].dropna().unique().tolist())
        else:
            available_cities_df = pd.DataFrame(columns=cities_df.columns)
            available_city_names = []

        # Spread out European cities
        default_cities = ["BERLIN", "MADRID", "ROME", "STOCKHOLM", "WARSAW"]
        selected_cities = st.multiselect("3. Select City(ies)", available_city_names, default=[c for c in default_cities if c in available_city_names])

    st.divider()

    st.subheader("Generation Options")
    st.write("**Transfer Pricing Role Distribution**")
    r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
    with r_col1:
        num_principals = st.number_input("IP Principals", min_value=1, value=2)
    with r_col2:
        num_distributors = st.number_input("Distributors", min_value=0, value=2)
    with r_col3:
        num_manufacturers = st.number_input("Contract Manufacturers", min_value=0, value=2)
    with r_col4:
        num_service_providers = st.number_input("Service Providers", min_value=0, value=1)
    with r_col5:
        num_traders = st.number_input("Commodity Traders", min_value=0, value=1)
    
    num_companies = num_principals + num_distributors + num_manufacturers + num_service_providers + num_traders
    st.info(f"Total companies: **{num_companies}**")

    st.divider()
    
    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
    with col_opt1:
        genre = st.selectbox("Company Genre", ["General", "Tech", "Health", "Food", "Logistics"])
    with col_opt2:
        group_currency = st.text_input("Group Currency", value="EUR", max_chars=3).upper()
    with col_opt3:
        num_materials_input = st.number_input("Number of Materials", min_value=1, max_value=5000, value=20)
    with col_opt4:
        num_transactions_input = st.number_input("Number of Transactions", min_value=10, max_value=50000, value=1000)

    st.write("**Advanced Simulation Parameters**")
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    with adv_col1:
        qty_max = st.slider("Max Qty per Transaction", min_value=10, max_value=5000, value=100)
    with adv_col2:
        opex_range = st.slider("OPEX % of Revenue Bounds", min_value=0.01, max_value=0.50, value=(0.08, 0.35), step=0.01)
    with adv_col3:
        service_fee_range = st.slider("Service Fee Bounds (EUR)", min_value=1000, max_value=100000, value=(5000, 25000), step=1000)

    if st.button("Generate Global Structure", type="primary"):
        if not countries_to_use:
            st.error("Please select at least one region or country.")
        else:
            st.session_state['role_counts'] = {
                "principals": num_principals,
                "distributors": num_distributors,
                "manufacturers": num_manufacturers,
                "service_providers": num_service_providers,
                "traders": num_traders
            }
            st.session_state['sim_params'] = {
                "qty_max": qty_max,
                "opex_min": opex_range[0],
                "opex_max": opex_range[1],
                "service_fee_min": service_fee_range[0],
                "service_fee_max": service_fee_range[1]
            }
            
            company_data = []
            progress_bar = st.progress(0, text="Generating companies...")
            cities_to_insert = list(selected_cities)

            for i in range(1, num_companies + 1):
                if cities_to_insert:
                    rand_city = cities_to_insert.pop(0)
                    city_rows = available_cities_df[available_cities_df['City'] == rand_city]
                    if not city_rows.empty:
                        iso3_code = city_rows.iloc[0]['ISO3166-1-Alpha-3']
                        country_row = countries_df[countries_df['ISO3166-1-Alpha-3'] == iso3_code].iloc[0]
                        rand_country = country_row['CLDR display name']
                    else:
                        rand_country = random.choice(countries_to_use)
                        country_row = filtered_countries[filtered_countries['CLDR display name'] == rand_country].iloc[0]
                        iso3_code = country_row['ISO3166-1-Alpha-3']
                else:
                    rand_country = random.choice(countries_to_use)
                    country_row = filtered_countries[filtered_countries['CLDR display name'] == rand_country].iloc[0]
                    iso3_code = country_row['ISO3166-1-Alpha-3']
                    country_cities = cities_df[cities_df['ISO3166-1-Alpha-3'] == iso3_code]
                    rand_city = random.choice(country_cities['City'].dropna().tolist()) if not country_cities.empty else "Capital"

                region_name = country_row['Region Name']
                currency = country_row['ISO4217-currency_alphabetic_code']
                currency = "EUR" if pd.isna(currency) else str(currency).split(',')[0]

                company_data.append({
                    "Reroll": False,
                    "Company Code": f"Co{str(i).zfill(2)}",
                    "Company Name": generate_company_name(genre),
                    "City": rand_city,
                    "Country Name": rand_country,
                    "Region": region_name,
                    "Country Key": iso3_code,
                    "Co Currency": currency,
                    "Group Currency": group_currency,  
                    "Language Key": "EN",
                    "Chart of Accounts": "COA"
                })
                progress_bar.progress(i / num_companies, text=f"Generating companies... ({i}/{num_companies})")

            st.session_state['company_data'] = pd.DataFrame(company_data)
            
            # Pre-populate coordinates mapping
            company_coords = {}
            map_coords = []
            for _, row in st.session_state['company_data'].iterrows():
                c_lat, c_lon = get_coordinates(row['City'], row['Country Name'])
                if c_lat and c_lon:
                    company_coords[row['Company Code']] = (c_lat, c_lon)
                    map_coords.append({'lat': c_lat, 'lon': c_lon})
            st.session_state['company_coords'] = company_coords
            st.session_state['map_coords'] = map_coords

            df_mat_class, df_material = generate_materials(num_materials_input)
            st.session_state['df_mat_class'] = df_mat_class
            st.session_state['df_material'] = df_material

            for key in ['flow_state', 'tp_roles', 'benchmark_data']:
                if key in st.session_state: del st.session_state[key]

            progress_bar.empty()
            st.rerun()

    if 'company_data' in st.session_state:
        df = st.session_state['company_data']
        st.subheader("Preview & Editing (Companies)")
        editor_country_options = countries_df['CLDR display name'].dropna().unique().tolist()
        editor_city_options = sorted(cities_df[cities_df['ISO3166-1-Alpha-3'].isin(filtered_countries['ISO3166-1-Alpha-3'].tolist())]['City'].dropna().unique().tolist()) if not filtered_countries.empty else sorted(cities_df['City'].dropna().unique().tolist())

        edited_df = st.data_editor(
            df, width='stretch', hide_index=True,
            column_config={
                "Reroll": st.column_config.CheckboxColumn("Reroll?", default=False),
                "Country Name": st.column_config.SelectboxColumn("Country", options=editor_country_options, required=True),
                "City": st.column_config.SelectboxColumn("City", options=editor_city_options, required=True)
            }
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Reroll selected names"):
                for idx, row in edited_df.iterrows():
                    if row['Reroll']:
                        edited_df.at[idx, 'Company Name'] = generate_company_name(genre)
                        edited_df.at[idx, 'Reroll'] = False
                st.session_state['company_data'] = edited_df
                st.rerun()

        with col_btn2:
            if st.button("Update Data & Map", type="secondary"):
                for idx, row in edited_df.iterrows():
                    c_name = row['Country Name']
                    c_row = countries_df[countries_df['CLDR display name'] == c_name]
                    if not c_row.empty:
                        edited_df.at[idx, 'Country Key'] = c_row.iloc[0]['ISO3166-1-Alpha-3']
                        edited_df.at[idx, 'Region'] = c_row.iloc[0]['Region Name']
                        currency = c_row.iloc[0]['ISO4217-currency_alphabetic_code']
                        edited_df.at[idx, 'Co Currency'] = "EUR" if pd.isna(currency) else str(currency).split(',')[0]

                st.session_state['company_data'] = edited_df
                company_coords = {}
                map_coords = []
                for _, row in edited_df.iterrows():
                    code = row['Company Code']
                    c_lat, c_lon = get_coordinates(row['City'], row['Country Name'])
                    if c_lat and c_lon:
                        company_coords[code] = (c_lat, c_lon)
                        map_coords.append({'lat': c_lat, 'lon': c_lon})
                st.session_state['company_coords'] = company_coords
                st.session_state['map_coords'] = map_coords
                st.rerun()

        st.divider()
        st.subheader("Global Presence (Map)")
        if 'map_coords' in st.session_state and st.session_state['map_coords']:
            st.map(pd.DataFrame(st.session_state['map_coords']), zoom=3, width='stretch')
        else:
            st.info("The map is currently in sleep mode. Click 'Update Data & Map' above to load locations.")

with tab2:
    st.subheader("Material Configuration")
    if 'df_material' not in st.session_state:
        st.info("Generate data in Tab 1 first to edit materials.")
    else:
        m_col1, m_col2 = st.columns([1, 2])
        with m_col1:
            st.write("**Customize Brands & Classes**")
            if 'mat_brands' not in st.session_state:
                st.session_state['mat_brands'] = ["AlphaTech", "BetaMed", "GammaFoods", "DeltaLogistics", "NexGen", "CoreSystems"]

            edited_brands = st.data_editor(pd.DataFrame(st.session_state['mat_brands'], columns=["Brand"]), num_rows="dynamic", hide_index=True)
            st.session_state['mat_brands'] = edited_brands["Brand"].tolist()
            st.session_state['df_mat_class'] = st.data_editor(st.session_state['df_mat_class'], num_rows="dynamic", hide_index=True)

            if st.button("Regenerate Materials"):
                _, st.session_state['df_material'] = generate_materials(
                    num_materials_input, brands=st.session_state['mat_brands'], mat_classes=st.session_state['df_mat_class']
                )
                st.rerun()

        with m_col2:
            st.write("**Material List**")
            st.session_state['df_material'] = st.data_editor(st.session_state['df_material'], width='stretch', hide_index=True, num_rows="dynamic")

with tab3:
    if 'company_data' in st.session_state:
        st.subheader("Export & Validation")
        if st.button("Generate Final Report", type="primary"):
            with st.spinner("Generating data..."):
                export_df = st.session_state['company_data'].copy()
                df_pnl, df_tp_segments = generate_master_data()
                role_counts = st.session_state.get('role_counts')

                if 'tp_roles' in st.session_state and 'benchmark_data' in st.session_state:
                    df_c_tp_segment = st.session_state['tp_roles']
                    df_benchmark = st.session_state['benchmark_data']
                    _, _, df_indirect_alloc = generate_config_data(export_df, df_tp_segments, role_counts=role_counts, custom_benchmarks=df_benchmark)
                else:
                    df_c_tp_segment, df_benchmark, df_indirect_alloc = generate_config_data(export_df, df_tp_segments, role_counts=role_counts)
                    st.session_state['tp_roles'] = df_c_tp_segment
                    st.session_state['benchmark_data'] = df_benchmark

                final_company_info = export_df.drop(columns=["Reroll", "Country Name", "Region"])
                final_region_mapping = pd.DataFrame({'Company code': export_df['Company Code'], 'Name': export_df['Company Name'], 'Country': export_df['Country Key'], 'Region': export_df['Region']})

                df_mat_class = st.session_state['df_mat_class']
                df_material = st.session_state['df_material']

                sp = st.session_state.get('sim_params', {})
                df_sales_tx, df_opex_tx = generate_transactions(
                    export_df, df_material, df_pnl, num_transactions_input, df_c_tp_segment,
                    qty_max=sp.get('qty_max', 100),
                    service_fee_min=sp.get('service_fee_min', 5000),
                    service_fee_max=sp.get('service_fee_max', 25000),
                    opex_min=sp.get('opex_min', 0.08),
                    opex_max=sp.get('opex_max', 0.35)
                )
                p_seg_sales, p_seg_opex, p_direct, p_indirect, p_total = calculate_allocations(df_sales_tx, df_opex_tx, export_df, df_benchmark, df_c_tp_segment, return_all=True)
                
                # Generate Transactional TP Adjustments
                df_tp_adjustments = generate_tp_adjustments(df_sales_tx, df_opex_tx, export_df, p_total, df_c_tp_segment, year=2025)

                st.session_state['last_report'] = {
                    'metrics': {
                        'revenue': p_total['Revenue'].sum(),
                        'opex': p_total['OPEX'].sum(),
                        'ebit': p_total['Final Operating Profit'].sum(),
                        'ic_volume': df_sales_tx[df_sales_tx["TypeOfSales"] == "IC"]["Total Amount Sales"].sum(),
                        'tp_adj_total': p_total['TP Adjustment'].abs().sum() / 2.0  # Symmetric sum, divided by 2
                    },
                    'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                    'p_total': p_total,
                    'sales_tx': df_sales_tx,
                    'opex_tx': df_opex_tx,
                    'tp_adjustments': df_tp_adjustments,
                    'df_benchmark': df_benchmark,
                    'companies': export_df
                }

                # Construct P_Total Allocation template structure matching the Excel headers
                p_total_template = p_total.copy()
                p_total_template = p_total_template.merge(export_df[["Company Code", "Region"]], on="Company Code", how="left")
                p_total_template["CoCo"] = p_total_template["Company Code"]
                p_total_template["Year"] = 2025
                p_total_template["PeriodRange"] = "12.2025"
                p_total_template["Total Sales"] = p_total_template["Revenue"]
                p_total_template["Total Amount Sales"] = p_total_template["Revenue"]
                p_total_template["Total COGS"] = p_total_template["COGS"]
                p_total_template["Total Amount COGS"] = -p_total_template["COGS"]
                p_total_template["EBIT"] = p_total_template["Final Operating Profit"]
                p_total_template["TP Function"] = p_total_template["TP Segment"]
                p_total_template["Sales Quatity"] = p_total_template["Sales Quantity"]
                p_total_template["RUNIT"] = p_total_template["Co Currency"] if "Co Currency" in p_total_template.columns else "EUR"
                p_total_template["GlobalCurrency"] = "EUR"

                # Combine OPEX with TP Adjustments dynamically for SD_Financials_OPEX sheet
                df_opex_combined = pd.concat([df_opex_tx, df_tp_adjustments], ignore_index=True)

                data_dict = {
                    'Company Info': final_company_info,
                    'Region Mapping': final_region_mapping,
                    'TPMD_PnL': df_pnl,
                    'TPMD_MaterialTypeClass': df_mat_class,
                    'TPMD_TPsegment': df_c_tp_segment[["Company Code", "TP Segment"]],
                    'TPMD_Material': df_material,
                    'C_TP Segment': df_c_tp_segment,
                    'C_Benchmark': df_benchmark,
                    'C_Indirect Allocation': df_indirect_alloc,
                    'SD_Financial_Sales_COGS': df_sales_tx,
                    'SD_Financials_OPEX': df_opex_combined,
                    'P_Segmentation_Sales_COGS': p_seg_sales,
                    'P_Segmentation_OPEX': p_seg_opex,
                    'P_Direct Allocation': p_direct,
                    'P_Indirect Allocation': p_indirect,
                    'P_Total Allocation': p_total_template
                }

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for sheet_name, df in data_dict.items():
                        df.to_excel(writer, index=False, sheet_name=sheet_name)

                st.session_state['last_report']['excel_data'] = output.getvalue()
                st.session_state['data_dict'] = data_dict
                st.success("Report successfully generated!")

        if 'last_report' in st.session_state:
            report = st.session_state['last_report']
            st.divider()
            st.write("### Operational TP Analytics Dashboard")
            
            # 1. Extract dataframes
            p_total = report['p_total'].copy()
            df_benchmark = report['df_benchmark'].copy()
            df_sales_tx = report['sales_tx'].copy()
            export_df = report['companies'].copy()
            
            # 2. Pre-calculate compliance rates
            df_comp = p_total.merge(df_benchmark[["TP Function", "Q1", "Q3"]], left_on="TP Segment", right_on="TP Function", how="left")
            pre_margins = []
            post_margins = []
            companies_list = []
            q1_list = []
            q3_list = []
            median_list = []
            
            for idx, r in df_comp.iterrows():
                if r["TP Segment"] == "IP Principal" or pd.isna(r["Q1"]):
                    continue
                pli = r["PLI Name"]
                rev = r["Revenue"]
                cogs = r["COGS"]
                opex = r["OPEX"]
                pre_op = r["Preliminary Operating Profit"]
                final_op = r["Final Operating Profit"]
                
                pre_val = 0.0
                post_val = 0.0
                
                if pli == "OM" and rev > 0:
                    pre_val = pre_op / rev
                    post_val = final_op / rev
                elif pli == "NCP" and (cogs + opex) > 0:
                    pre_val = pre_op / (cogs + opex)
                    post_val = final_op / (cogs + opex)
                elif pli == "Gross Margin" and rev > 0:
                    pre_val = (rev - cogs) / rev
                    post_val = (final_op + opex) / rev
                elif pli == "Gross Mark-up" and cogs > 0:
                    pre_val = (rev - cogs) / cogs
                    post_val = (final_op + opex) / cogs
                    
                pre_margins.append(pre_val)
                post_margins.append(post_val)
                companies_list.append(f"{r['Company Code']} ({r['TP Segment'].split(' - ')[0]})")
                q1_list.append(r["Q1"])
                q3_list.append(r["Q3"])
                median_list.append(r["Target Margin"])
            
            compliant_count = 0
            for i in range(len(companies_list)):
                if q1_list[i] <= post_margins[i] <= q3_list[i]:
                    compliant_count += 1
            compliance_rate = (compliant_count / len(companies_list)) * 100 if companies_list else 100.0
            
            # 3. Pre-calculate tax arbitrage
            countries_df_cit, _ = load_data()
            try:
                cit_df = pd.read_csv("data/CIT Rate Europe.csv")
            except FileNotFoundError:
                cit_df = pd.DataFrame()
            co_to_iso2 = dict(zip(countries_df_cit["ISO3166-1-Alpha-3"], countries_df_cit["ISO3166-1-Alpha-2"]))
            cit_rate_map = dict(zip(cit_df["iso-2"], cit_df["CIT rate"])) if not cit_df.empty else {}
            
            p_total["ISO2"] = p_total["Country Code"].map(co_to_iso2)
            p_total["CIT Rate"] = p_total["ISO2"].map(cit_rate_map).fillna(21.0)
            
            p_total["Tax Pre-Adj"] = p_total.apply(lambda r: max(0.0, r["Preliminary Operating Profit"] * (r["CIT Rate"] / 100.0)), axis=1)
            p_total["Tax Post-Adj"] = p_total.apply(lambda r: max(0.0, r["Final Operating Profit"] * (r["CIT Rate"] / 100.0)), axis=1)
            tax_saving = p_total["Tax Pre-Adj"].sum() - p_total["Tax Post-Adj"].sum()

            # Premium styled metric cards
            st.markdown("""
            <style>
            div[data-testid="stMetricValue"] > div {
                font-size: 1.5rem !important;
                white-space: normal !important;
                word-wrap: break-word;
            }
            </style>
            """, unsafe_allow_html=True)
            
            def fmt_num(n):
                if abs(n) >= 1_000_000_000: return f"{n/1_000_000_000:,.2f}B €"
                if abs(n) >= 1_000_000: return f"{n/1_000_000:,.2f}M €"
                if abs(n) >= 1_000: return f"{n/1_000:,.0f}K €"
                return f"{n:,.0f} €"

            st.write("#### Key Financial Totals")
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
            with m_col1:
                st.metric("Total Revenue", fmt_num(report['metrics']['revenue']))
            with m_col2:
                st.metric("Total OPEX", fmt_num(report['metrics']['opex']))
            with m_col3:
                st.metric("System EBIT", fmt_num(report['metrics']['ebit']))
            with m_col4:
                st.metric("Intercompany Volume", fmt_num(report['metrics']['ic_volume']))
            with m_col5:
                st.metric("Total TP True-ups", fmt_num(report['metrics']['tp_adj_total']))
            
            # Dynamic Sanity Checks
            total_ic_rev = df_sales_tx[df_sales_tx["TypeOfSales"] == "IC"]["Total Amount Sales"].sum()
            total_ic_exp = df_sales_tx[df_sales_tx["GL Account COGS"] == "500000"]["Total Amount COGS"].abs().sum()
            ic_diff = abs(total_ic_rev - total_ic_exp)
            ic_check = f"Passed ({fmt_num(ic_diff)})" if ic_diff < 1.0 else f"Failed ({fmt_num(ic_diff)})"
            
            tp_adj_net = report['tp_adjustments']['Total Amount'].sum() if 'tp_adjustments' in report else 0.0
            tp_check = fmt_num(tp_adj_net) if abs(tp_adj_net) >= 0.01 else "0 € (Bal)"

            # Validation Metrics Panel
            st.write("#### Operational TP Data Sanity & Validation Panel")
            v_col1, v_col2, v_col3, v_col4 = st.columns(4)
            with v_col1:
                st.metric("Symmetric IC Accounting Check", ic_check, help="Verifies that total Intercompany Revenue matches Intercompany Expense across all companies.")
            with v_col2:
                st.metric("Routine Compliance Rate", f"{compliance_rate:.1f}%", help="Percentage of routine entities whose operating margins lie within the arm's length benchmark range.")
            with v_col3:
                st.metric("Total True-ups Net Effect", tp_check, help="Symmetric TP Adjustments net to zero at the group level, confirming no profit is lost.")
            with v_col4:
                st.metric("Tax Arbitrage Net Effect", fmt_num(tax_saving), help="Group-wide tax savings/cost shift pre-adjustment vs post-adjustment.")
            
            # Draw charts
            st.write("#### Consolidated Profitability & Compliance")
            c_row1_col1, c_row1_col2 = st.columns(2)
            
            # 1. P&L Waterfall
            with c_row1_col1:
                rev = p_total['Revenue'].sum()
                cogs = p_total['COGS'].sum()
                gp = p_total['Gross Profit'].sum()
                opex = p_total['OPEX'].sum()
                pre_ebit = p_total['Preliminary Operating Profit'].sum()
                tp_adj = p_total['TP Adjustment'].sum()
                final_ebit = p_total['Final Operating Profit'].sum()
                
                fig_waterfall = go.Figure(go.Waterfall(
                    name = "Group P&L",
                    orientation = "v",
                    measure = ["relative", "relative", "total", "relative", "total", "relative", "total"],
                    x = ["Revenue", "COGS", "Gross Profit", "OPEX", "Pre-Adj EBIT", "TP Adjustments", "Final EBIT"],
                    textposition = "outside",
                    text = [f"{v/1e6:,.1f}M" for v in [rev, -cogs, gp, -opex, pre_ebit, tp_adj, final_ebit]],
                    y = [rev, -cogs, 0, -opex, 0, tp_adj, 0],
                    connector = {"line":{"color":"rgba(255,255,255,0.2)", "width":1}},
                    decreasing = {"marker":{"color":"#f64f59"}},
                    increasing = {"marker":{"color":"#12c2e9"}},
                    totals = {"marker":{"color":"#00e5ff"}}
                ))
                fig_waterfall.update_layout(
                    title="Consolidated Group P&L Flow (EUR)",
                    showlegend=False,
                    template="plotly_dark",
                    height=400,
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                st.plotly_chart(fig_waterfall, use_container_width=True)
                
            # 2. Compliance Ranges
            with c_row1_col2:
                if companies_list:
                    fig_comp = go.Figure()
                    
                    # Add benchmark range bars (Q1 to Q3)
                    for i in range(len(companies_list)):
                        fig_comp.add_shape(
                            type="rect",
                            x0=q1_list[i] * 100, y0=i - 0.2,
                            x1=q3_list[i] * 100, y1=i + 0.2,
                            line=dict(color="rgba(255, 255, 255, 0.1)", width=1),
                            fillcolor="rgba(255, 255, 255, 0.07)",
                            layer="below"
                        )
                    
                    # Add Q1, Median, Q3 markers
                    fig_comp.add_trace(go.Scatter(
                        x=[m * 100 for m in median_list],
                        y=companies_list,
                        mode="markers",
                        marker=dict(symbol="line-ns-open", size=14, line_width=3, color="#ffc107"),
                        name="Target Median"
                    ))
                    
                    # Add Pre-Adjustment Margin
                    fig_comp.add_trace(go.Scatter(
                        x=[m * 100 for m in pre_margins],
                        y=companies_list,
                        mode="markers",
                        marker=dict(symbol="circle", size=10, color="#f64f59"),
                        name="Pre-Adjustment"
                    ))
                    
                    # Add Post-Adjustment Margin
                    fig_comp.add_trace(go.Scatter(
                        x=[m * 100 for m in post_margins],
                        y=companies_list,
                        mode="markers",
                        marker=dict(symbol="diamond", size=11, color="#00e5ff"),
                        name="Post-Adjustment"
                    ))
                    
                    fig_comp.update_layout(
                        title="Arm's Length Range Compliance Chart (PLI Margin %)",
                        xaxis_title="Margin / Markup (%)",
                        yaxis_title="Routine Entities",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        template="plotly_dark",
                        height=400,
                        margin=dict(l=40, r=40, t=60, b=40)
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)
                else:
                    st.info("No routine entities available for compliance mapping.")
            
            # 3. 3D Intercompany Trade Flow Arcs Map (As requested: arclayer map showing transactions between countries)
            st.write("#### 🌐 Intercompany Trade Flow Arcs (3D Map)")
            import pydeck as pdk
            company_coords = st.session_state.get('company_coords', {})
            ic_sales = df_sales_tx[df_sales_tx["TypeOfSales"] == "IC"]
            
            arcs_data = []
            if company_coords and not ic_sales.empty:
                flow_totals = ic_sales.groupby(["Company Code", "TradingPartner"])["Total Amount Sales"].sum().reset_index()
                for _, r in flow_totals.iterrows():
                    sender = r["Company Code"]
                    receiver = r["TradingPartner"]
                    volume = r["Total Amount Sales"]
                    
                    if sender in company_coords and receiver in company_coords:
                        s_lat, s_lon = company_coords[sender]
                        r_lat, r_lon = company_coords[receiver]
                        
                        arcs_data.append({
                            "sender": sender,
                            "receiver": receiver,
                            "s_lat": s_lat,
                            "s_lon": s_lon,
                            "r_lat": r_lat,
                            "r_lon": r_lon,
                            "volume": volume,
                            "tooltip": f"{sender} ➔ {receiver}: {volume:,.0f} EUR"
                        })
            
            if arcs_data:
                df_arcs = pd.DataFrame(arcs_data)
                layer = pdk.Layer(
                    "ArcLayer",
                    df_arcs,
                    get_source_position="[s_lon, s_lat]",
                    get_target_position="[r_lon, r_lat]",
                    get_source_color="[0, 229, 255, 160]", # Bright Cyan
                    get_target_color="[246, 79, 89, 200]", # Coral Red
                    get_width="1 + (volume / 200000) * 3",
                    pickable=True,
                    auto_highlight=True
                )
                view_state = pdk.ViewState(
                    latitude=df_arcs["s_lat"].mean(),
                    longitude=df_arcs["s_lon"].mean(),
                    zoom=3.5,
                    pitch=45
                )
                r_map = pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip={"text": "{tooltip}"},
                    map_style=None
                )
                st.pydeck_chart(r_map)
            else:
                st.info("The 3D Arc Map is asleep. Make sure your generated companies have valid European/Global cities geocoded in Tab 1.")

            st.write("#### Trade Flows & Taxation Mapping")
            c_row2_col1, c_row2_col2 = st.columns(2)
            
            # 4. Intercompany Trade Matrix Heatmap
            with c_row2_col1:
                ic_sales = df_sales_tx[df_sales_tx["TypeOfSales"] == "IC"]
                if not ic_sales.empty:
                    trade_matrix = ic_sales.groupby(["Company Code", "TradingPartner"])["Total Amount Sales"].sum().unstack(fill_value=0)
                    trade_matrix = trade_matrix.reindex(index=sorted(trade_matrix.index), columns=sorted(trade_matrix.columns), fill_value=0)
                    
                    fig_matrix = px.imshow(
                        trade_matrix,
                        labels=dict(x="Receiver (Buyer)", y="Sender (Seller)", color="Trade Volume (EUR)"),
                        color_continuous_scale="Tealrose",
                        text_auto=".0f",
                        title="Intercompany Trade Flow Matrix (EUR)"
                    )
                    fig_matrix.update_layout(
                        template="plotly_dark",
                        height=400,
                        margin=dict(l=40, r=40, t=60, b=40)
                    )
                    st.plotly_chart(fig_matrix, use_container_width=True)
                else:
                    st.info("No intercompany trade flows found.")
                    
            # 5. Tax Arbitrage
            with c_row2_col2:
                fig_tax = go.Figure()
                
                # Profit bars
                fig_tax.add_trace(go.Bar(
                    x=p_total["Company Code"],
                    y=p_total["Preliminary Operating Profit"],
                    name="Pre-Adjustment OP",
                    marker_color="#f64f59",
                    opacity=0.75
                ))
                
                fig_tax.add_trace(go.Bar(
                    x=p_total["Company Code"],
                    y=p_total["Final Operating Profit"],
                    name="Post-Adjustment OP",
                    marker_color="#12c2e9",
                    opacity=0.85
                ))
                
                # Statutory rate line on right y-axis
                fig_tax.add_trace(go.Scatter(
                    x=p_total["Company Code"],
                    y=p_total["CIT Rate"],
                    name="CIT Rate (%)",
                    yaxis="y2",
                    line=dict(color="#ffc107", width=3, dash="dot"),
                    mode="lines+markers"
                ))
                
                fig_tax.update_layout(
                    title="Operating Profit vs Statutory CIT Rates",
                    xaxis_title="Company Code",
                    yaxis_title="Operating Profit (EUR)",
                    yaxis2=dict(
                        title="Statutory CIT Rate (%)",
                        overlaying="y",
                        side="right",
                        range=[0, 40]
                    ),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    template="plotly_dark",
                    height=400,
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                st.plotly_chart(fig_tax, use_container_width=True)

            st.divider()
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                file_name = f"OTP_Data_{report['timestamp']}.xlsx"
                st.download_button(label=f"Download SAP PaPM Dataset ('{file_name}')", data=report['excel_data'], file_name=file_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
            with col_d2:
                csv_data = df_comp.to_csv(index=False).encode('utf-8')
                st.download_button(label=f"Download Dashboard Data (CSV)", data=csv_data, file_name=f"OTP_Dashboard_{report['timestamp']}.csv", mime="text/csv", type="secondary")
    else:
        st.info("Generate data in Tab 1 first to enable export and analytics.")

with tab4:
    st.subheader("Interactive TP Network")
    if 'company_data' in st.session_state:
        if 'tp_roles' not in st.session_state or 'benchmark_data' not in st.session_state:
            export_df = st.session_state['company_data'].copy()
            _, df_tp_segments = generate_master_data()
            role_counts = st.session_state.get('role_counts')
            df_c_tp_segment, df_benchmark, _ = generate_config_data(export_df, df_tp_segments, role_counts=role_counts)
            st.session_state['tp_roles'] = df_c_tp_segment
            st.session_state['benchmark_data'] = df_benchmark

        st.info("Drag nodes to organize your supply chain.")
        if 'flow_state' not in st.session_state:
            export_df = st.session_state['company_data'].copy()
            df_pnl, _ = generate_master_data()
            sp = st.session_state.get('sim_params', {})
            df_sales_tx, _ = generate_transactions(
                export_df, st.session_state['df_material'], df_pnl, num_transactions_input, st.session_state['tp_roles'],
                qty_max=sp.get('qty_max', 100),
                service_fee_min=sp.get('service_fee_min', 5000),
                service_fee_max=sp.get('service_fee_max', 25000),
                opex_min=sp.get('opex_min', 0.08),
                opex_max=sp.get('opex_max', 0.35)
            )
            st.session_state.flow_state = build_flow_state(export_df, st.session_state['tp_roles'], df_sales_tx)

        st.session_state.flow_state = streamlit_flow('tp_network_flow', state=st.session_state.flow_state, fit_view=True, height=500, enable_pane_menu=True, enable_node_menu=True, enable_edge_menu=True, pan_on_drag=True, allow_zoom=True)
        
        st.divider()
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            st.subheader("TP Roles")
            st.session_state['tp_roles'] = st.data_editor(st.session_state['tp_roles'], width='stretch', hide_index=True, column_config={"TP Segment": st.column_config.SelectboxColumn("TP Segment", options=["Distributor - TNMM", "Distributor - RPM", "Routine Manufacturer", "Cost Plus Manufacturer", "IP Principal", "Service Provider", "Commodity Trader"], required=True)})
            if st.button("Apply Roles to Flow"):
                export_df = st.session_state['company_data'].copy()
                df_pnl, _ = generate_master_data()
                sp = st.session_state.get('sim_params', {})
                df_sales_tx, _ = generate_transactions(
                    export_df, st.session_state['df_material'], df_pnl, num_transactions_input, st.session_state['tp_roles'],
                    qty_max=sp.get('qty_max', 100),
                    service_fee_min=sp.get('service_fee_min', 5000),
                    service_fee_max=sp.get('service_fee_max', 25000),
                    opex_min=sp.get('opex_min', 0.08),
                    opex_max=sp.get('opex_max', 0.35)
                )
                st.session_state.flow_state = build_flow_state(export_df, st.session_state['tp_roles'], df_sales_tx)
                st.rerun()

        with col_ed2:
            st.subheader("Benchmarks")
            st.session_state['benchmark_data'] = st.data_editor(st.session_state['benchmark_data'], width='stretch', hide_index=True)
    else:
        st.info("Generate data in Tab 1 first to visualize the network.")

with tab5:
    st.subheader("Corporate Income Tax Rates in Europe")
    html_code = """
    <iframe title="Corporate Income Tax Rates in Europe" aria-label="Choropleth map" id="datawrapper-chart-aExmQ" src="https://datawrapper.dwcdn.net/aExmQ/2/" scrolling="no" frameborder="0" style="width: 0; min-width: 100% !important; border: none;" height="763" data-external="1"></iframe>
    <script type="text/javascript">window.addEventListener("message",function(a){if(void 0!==a.data["datawrapper-height"]){var e=document.querySelectorAll("iframe");for(var t in a.data["datawrapper-height"])for(var r,i=0;r=e[i];i++)if(r.contentWindow===a.source){var d=a.data["datawrapper-height"][t]+"px";r.style.height=d}}});</script>
    """
    components.html(html_code, height=800)
