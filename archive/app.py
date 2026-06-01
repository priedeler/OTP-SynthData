import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from mimesis import Finance
from mimesis.locales import Locale
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import io
import random
from datetime import datetime
import numpy as np

# Streamlit Flow Imports
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState

# Konfiguration der Seite
st.set_page_config(page_title="Company & Material Data Generator", layout="wide")

# ... rest of functions ...

def build_flow_state(companies_df, tp_roles_df=None, transactions_df=None):
    nodes = []
    edges = []
    
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
        segment = roles_map.get(node_id, "Distributor")
        
        config = segment_configs.get(segment, segment_configs["Distributor"])
        x = config["x"]
        y = y_counters[segment]
        y_counters[segment] += 150
        
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

# 1. Daten laden, cachen und BEREINIGEN (Wichtig für funktionierende Filter!)
@st.cache_data
def load_data():
    countries_df = pd.read_csv("All ISO, Countries, Currency, region.csv", sep=";")
    cities_df = pd.read_csv("Citys_mit_ISO.csv", sep=",")
    
    # Unsichtbare Leerzeichen entfernen, damit der Filter nicht abbricht!
    countries_df['ISO3166-1-Alpha-3'] = countries_df['ISO3166-1-Alpha-3'].astype(str).str.strip()
    countries_df['Region Name'] = countries_df['Region Name'].astype(str).str.strip()
    countries_df['CLDR display name'] = countries_df['CLDR display name'].astype(str).str.strip()
    
    cities_df['ISO3166-1-Alpha-3'] = cities_df['ISO3166-1-Alpha-3'].astype(str).str.strip()
    cities_df['City'] = cities_df['City'].astype(str).str.strip()
    
    return countries_df, cities_df

try:
    countries_df, cities_df = load_data()
except FileNotFoundError:
    st.error("Bitte stelle sicher, dass die CSV-Dateien im selben Verzeichnis liegen.")
    st.stop()

# Cache für die Geocoding-Anfragen
@st.cache_data
def get_coordinates(city, country):
    if not city or not country or city == "Hauptstadt":
        return None, None
    geolocator = Nominatim(user_agent="company_generator_global_v7")
    try:
        location = geolocator.geocode(f"{city}, {country}")
        if location:
            return location.latitude, location.longitude
        return None, None
    except GeocoderTimedOut:
        return None, None

def generate_company_name(genre):
    finance = Finance(locale=Locale.EN)
    name = finance.company()
    if genre == "Tech": name += " Technologies"
    elif genre == "Health": name += " Healthcare"
    elif genre == "Food": name += " Foods"
    elif genre == "Logistics": name += " Logistics"
    return name

def generate_materials(num_materials, brands=None, mat_classes=None):
    # 1. TPMD_MaterialTypeClass (Statische Stammdaten)
    if mat_classes is None:
        mat_classes_list = [
            {"Valuation Class": "OMP", "Type of Sales": "Intercompany & 3P", "Description": "Own Manufactured Products"},
            {"Valuation Class": "MER", "Type of Sales": "3P", "Description": "Merchandise"},
            {"Valuation Class": "RAW", "Type of Sales": "Intercompany", "Description": "Raw Materials"}
        ]
        df_mat_class = pd.DataFrame(mat_classes_list)
    else:
        df_mat_class = mat_classes.copy()
    
    # 2. TPMD_Material (Dynamische Stammdaten)
    materials = []
    # Ein paar generische Marken passend zu deinen Genres
    if brands is None:
        brands = ["AlphaTech", "BetaMed", "GammaFoods", "DeltaLogistics", "NexGen", "CoreSystems"]
    
    for i in range(1, num_materials + 1):
        mat_id = f"MAT-{str(i).zfill(4)}"
        brand = random.choice(brands) if isinstance(brands, list) and brands else "Generic"
        
        # Logische Preisgestaltung (Raw < IC < 3P)
        raw_price = round(random.uniform(5.0, 50.0), 2)
        ic_price = round(raw_price * random.uniform(1.15, 1.40), 2) # 15-40% Aufschlag für IC
        mer_price = round(raw_price * random.uniform(1.10, 1.30), 2)
        tp_price = round(max(ic_price, mer_price) * random.uniform(1.30, 2.00), 2) # Höchste Marge für den Endkunden
        
        qty = random.randint(100, 5000)
        
        materials.append({
            "Material": mat_id,
            "Brand": brand,
            "Raw Material Price": raw_price,
            "IC Sales Price": ic_price,
            "MER Material Price": mer_price,
            "3P Sales Price": tp_price,
            "Column1": "", # Platzhalter aus dem Template
            "Quantities for Jan 2025": qty
        })
        
    df_material = pd.DataFrame(materials)
    return df_mat_class, df_material

