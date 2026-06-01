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

def generate_materials(num_materials):
    mat_classes = [
        {"Valuation Class": "OMP", "Type of Sales": "Intercompany & 3P", "Description": "Own Manufactured Products"},
        {"Valuation Class": "MER", "Type of Sales": "3P", "Description": "Merchandise"},
        {"Valuation Class": "RAW", "Type of Sales": "Intercompany", "Description": "Raw Materials"}
    ]
    df_mat_class = pd.DataFrame(mat_classes)
    
    materials = []
    brands = ["AlphaTech", "BetaMed", "GammaFoods", "DeltaLogistics", "NexGen", "CoreSystems"]
    
    for i in range(1, num_materials + 1):
        mat_id = f"MAT-{str(i).zfill(4)}"
        brand = random.choice(brands)
        raw_price = round(random.uniform(5.0, 50.0), 2)
        ic_price = round(raw_price * random.uniform(1.15, 1.40), 2)
        mer_price = round(raw_price * random.uniform(1.10, 1.30), 2)
        tp_price = round(max(ic_price, mer_price) * random.uniform(1.30, 2.00), 2)
        qty = random.randint(100, 5000)
        
        materials.append({
            "Material": mat_id,
            "Brand": brand,
            "Raw Material Price": raw_price,
            "IC Sales Price": ic_price,
            "MER Material Price": mer_price,
            "3P Sales Price": tp_price,
            "Quantities for Jan 2021": qty
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
    segments = [
        {"TP Segment key": "DIST", "TP Segment description": "Distributor"},
        {"TP Segment key": "CM", "TP Segment description": "Contract Manufacturer"},
        {"TP Segment key": "PRIN", "TP Segment description": "IP Principal"},
        {"TP Segment key": "SERV", "TP Segment description": "Service Provider"}
    ]
    return pd.DataFrame(pnl_data), pd.DataFrame(segments)

def generate_config_data(companies_df, segments_df):
    segments = segments_df["TP Segment description"].tolist()
    tp_segments = []
    for _, row in companies_df.iterrows():
        tp_segments.append({
            "Company Code": row["Company Code"],
            "Pri": 1,
            "TP Segment": random.choice(segments),
            "Type of Sales": "3P",
            "Valuation Class": "OMP",
            "Trading Partner?": "No",
            "Material Number": "*",
            "Valid from": "01.01.2021",
            "Valid to": "31.12.2021"
        })
    df_c_tp_segment = pd.DataFrame(tp_segments)

    benchmarks = [
        {"TP Function": "Distributor", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "OM", "PLI Formula": "EBIT/Sales", "Q1": 0.02, "Median": 0.035, "Q3": 0.05},
        {"TP Function": "Contract Manufacturer", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "NCP", "PLI Formula": "EBIT/Total Cost", "Q1": 0.05, "Median": 0.075, "Q3": 0.10},
        {"TP Function": "IP Principal", "TP Method": "CUP", "Price Setting": "Fixed", "PLI Name": "Residual", "PLI Formula": "Residual", "Q1": 0.10, "Median": 0.15, "Q3": 0.25},
        {"TP Function": "Service Provider", "TP Method": "TNMM", "Price Setting": "Target", "PLI Name": "Mark-up", "PLI Formula": "EBIT/Total Cost", "Q1": 0.03, "Median": 0.05, "Q3": 0.07}
    ]
    
    return df_c_tp_segment, pd.DataFrame(benchmarks)

def generate_transactions(companies_df, materials_df, num_transactions, df_c_tp_segment):
    sales_tx = []
    opex_tx = []
    company_codes = companies_df["Company Code"].tolist()
    co_to_country = dict(zip(companies_df["Company Code"], companies_df["Country Key"]))
    co_to_name = dict(zip(companies_df["Company Code"], companies_df["Company Name"]))
    co_to_currency = dict(zip(companies_df["Company Code"], companies_df["Co Currency"]))
    co_to_segment = dict(zip(df_c_tp_segment["Company Code"], df_c_tp_segment["TP Segment"]))
    
    # Segment groupings for routing
    principals = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "IP Principal"]["Company Code"].tolist()
    distributors = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "Distributor"]["Company Code"].tolist()
    manufacturers = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "Contract Manufacturer"]["Company Code"].tolist()
    service_providers = df_c_tp_segment[df_c_tp_segment["TP Segment"] == "Service Provider"]["Company Code"].tolist()
    
    revenue_tracker = {code: 0 for code in company_codes}

    for flow_id in range(num_transactions):
        # 1. Randomly select material, qty, and period
        material = materials_df.sample(n=1).iloc[0]
        qty = random.randint(1, 100)
        month = random.randint(1, 12)
        period = f"{str(month).zfill(2)}.2021"

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
                "Country": co_to_country[seller],
                "PeriodRange": period,
                "MaterialNumber": material["Material"],
                "TradingPartner": buyer,
                "TypeOfSales": "IC",
                "RUNIT": co_to_currency[seller],
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs
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
                "Country": co_to_country[seller],
                "PeriodRange": period,
                "MaterialNumber": material["Material"],
                "TradingPartner": buyer,
                "TypeOfSales": "IC",
                "RUNIT": co_to_currency[seller],
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs
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
                "Country": co_to_country[seller],
                "PeriodRange": period,
                "MaterialNumber": material["Material"],
                "TradingPartner": buyer,
                "TypeOfSales": "3P",
                "RUNIT": co_to_currency[seller],
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs
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
                "Country": co_to_country[seller],
                "PeriodRange": period,
                "MaterialNumber": material["Material"],
                "TradingPartner": buyer,
                "TypeOfSales": "3P",
                "RUNIT": co_to_currency[seller],
                "Total Amount Sales": revenue,
                "Total Amount COGS": -cogs
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
                "Country": co_to_country[seller],
                "PeriodRange": period,
                "MaterialNumber": "*",
                "TradingPartner": buyer,
                "TypeOfSales": "IC",
                "RUNIT": co_to_currency[seller],
                "Total Amount Sales": service_fee,
                "Total Amount COGS": 0
            })
            revenue_tracker[seller] += service_fee

    opex_accounts = [("600000", "Marketing"), ("610000", "R&D"), ("620000", "General Admin"), ("630000", "Logistics")]
    for code in company_codes:
        revenue = revenue_tracker.get(code, 0)
        annual_opex = (revenue * random.uniform(0.10, 0.25)) if revenue > 0 else random.uniform(50000, 150000)
        amount_per_entry = annual_opex / (len(opex_accounts) * 12)

        for acc_code, acc_desc in opex_accounts:
            for month in range(1, 13):
                opex_tx.append({
                    "Company Code": code,
                    "Company": co_to_name[code],
                    "Country": co_to_country[code],
                    "PeriodRange": f"{str(month).zfill(2)}.2021",
                    "GL Account": acc_code,
                    "GL Description": acc_desc,
                    "TypeOfSales": "OPEX",
                    "RUNIT": co_to_currency[code],
                    "Total Amount": round(amount_per_entry * random.uniform(0.85, 1.15), 2)
                })

    return pd.DataFrame(sales_tx), pd.DataFrame(opex_tx)

