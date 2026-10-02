# 1. Prices for the latest day available (usually tomorrow)
last_day = prices["date"].max()
day_prices = prices[prices["date"] == last_day]
sorted_prices = day_prices.sort_values("price_pt")
cheapest = sorted_prices.iloc[0]
most_expensive = sorted_prices.iloc[-1]

st.header(f"Electricity prices for {last_day}")
col1, col2, col3 = st.columns(3)
col1.metric("Average price", f"{day_prices['price_pt'].mean():.1f} €/MWh")
col2.metric(f"Cheapest hour ({cheapest['price_pt']:.1f} €/MWh)", f"{int(cheapest['hour'])}:00")
col3.metric(f"Most expensive hour ({most_expensive['price_pt']:.1f} €/MWh)", f"{int(most_expensive['hour'])}:00")

# Hourly prices as a bar chart (hour as the index)
chart_data = day_prices.set_index("hour")["price_pt"]
st.bar_chart(chart_data, x_label="Hour (Portuguese time)", y_label="€ per MWh")

# The 3 cheapest hours, as text
cheapest_hours = sorted(sorted_prices.head(3)["hour"].tolist())
st.write("The 3 cheapest hours are:", ", ".join(f"{hour}:00" for hour in cheapest_hours))
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

# Footer
st.caption("Built by José Nunes with public data from OMIE and REN. Personal project, views are my own.")