def generate_master_data():
    # TPMD_PnL
    pnl_data = [
        {"P&L line": "Sales - IC", "MPR Account": "400000"},
        {"P&L line": "Sales - 3P", "MPR Account": "410000"},
        {"P&L line": "COGS - IC", "MPR Account": "500000"},
        {"P&L line": "COGS - 3P", "MPR Account": "510000"},
        {"P&L line": "Marketing", "MPR Account": "600000"},
        {"P&L line": "R&D", "MPR Account": "610000"},
        {"P&L line": "General Administration", "MPR Account": "620000"},
        {"P&L line": "Logistics", "MPR Account": "630000"}
    ]
    df_pnl = pd.DataFrame(pnl_data)

    # TPMD_TPsegment
    segments = [
        {"TP Segment key": "DIST", "TP Segment description": "Distributor"},
        {"TP Segment key": "CM", "TP Segment description": "Contract Manufacturer"},
        {"TP Segment key": "PRIN", "TP Segment description": "IP Principal"},
        {"TP Segment key": "SERV", "TP Segment description": "Service Provider"}
    ]
    df_segments = pd.DataFrame(segments)
    
    return df_pnl, df_segments

def generate_config_data(companies_df, segments_df, role_counts=None):
    # C_TP Segment
    tp_segments = []
    
    if role_counts:
        # Create a deterministic pool based on user input
        roles_pool = (
            ["IP Principal"] * role_counts.get("principals", 1) +
            ["Distributor"] * role_counts.get("distributors", 0) +
            ["Contract Manufacturer"] * role_counts.get("manufacturers", 0) +
            ["Service Provider"] * role_counts.get("service_providers", 0)
        )
        # Ensure pool matches number of companies
        while len(roles_pool) < len(companies_df):
            roles_pool.append("Distributor")
        roles_pool = roles_pool[:len(companies_df)]
    else:
        # Fallback to random if no counts provided
        segments = segments_df["TP Segment description"].tolist()
        roles_pool = [random.choice(segments) for _ in range(len(companies_df))]

    for i, (_, row) in enumerate(companies_df.iterrows()):
        tp_segments.append({
            "Company Code": row["Company Code"],
            "#": "",
            "Pri": 1,
            "TP Segment": roles_pool[i],
            "Column1": "",
            "Type of Sales": "3P",
            "Valuation Class": "OMP",
            "Trading Partner?": "No",
            "Material Number": "*",
            "Valid from": "01.01.2025",
            "Valid to": "31.12.2025"
        })
    df_c_tp_segment = pd.DataFrame(tp_segments)

    # C_Benchmark
    benchmarks = [
        {"TP Function": "Distributor", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "OM", "PLI Formula": "EBIT/Sales", "Q1": 0.02, "Median": 0.035, "Q3": 0.05, "Valid from": "01.01.2025", "Valid to": "31.12.2025", "User ID": "SYS"},
        {"TP Function": "Contract Manufacturer", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "NCP", "PLI Formula": "EBIT/Total Cost", "Q1": 0.05, "Median": 0.075, "Q3": 0.10, "Valid from": "01.01.2025", "Valid to": "31.12.2025", "User ID": "SYS"},
        {"TP Function": "IP Principal", "TP Method": "CUP", "Price Setting": "Fixed", "PLI Name": "Residual", "PLI Formula": "Residual", "Q1": 0.10, "Median": 0.15, "Q3": 0.25, "Valid from": "01.01.2025", "Valid to": "31.12.2025", "User ID": "SYS"},
        {"TP Function": "Service Provider", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "Mark-up", "PLI Formula": "EBIT/Total Cost", "Q1": 0.03, "Median": 0.05, "Q3": 0.07, "Valid from": "01.01.2025", "Valid to": "31.12.2025", "User ID": "SYS"}
    ]
    df_benchmark = pd.DataFrame(benchmarks)

    # C_Indirect Allocation
    indirect_alloc = []
    pnl_lines = ["Marketing", "R&D", "General Administration", "Logistics"]
    for line in pnl_lines:
        indirect_alloc.append({
            "P&Ll line Item": line,
            "Account": "*",
            "Allocation Key": random.choice(["Headcount", "Revenue", "Floor Space"]),
            "User ID": "SYS"
        })
    df_indirect_alloc = pd.DataFrame(indirect_alloc)

    return df_c_tp_segment, df_benchmark, df_indirect_alloc

