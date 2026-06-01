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
    generate_config_data, generate_transactions, calculate_allocations
)

# Streamlit Flow Imports
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState

# Page Configuration
st.set_page_config(page_title="Company & Material Data Generator", layout="wide")

def build_flow_state(companies_df, tp_roles_df=None, transactions_df=None):
    nodes = []
    edges = []
    
    # Map granular OECD roles to visual lanes
    visual_category_map = {
        "Service Provider": "Service Provider",
        "Routine Manufacturer": "Contract Manufacturer",
        "Cost Plus Manufacturer": "Contract Manufacturer",
        "Commodity Trader": "Service Provider",
        "IP Principal": "IP Principal",
        "Distributor - TNMM": "Distributor",
        "Distributor - RPM": "Distributor"
    }

    # Segment configuration
    segment_configs = {
        "Service Provider": {"x": 100, "style": {'backgroundColor': '#f3e5f5', 'border': '2px solid #9c27b0', 'color': 'black'}},
        "Contract Manufacturer": {"x": 100, "style": {'backgroundColor': '#e8f5e9', 'border': '2px solid #4caf50', 'color': 'black'}},
        "IP Principal": {"x": 500, "style": {'backgroundColor': '#fff8e1', 'border': '2px solid #ffc107', 'color': 'black'}},
        "Distributor": {"x": 900, "style": {'backgroundColor': '#e3f2fd', 'border': '2px solid #2196f3', 'color': 'black'}}
    }
    
    y_counters = {
        "Service Provider": 0,
        "Contract Manufacturer": 600,  # Big vertical gap
        "IP Principal": 0,
        "Distributor": 0
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
    except GeocoderTimedOut:
        return None, None

st.title("Global Company & Material Data Generator")

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
        selected_countries = st.multiselect("2. Select Country(ies)", all_country_names)

    with col3:
        countries_to_use = selected_countries if selected_countries else all_country_names

        if countries_to_use:
            selected_iso_codes = filtered_countries[filtered_countries['CLDR display name'].isin(countries_to_use)]['ISO3166-1-Alpha-3'].tolist()
            available_cities_df = cities_df[cities_df['ISO3166-1-Alpha-3'].isin(selected_iso_codes)]
            available_city_names = sorted(available_cities_df['City'].dropna().unique().tolist())
        else:
            available_cities_df = pd.DataFrame(columns=cities_df.columns)
            available_city_names = []

        selected_cities = st.multiselect("3. Select City(ies)", available_city_names)

    st.divider()

    st.subheader("Generation Options")
    st.write("**Transfer Pricing Role Distribution**")
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    with r_col1:
        num_principals = st.number_input("IP Principals", min_value=1, value=2)
    with r_col2:
        num_distributors = st.number_input("Distributors", min_value=0, value=2)
    with r_col3:
        num_manufacturers = st.number_input("Contract Manufacturers", min_value=0, value=2)
    with r_col4:
        num_service_providers = st.number_input("Service Providers", min_value=0, value=1)
    
    num_companies = num_principals + num_distributors + num_manufacturers + num_service_providers
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
        num_transactions_input = st.number_input("Number of Transactions", min_value=10, max_value=50000, value=100)

    if st.button("Generate Global Structure", type="primary"):
        if not countries_to_use:
            st.error("Please select at least one region or country.")
        else:
            st.session_state['role_counts'] = {
                "principals": num_principals,
                "distributors": num_distributors,
                "manufacturers": num_manufacturers,
                "service_providers": num_service_providers
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
            df_mat_class, df_material = generate_materials(num_materials_input)
            st.session_state['df_mat_class'] = df_mat_class
            st.session_state['df_material'] = df_material

            for key in ['map_coords', 'flow_state', 'tp_roles', 'benchmark_data']:
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
                map_coords = []
                unique_locations = edited_df[['City', 'Country Name']].drop_duplicates().head(30)
                for _, row in unique_locations.iterrows():
                    c_lat, c_lon = get_coordinates(row['City'], row['Country Name'])
                    if c_lat and c_lon: map_coords.append({'lat': c_lat, 'lon': c_lon})
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
                    _, _, df_indirect_alloc = generate_config_data(export_df, df_tp_segments, role_counts=role_counts)
                else:
                    df_c_tp_segment, df_benchmark, df_indirect_alloc = generate_config_data(export_df, df_tp_segments, role_counts=role_counts)
                    st.session_state['tp_roles'] = df_c_tp_segment
                    st.session_state['benchmark_data'] = df_benchmark

                final_company_info = export_df.drop(columns=["Reroll", "Country Name", "Region"])
                final_region_mapping = pd.DataFrame({'Company code': export_df['Company Code'], 'Name': export_df['Company Name'], 'Country': export_df['Country Key'], 'Region': export_df['Region']})

                df_mat_class = st.session_state['df_mat_class']
                df_material = st.session_state['df_material']

                df_sales_tx, df_opex_tx = generate_transactions(export_df, df_material, df_pnl, num_transactions_input, df_c_tp_segment)
                p_total = calculate_allocations(df_sales_tx, df_opex_tx, export_df, df_benchmark, df_c_tp_segment)

                st.session_state['last_report'] = {
                    'metrics': {'revenue': p_total['Revenue'].sum(), 'opex': p_total['OPEX'].sum(), 'ebit': p_total['Final Operating Profit'].sum()},
                    'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
                }

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_company_info.to_excel(writer, index=False, sheet_name='Company Info')
                    final_region_mapping.to_excel(writer, index=False, sheet_name='Region Mapping')
                    df_pnl.to_excel(writer, index=False, sheet_name='TPMD_PnL')
                    df_mat_class.to_excel(writer, index=False, sheet_name='TPMD_MaterialTypeClass')
                    df_c_tp_segment[["Company Code", "TP Segment"]].to_excel(writer, index=False, sheet_name='TPMD_TPsegment')
                    df_material.to_excel(writer, index=False, sheet_name='TPMD_Material')
                    df_c_tp_segment.to_excel(writer, index=False, sheet_name='C_TP Segment')
                    df_benchmark.to_excel(writer, index=False, sheet_name='C_Benchmark')
                    df_indirect_alloc.to_excel(writer, index=False, sheet_name='C_Indirect Allocation')
                    df_sales_tx.to_excel(writer, index=False, sheet_name='SD_Financial_Sales_COGS')
                    df_opex_tx.to_excel(writer, index=False, sheet_name='SD_Financials_OPEX')
                    p_total.to_excel(writer, index=False, sheet_name='P_Total Allocation')

                st.session_state['last_report']['excel_data'] = output.getvalue()
                st.success("Report successfully generated!")

        if 'last_report' in st.session_state:
            report = st.session_state['last_report']
            st.divider()
            st.write("### Validation Dashboard")
            val_col1, val_col2, val_col3 = st.columns(3)
            with val_col1: st.metric("Total Revenue", f"{report['metrics']['revenue']:,.2f} EUR")
            with val_col2: st.metric("Total OPEX", f"{report['metrics']['opex']:,.2f} EUR")
            with val_col3: st.metric("System EBIT", f"{report['metrics']['ebit']:,.2f} EUR")

            file_name = f"OTP_Data_{report['timestamp']}.xlsx"
            st.download_button(label=f"Download '{file_name}'", data=report['excel_data'], file_name=file_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    else:
        st.info("Generate data in Tab 1 first to enable export.")

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
            df_sales_tx, _ = generate_transactions(export_df, st.session_state['df_material'], df_pnl, num_transactions_input, st.session_state['tp_roles'])
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
                df_sales_tx, _ = generate_transactions(export_df, st.session_state['df_material'], df_pnl, num_transactions_input, st.session_state['tp_roles'])
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
