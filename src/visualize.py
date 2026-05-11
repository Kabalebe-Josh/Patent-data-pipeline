"""
Generate static charts from query results.
Saves PNG files to the reports/ directory.
"""
import matplotlib.pyplot as plt
import pandas as pd
import config

def set_style():
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.rcParams['figure.figsize'] = (10, 6)

def yearly_trend_chart():
    df = pd.read_csv(config.REPORTS_DIR / "yearly_trend.csv")
    fig, ax = plt.subplots()
    ax.bar(df['year'], df['patent_count'], color='steelblue')
    ax.set_title('Patents Granted per Year')
    ax.set_xlabel('Year')
    ax.set_ylabel('Number of Patents')
    ax.ticklabel_format(style='plain', axis='y')
    plt.tight_layout()
    plt.savefig(config.REPORTS_DIR / "yearly_trend.png", dpi=100)
    plt.close()

def top_countries_chart():
    df = pd.read_csv(config.REPORTS_DIR / "country_trends.csv").head(10)
    fig, ax = plt.subplots()
    ax.barh(df['country'], df['patent_count'], color='forestgreen')
    ax.set_title('Top 10 Countries by Patent Count')
    ax.set_xlabel('Patent Count')
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(config.REPORTS_DIR / "top_countries.png", dpi=100)
    plt.close()

def top_inventors_chart():
    df = pd.read_csv(config.REPORTS_DIR / "top_inventors.csv").head(10)
    fig, ax = plt.subplots()
    ax.barh(df['name'], df['patent_count'], color='darkorange')
    ax.set_title('Top 10 Inventors by Patent Count')
    ax.set_xlabel('Patent Count')
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(config.REPORTS_DIR / "top_inventors.png", dpi=100)
    plt.close()

def run():
    set_style()
    yearly_trend_chart()
    top_countries_chart()
    top_inventors_chart()
    print("[viz] Charts saved to reports/")

if __name__ == "__main__":
    run()