def generate_transactions(companies_df, materials_df, pnl_df, num_transactions, df_c_tp_segment):
    sales_tx = []
    opex_tx = []
    
    company_codes = companies_df["Company Code"].tolist()
    
    # Mappings for efficiency
    co_to_country = dict(zip(companies_df["Company Code"], companies_df["Country Key"]))
    co_to_name = dict(zip(companies_df["Company Code"], companies_df["Company Name"]))
    co_to_currency = dict(zip(companies_df["Company Code"], companies_df["Co Currency"]))
    co_to_segment = dict(zip(df_c_tp_segment["Company Code"], df_c_tp_segment["TP Segment"]))
    
    # Segment groupings for routing
    principals = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "IP Principal"]["Company Code"].tolist()
    distributors = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "Distributor"]["Company Code"].tolist()
    manufacturers = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "Contract Manufacturer"]["Company Code"].tolist()
    service_providers = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "Service Provider"]["Company Code"].tolist()
    
    # PnL accounts
    ic_sales_acc = "400000"
    tp_sales_acc = "410000"
    ic_cogs_acc = "500000"
    tp_cogs_acc = "510000"
    
    # Track revenue per company for OPEX scaling
    revenue_tracker = {code: 0 for code in company_codes}

    for flow_id in range(num_transactions):
        # 1. Randomly select material, qty, and period
        material = materials_df.sample(n=1).iloc[0]
        qty = random.randint(1, 100)
        month = random.randint(1, 12)
        period = f"{str(month).zfill(2)}.2025"

        # 2. Trace Supply Chain Flows
        
        # A. MANUFACTURING LEG (CM -> PRIN)
        current_buyer = None
        if manufacturers and principals:
            seller = random.choice(manufacturers)
            buyer = random.choice(principals)
            
            price_sales = material["IC Sales Price"]
            price_cogs = material["Raw Material Price"]
            revenue = round(qty * price_sales, 2)
            cogs = round(qty * price_cogs, 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": 2025,
                "PeriodRange": period,
                "GL Account Sales": ic_sales_acc,
                "GL Description Sales": "Sales",
                "GL Account COGS": ic_cogs_acc,
                "GL Description COGS": "COGS",
                "MaterialNumber": material["Material"],
                "Brand": material["Brand"],
                "BusinessType": "Sales",
                "ValuationClass": "OMP",
                "TradingPartner": buyer,
                "Trading Partner": buyer,
                "Trading Partner Region": "Global",
                "TypeOfSales": "IC",
                "RUNIT": co_to_currency[seller],
                "GlobalCurrency": "EUR",
                "Price Sales": price_sales,
                "Price COGS": price_cogs,
                "Total Sales": qty,
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs,
                "Column": ""
            })
            revenue_tracker[seller] += revenue
            current_buyer = buyer

        # B. PRINCIPAL LEG (PRIN -> DIST)
        prev_buyer = current_buyer
        if principals and distributors:
            seller = prev_buyer if prev_buyer else random.choice(principals)
            buyer = random.choice(distributors)
            
            # If we had a CM leg, PRIN's COGS must match CM's Sales
            price_cogs = material["IC Sales Price"] if prev_buyer else material["Raw Material Price"]
            price_sales = material["MER Material Price"]
            
            revenue = round(qty * price_sales, 2)
            cogs = round(qty * price_cogs, 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": 2025,
                "PeriodRange": period,
                "GL Account Sales": ic_sales_acc,
                "GL Description Sales": "Sales",
                "GL Account COGS": ic_cogs_acc,
                "GL Description COGS": "COGS",
                "MaterialNumber": material["Material"],
                "Brand": material["Brand"],
                "BusinessType": "Sales",
                "ValuationClass": "OMP",
                "TradingPartner": buyer,
                "Trading Partner": buyer,
                "Trading Partner Region": "Global",
                "TypeOfSales": "IC",
                "RUNIT": co_to_currency[seller],
                "GlobalCurrency": "EUR",
                "Price Sales": price_sales,
                "Price COGS": price_cogs,
                "Total Sales": qty,
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs,
                "Column": ""
            })
            revenue_tracker[seller] += revenue
            current_buyer = buyer
        elif principals and not distributors:
            # PRIN sells directly to EXTERNAL
            seller = prev_buyer if prev_buyer else random.choice(principals)
            buyer = "EXTERNAL"
            
            price_cogs = material["IC Sales Price"] if prev_buyer else material["Raw Material Price"]
            price_sales = material["3P Sales Price"]
            
            revenue = round(qty * price_sales, 2)
            cogs = round(qty * price_cogs, 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": 2025,
                "PeriodRange": period,
                "GL Account Sales": tp_sales_acc,
                "GL Description Sales": "Sales",
                "GL Account COGS": tp_cogs_acc,
                "GL Description COGS": "COGS",
                "MaterialNumber": material["Material"],
                "Brand": material["Brand"],
                "BusinessType": "Sales",
                "ValuationClass": "OMP",
                "TradingPartner": buyer,
                "Trading Partner": buyer,
                "Trading Partner Region": "Global",
                "TypeOfSales": "3P",
                "RUNIT": co_to_currency[seller],
                "GlobalCurrency": "EUR",
                "Price Sales": price_sales,
                "Price COGS": price_cogs,
                "Total Sales": qty,
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs,
                "Column": ""
            })
            revenue_tracker[seller] += revenue

        # C. DISTRIBUTION LEG (DIST -> EXTERNAL)
        prev_buyer = current_buyer
        if distributors:
            seller = prev_buyer if prev_buyer else random.choice(distributors)
            buyer = "EXTERNAL"
            
            # If we had a PRIN leg, DIST's COGS must match PRIN's Sales
            price_cogs = material["MER Material Price"] if prev_buyer else material["MER Material Price"]
            price_sales = material["3P Sales Price"]
            
            revenue = round(qty * price_sales, 2)
            cogs = round(qty * price_cogs, 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": 2025,
                "PeriodRange": period,
                "GL Account Sales": tp_sales_acc,
                "GL Description Sales": "Sales",
                "GL Account COGS": tp_cogs_acc,
                "GL Description COGS": "COGS",
                "MaterialNumber": material["Material"],
                "Brand": material["Brand"],
                "BusinessType": "Sales",
                "ValuationClass": "OMP",
                "TradingPartner": buyer,
                "Trading Partner": buyer,
                "Trading Partner Region": "Global",
                "TypeOfSales": "3P",
                "RUNIT": co_to_currency[seller],
                "GlobalCurrency": "EUR",
                "Price Sales": price_sales,
                "Price COGS": price_cogs,
                "Total Sales": qty,
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs,
                "Column": ""
            })
            revenue_tracker[seller] += revenue

        # D. SERVICE PROVIDERS (20% chance)
        if service_providers and random.random() < 0.20:
            seller = random.choice(service_providers)
            buyer = random.choice(principals) if principals else (random.choice(distributors) if distributors else random.choice(company_codes))
            
            service_fee = round(random.uniform(5000, 25000), 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": 2025,
                "PeriodRange": period,
                "GL Account Sales": ic_sales_acc,
                "GL Description Sales": "Service Fee",
                "GL Account COGS": ic_cogs_acc,
                "GL Description COGS": "Cost of Services",
                "MaterialNumber": "*",
                "Brand": "*",
                "BusinessType": "Service",
                "ValuationClass": "*",
                "TradingPartner": buyer,
                "Trading Partner": buyer,
                "Trading Partner Region": "Global",
                "TypeOfSales": "IC",
                "RUNIT": co_to_currency[seller],
                "GlobalCurrency": "EUR",
                "Price Sales": service_fee,
                "Price COGS": 0,
                "Total Sales": 1,
                "Total Amount Sales": service_fee,
                "Total Amount COGS": 0,
                "Column": ""
            })
            revenue_tracker[seller] += service_fee

    # OPEX transactions (Scaled to Revenue)
    opex_accounts = [("600000", "Marketing"), ("610000", "R&D"), ("620000", "General Admin"), ("630000", "Logistics")]
    for code in company_codes:
        segment = co_to_segment.get(code)
        
        # Calculate Annual OPEX
        revenue = revenue_tracker.get(code, 0)
        if revenue > 0:
            annual_opex = revenue * random.uniform(0.10, 0.25)
        else:
            # Baseline for cost centers (Principals/Service Providers with no direct 3P revenue)
            annual_opex = random.uniform(50000, 150000)
            
        amount_per_entry = annual_opex / (len(opex_accounts) * 12)

        for acc_code, acc_desc in opex_accounts:
            for month in range(1, 13):
                period = f"{str(month).zfill(2)}.2025"
                # Add slight monthly variance
                monthly_amount = round(amount_per_entry * random.uniform(0.85, 1.15), 2)
                
                # Service Providers mostly serve Principals
                if segment == "Service Provider" and principals:
                    partner = random.choice(principals)
                else:
                    partner = "VARIOUS"
                    
                opex_tx.append({
                    "Company Code": code,
                    "Company": co_to_name[code],
                    "Country Code": co_to_country[code],
                    "Country": co_to_country[code],
                    "Region CoCo": "Europe",
                    "Year": 2025,
                    "PeriodRange": period,
                    "GL Account": acc_code,
                    "GL Description": acc_desc,
                    "MaterialNumber": "*",
                    "Brand": "*",
                    "BusinessType": "OPEX",
                    "ValuationClass": "*",
                    "TradingPartner": partner,
                    "Trading Partner": partner,
                    "Trading": partner,
                    "TypeOfSales": "OPEX",
                    "RUNIT": co_to_currency[code],
                    "GlobalCurrency": "EUR",
                    "Price": 0,
                    "Total Sales": 0,
                    "Total Amount": monthly_amount
                })

    return pd.DataFrame(sales_tx), pd.DataFrame(opex_tx)

