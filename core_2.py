import pandas as pd
import random
import numpy as np
from mimesis import Finance
from mimesis.locales import Locale
from datetime import datetime

def generate_company_name(genre):
    finance = Finance(locale=Locale.EN)
    name = finance.company()
    if genre == "Tech": name += " Technologies"
    elif genre == "Health": name += " Healthcare"
    elif genre == "Food": name += " Foods"
    elif genre == "Logistics": name += " Logistics"
    return name

def generate_materials(num_materials, brands=None, mat_classes=None, year=2025):
    # 1. TPMD_MaterialTypeClass (Static Master Data)
    if mat_classes is None:
        mat_classes_list = [
            {"Valuation Class": "OMP", "Type of Sales": "Intercompany & 3P", "Description": "Own Manufactured Products"},
            {"Valuation Class": "MER", "Type of Sales": "3P", "Description": "Merchandise"},
            {"Valuation Class": "RAW", "Type of Sales": "Intercompany", "Description": "Raw Materials"}
        ]
        df_mat_class = pd.DataFrame(mat_classes_list)
    else:
        df_mat_class = mat_classes.copy()
    
    # 2. TPMD_Material (Dynamic Master Data)
    materials = []
    if brands is None:
        brands = ["AlphaTech", "BetaMed", "GammaFoods", "DeltaLogistics", "NexGen", "CoreSystems"]
    
    for i in range(1, num_materials + 1):
        mat_id = f"MAT-{str(i).zfill(4)}"
        brand = random.choice(brands) if isinstance(brands, list) and brands else "Generic"
        
        raw_price = round(random.uniform(5.0, 50.0), 2)
        ic_price = round(raw_price * random.uniform(1.15, 1.40), 2)
        mer_price = round(raw_price * random.uniform(1.10, 1.30), 2)
        tp_price = round(max(ic_price, mer_price) * random.uniform(1.80, 3.50), 2)
        
        qty = random.randint(100, 5000)
        
        materials.append({
            "Material": mat_id,
            "Brand": brand,
            "Raw Material Price": raw_price,
            "IC Sales Price": ic_price,
            "MER Material Price": mer_price,
            "3P Sales Price": tp_price,
            "Column1": "",
            f"Quantities for Jan {year}": qty
        })
        
    return df_mat_class, pd.DataFrame(materials)

def generate_master_data():
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

    segments = [
        {"TP Segment key": "DIST-T", "TP Segment description": "Distributor - TNMM"},
        {"TP Segment key": "DIST-R", "TP Segment description": "Distributor - RPM"},
        {"TP Segment key": "CM-T", "TP Segment description": "Routine Manufacturer"},
        {"TP Segment key": "CM-C", "TP Segment description": "Cost Plus Manufacturer"},
        {"TP Segment key": "PRIN", "TP Segment description": "IP Principal"},
        {"TP Segment key": "SERV", "TP Segment description": "Service Provider"},
        {"TP Segment key": "CUP", "TP Segment description": "Commodity Trader"}
    ]
    df_segments = pd.DataFrame(segments)
    
    return df_pnl, df_segments

