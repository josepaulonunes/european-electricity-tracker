import pandas as pd
import streamlit as st
import altair as alt
import plotly.express as px

# Page settings
st.set_page_config(page_title="European Electricity Tracker", page_icon="⚡", layout="wide")

# Load the data from the CSV files (kept in memory for one hour so the app stays fast)
@st.cache_data(ttl=3600)
def load_data():
    prices = pd.read_csv("data/prices_hourly.csv")
    production = pd.read_csv("data/production_hourly.csv")
    return prices, production

prices, production = load_data()

# Load the European prices (26 bidding zones) and the 2025 summary, in Central European time
@st.cache_data(ttl=3600)
def load_europe():
    europe = pd.read_csv("data/europe_prices.csv", index_col="time_utc")
    europe.index = pd.to_datetime(europe.index, utc=True).tz_convert("Europe/Brussels")
    summary = pd.read_csv("data/europe_summary_2025.csv", index_col=0)
    return europe, summary

europe, summary = load_europe()

# Profit of a 1 MW battery in one day: buy in the cheapest hours, sell in the most expensive, losing 15% of the energy
def battery_profit(day_prices, hours):
    sorted_prices = day_prices.sort_values()
    cost = sorted_prices.head(hours).sum()
    revenue = sorted_prices.tail(hours).sum() * 0.85
    return revenue - cost

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

# Title
st.title("⚡ European Electricity Tracker")
st.write("Wholesale electricity prices across Europe, with a closer look at Portugal, updated every day. Data: ENTSO-E, OMIE and REN.")

# 1. Europe: latest day with prices for at least 20 countries (usually tomorrow), in Central European time
hours_by_day = europe.groupby(europe.index.strftime("%Y-%m-%d")).count()
countries_per_day = (hours_by_day >= 20).sum(axis=1)
last_europe_day = countries_per_day[countries_per_day >= 20].index.max()
day_europe = europe[europe.index.strftime("%Y-%m-%d") == last_europe_day]

# Average price of the day in each country (only countries with at least 20 hours published)
rows = []
for zone in day_europe.columns:
    if day_europe[zone].count() >= 20:
        rows.append({"country": zones[zone][0], "iso": zones[zone][1], "price": round(day_europe[zone].mean(), 1)})
map_data = pd.DataFrame(rows).sort_values("price")

st.header(f"Electricity prices across Europe on {last_europe_day}")
map_tab, hourly_tab, numbers_tab = st.tabs(["Map", "Hour by hour", "2025 in numbers"])

# Map tab: map and ranking of the average price
with map_tab:
    cheapest_country = map_data.iloc[0]
    most_expensive_country = map_data.iloc[-1]
    portugal_rank = map_data["country"].tolist().index("Portugal") + 1
    portugal_price = map_data[map_data["country"] == "Portugal"]["price"].iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Cheapest ({cheapest_country['price']} €/MWh)", cheapest_country["country"])
    col2.metric(f"Most expensive ({most_expensive_country['price']} €/MWh)", most_expensive_country["country"])
    col3.metric(f"Portugal ({portugal_price} €/MWh)", f"{portugal_rank}.º of {len(map_data)}")

    # Map of Europe coloured by the average price, from green (cheap) to red (expensive)
    fig = px.choropleth(map_data, locations="iso", color="price", hover_name="country",
                        scope="europe", color_continuous_scale="RdYlGn_r", labels={"price": "€/MWh"})
    fig.update_geos(fitbounds="locations")
    fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig)

    # Ranking from cheapest to most expensive, with Portugal in red
    ranking = alt.Chart(map_data).mark_bar().encode(
        x=alt.X("price", title="Average price (€ per MWh)"),
        y=alt.Y("country", sort="x", title=None),
        color=alt.condition(alt.datum.country == "Portugal", alt.value("#d62728"), alt.value("#999999")),
    )
    st.altair_chart(ranking)
    st.caption("Countries with more than one market zone are shown with one zone: Italy (North), Denmark (West), Sweden (Stockholm) and Norway (Oslo). Germany includes Luxembourg.")

# Hour by hour tab: hourly prices of the countries the user picks
with hourly_tab:
    country_names = [zones[zone][0] for zone in zones]
    chosen = st.multiselect("Choose countries", country_names, default=["Portugal", "Spain", "France", "Germany"])
    hourly = day_europe.copy()
    hourly.columns = [zones[zone][0] for zone in hourly.columns]
    hourly.index = hourly.index.hour
    st.line_chart(hourly[chosen], x_label="Hour (Central European time)", y_label="€ per MWh")
    st.write("Countries with a lot of solar have cheap middays and expensive evenings. Countries with a lot of hydro, like Norway, have flat prices.")

# 2025 tab: summary of 2025 for every country
with numbers_tab:
    table = summary.rename(columns={
        "average_price": "Average price (€/MWh)",
        "negative_hours": "Hours with a negative price",
        "solar_capture_rate": "Solar capture rate (%)",
        "battery_profit": "Battery profit (thousand €/MW)",
    })
    st.dataframe(table)
    st.caption("Solar capture rate: price received by solar compared with the average price. Battery profit: a 1 MW / 4 MWh battery that buys in the 4 cheapest hours and sells in the 4 most expensive each day. None: no reliable solar data for that country.")

# 2. Portugal: prices for the latest day available (usually tomorrow), in Portuguese time
last_day = prices["date"].max()
day_prices = prices[prices["date"] == last_day].copy()
day_prices["time"] = day_prices["hour"].astype(str) + ":00"
sorted_prices = day_prices.sort_values("price_pt")
cheapest = sorted_prices.iloc[0]
most_expensive = sorted_prices.iloc[-1]