def calculate_allocations(sales_tx, opex_tx, companies_df, df_benchmark, df_c_tp_segment):
    # 1. P_Segmentation_Sales_COGS
    p_seg_sales = sales_tx.copy()
    p_seg_sales.rename(columns={"Region CoCo": "Region", "Trading Partner": "Trading Partner Country"}, inplace=True)
    p_seg_sales["TP Function"] = "Distributor"
    if "Column" in p_seg_sales.columns:
        p_seg_sales.drop(columns=["Column"], inplace=True)

    # 2. P_Segmentation_OPEX
    p_seg_opex = opex_tx.copy()
    p_seg_opex.rename(columns={
        "Region CoCo": "Region",
        "GL Account": "GL Account Sales",
        "GL Description": "GL Description Sales",
        "Total Amount": "Total Amount Sales",
        "Trading Partner": "Trading Partner Country",
        "Trading": "Trading Partner Region"
    }, inplace=True)
    p_seg_opex["CoCo"] = p_seg_opex["Company Code"]
    p_seg_opex["GL Account COGS"] = ""
    p_seg_opex["GL Description COGS"] = ""
    p_seg_opex["Total Amount COGS"] = 0
    p_seg_opex["Price Sales"] = 0
    p_seg_opex["Price COGS"] = 0
    p_seg_opex["TP Function"] = "Distributor"
    
    # 3. P_Direct Allocation
    p_direct = p_seg_opex.copy()
    
    # 4. P_Indirect Allocation
    p_indirect = opex_tx.copy()
    p_indirect.rename(columns={"Region CoCo": "Region", "Trading": "Trading Partner Region", "Trading Partner": "Trading Partner Country"}, inplace=True)
    p_indirect["CoCo"] = p_indirect["Company Code"]

    # 5. P_Total Allocation (TP Rule Engine)
    # Start with an aggregated view of Sales and COGS per Company
    p_total = sales_tx.groupby(["Company Code", "Company", "Country Code", "Country", "Co Currency" if "Co Currency" in sales_tx.columns else "RUNIT"]).agg({
        "Total Amount Sales": "sum",
        "Total Amount COGS": "sum",
        "Total Sales": "sum"
    }).reset_index()
    
    p_total.rename(columns={"Total Sales": "Sales Quantity", "Total Amount Sales": "Revenue", "Total Amount COGS": "COGS"}, inplace=True)
    
    # 2. Standardize Expense Sign Conventions (COGS and OPEX as absolute values)
    p_total["COGS"] = p_total["COGS"].abs()
    
    # Add OPEX per company
    opex_sum = opex_tx.groupby("Company Code")["Total Amount"].sum().reset_index()
    opex_sum.rename(columns={"Total Amount": "OPEX"}, inplace=True)
    p_total = p_total.merge(opex_sum, on="Company Code", how="left").fillna(0)
    p_total["OPEX"] = p_total["OPEX"].abs()
    
    # Map TP Segments and Benchmarks to Companies
    p_total = p_total.merge(df_c_tp_segment[["Company Code", "TP Segment"]], on="Company Code", how="left")
    # Include PLI Name to identify Residual entities
    p_total = p_total.merge(df_benchmark[["TP Function", "TP Method", "Median", "PLI Name"]], left_on="TP Segment", right_on="TP Function", how="left")
    p_total.rename(columns={"Median": "Target Margin"}, inplace=True)
    
    # 2. Calculate Preliminary Operating Profit: Revenue - COGS - OPEX
    p_total["Preliminary Operating Profit"] = p_total["Revenue"] - p_total["COGS"] - p_total["OPEX"]
    
    # 1. Fix the IP Principal / Entrepreneur Residual Logic (Conservation of Profit)
    # Identify Routine vs Principal entities
    is_principal = (p_total["TP Segment"] == "IP Principal") | (p_total["PLI Name"] == "Residual")
    is_routine = ~is_principal

    # Calculate Target OP for Routine Entities
    p_total["Target OP"] = 0.0
    # Distributors (TNMM - OM): Target OP = Revenue * Target Margin
    p_total.loc[p_total["TP Segment"] == "Distributor", "Target OP"] = p_total["Revenue"] * p_total["Target Margin"]
    # CM & SP (TNMM - NCP): Target OP = (COGS + OPEX) * Target Margin
    p_total.loc[p_total["TP Segment"].isin(["Contract Manufacturer", "Service Provider"]), "Target OP"] = (p_total["COGS"] + p_total["OPEX"]) * p_total["Target Margin"]
    
    # Initial TP Adjustment for routine entities
    p_total["TP Adjustment"] = 0.0
    p_total.loc[is_routine, "TP Adjustment"] = p_total["Target OP"] - p_total["Preliminary Operating Profit"]
    
    # Conservation of Profit: Principal absorbs the exact inverse of routine adjustments
    total_routine_adjustment = p_total.loc[is_routine, "TP Adjustment"].sum()
    if is_principal.any():
        # If there are multiple principals, they share the residual adjustment (usually only one)
        principal_count = is_principal.sum()
        p_total.loc[is_principal, "TP Adjustment"] = -total_routine_adjustment / principal_count
    
    # Final Operating Profit
    p_total["Final Operating Profit"] = p_total["Preliminary Operating Profit"] + p_total["TP Adjustment"]
    
    # For reporting, the IP Principal's Target OP is its Final Operating Profit
    p_total.loc[is_principal, "Target OP"] = p_total["Final Operating Profit"]
    
    # 3. Clean Up Floating-Point Arithmetic (Rounding to 2 decimals)
    cols_to_round = ["Revenue", "COGS", "OPEX", "Target OP", "Preliminary Operating Profit", "TP Adjustment", "Final Operating Profit"]
    p_total[cols_to_round] = p_total[cols_to_round].round(2)
    
    # Add dummy columns for template
    extra_cols = ["Sales", "Sales IC", "Rebates", "Discounts", "Deductions", "Other Income"]
    for col in extra_cols:
        if col not in p_total.columns:
            p_total[col] = 0

    return p_seg_sales, p_seg_opex, p_direct, p_indirect, p_total

    return p_seg_sales, p_seg_opex, p_direct, p_indirect, p_total