def generate_config_data(companies_df, segments_df, role_counts=None, year=2025):
    tp_segments = []
    
    if role_counts:
        roles_pool = (
            ["IP Principal"] * role_counts.get("principals", 2) +
            ["Distributor - TNMM", "Distributor - RPM"][:role_counts.get("distributors", 2)] +
            ["Routine Manufacturer", "Cost Plus Manufacturer"][:role_counts.get("manufacturers", 2)] +
            ["Service Provider"] * role_counts.get("service_providers", 1) +
            ["Commodity Trader"] * max(0, role_counts.get("traders", 0))
        )
        while len(roles_pool) < len(companies_df):
            roles_pool.append("Distributor - TNMM")
        roles_pool = roles_pool[:len(companies_df)]
    else:
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
            "Valid from": f"01.01.{year}",
            "Valid to": f"31.12.{year}"
        })
    df_c_tp_segment = pd.DataFrame(tp_segments)

    benchmarks = [
        {"TP Function": "Distributor - TNMM", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "OM", "PLI Formula": "EBIT/Sales", "Q1": 0.02, "Median": 0.035, "Q3": 0.05, "Valid from": f"01.01.{year}", "Valid to": f"31.12.{year}", "User ID": "SYS"},
        {"TP Function": "Distributor - RPM", "TP Method": "Resale Minus", "Price Setting": "Target", "PLI Name": "Gross Margin", "PLI Formula": "Gross Profit/Sales", "Q1": 0.15, "Median": 0.20, "Q3": 0.25, "Valid from": f"01.01.{year}", "Valid to": f"31.12.{year}", "User ID": "SYS"},
        {"TP Function": "Routine Manufacturer", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "NCP", "PLI Formula": "EBIT/Total Cost", "Q1": 0.05, "Median": 0.075, "Q3": 0.10, "Valid from": f"01.01.{year}", "Valid to": f"31.12.{year}", "User ID": "SYS"},
        {"TP Function": "Service Provider", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "Mark-up", "PLI Formula": "EBIT/Total Cost", "Q1": 0.03, "Median": 0.05, "Q3": 0.07, "Valid from": f"01.01.{year}", "Valid to": f"31.12.{year}", "User ID": "SYS"},
        {"TP Function": "Cost Plus Manufacturer", "TP Method": "Cost Plus", "Price Setting": "Target", "PLI Name": "Gross Mark-up", "PLI Formula": "Gross Profit/COGS", "Q1": 0.10, "Median": 0.15, "Q3": 0.20, "Valid from": f"01.01.{year}", "Valid to": f"31.12.{year}", "User ID": "SYS"},
        {"TP Function": "Commodity Trader", "TP Method": "CUP", "Price Setting": "Exact", "PLI Name": "Price", "PLI Formula": "Internal vs External", "Q1": 0.0, "Median": 0.0, "Q3": 0.0, "Valid from": f"01.01.{year}", "Valid to": f"31.12.{year}", "User ID": "SYS"},
        {"TP Function": "IP Principal", "TP Method": "PSM", "Price Setting": "Split", "PLI Name": "Residual", "PLI Formula": "OPEX Allocation Key", "Q1": 0.0, "Median": 0.0, "Q3": 0.0, "Valid from": f"01.01.{year}", "Valid to": f"31.12.{year}", "User ID": "SYS"}
    ]
    df_benchmark = pd.DataFrame(benchmarks)

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

