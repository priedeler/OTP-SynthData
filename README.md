# Synthetic Transfer Pricing (TP) Data Generation & Rule Engine

## University Project Overview
This project was developed to simulate complex intercompany (IC) financial flows within multinational enterprise (MNE) groups. It serves as a tool for studying **Transfer Pricing (TP)**, **Symmetric IC Accounting**, and **Value Chain Analysis**. The system generates synthetic supply chains, traces product/service flows, and applies a "TP Rule Engine" to perform profit allocations based on functional profiles.

---

## System Architecture

The project follows a **Decoupled Three-Tier Architecture** to ensure a "Single Source of Truth" (SSoT):

1.  **Core Logic Tier (`core_2.py`)**: The central engine containing all financial math, supply chain routing algorithms, and TP adjustment logic. It is shared by both the UI and CLI.
2.  **Presentation Tier (`app_2.py`)**: A Streamlit-based interactive dashboard that allows users to visualize supply chains via network graphs, adjust benchmarks, and generate validated reports.
3.  **Automation Tier (`cli_suite/`)**: A Typer-based Command Line Interface (CLI) designed for high-volume batch generation and automated reporting.

---

## Key Features

### 1. End-to-End Supply Chain Flow Generator
Unlike traditional generators that create isolated transactions, this system utilizes a **Trace-Back Flow Algorithm**:
*   **Flow Genesis**: A product is "sold" to an external customer.
*   **Tracing**: The system traces the product backward through the chain: `Distributor` ➔ `IP Principal` ➔ `Contract Manufacturer`.
*   **Symmetric Accounting**: For every IC handover, the system validates that:
    $$\text{Seller Revenue} \equiv \text{Buyer COGS}$$
    This eliminates "phantom profits" and ensures the group's consolidated profit is mathematically sound.

### 2. Resilient Routing Engine
The system is built to handle arbitrary supply chain topologies. If a user defines a group with 0 manufacturers or 0 distributors, the engine automatically calculates alternative "Short-Circuit" routes (e.g., Principals buying directly from 3rd party suppliers) to maintain data integrity.

### 3. TP Rule Engine & Profit Allocation
After generating raw transactions, the system applies the **Functional Profile Method**:
*   **Routine Entities** (Distributors, CMs, SPs): Allocated a "Target Margin" based on Benchmarks (Median/Q1/Q3).
*   **Residual Entity** (IP Principal): Absorbs the group's residual profit or loss after routine adjustments.
*   **Conservation of Profit**: The system ensures that the sum of all IC adjustments across the group equals zero.

### 4. Interactive Visualization
*   **TP Network Graph**: An animated, interactive diagram showing the flow of goods and services between legal entities.
*   **Geographic Mapping**: Automatic geocoding of company headquarters to visualize global footprint.

---

## Project Structure

```text
├── app_2.py            # Main Streamlit UI Application
├── core_2.py           # Shared Backend & Financial Logic (SSoT)
├── GEMINI.md           # Internal Developer/Maintenance Guide
├── README.md           # This Project Documentation
├── requirements.txt    # Python Dependencies
├── data/               # Master Data & Templates
│   ├── All ISO...csv   # Global ISO/Country/Currency data
│   ├── Citys_mit...csv # Global City database
│   └── OTP_Template.xlsx # Excel Export Template
├── cli_suite/          # CLI Tools for batch processing
│   └── main_2.py       # Typer CLI Entry Point
└── archive/            # Legacy versions and artifacts
```

---

## Installation & Usage

### Prerequisites
*   Python 3.9+
*   Recommended: Virtual Environment (`venv`)

### Setup
```bash
pip install -r requirements.txt
```

### Running the UI
```bash
streamlit run app_2.py
```

### Running the CLI
```bash
# Generate a dataset for 10 companies for the year 2026
python cli_suite/main_2.py generate 10 --transactions 200 --year 2026 --output my_tp_data.xlsx

# Generate a TP Allocation Report from existing data
python cli_suite/main_2.py report my_tp_data.xlsx --output final_report.xlsx
```

---

## Scientific Considerations
This project addresses several critical pitfalls in financial data synthesis:
*   **The "One-Sided" Bug**: In previous versions, service fees were only recorded by the seller. V2 enforces a mandatory "Insta-Expense" row for the buyer.
*   **Stale Data**: By parameterizing the simulation year, the system avoids hardcoded dates (e.g., 2021) that often plague financial models.
*   **OPEX Scaling**: Operating Expenses are dynamically scaled based on generated revenue to simulate realistic EBIT margins before TP adjustments.