st.title("🏭 Globaler Firmen- & Material-Daten Generator")

# Tabs definieren
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Stammdaten & Karte", "📦 Material-Konfiguration", "💾 Export", "🔗 TP Network & Rules", "🌍 CIT Rates"])

with tab1:
    # 2. UI: Filter-Logik 
    col1, col2, col3 = st.columns(3)

    with col1:
        regions = sorted(countries_df['Region Name'].dropna().unique().tolist())
        default_regions = ["Europe"] if "Europe" in regions else []
        selected_regions = st.multiselect("1. Region(en) wählen", regions, default=default_regions)

    with col2:
        if selected_regions:
            filtered_countries = countries_df[countries_df['Region Name'].isin(selected_regions)]
        else:
            filtered_countries = pd.DataFrame(columns=countries_df.columns)

        all_country_names = sorted(filtered_countries['CLDR display name'].dropna().unique().tolist())
        selected_countries = st.multiselect("2. Länder wählen", all_country_names)

    with col3:
        if selected_countries:
            countries_to_use = selected_countries
        else:
            countries_to_use = all_country_names

        if countries_to_use:
            selected_iso_codes = filtered_countries[filtered_countries['CLDR display name'].isin(countries_to_use)]['ISO3166-1-Alpha-3'].tolist()

            available_cities_df = cities_df[cities_df['ISO3166-1-Alpha-3'].isin(selected_iso_codes)]
            available_city_names = sorted(available_cities_df['City'].dropna().unique().tolist())
        else:
            available_cities_df = pd.DataFrame(columns=cities_df.columns)
            available_city_names = []

        selected_cities = st.multiselect("3. Städte wählen", available_city_names)

    st.divider()

    # Generierungs-Optionen
    st.subheader("⚙️ Generierungs-Optionen")
    
    st.write("**Transfer Pricing Role Distribution**")
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    with r_col1:
        num_principals = st.number_input("IP Principals", min_value=1, value=1)
    with r_col2:
        num_distributors = st.number_input("Distributors", min_value=0, value=2)
    with r_col3:
        num_manufacturers = st.number_input("Contract Manufacturers", min_value=0, value=1)
    with r_col4:
        num_service_providers = st.number_input("Service Providers", min_value=0, value=1)
    
    num_companies = num_principals + num_distributors + num_manufacturers + num_service_providers
    st.info(f"Gesamtanzahl Gesellschaften: **{num_companies}**")

    st.divider()
    
    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
    with col_opt1:
        genre = st.selectbox("Genre der Firmen", ["General", "Tech", "Health", "Food", "Logistics"])
    with col_opt2:
        group_currency = st.text_input("Konzernwährung (Group Currency)", value="EUR", max_chars=3).upper()
    with col_opt3:
        num_materials = st.number_input("Anzahl Materialien", min_value=1, max_value=5000, value=20)
    with col_opt4:
        num_transactions = st.number_input("Anzahl Transaktionen", min_value=10, max_value=50000, value=100)

    # 3. Daten generieren
    if st.button("🚀 Globale Struktur Generieren", type="primary"):
        if not countries_to_use:
            st.error("Bitte wähle mindestens eine Region oder ein Land aus.")
        else:
            # Save role breakdown for downstream logic
            st.session_state['role_counts'] = {
                "principals": num_principals,
                "distributors": num_distributors,
                "manufacturers": num_manufacturers,
                "service_providers": num_service_providers
            }
            
            company_data = []
            progress_bar = st.progress(0, text="Generiere Gesellschaften...")

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
                    if not country_cities.empty:
                        rand_city = random.choice(country_cities['City'].dropna().tolist())
                    else:
                        rand_city = "Hauptstadt"

                region_name = country_row['Region Name']
                currency = country_row['ISO4217-currency_alphabetic_code']
                if pd.isna(currency): currency = "EUR"
                else: currency = str(currency).split(',')[0]

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
                progress_bar.progress(i / num_companies, text=f"Generiere Gesellschaften... ({i}/{num_companies})")

            st.session_state['company_data'] = pd.DataFrame(company_data)

            # Materialien initial generieren
            df_mat_class, df_material = generate_materials(num_materials)
            st.session_state['df_mat_class'] = df_mat_class
            st.session_state['df_material'] = df_material

            if 'map_coords' in st.session_state:
                del st.session_state['map_coords']

            if 'flow_state' in st.session_state:
                del st.session_state['flow_state']

            if 'tp_roles' in st.session_state:
                del st.session_state['tp_roles']
            
            if 'benchmark_data' in st.session_state:
                del st.session_state['benchmark_data']

            progress_bar.empty()
            st.rerun()

    # 4. TABELLE ZUERST Anzeigen
    if 'company_data' in st.session_state:
        df = st.session_state['company_data']

        st.subheader("📝 Vorschau & Bearbeitung (Firmen)")

        editor_country_options = countries_df['CLDR display name'].dropna().unique().tolist()

        if not filtered_countries.empty:
            editor_city_options = sorted(cities_df[cities_df['ISO3166-1-Alpha-3'].isin(filtered_countries['ISO3166-1-Alpha-3'].tolist())]['City'].dropna().unique().tolist())
        else:
            editor_city_options = sorted(cities_df['City'].dropna().unique().tolist())

        edited_df = st.data_editor(
            df, 
            width='stretch',
            hide_index=True,
            column_config={
                "Reroll": st.column_config.CheckboxColumn("Neu Würfeln?", default=False),
                "Country Name": st.column_config.SelectboxColumn(
                    "Land",
                    options=editor_country_options,
                    required=True
                ),
                "City": st.column_config.SelectboxColumn(
                    "Stadt",
                    options=editor_city_options,
                    required=True
                )
            }
        )

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("🎲 Ausgewählte Namen neu würfeln"):
                for idx, row in edited_df.iterrows():
                    if row['Reroll']:
                        edited_df.at[idx, 'Company Name'] = generate_company_name(genre)
                        edited_df.at[idx, 'Reroll'] = False
                st.session_state['company_data'] = edited_df
                st.rerun()

        with col_btn2:
            if st.button("🔄 Daten & Karte aktualisieren", type="secondary"):
                map_coords = []
                for idx, row in edited_df.iterrows():
                    c_name = row['Country Name']
                    c_row = countries_df[countries_df['CLDR display name'] == c_name]
                    if not c_row.empty:
                        edited_df.at[idx, 'Country Key'] = c_row.iloc[0]['ISO3166-1-Alpha-3']
                        edited_df.at[idx, 'Region'] = c_row.iloc[0]['Region Name']

                        currency = c_row.iloc[0]['ISO4217-currency_alphabetic_code']
                        if pd.isna(currency): currency = "EUR"
                        else: currency = str(currency).split(',')[0]
                        edited_df.at[idx, 'Co Currency'] = currency

                st.session_state['company_data'] = edited_df

                unique_locations = edited_df[['City', 'Country Name']].drop_duplicates().head(30)
                for _, row in unique_locations.iterrows():
                    c_lat, c_lon = get_coordinates(row['City'], row['Country Name'])
                    if c_lat and c_lon:
                        map_coords.append({'lat': c_lat, 'lon': c_lon})

                st.session_state['map_coords'] = map_coords
                st.rerun()

        st.divider()

        # 5. KARTE ZULETZT
        st.subheader("🗺️ Globale Präsenz (Karte)")
        if 'map_coords' in st.session_state and st.session_state['map_coords']:
            st.map(pd.DataFrame(st.session_state['map_coords']), zoom=3, width='stretch')
        else:
            st.info("💡 Die Karte ist aktuell im Ruhemodus. Klicke oben auf '🔄 Daten & Karte aktualisieren', um die Standorte zu laden.")

