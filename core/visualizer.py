import plotly.express as px
import pandas as pd

def plot_by_category(df):
    ausgaben = df[df["type"] == "Ausgabe"].copy()
    by_category = ausgaben.groupby("sub_category")["amount"].sum().abs().reset_index()
    by_category.columns = ["Kategorie", "Betrag"]
    by_category = by_category.sort_values("Betrag", ascending=False)

    fig = px.bar(
        by_category,
        x="Kategorie",
        y="Betrag",
        title="Ausgaben nach Kategorie",
        color="Betrag",
        color_continuous_scale="Reds",
        labels={"Betrag": "Betrag (€)"}
    )
    return fig   
    
def plot_by_month(df):
    by_month = df.groupby(df["date"].dt.strftime("%Y-%m"))["amount"].sum().reset_index()
    by_month.columns = ["Monat", "Betrag"]
    
    fig = px.bar(
        by_month,
        x="Monat",
        y="Betrag",
        title="Einnahmen & Ausgaben pro Monat",
        color="Betrag",
        color_continuous_scale="RdYlGn",
        labels={"Betrag": "Betrag (€)"}
    )
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    return fig

def plot_pie_category(df):
    ausgaben = df[df["type"] == "Ausgabe"].copy()
    by_category = ausgaben.groupby("sub_category")["amount"].sum().abs().reset_index()
    by_category.columns = ["Kategorie", "Betrag"]

    fig = px.pie(
        by_category,
        names="Kategorie",
        values="Betrag",
        title="Ausgaben Verteilung nach Kategorie"
    )
    return fig

def plot_over_time(df):
    df_sorted = df.sort_values("date")
    df_sorted["kumulativ"] = df_sorted["amount"].cumsum()

    fig = px.line(
        df_sorted,
        x="date",
        y="kumulativ",
        title="Kontostand Verlauf (kumulativ)",
        labels={"date": "Datum", "kumulativ": "Betrag (€)"}
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red")
    return fig

def plot_income_vs_expenses(df):
    einnahmen = df[df["type"] == "Einnahme"]["amount"].sum().round(2)
    ausgaben = abs(df[df["type"] == "Ausgabe"]["amount"].sum().round(2))
    differenz = round(einnahmen - ausgaben, 2)


    fig = px.bar(
        x=["Einnahmen", "Ausgaben", "Differenz"],
        y=[einnahmen, ausgaben, differenz],
        color=["Einnahmen", "Ausgaben", "Differenz"],
        color_discrete_map={"Einnahmen": "green", "Ausgaben": "tomato", "Differenz": "steelblue" if differenz >= 0 else "orange"},
        title="Einnahmen vs Ausgaben vs Differenz",
        labels={"x": "", "y": "Betrag (€)"}
    )
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    return fig
    