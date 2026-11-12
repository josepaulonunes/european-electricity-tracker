import pandas as pd
import streamlit as st
import plotly.express as px

# Page settings
st.set_page_config(page_title="European Electricity Tracker", page_icon="⚡", layout="wide")

# All the style of the app in one place: the top banner, the white cards and the phone layout
st.markdown("""
<style>
.block-container {padding-top: 2rem;}
.hero {background: linear-gradient(135deg, #0b2545 0%, #1d4e89 60%, #f59e0b 135%); color: white; border-radius: 18px; padding: 28px 32px; margin-bottom: 10px;}
.hero-title {font-size: 2.2rem; font-weight: 700; line-height: 1.2;}
.hero-text {opacity: 0.9; margin: 6px 0 14px 0;}
.chip {display: inline-block; background: rgba(255,255,255,0.16); border-radius: 999px; padding: 4px 12px; margin: 0 6px 6px 0; font-size: 0.85rem;}
div[data-testid="stMetric"] {background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
div[data-testid="stMetricLabel"] p {color: #6b7280;}
[class*="st-key-card"] {background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
@media (max-width: 640px) {
    .hero {padding: 20px;}
    .hero-title {font-size: 1.6rem;}
    [class*="st-key-kpi"] div[data-testid="stColumn"] {min-width: calc(50% - 1rem); flex: 1 1 calc(50% - 1rem);}
}
</style>
""", unsafe_allow_html=True)

# Colours used in every chart, with one fixed colour for each energy source
colours = {"main": "#1d4e89", "accent": "#f59e0b", "grey": "#94a3b8", "text": "#111827", "grid": "#e5e7eb"}
palette = ["#1d4e89", "#0e7490", "#7c3aed", "#db2777", "#65a30d", "#9a3412", "#475569", "#38bdf8", "#94a3b8"]
price_scale = ["#fef3c7", "#fbbf24", "#ea580c", "#7c2d12"]
source_colours = {
    "Hydro": "#0e7490", "Wind": "#3b82f6", "Solar": "#f5b301",
    "Natural gas": "#9a3412", "Biomass": "#65a30d", "Imports": "#94a3b8",
}
year_colours = {
    "2019": "#cbd5e1", "2020": "#94a3b8", "2021": "#64748b", "2022": "#38bdf8",
    "2023": "#3b82f6", "2024": "#1d4e89", "2025": "#f59e0b", "2026": "#9a3412",
}


