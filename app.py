import pandas as pd
import streamlit as st
import altair as alt

# Page settings
st.set_page_config(page_title="Portugal Electricity Tracker", page_icon="⚡", layout="wide")

# Load the data from the CSV files (kept in memory for one hour so the app stays fast)
@st.cache_data(ttl=3600)
def load_data():
    prices = pd.read_csv("data/prices_hourly.csv")
    production = pd.read_csv("data/production_hourly.csv")
    return prices, production

prices, production = load_data()

# Profit of a 1 MW battery in one day: buy in the cheapest hours, sell in the most expensive, losing 15% of the energy
def battery_profit(day_prices, hours):
    sorted_prices = day_prices.sort_values()
    cost = sorted_prices.head(hours).sum()
    revenue = sorted_prices.tail(hours).sum() * 0.85
    return revenue - cost

# Title
st.title("⚡ Portugal Electricity Tracker")
st.write("Wholesale electricity prices and production by source in Portugal, updated every day. Data: OMIE and REN.")

# 1. Prices for the latest day available (usually tomorrow), in Portuguese time
last_day = prices["date"].max()
day_prices = prices[prices["date"] == last_day].copy()
day_prices["time"] = day_prices["hour"].astype(str) + ":00"
sorted_prices = day_prices.sort_values("price_pt")
cheapest = sorted_prices.iloc[0]
most_expensive = sorted_prices.iloc[-1]

st.header(f"Electricity prices for {last_day}")
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

# 2. Electricity mix on the latest day with production data
last_production_day = production["date"].max()
day_production = production[production["date"] == last_production_day]
sources = ["hydro", "wind", "solar", "natural_gas", "biomass", "import"]

st.header(f"Where the electricity came from on {last_production_day}")
st.area_chart(day_production.set_index("hour")[sources], x_label="Hour (Portuguese time)", y_label="MW")

# Join prices and production for the long-term analysis
df = pd.merge(prices, production, on=["date", "hour"])
df["year"] = df["date"].str[:4]
df["renewable_share"] = (df["wind"] + df["solar"]) / df["consumption"] * 100

# 3. Long-term analysis in four tabs
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
st.caption("Built by José Nunes with public data from OMIE and REN. Personal project, views are my own.")