st.header(f"Portugal in detail: electricity prices for {last_day}")
col1, col2, col3 = st.columns(3)
col1.metric("Average price", f"{day_prices['price_pt'].mean():.1f} €/MWh")
col2.metric(f"Cheapest hour ({cheapest['price_pt']:.1f} €/MWh)", f"{int(cheapest['hour'])}:00")
col3.metric(f"Most expensive hour ({most_expensive['price_pt']:.1f} €/MWh)", f"{int(most_expensive['hour'])}:00")

# Hourly prices as a bar chart with all 24 hours of the day, from 0:00 to 23:00
all_hours = [f"{hour}:00" for hour in range(24)]
chart = alt.Chart(day_prices).mark_bar().encode(
    x=alt.X("time", sort=all_hours, scale=alt.Scale(domain=all_hours), title="Hour (Portuguese time)", axis=alt.Axis(labelAngle=0)),
    y=alt.Y("price_pt", title="€ per MWh"),
)
st.altair_chart(chart)

# Note when 23:00 is not published yet
if len(day_prices) < 24:
    st.caption("23:00 is not published yet. The market works on Spanish time, one hour ahead, so 23:00 in Portugal belongs to the next market day and appears tomorrow afternoon.")

# The 3 cheapest hours, as text
cheapest_hours = sorted_prices.head(3).sort_index()["hour"].tolist()
st.write("The 3 cheapest hours are:", ", ".join(f"{hour}:00" for hour in cheapest_hours))

# 3. Electricity mix on the latest day with production data
last_production_day = production["date"].max()
day_production = production[production["date"] == last_production_day]
sources = ["hydro", "wind", "solar", "natural_gas", "biomass", "import"]

st.header(f"Where the electricity came from on {last_production_day}")
st.area_chart(day_production.set_index("hour")[sources], x_label="Hour (Portuguese time)", y_label="MW")

# Join prices and production for the long-term analysis
df = pd.merge(prices, production, on=["date", "hour"])
df["year"] = df["date"].str[:4]
df["renewable_share"] = (df["wind"] + df["solar"]) / df["consumption"] * 100

# 4. Long-term analysis in four tabs
st.header("How wind and solar are changing electricity prices")
tab1, tab2, tab3, tab4 = st.tabs(["Prices by hour of the day", "The value of solar", "Price vs wind and solar", "The value of a battery"])

# Tab 1: average price by hour, for the years the user picks
with tab1:
    years = st.multiselect("Choose years", sorted(df["year"].unique()), default=["2019", "2023", "2025"])
    by_hour = df[df["year"].isin(years)].groupby(["hour", "year"])["price_pt"].mean().unstack()
    st.line_chart(by_hour, x_label="Hour (Portuguese time)", y_label="€ per MWh")
    st.write("Solar now pushes midday prices down, while evening prices stay high: the duck curve.")

# Tab 2: solar capture rate by year
with tab2:
    df["price_x_solar"] = df["price_pt"] * df["solar"]
    yearly = df.groupby("year")[["price_x_solar", "solar"]].sum()
    yearly["capture_rate"] = yearly["price_x_solar"] / yearly["solar"] / df.groupby("year")["price_pt"].mean() * 100
    st.line_chart(yearly["capture_rate"], x_label="Year", y_label="% of the average price")
    st.write("Solar energy used to be worth the average price. Today it is worth about half, because all solar plants produce at the same hours.")

# Tab 3: average price by share of wind and solar (2023 onwards)
with tab3:
    df["share_group"] = ((df["renewable_share"] // 10) * 10).clip(upper=100)
    by_share = df[df["year"] >= "2023"].groupby("share_group")["price_pt"].mean()
    st.bar_chart(by_share, x_label="Wind and solar as % of consumption", y_label="€ per MWh")
    st.write("Each extra percentage point of wind and solar lowers the price by about 0.94 €/MWh (regression controlling for demand, hydro and year).")

# Tab 4: what a 1 MW battery would earn, tomorrow and in each year
with tab4:
    hours = st.slider("Hours of storage (a 1 MW battery that charges and discharges once a day)", 1, 6, 4)

    # Tomorrow: best hours to charge and discharge
    charge_hours = sorted_prices.head(hours).sort_index()["hour"].tolist()
    discharge_hours = sorted_prices.tail(hours).sort_index()["hour"].tolist()
    st.metric(f"Profit on {last_day}", f"{battery_profit(day_prices['price_pt'], hours):.0f} €")
    st.write("Charge at:", ", ".join(f"{hour}:00" for hour in charge_hours), "| Discharge at:", ", ".join(f"{hour}:00" for hour in discharge_hours))

    # Every year: average daily profit times 365, in thousand euros
    daily = prices.groupby("date")["price_pt"].apply(battery_profit, hours).reset_index(name="profit")
    daily["year"] = daily["date"].str[:4]
    by_year = daily.groupby("year")["profit"].mean() * 365 / 1000
    st.bar_chart(by_year, x_label="Year", y_label="Thousand € per MW per year")
    st.write("The bigger the gap between midday and evening prices, the more a battery earns. This is a simple upper estimate: it ignores the order of the hours, network costs and battery wear. 2026 is shown at the pace of the year so far.")

# Footer
st.caption("Built by José Nunes with public data from ENTSO-E, OMIE and REN. Personal project, views are my own.")