with tab2:
    st.subheader("📦 Material-Konfiguration")
    if 'df_material' not in st.session_state:
        st.info("💡 Generiere zuerst Daten in Tab 1, um die Materialien zu bearbeiten.")
    else:
        m_col1, m_col2 = st.columns([1, 2])
        with m_col1:
            st.write("**Marken & Klassen anpassen**")
            # Default brands for the editor
            if 'mat_brands' not in st.session_state:
                st.session_state['mat_brands'] = ["AlphaTech", "BetaMed", "GammaFoods", "DeltaLogistics", "NexGen", "CoreSystems"]

            edited_brands = st.data_editor(pd.DataFrame(st.session_state['mat_brands'], columns=["Brand"]), num_rows="dynamic", hide_index=True)
            st.session_state['mat_brands'] = edited_brands["Brand"].tolist()

            st.session_state['df_mat_class'] = st.data_editor(st.session_state['df_mat_class'], num_rows="dynamic", hide_index=True)

            if st.button("🎲 Materialien neu generieren"):
                _, st.session_state['df_material'] = generate_materials(
                    num_materials, 
                    brands=st.session_state['mat_brands'], 
                    mat_classes=st.session_state['df_mat_class']
                )
                st.rerun()

        with m_col2:
            st.write("**Materialliste**")
            st.session_state['df_material'] = st.data_editor(
                st.session_state['df_material'],
                width='stretch',
                hide_index=True,
                num_rows="dynamic"
            )