# One look for every chart: same font, soft grid, legend on top, no toolbar
def show_chart(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        font=dict(family="Inter, sans-serif", size=13, color=colours["text"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", title_text=""),
        hoverlabel=dict(bgcolor="white", font_size=13),
        dragmode=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor=colours["grid"], zeroline=False)
    st.plotly_chart(fig, config={"displayModeBar": False})


# A date like 2026-11-12 written as 12 November 2026
def nice_date(day):
    return pd.to_datetime(day).strftime("%d %B %Y")


# Profit of a 1 MW battery in one day: buy in the cheapest hours, sell in the most expensive, losing 15% of the energy
def battery_profit(day_prices, hours):
    sorted_prices = day_prices.sort_values()
    cost = sorted_prices.head(hours).sum()
    revenue = sorted_prices.tail(hours).sum() * 0.85
    return revenue - cost


# Load the Portuguese data from the CSV files (kept in memory for one hour so the app stays fast)
@st.cache_data(ttl=3600)
def load_data():
    prices = pd.read_csv("data/prices_hourly.csv")
    production = pd.read_csv("data/production_hourly.csv")
    return prices, production


# Load the European prices (26 bidding zones) and the 2025 summary, in Central European time
@st.cache_data(ttl=3600)
def load_europe():
    europe = pd.read_csv("data/europe_prices.csv", index_col="time_utc")
    europe.index = pd.to_datetime(europe.index, utc=True).tz_convert("Europe/Brussels")
    summary = pd.read_csv("data/europe_summary_2025.csv", index_col=0)
    return europe, summary


prices, production = load_data()
europe, summary = load_europe()

# Name and country code (for the map) of each bidding zone
zones = {
    "PT": ["Portugal", "PRT"], "ES": ["Spain", "ESP"], "FR": ["France", "FRA"],
    "BE": ["Belgium", "BEL"], "NL": ["Netherlands", "NLD"], "DE_LU": ["Germany", "DEU"],
    "AT": ["Austria", "AUT"], "CH": ["Switzerland", "CHE"], "IT_NORD": ["Italy", "ITA"],
    "PL": ["Poland", "POL"], "CZ": ["Czechia", "CZE"], "SK": ["Slovakia", "SVK"],
    "HU": ["Hungary", "HUN"], "SI": ["Slovenia", "SVN"], "HR": ["Croatia", "HRV"],
    "RO": ["Romania", "ROU"], "BG": ["Bulgaria", "BGR"], "GR": ["Greece", "GRC"],
    "DK_1": ["Denmark", "DNK"], "SE_3": ["Sweden", "SWE"], "NO_1": ["Norway", "NOR"],
    "FI": ["Finland", "FIN"], "EE": ["Estonia", "EST"], "LV": ["Latvia", "LVA"],
    "LT": ["Lithuania", "LTU"], "IE_SEM": ["Ireland", "IRL"],
}

# Europe: latest day with prices for at least 20 countries (usually tomorrow), in Central European time
recent = europe.tail(24 * 10)
recent_days = recent.index.strftime("%Y-%m-%d")
hours_by_day = recent.groupby(recent_days).count()
countries_per_day = (hours_by_day >= 20).sum(axis=1)
last_europe_day = countries_per_day[countries_per_day >= 20].index.max()
day_europe = recent[recent_days == last_europe_day]

# Average price of the day in each country (only countries with at least 20 hours published)
rows = []
for zone in day_europe.columns:
    if day_europe[zone].count() >= 20:
        group = "Other markets"
        if zone == "PT":
            group = "Portugal"
        rows.append({"country": zones[zone][0], "iso": zones[zone][1], "price": round(day_europe[zone].mean(), 1), "group": group})
map_data = pd.DataFrame(rows).sort_values("price")
cheapest_country = map_data.iloc[0]
most_expensive_country = map_data.iloc[-1]

# Portugal in the European ranking (some days ENTSO-E has no Portuguese prices yet)
portugal_label = "Portugal"
portugal_price = "No data yet"
if "Portugal" in map_data["country"].tolist():
    portugal_rank = map_data["country"].tolist().index("Portugal") + 1
    portugal_label = f"Portugal (#{portugal_rank} cheapest of {len(map_data)})"
    portugal_price = f"{map_data[map_data['country'] == 'Portugal']['price'].iloc[0]:.1f} €/MWh"

# Portugal: prices for the latest day available (usually tomorrow), in Portuguese time
last_day = prices["date"].max()
day_prices = prices[prices["date"] == last_day].copy()
sorted_prices = day_prices.sort_values("price_pt")
cheapest = sorted_prices.iloc[0]
most_expensive = sorted_prices.iloc[-1]
cheapest_hours = sorted_prices.head(3).sort_index()["hour"].tolist()

# Portugal: electricity mix on the latest day with production data
last_production_day = production["date"].max()
day_production = production[production["date"] == last_production_day]
wind_solar_share = (day_production["wind"].sum() + day_production["solar"].sum()) / day_production["consumption"].sum() * 100

# Join prices and production for the long-term analysis
df = pd.merge(prices, production, on=["date", "hour"])
df["year"] = df["date"].str[:4]
df["renewable_share"] = (df["wind"] + df["solar"]) / df["consumption"] * 100

# Solar capture rate by year: price received by solar divided by the average price
df["price_x_solar"] = df["price_pt"] * df["solar"]
yearly = df.groupby("year")[["price_x_solar", "solar"]].sum()
yearly["capture_rate"] = yearly["price_x_solar"] / yearly["solar"] / df.groupby("year")["price_pt"].mean() * 100
capture = yearly["capture_rate"].reset_index()
last_year = capture["year"].iloc[-1]
last_capture = capture["capture_rate"].iloc[-1]

# Top banner with the main numbers of the day
st.markdown(f"""
<div class="hero">
    <div class="hero-title">⚡ European Electricity Tracker</div>
    <div class="hero-text">Day-ahead power prices for 26 European markets, with a closer look at Portugal. Updated every afternoon.</div>
    <span class="chip">Prices for {nice_date(last_europe_day)}</span>
    <span class="chip">Cheapest: {cheapest_country['country']} at {cheapest_country['price']:.0f} €/MWh</span>
    <span class="chip">Most expensive: {most_expensive_country['country']} at {most_expensive_country['price']:.0f} €/MWh</span>
    <span class="chip">Portugal: {portugal_price}</span>
    <span class="chip">Solar earns {last_capture:.0f}% of the average price in Portugal in {last_year}</span>
</div>
""", unsafe_allow_html=True)
st.caption("Data from ENTSO-E, OMIE and REN. Built by José Nunes. Personal project, views are my own.")

tab_europe, tab_portugal, tab_renewables, tab_battery = st.tabs([
    ":material/public: Europe",
    ":material/flag: Portugal",
    ":material/solar_power: Wind and solar",
    ":material/battery_charging_full: Battery",
])

# 1. Europe: map, ranking, hourly prices and the 2025 numbers
with tab_europe:
    st.subheader(f":material/public: Prices across Europe on {nice_date(last_europe_day)}")

    # Top numbers
    with st.container(key="kpi_europe"):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f":material/arrow_downward: Cheapest: {cheapest_country['country']}", f"{cheapest_country['price']:.1f} €/MWh")
        col2.metric(f":material/arrow_upward: Most expensive: {most_expensive_country['country']}", f"{most_expensive_country['price']:.1f} €/MWh")
        col3.metric(f":material/flag: {portugal_label}", portugal_price)
        col4.metric(":material/bolt: Average of all markets", f"{map_data['price'].mean():.1f} €/MWh")

    col_map, col_ranking = st.columns([3, 2])

    # Map of Europe coloured by the average price, from light yellow (cheap) to dark red (expensive)
    with col_map:
        with st.container(border=True, key="card_map"):
            st.subheader(":material/map: Average price of the day")
            fig = px.choropleth(map_data, locations="iso", color="price", hover_name="country", scope="europe",
                                color_continuous_scale=price_scale, labels={"price": "€/MWh"}, hover_data={"iso": False})
            fig.update_geos(fitbounds="locations", showframe=False, showcoastlines=False, showland=True, landcolor="#e5e7eb",
                            showcountries=True, countrycolor="white", bgcolor="rgba(0,0,0,0)")
            fig.update_traces(marker_line_color="white", marker_line_width=0.8)
            fig.update_layout(coloraxis_colorbar=dict(title="€/MWh", orientation="h", thickness=14, len=0.7, y=-0.08))
            show_chart(fig, 560)
            st.caption("Darker means more expensive. Countries in grey have no prices for this day yet.")

    # Ranking from cheapest to most expensive, with Portugal highlighted
    with col_ranking:
        with st.container(border=True, key="card_ranking"):
            st.subheader(":material/leaderboard: From cheapest to most expensive")
            fig = px.bar(map_data, x="price", y="country", orientation="h", color="group", text_auto=".0f",
                         color_discrete_map={"Portugal": colours["accent"], "Other markets": colours["grey"]},
                         category_orders={"country": map_data["country"].tolist()})
            fig.update_layout(showlegend=False, xaxis_title="€ per MWh", yaxis_title="")
            fig.update_yaxes(autorange="reversed")
            show_chart(fig, 560)
            st.caption("Average day-ahead price in each market. Portugal is the orange bar.")

    st.caption("Countries with more than one market zone are shown with one zone: Italy (North), Denmark (West), Sweden (Stockholm) and Norway (Oslo). Germany includes Luxembourg.")

    # Hourly prices of the countries the user picks
    with st.container(border=True, key="card_hourly"):
        st.subheader(":material/schedule: Hour by hour")
        available = [zones[zone][0] for zone in day_europe.columns if day_europe[zone].count() >= 20]
        default = [country for country in ["Portugal", "Spain", "France", "Germany"] if country in available]
        chosen = st.multiselect("Choose countries", available, default=default)
        hourly = day_europe.copy()
        hourly.columns = [zones[zone][0] for zone in hourly.columns]
        hourly.index = hourly.index.hour
        if len(chosen) > 0:
            fig = px.line(hourly[chosen], color_discrete_sequence=palette, color_discrete_map={"Portugal": colours["accent"]})
            fig.update_traces(line_width=2)
            fig.update_layout(xaxis_title="Hour (Central European time)", yaxis_title="€ per MWh", hovermode="x unified")
            show_chart(fig, 380)
        else:
            st.info("Pick at least one country to see the chart.", icon=":material/info:")
        st.caption("Countries with a lot of solar have cheap middays and expensive evenings. Countries with a lot of hydro, like Norway, have flatter prices.")

    # Summary of 2025 for every country
    with st.container(border=True, key="card_2025"):
        st.subheader(":material/table_chart: 2025 in numbers")
        table = summary.rename(columns={
            "average_price": "Average price (€/MWh)",
            "negative_hours": "Hours with a negative price",
            "solar_capture_rate": "Solar capture rate (%)",
            "battery_profit": "Battery margin (thousand €/MW)",
        })
        st.dataframe(table)
        st.caption("Solar capture rate: price received by solar compared with the average price. Battery margin: a 1 MW / 4 MWh battery that buys in the 4 cheapest hours and sells in the 4 most expensive each day. Since October 2025 the market uses 15-minute prices, which I average into hours, so negative hours are counted on the low side. None: no reliable solar data for that country.")

# 2. Portugal: prices and electricity mix of the latest day
with tab_portugal:
    st.subheader(f":material/flag: Prices in Portugal on {nice_date(last_day)}")

    # Top numbers
    with st.container(key="kpi_portugal"):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(":material/euro: Average price", f"{day_prices['price_pt'].mean():.1f} €/MWh")
        col2.metric(f":material/arrow_downward: Cheapest hour ({int(cheapest['hour'])}:00)", f"{cheapest['price_pt']:.1f} €/MWh")
        col3.metric(f":material/arrow_upward: Most expensive hour ({int(most_expensive['hour'])}:00)", f"{most_expensive['price_pt']:.1f} €/MWh")
        col4.metric(f":material/wind_power: Wind and solar on {nice_date(last_production_day)}", f"{wind_solar_share:.0f}% of consumption")

    # Hourly prices as a bar chart, with the 3 cheapest hours highlighted
    with st.container(border=True, key="card_prices"):
        st.subheader(":material/bar_chart: Price in each hour")
        day_prices["group"] = "Other hours"
        day_prices.loc[day_prices["hour"].isin(cheapest_hours), "group"] = "3 cheapest hours"
        fig = px.bar(day_prices, x="hour", y="price_pt", color="group",
                     color_discrete_map={"3 cheapest hours": colours["accent"], "Other hours": colours["main"]})
        fig.update_layout(xaxis_title="Hour (Portuguese time)", yaxis_title="€ per MWh", bargap=0.15)
        fig.update_xaxes(range=[-0.5, 23.5], dtick=2)
        show_chart(fig, 380)
        st.write("The 3 cheapest hours are:", ", ".join(f"{hour}:00" for hour in cheapest_hours))

        # Note when 23:00 is not published yet
        if len(day_prices) < 24:
            st.caption("23:00 is not published yet. The market works on Spanish time, one hour ahead, so 23:00 in Portugal belongs to the next market day and appears tomorrow afternoon.")

    # Electricity mix by source, with consumption as a dotted line
    with st.container(border=True, key="card_mix"):
        st.subheader(f":material/stacked_line_chart: Where the electricity came from on {nice_date(last_production_day)}")
        mix = day_production.rename(columns={
            "hydro": "Hydro", "wind": "Wind", "solar": "Solar",
            "natural_gas": "Natural gas", "biomass": "Biomass", "import": "Imports",
        })
        fig = px.area(mix, x="hour", y=list(source_colours.keys()), color_discrete_map=source_colours)
        fig.update_traces(line_width=0.5)
        fig.add_scatter(x=mix["hour"], y=mix["consumption"], name="Consumption", mode="lines",
                        line=dict(color=colours["text"], width=2, dash="dot"))
        fig.update_layout(xaxis_title="Hour (Portuguese time)", yaxis_title="MW", hovermode="x unified")
        fig.update_xaxes(dtick=2)
        show_chart(fig, 400)
        st.caption("Each colour is one source and the dotted line is consumption. When the colours go above the line, the extra power is exported or used to pump water uphill.")

# 3. Long-term analysis: how wind and solar change prices in Portugal
with tab_renewables:
    st.subheader(":material/solar_power: How wind and solar are changing prices in Portugal")

    # Average price by hour, for the years the user picks
    with st.container(border=True, key="card_duck"):
        st.subheader(":material/show_chart: Prices by hour of the day")
        years = st.multiselect("Choose years", sorted(df["year"].unique()), default=["2019", "2023", "2025"])
        if len(years) > 0:
            by_hour = df[df["year"].isin(years)].groupby(["hour", "year"])["price_pt"].mean().unstack()
            fig = px.line(by_hour, color_discrete_map=year_colours)
            fig.update_traces(line_width=2)
            fig.update_layout(xaxis_title="Hour (Portuguese time)", yaxis_title="€ per MWh", hovermode="x unified")
            fig.update_xaxes(dtick=2)
            show_chart(fig, 380)
        else:
            st.info("Pick at least one year to see the chart.", icon=":material/info:")
        st.caption("Solar now pushes midday prices down, while evening prices stay high. This shape is called the duck curve.")

    col_capture, col_share = st.columns(2)

    # Solar capture rate by year
    with col_capture:
        with st.container(border=True, key="card_capture"):
            st.subheader(":material/trending_down: The value of solar")
            fig = px.line(capture, x="year", y="capture_rate", markers=True, color_discrete_sequence=[colours["accent"]])
            fig.update_traces(line_width=3, marker_size=9)
            fig.add_hline(y=100, line_dash="dot", line_color=colours["grey"])
            fig.update_layout(xaxis_title="", yaxis_title="% of the average price")
            show_chart(fig, 360)
            st.caption("Solar energy used to be worth the average price (the dotted line). Today it is worth about half, because all solar plants produce at the same hours.")

    # Average price by share of wind and solar (2023 onwards)
    with col_share:
        with st.container(border=True, key="card_share"):
            st.subheader(":material/wind_power: Price vs wind and solar")
            df["share_group"] = ((df["renewable_share"] // 10) * 10).clip(upper=100)
            by_share = df[df["year"] >= "2023"].groupby("share_group")["price_pt"].mean().reset_index()
            fig = px.bar(by_share, x="share_group", y="price_pt", color_discrete_sequence=[colours["main"]])
            fig.update_layout(xaxis_title="Wind and solar as % of consumption", yaxis_title="€ per MWh")
            fig.update_xaxes(dtick=10)
            show_chart(fig, 360)
            st.caption("Average price since 2023, in groups of 10 points. In a regression on hourly data from 2019 to October 2026, each extra point of wind and solar goes with a price about 0.94 €/MWh lower, holding demand, hydro and the year constant. It is a strong link, not proof of cause, because the gas price is not in the model.")

# 4. What a 1 MW battery would earn, on the latest day and in each year
with tab_battery:
    st.subheader(":material/battery_charging_full: The value of a battery in Portugal")
    with st.container(border=True, key="card_battery"):
        hours = st.slider("Hours of storage (a 1 MW battery that charges and discharges once a day)", 1, 6, 4)

        # Latest day: best hours to charge and discharge
        charge_hours = sorted_prices.head(hours).sort_index()["hour"].tolist()
        discharge_hours = sorted_prices.tail(hours).sort_index()["hour"].tolist()
        st.metric(f":material/euro: Margin on {nice_date(last_day)}", f"{battery_profit(day_prices['price_pt'], hours):.0f} €")
        st.write("Charge at:", ", ".join(f"{hour}:00" for hour in charge_hours), "| Discharge at:", ", ".join(f"{hour}:00" for hour in discharge_hours))

        # Every year: average daily margin times 365, in thousand euros
        daily = prices.groupby("date")["price_pt"].apply(battery_profit, hours).reset_index(name="profit")
        daily["year"] = daily["date"].str[:4]
        by_year = (daily.groupby("year")["profit"].mean() * 365 / 1000).reset_index()
        by_year["group"] = "Full year"
        by_year.loc[by_year["year"] == by_year["year"].max(), "group"] = "Year so far, at a yearly pace"
        fig = px.bar(by_year, x="year", y="profit", color="group", text_auto=".0f",
                     color_discrete_map={"Full year": colours["main"], "Year so far, at a yearly pace": colours["accent"]})
        fig.update_layout(xaxis_title="", yaxis_title="Thousand € per MW per year")
        show_chart(fig, 380)
        st.caption("The bigger the gap between midday and evening prices, the more a battery earns. This is a rough estimate of the trading margin, not a business case: it ignores the order of the hours, network costs, battery wear and the cost of the battery itself.")
