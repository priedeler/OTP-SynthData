import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import pandas as pd
import os
import random
from dotenv import load_dotenv
from . import core
import logging

# Load environment variables
load_dotenv()

app = typer.Typer(
    name="tp-gen",
    help="🚀 Synthetic Transfer Pricing Data Generator CLI",
    add_completion=False,
)

console = Console()
state = {"verbose": False}

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable detailed debug logs")
):
    """
    Expert TP Systems CLI for generating and managing synthetic financial data.
    """
    state["verbose"] = verbose
    setup_logging(verbose)

@app.command()
def generate(
    num_companies: int = typer.Argument(..., help="Number of companies to generate"),
    genre: str = typer.Option("General", "--genre", "-g", help="Company genre (Tech, Health, etc.)"),
    materials: int = typer.Option(20, "--materials", "-m", help="Number of materials"),
    transactions: int = typer.Option(100, "--transactions", "-t", help="Number of transactions"),
    output: str = typer.Option("tp_data.xlsx", "--output", "-o", help="Output filename"),
):
    """
    Generate synthetic companies, materials, and transactions.
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            
            # Step 1: Base Data
            progress.add_task(description="Generating master data...", total=None)
            df_pnl, df_segments = core.generate_master_data()
            
            # Step 2: Companies
            progress.add_task(description=f"Generating {num_companies} companies...", total=None)
            # Mocking company data generation based on inputs
            company_data = []
            for i in range(1, num_companies + 1):
                company_data.append({
                    "Company Code": f"Co{str(i).zfill(2)}",
                    "Company Name": core.generate_company_name(genre),
                    "Country Key": random_choice_country(), # Utility needed
                    "Co Currency": "EUR"
                })
            companies_df = pd.DataFrame(company_data)
            
            # Step 3: Config
            progress.add_task(description="Calculating TP configurations...", total=None)
            df_tp_roles, df_benchmarks = core.generate_config_data(companies_df, df_segments)
            
            # Step 4: Materials
            progress.add_task(description=f"Generating {materials} materials...", total=None)
            df_mat_class, df_material = core.generate_materials(materials)
            
            # Step 5: Transactions
            progress.add_task(description=f"Simulating {transactions} transactions...", total=None)
            df_sales, df_opex = core.generate_transactions(companies_df, df_material, transactions, df_tp_roles)
            
            # Step 6: Export
            progress.add_task(description=f"Saving to {output}...", total=None)
            with pd.ExcelWriter(output) as writer:
                companies_df.to_excel(writer, index=False, sheet_name="Companies")
                df_tp_roles.to_excel(writer, index=False, sheet_name="TP_Roles")
                df_benchmarks.to_excel(writer, index=False, sheet_name="Benchmarks")
                df_sales.to_excel(writer, index=False, sheet_name="Sales_TX")
                df_opex.to_excel(writer, index=False, sheet_name="OPEX_TX")

        console.print(f"[bold green]Success![/bold green] Generated dataset saved to [cyan]{output}[/cyan]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if state["verbose"]:
            logging.exception(e)
        raise typer.Exit(code=1)

@app.command()
def report(
    input_file: str = typer.Argument(..., help="Path to the generated Excel file"),
    output: str = typer.Option("tp_report.xlsx", "--output", "-o", help="Output filename for the report"),
):
    """
    Apply TP allocation logic and generate a consolidated financial report.
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Reading input data...", total=None)
            xls = pd.ExcelFile(input_file)
            df_sales = pd.read_excel(xls, "Sales_TX")
            df_opex = pd.read_excel(xls, "OPEX_TX")
            df_roles = pd.read_excel(xls, "TP_Roles")
            df_benchmarks = pd.read_excel(xls, "Benchmarks")
            
            progress.add_task(description="Applying TP Rule Engine...", total=None)
            df_total = core.calculate_allocations(df_sales, df_opex, df_benchmarks, df_roles)
            
            progress.add_task(description=f"Saving report to {output}...", total=None)
            df_total.to_excel(output, index=False)

        # Show a summary table
        table = Table(title="Financial Summary (Top 5 Entities)")
        table.add_column("CoCode", style="cyan")
        table.add_column("Revenue", justify="right")
        table.add_column("Profit", justify="right")
        table.add_column("TP Adj", justify="right", style="magenta")
        
        for _, row in df_total.head(5).iterrows():
            table.add_row(
                row["Company Code"],
                f"{row['Revenue']:,.2f}",
                f"{row['Final Operating Profit']:,.2f}",
                f"{row['TP Adjustment']:,.2f}",
            )
        
        console.print(table)
        console.print(f"[bold green]Report generated successfully![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if state["verbose"]:
            logging.exception(e)
        raise typer.Exit(code=1)

def random_choice_country():
    return random.choice(["DEU", "USA", "FRA", "GBR", "CHE", "NLD"])

if __name__ == "__main__":
    app()
