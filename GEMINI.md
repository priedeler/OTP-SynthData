# Synthetic TP Data Project - Developer Guide

## Project Architecture (V2)
This project follows a **Strict Single Source of Truth** architecture. 

*   **`core_2.py`**: The "Brain". All financial math, supply chain routing, and data generation logic lives here. **Never** duplicate logic from here into the UI or CLI layers.
*   **`app_2.py`**: The "Face". A Streamlit-based UI. It handles state management and user interaction but delegates all heavy lifting to `core_2.py`.
*   **`data/`**: The "Memory". Contains all master data CSVs (ISO codes, CIT rates) and Excel templates.
*   **`cli_suite/`**: The "Automator". Contains the Typer-based CLI tool for batch processing.

## Key Workflows

### 1. Modifying Financial Logic
If you need to change how margins are calculated or add a new supply chain leg:
1.  Edit `core_2.py`.
2.  Test via CLI: `python cli_suite/main_2.py generate 5 -y 2026`.
3.  Verify in UI: `streamlit run app_2.py`.

### 2. Adding Master Data
If you add a new CSV to the `data/` folder, update the `load_data()` function in `app_2.py` to ensure it's cached and cleaned (strip whitespace).

### 3. Supply Chain Resilience
The routing engine in `core_2.py` is designed to be "cascading." If a pool (Principals, Distributors, etc.) is empty, the logic must fallback to "EXTERNAL" rather than crashing. Always maintain this defensive pattern.

## Critical Constraints
*   **Symmetric IC Accounting**: Every IC Revenue row must have a matching IC Expense row. This is implemented in `generate_transactions` for both products and services.
*   **Excel Schema**: Do not change dictionary keys in `sales_tx` or `opex_tx` without checking the Excel sheet names and column headers expected by the `calculate_allocations` function.
*   **Automatic GitHub Sync**: After every major code change or task milestone, commit the changes and push them to GitHub (`origin/master` or `origin/main` as appropriate) automatically.

## Folder Structure
- `/data`: Master data and templates.
- `/cli_suite`: CLI tool and legacy CLI modules.
- `/archive`: Old versions of the app.
- `core_2.py`: Shared backend logic.
- `app_2.py`: Streamlit application.
- `GEMINI.md`: This guide.
