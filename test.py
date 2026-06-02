import core_2
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

df_pnl, df_tp_segments = core_2.generate_master_data()

companies = [
    {"Company Code": "Co01", "Company Name": "Manu", "Country Key": "FRA", "Co Currency": "EUR"},
    {"Company Code": "Co02", "Company Name": "Dist", "Country Key": "DEU", "Co Currency": "EUR"},
    {"Company Code": "Co03", "Company Name": "Prin", "Country Key": "CHE", "Co Currency": "EUR"},
    {"Company Code": "Co04", "Company Name": "Serv", "Country Key": "IRL", "Co Currency": "EUR"},
    {"Company Code": "Co05", "Company Name": "Trad", "Country Key": "GBR", "Co Currency": "GBP"},
    {"Company Code": "Co06", "Company Name": "ManuCP", "Country Key": "FRA", "Co Currency": "EUR"},
    {"Company Code": "Co07", "Company Name": "DistRPM", "Country Key": "DEU", "Co Currency": "EUR"}
]
df_companies = pd.DataFrame(companies)

roles_pool = ["Routine Manufacturer", "Distributor - TNMM", "IP Principal", "Service Provider", "Commodity Trader", "Cost Plus Manufacturer", "Distributor - RPM"]
df_c_tp_segment, df_benchmark, df_indirect_alloc = core_2.generate_config_data(
    df_companies, df_tp_segments, 
    role_counts={"principals": 1, "distributors": 2, "manufacturers": 2, "service_providers": 1, "traders": 1}
)
df_c_tp_segment["TP Segment"] = roles_pool

df_mat_class, df_material = core_2.generate_materials(50)

df_sales_tx, df_opex_tx = core_2.generate_transactions(
    df_companies, df_material, df_pnl, 1000, df_c_tp_segment
)

p_seg_sales, p_seg_opex, p_direct, p_indirect, p_total = core_2.calculate_allocations(
    df_sales_tx, df_opex_tx, df_companies, df_benchmark, df_c_tp_segment, return_all=True
)

for _, row in p_total.iterrows():
    print(f"\n{row['Company Code']} ({row['TP Segment']})")
    print(f"  Revenue: {row['Revenue']}, COGS: {row['COGS']}, GP: {row['Gross Profit']}, OPEX: {row['OPEX']}")
    print(f"  Pre-OP: {row['Preliminary Operating Profit']}, Target OP: {row['Target OP']}")
    print(f"  Final OP: {row['Final Operating Profit']}, TP Adj: {row['TP Adjustment']}")