def calculate_allocations(sales_tx, opex_tx, df_benchmark, df_c_tp_segment):
    p_total = sales_tx.groupby(["Company Code", "Company", "Country", "RUNIT"]).agg({
        "Total Amount Sales": "sum",
        "Total Amount COGS": "sum"
    }).reset_index()
    
    p_total.rename(columns={"Total Amount Sales": "Revenue", "Total Amount COGS": "COGS"}, inplace=True)
    p_total["COGS"] = p_total["COGS"].abs()
    
    opex_sum = opex_tx.groupby("Company Code")["Total Amount"].sum().reset_index()
    opex_sum.rename(columns={"Total Amount": "OPEX"}, inplace=True)
    p_total = p_total.merge(opex_sum, on="Company Code", how="left").fillna(0)
    p_total["OPEX"] = p_total["OPEX"].abs()
    
    p_total = p_total.merge(df_c_tp_segment[["Company Code", "TP Segment"]], on="Company Code", how="left")
    p_total = p_total.merge(df_benchmark[["TP Function", "Median", "PLI Name"]], left_on="TP Segment", right_on="TP Function", how="left")
    p_total.rename(columns={"Median": "Target Margin"}, inplace=True)
    
    p_total["Preliminary Operating Profit"] = p_total["Revenue"] - p_total["COGS"] - p_total["OPEX"]
    
    is_principal = (p_total["TP Segment"] == "IP Principal") | (p_total["PLI Name"] == "Residual")
    is_routine = ~is_principal

    p_total["Target OP"] = 0.0
    p_total.loc[p_total["TP Segment"] == "Distributor", "Target OP"] = p_total["Revenue"] * p_total["Target Margin"]
    p_total.loc[p_total["TP Segment"].isin(["Contract Manufacturer", "Service Provider"]), "Target OP"] = (p_total["COGS"] + p_total["OPEX"]) * p_total["Target Margin"]
    
    p_total["TP Adjustment"] = 0.0
    p_total.loc[is_routine, "TP Adjustment"] = p_total["Target OP"] - p_total["Preliminary Operating Profit"]
    
    total_routine_adjustment = p_total.loc[is_routine, "TP Adjustment"].sum()
    if is_principal.any():
        principal_count = is_principal.sum()
        p_total.loc[is_principal, "TP Adjustment"] = -total_routine_adjustment / principal_count
    
    p_total["Final Operating Profit"] = p_total["Preliminary Operating Profit"] + p_total["TP Adjustment"]
    p_total.loc[is_principal, "Target OP"] = p_total["Final Operating Profit"]
    
    cols_to_round = ["Revenue", "COGS", "OPEX", "Target OP", "Preliminary Operating Profit", "TP Adjustment", "Final Operating Profit"]
    p_total[cols_to_round] = p_total[cols_to_round].round(2)
    
    return p_total