with tab3:
    if 'company_data' in st.session_state:
        # 6. EXPORT ALS EXCEL
        st.subheader("💾 Export & Validation")

        if st.button("🚀 Final Report Generieren", type="primary"):
            with st.spinner("Generiere Daten..."):
                export_df = st.session_state['company_data'].copy()
                df_pnl, df_tp_segments = generate_master_data()
                role_counts = st.session_state.get('role_counts')

                # Use session state roles and benchmarks if available
                if 'tp_roles' in st.session_state and 'benchmark_data' in st.session_state:
                    df_c_tp_segment = st.session_state['tp_roles']
                    df_benchmark = st.session_state['benchmark_data']
                    _, _, df_indirect_alloc = generate_config_data(export_df, df_tp_segments, role_counts=role_counts)
                else:
                    df_c_tp_segment, df_benchmark, df_indirect_alloc = generate_config_data(export_df, df_tp_segments, role_counts=role_counts)
                    st.session_state['tp_roles'] = df_c_tp_segment
                    st.session_state['benchmark_data'] = df_benchmark

                final_company_info = export_df.drop(columns=["Reroll", "Country Name", "Region"])

                final_region_mapping = pd.DataFrame({
                    'Company code': export_df['Company Code'],
                    'Name': export_df['Company Name'],
                    'Country': export_df['Country Key'],
                    'Region': export_df['Region']
                })

                # Neue Daten generieren (oder aus Session State nehmen)
                if 'df_material' in st.session_state and 'df_mat_class' in st.session_state:
                    df_mat_class = st.session_state['df_mat_class']
                    df_material = st.session_state['df_material']
                else:
                    df_mat_class, df_material = generate_materials(num_materials)
                    st.session_state['df_mat_class'] = df_mat_class
                    st.session_state['df_material'] = df_material

                df_sales_tx, df_opex_tx = generate_transactions(export_df, df_material, df_pnl, num_transactions, df_c_tp_segment)
                p_seg_sales, p_seg_opex, p_direct, p_indirect, p_total = calculate_allocations(df_sales_tx, df_opex_tx, export_df, df_benchmark, df_c_tp_segment)

                # Store in session state for persistence
                st.session_state['last_report'] = {
                    'metrics': {
                        'revenue': p_total['Revenue'].sum(),
                        'opex': p_total['OPEX'].sum(),
                        'ebit': p_total['Final Operating Profit'].sum()
                    },
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
                    p_seg_sales.to_excel(writer, index=False, sheet_name='P_Segmentation_Sales_COGS')
                    p_seg_opex.to_excel(writer, index=False, sheet_name='P_Segmentation_OPEX')
                    p_direct.to_excel(writer, index=False, sheet_name='P_Direct Allocation')
                    p_indirect.to_excel(writer, index=False, sheet_name='P_Indirect Allocation')
                    p_total.to_excel(writer, index=False, sheet_name='P_Total Allocation')

                st.session_state['last_report']['excel_data'] = output.getvalue()
                st.success("Report erfolgreich generiert!")

        # Display report if it exists in session state
        if 'last_report' in st.session_state:
            report = st.session_state['last_report']

            # Validation Dashboard
            st.divider()
            st.write("### 📊 Validation Dashboard")
            val_col1, val_col2, val_col3 = st.columns(3)
            with val_col1:
                st.metric("Total Revenue", f"{report['metrics']['revenue']:,.2f} EUR")
            with val_col2:
                st.metric("Total OPEX", f"{report['metrics']['opex']:,.2f} EUR")
            with val_col3:
                st.metric("System EBIT", f"{report['metrics']['ebit']:,.2f} EUR")

            file_name = f"OTP_Data_{report['timestamp']}.xlsx"
            st.download_button(
                label=f"📥 '{file_name}' herunterladen",
                data=report['excel_data'],
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
    else:
        st.info("💡 Generiere zuerst Daten in Tab 1, um den Export zu aktivieren.")

with tab4:
    st.subheader("🔗 Interactive TP Network")
    if 'company_data' in st.session_state:
        # Initialize configurations if they don't exist
        if 'tp_roles' not in st.session_state or 'benchmark_data' not in st.session_state:
            export_df = st.session_state['company_data'].copy()
            _, df_tp_segments = generate_master_data()
            role_counts = st.session_state.get('role_counts')
            df_c_tp_segment, df_benchmark, _ = generate_config_data(export_df, df_tp_segments, role_counts=role_counts)
            st.session_state['tp_roles'] = df_c_tp_segment
            st.session_state['benchmark_data'] = df_benchmark

        st.info("Drag nodes to organize your supply chain.")

        # Rebuild flow state if roles changed or not yet built
        if 'flow_state' not in st.session_state:
            export_df = st.session_state['company_data'].copy()
            df_pnl, _ = generate_master_data()
            _, df_material = generate_materials(num_materials)
            df_sales_tx, _ = generate_transactions(export_df, df_material, df_pnl, num_transactions, st.session_state['tp_roles'])
            st.session_state.flow_state = build_flow_state(export_df, st.session_state['tp_roles'], df_sales_tx)

        # Call the flow component with interactive flags
        st.session_state.flow_state = streamlit_flow('tp_network_flow',
                                    state=st.session_state.flow_state,
                                    fit_view=True,
                                    height=500,
                                    enable_pane_menu=True,
                                    enable_node_menu=True,
                                    enable_edge_menu=True,
                                    pan_on_drag=True,
                                    allow_zoom=True)
        
        st.divider()
        col_ed1, col_ed2 = st.columns(2)
        
        with col_ed1:
            st.subheader("📋 TP Roles")
            st.session_state['tp_roles'] = st.data_editor(
                st.session_state['tp_roles'],
                width='stretch',
                hide_index=True,
                column_config={
                    "TP Segment": st.column_config.SelectboxColumn(
                        "TP Segment",
                        options=["Distributor", "Contract Manufacturer", "IP Principal", "Service Provider"],
                        required=True
                    )
                }
            )
            if st.button("🔄 Apply Roles to Flow"):
                export_df = st.session_state['company_data'].copy()
                df_pnl, _ = generate_master_data()
                _, df_material = generate_materials(num_materials)
                df_sales_tx, _ = generate_transactions(export_df, df_material, df_pnl, num_transactions, st.session_state['tp_roles'])
                st.session_state.flow_state = build_flow_state(export_df, st.session_state['tp_roles'], df_sales_tx)
                st.rerun()

        with col_ed2:
            st.subheader("📈 Benchmarks")
            st.session_state['benchmark_data'] = st.data_editor(
                st.session_state['benchmark_data'],
                width='stretch',
                hide_index=True
            )
    else:
        st.info("💡 Generiere zuerst Daten in Tab 1, um das Netzwerk zu visualisieren.")

with tab5:
    # Datawrapper Chart
    st.subheader("🌍 Corporate Income Tax Rates in Europe")
    html_code = """
    <iframe title="Corporate Income Tax Rates in Europe" aria-label="Choropleth map" id="datawrapper-chart-aExmQ" src="https://datawrapper.dwcdn.net/aExmQ/2/" scrolling="no" frameborder="0" style="width: 0; min-width: 100% !important; border: none;" height="763" data-external="1"></iframe>
    <script type="text/javascript">window.addEventListener("message",function(a){if(void 0!==a.data["datawrapper-height"]){var e=document.querySelectorAll("iframe");for(var t in a.data["datawrapper-height"])for(var r,i=0;r=e[i];i++)if(r.contentWindow===a.source){var d=a.data["datawrapper-height"][t]+"px";r.style.height=d}}});</script>
    """
    components.html(html_code, height=800)