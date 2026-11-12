import pandas as pd
import matplotlib.pyplot as plt

# Colours of the app: Portugal in orange, other countries in light grey
orange = "#f59e0b"
grey = "#cbd5e1"
navy = "#0b2545"


# Clean look for every chart: bold title on the left, no box around it
def clean_chart(ax, title):
    ax.set_title(title, fontsize=14, fontweight="bold", color=navy, loc="left", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# Ranking of the countries in 2025, with Portugal in orange and the value at the end of each bar
def ranking_chart(column, title, xlabel, file):
    values = summary[column].dropna().sort_values()
    colours = []
    for country in values.index:
        if country == "Portugal":
            colours.append(orange)
        else:
            colours.append(grey)

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(values.index, values, color=colours)
    for i in range(len(values)):
        ax.text(values.iloc[i], i, " " + str(round(values.iloc[i])), va="center", fontsize=9, color="#475569")
    clean_chart(ax, title)
    ax.set_xlabel(xlabel)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    fig.tight_layout()
    fig.savefig("figures/" + file, dpi=150)
    plt.close(fig)


# 1. The four European rankings for 2025
summary = pd.read_csv("data/europe_summary_2025.csv", index_col=0)
ranking_chart("average_price", "Average price in 2025 (€ per MWh)", "", "europe_price_ranking.png")
ranking_chart("negative_hours", "Hours with a negative price in 2025", "", "europe_negative_hours.png")
ranking_chart("solar_capture_rate", "What solar earns, as % of the average price (2025)", "", "europe_capture_rate.png")
ranking_chart("battery_profit", "Yearly margin of a 1 MW / 4 MWh battery in 2025 (thousand €)", "", "europe_battery_value.png")

# 2. Portugal: average price by hour of the day in 2019, 2023 and 2025
prices = pd.read_csv("data/prices_hourly.csv")
prices["year"] = prices["date"].str[:4]
year_colours = {"2019": "#94a3b8", "2023": "#3b82f6", "2025": orange}

fig, ax = plt.subplots(figsize=(9, 5))
for year in year_colours:
    by_hour = prices[prices["year"] == year].groupby("hour")["price_pt"].mean()
    ax.plot(by_hour.index, by_hour.values, color=year_colours[year], linewidth=3, label=year)
clean_chart(ax, "Portugal: average price by hour of the day (€ per MWh)")
ax.set_xlabel("Hour (Portuguese time)")
ax.set_xticks(range(0, 24, 2))
ax.grid(True, axis="y", color="#e5e7eb")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig("figures/duck_curve.png", dpi=150)
plt.close(fig)

# 3. Portugal: average price by share of wind and solar, since 2023
production = pd.read_csv("data/production_hourly.csv")
df = pd.merge(prices, production, on=["date", "hour"])
df = df[df["year"] >= "2023"]
df["share_group"] = ((df["wind"] + df["solar"]) / df["consumption"] * 100 // 10 * 10).clip(upper=100)
by_share = df.groupby("share_group")["price_pt"].mean()

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(by_share.index, by_share.values, width=8, color="#1d4e89")
clean_chart(ax, "Portugal: average price by share of wind and solar, 2023 onwards")
ax.set_xlabel("Wind and solar as % of consumption")
ax.set_ylabel("€ per MWh")
ax.grid(True, axis="y", color="#e5e7eb")
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig("figures/price_by_renewable_share.png", dpi=150)
plt.close(fig)

print("Saved 6 charts in figures/")
