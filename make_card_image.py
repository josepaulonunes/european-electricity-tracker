import pandas as pd
import matplotlib.pyplot as plt

# Average price by hour of the day in Portugal, in 2019 and in 2025
prices = pd.read_csv("data/prices_hourly.csv")
prices["year"] = prices["date"].str[:4]
by_hour = prices[prices["year"].isin(["2019", "2025"])].groupby(["hour", "year"])["price_pt"].mean().unstack()

# Chart for the project card on my site: the solar hours in light yellow, 2019 in grey and 2025 in orange
fig, ax = plt.subplots(figsize=(6, 5))
ax.axvspan(9, 17, color="#fef3c7")
ax.plot(by_hour.index, by_hour["2019"], color="#94a3b8", linewidth=4)
ax.plot(by_hour.index, by_hour["2025"], color="#f59e0b", linewidth=5)

# Labels written next to the lines instead of a legend
ax.text(13, by_hour["2019"][13] + 4, "2019", color="#64748b", fontsize=17, fontweight="bold", ha="center")
ax.text(13, by_hour["2025"][13] - 10, "2025", color="#b45309", fontsize=17, fontweight="bold", ha="center")
ax.text(13, 4, "solar hours", color="#b45309", fontsize=13, ha="center")

# Title, axes and a clean frame
ax.set_title("Electricity price by hour in Portugal", fontsize=17, fontweight="bold", color="#0b2545", loc="left", pad=14)
ax.set_xlabel("Hour of the day", fontsize=13)
ax.set_ylabel("€ per MWh", fontsize=13)
ax.set_xticks([0, 6, 12, 18, 23])
ax.set_xlim(0, 23)
ax.set_ylim(0, 120)
ax.tick_params(labelsize=12)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
fig.tight_layout()
fig.savefig("figures/site_card.png", dpi=150)
print("Saved figures/site_card.png")