def generate_transactions(companies_df, materials_df, pnl_df, num_transactions, df_c_tp_segment, year=2025):
    sales_tx = []
    company_codes = companies_df["Company Code"].tolist()
    
    co_to_country = dict(zip(companies_df["Company Code"], companies_df["Country Key"]))
    co_to_name = dict(zip(companies_df["Company Code"], companies_df["Company Name"]))
    co_to_currency = dict(zip(companies_df["Company Code"], companies_df["Co Currency"]))
    co_to_segment = dict(zip(df_c_tp_segment["Company Code"], df_c_tp_segment["TP Segment"]))
    
    principals = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "IP Principal"]["Company Code"].tolist()
    distributors = df_c_tp_segment[df_c_tp_segment["TP Segment"].str.contains("Distributor")]["Company Code"].tolist()
    manufacturers = df_c_tp_segment[df_c_tp_segment["TP Segment"].str.contains("Manufacturer")]["Company Code"].tolist()
    service_providers = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "Service Provider"]["Company Code"].tolist()
    
    ic_sales_acc = "400000"
    tp_sales_acc = "410000"
    ic_cogs_acc = "500000"
    tp_cogs_acc = "510000"
    
    revenue_tracker = {code: 0 for code in company_codes}

    for flow_id in range(num_transactions):
        material = materials_df.sample(n=1).iloc[0]
        qty = random.randint(1, 100)
        month = random.randint(1, 12)
        period = f"{str(month).zfill(2)}.{year}"

        # --- RESILIENT ROUTING ENGINE ---
        
        # A. MANUFACTURING LEG
        current_buyer = None
        if manufacturers:
            seller = random.choice(manufacturers)
            # Resilient Buyer Selection
            if principals:
                buyer = random.choice(principals)
                type_sales = "IC"
            elif distributors:
                buyer = random.choice(distributors)
                type_sales = "IC"
            else:
                buyer = "EXTERNAL"
                type_sales = "3P"
            
            price_sales = material["IC Sales Price"] if buyer != "EXTERNAL" else material["3P Sales Price"]
            price_cogs = material["Raw Material Price"]
            revenue = round(qty * price_sales, 2)
            cogs = round(qty * price_cogs, 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": year,
                "PeriodRange": period,
                "GL Account Sales": ic_sales_acc if type_sales == "IC" else tp_sales_acc,
                "GL Description Sales": "Sales",
                "GL Account COGS": ic_cogs_acc if type_sales == "IC" else tp_cogs_acc,
                "GL Description COGS": "COGS",
                "MaterialNumber": material["Material"],
                "Brand": material["Brand"],
                "BusinessType": "Sales",
                "ValuationClass": "OMP",
                "TradingPartner": buyer,
                "Trading Partner": buyer,
                "Trading Partner Region": "Global",
                "TypeOfSales": type_sales,
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
            if buyer != "EXTERNAL":
                current_buyer = buyer

        # B. PRINCIPAL LEG
        if principals:
            seller = current_buyer if (current_buyer in principals) else random.choice(principals)
            # Resilient Buyer Selection
            if distributors:
                buyer = random.choice(distributors)
                type_sales = "IC"
                price_sales = material["MER Material Price"]
            else:
                buyer = "EXTERNAL"
                type_sales = "3P"
                price_sales = material["3P Sales Price"]
            
            # Match COGS to previous leg's Sales if applicable
            price_cogs = material["IC Sales Price"] if current_buyer == seller else material["Raw Material Price"]
            
            revenue = round(qty * price_sales, 2)
            cogs = round(qty * price_cogs, 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": year,
                "PeriodRange": period,
                "GL Account Sales": ic_sales_acc if type_sales == "IC" else tp_sales_acc,
                "GL Description Sales": "Sales",
                "GL Account COGS": ic_cogs_acc if type_sales == "IC" else tp_cogs_acc,
                "GL Description COGS": "COGS",
                "MaterialNumber": material["Material"],
                "Brand": material["Brand"],
                "BusinessType": "Sales",
                "ValuationClass": "OMP",
                "TradingPartner": buyer,
                "Trading Partner": buyer,
                "Trading Partner Region": "Global",
                "TypeOfSales": type_sales,
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
            if buyer != "EXTERNAL":
                current_buyer = buyer
            else:
                current_buyer = None

        # C. DISTRIBUTION LEG
        if distributors:
            # Only act as seller if we are a distributor
            seller = current_buyer if (current_buyer in distributors) else random.choice(distributors)
            buyer = "EXTERNAL"
            
            price_cogs = material["MER Material Price"] if current_buyer == seller else material["MER Material Price"]
            price_sales = material["3P Sales Price"]
            
            revenue = round(qty * price_sales, 2)
            cogs = round(qty * price_cogs, 2)
            
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": year,
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

        # D. SERVICE PROVIDERS (FIXED: Symmetric IC Accounting)
        if service_providers and random.random() < 0.20:
            seller = random.choice(service_providers)
            buyer = random.choice(principals) if principals else (random.choice(distributors) if distributors else random.choice(company_codes))
            
            service_fee = round(random.uniform(5000, 25000), 2)
            
            # Seller Revenue Row
            sales_tx.append({
                "Company Code": seller,
                "Company": co_to_name[seller],
                "Country Code": co_to_country[seller],
                "Country": co_to_country[seller],
                "Region CoCo": "Europe",
                "Year": year,
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

            # Buyer Expense Row (The Fix)
            sales_tx.append({
                "Company Code": buyer,
                "Company": co_to_name[buyer],
                "Country Code": co_to_country[buyer],
                "Country": co_to_country[buyer],
                "Region CoCo": "Europe",
                "Year": year,
                "PeriodRange": period,
                "GL Account Sales": ic_sales_acc,
                "GL Description Sales": "Service Fee",
                "GL Account COGS": ic_cogs_acc,
                "GL Description COGS": "Purchased Services",
                "MaterialNumber": "*",
                "Brand": "*",
                "BusinessType": "Service",
                "ValuationClass": "*",
                "TradingPartner": seller,
                "Trading Partner": seller,
                "Trading Partner Region": "Global",
                "TypeOfSales": "IC",
                "RUNIT": co_to_currency[buyer],
                "GlobalCurrency": "EUR",
                "Price Sales": 0,
                "Price COGS": service_fee,
                "Total Sales": 0,
                "Total Amount Sales": 0,
                "Total Amount COGS": -service_fee,
                "Column": ""
            })

    # OPEX transactions (Scaled to Revenue)
    opex_tx = []
    opex_accounts = [("600000", "Marketing"), ("610000", "R&D"), ("620000", "General Admin"), ("630000", "Logistics")]
    for code in company_codes:
        segment = co_to_segment.get(code)
        revenue = revenue_tracker.get(code, 0)
        if segment == "Service Provider":
            annual_opex = random.uniform(10000, 35000)
        elif revenue > 0:
            annual_opex = revenue * random.uniform(0.08, 0.18)
        else:
            annual_opex = random.uniform(5000, 15000)
            
        amount_per_entry = annual_opex / (len(opex_accounts) * 12)

        for acc_code, acc_desc in opex_accounts:
            for month in range(1, 13):
                period = f"{str(month).zfill(2)}.{year}"
                monthly_amount = round(amount_per_entry * random.uniform(0.85, 1.15), 2)
                
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
                    "Year": year,
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
    # Aggregated view
    p_total = sales_tx.groupby(["Company Code", "Company", "Country Code", "Country", "Co Currency" if "Co Currency" in sales_tx.columns else "RUNIT"]).agg({
        "Total Amount Sales": "sum",
        "Total Amount COGS": "sum",
        "Total Sales": "sum"
    }).reset_index()
    
    p_total.rename(columns={"Total Sales": "Sales Quantity", "Total Amount Sales": "Revenue", "Total Amount COGS": "COGS"}, inplace=True)
    p_total["COGS"] = p_total["COGS"].abs()
    
    opex_sum = opex_tx.groupby("Company Code")["Total Amount"].sum().reset_index()
    opex_sum.rename(columns={"Total Amount": "OPEX"}, inplace=True)
    p_total = p_total.merge(opex_sum, on="Company Code", how="left").fillna(0)
    p_total["OPEX"] = p_total["OPEX"].abs()
    
    p_total = p_total.merge(df_c_tp_segment[["Company Code", "TP Segment"]], on="Company Code", how="left")
    p_total = p_total.merge(df_benchmark[["TP Function", "Median", "PLI Name", "TP Method"]], left_on="TP Segment", right_on="TP Function", how="left")
    p_total.rename(columns={"Median": "Target Margin"}, inplace=True)
    
    # Calculate Base Profits
    p_total["Gross Profit"] = p_total["Revenue"] - p_total["COGS"]
    p_total["Preliminary Operating Profit"] = p_total["Gross Profit"] - p_total["OPEX"]
    
    is_principal = p_total["TP Method"] == "PSM"
    is_routine = ~is_principal

    p_total["Target OP"] = 0.0
    p_total["Target Gross Profit"] = 0.0
    
    # 1. Resale Price Method (RPM) -> Target Gross = Revenue * Target Margin
    rpm_mask = p_total["TP Method"] == "Resale Minus"
    p_total.loc[rpm_mask, "Target Gross Profit"] = p_total["Revenue"] * p_total["Target Margin"]
    p_total.loc[rpm_mask, "Target OP"] = p_total["Target Gross Profit"] - p_total["OPEX"]
    
    # 2. Traditional Cost Plus (CPL) -> Target Gross = COGS * Target Margin
    cpl_mask = p_total["TP Method"] == "Cost Plus"
    p_total.loc[cpl_mask, "Target Gross Profit"] = p_total["COGS"] * p_total["Target Margin"]
    p_total.loc[cpl_mask, "Target OP"] = p_total["Target Gross Profit"] - p_total["OPEX"]

    # 3. TNMM (OM and NCP) -> Target OP calculated directly
    tnmm_om_mask = (p_total["TP Method"] == "TNMM") & (p_total["PLI Name"] == "OM")
    p_total.loc[tnmm_om_mask, "Target OP"] = p_total["Revenue"] * p_total["Target Margin"]
    
    tnmm_ncp_mask = (p_total["TP Method"] == "TNMM") & (p_total["PLI Name"] == "NCP")
    p_total.loc[tnmm_ncp_mask, "Target OP"] = (p_total["COGS"] + p_total["OPEX"]) * p_total["Target Margin"]

    # 4. CUP -> Managed at the transactional level, no year-end OP adjustment needed
    cup_mask = p_total["TP Method"] == "CUP"
    p_total.loc[cup_mask, "Target OP"] = p_total["Preliminary Operating Profit"]

    # Calculate Adjustments for Routine Entities
    p_total["TP Adjustment"] = 0.0
    p_total.loc[is_routine, "TP Adjustment"] = p_total["Target OP"] - p_total["Preliminary Operating Profit"]
    
    # 5. Contribution Profit Split Method (PSM)
    total_routine_adjustment = p_total.loc[is_routine, "TP Adjustment"].sum()
    if is_principal.any():
        total_principal_opex = p_total.loc[is_principal, "OPEX"].sum()
        if total_principal_opex > 0:
            # Split based on OPEX Allocation Key (proxy for R&D/Substance)
            p_total.loc[is_principal, "TP Adjustment"] = (-total_routine_adjustment) * (p_total.loc[is_principal, "OPEX"] / total_principal_opex)
        else:
            # Fallback to even split
            p_total.loc[is_principal, "TP Adjustment"] = -total_routine_adjustment / is_principal.sum()
    
    # Finalize
    p_total["Final Operating Profit"] = p_total["Preliminary Operating Profit"] + p_total["TP Adjustment"]
    p_total.loc[is_principal, "Target OP"] = p_total["Final Operating Profit"]
    
    cols_to_round = ["Revenue", "COGS", "Gross Profit", "OPEX", "Target OP", "Preliminary Operating Profit", "TP Adjustment", "Final Operating Profit"]
    p_total[cols_to_round] = p_total[cols_to_round].round(2)
    
    extra_cols = ["Sales", "Sales IC", "Rebates", "Discounts", "Deductions", "Other Income"]
    for col in extra_cols:
        if col not in p_total.columns:
            p_total[col] = 0

    return p_total
