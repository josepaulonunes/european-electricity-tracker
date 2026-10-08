import os
import pandas as pd
from entsoe import EntsoePandasClient

# Connect to the ENTSO-E API (on GitHub the token comes from a secret, on the computer from the file)
token = os.environ.get("ENTSOE_TOKEN")
if token is None:
    token = open("entsoe_token.txt").read().strip()
client = EntsoePandasClient(api_key=token, timeout=60)

# Zones with prices and zones with production
price_zones = ["PT", "ES", "FR", "BE", "NL", "DE_LU", "AT", "CH", "IT_NORD", "PL", "CZ", "SK", "HU",
               "SI", "HR", "RO", "BG", "GR", "DK_1", "SE_3", "NO_1", "FI", "EE", "LV", "LT", "IE_SEM"]
production_zones = ["PT", "ES", "FR", "DE_LU", "IT_NORD", "NL", "BE", "PL", "AT",
                    "DK_1", "FI", "GR", "HU", "RO", "CZ"]

# Read the European files that are already saved
prices = pd.read_csv("data/europe_prices.csv", index_col="time_utc")
production = pd.read_csv("data/europe_production.csv", index_col="time_utc")
prices.index = pd.to_datetime(prices.index, utc=True)
production.index = pd.to_datetime(production.index, utc=True)

# Download again from 3 days before the last saved day, to fill any gaps
today = pd.Timestamp.today(tz="Europe/Brussels").normalize()
start_prices = prices.index.max().tz_convert("Europe/Brussels").normalize() - pd.Timedelta(days=3)
start_production = production.index.max().tz_convert("Europe/Brussels").normalize() - pd.Timedelta(days=3)


# Solar, wind and consumption of one zone between two dates, as hourly values in UTC
def download_production(zone, start, end):
    generation = client.query_generation(zone, start=start, end=end)
    if isinstance(generation.columns, pd.MultiIndex):
        generation = generation.xs("Actual Aggregated", axis=1, level=1)
    generation = generation.resample("h").mean()
    load = client.query_load(zone, start=start, end=end).resample("h").mean()

    table = pd.DataFrame(index=generation.index)
    table[zone + "_solar"] = 0
    table[zone + "_wind"] = 0
    if "Solar" in generation.columns:
        table[zone + "_solar"] = generation["Solar"]
    if "Wind Onshore" in generation.columns:
        table[zone + "_wind"] = generation["Wind Onshore"]
    if "Wind Offshore" in generation.columns:
        table[zone + "_wind"] = table[zone + "_wind"] + generation["Wind Offshore"].fillna(0)
    table[zone + "_load"] = load["Actual Load"]
    return table.tz_convert("UTC")


# 1. New prices for every zone, until tomorrow
columns = []
for zone in price_zones:
    try:
        price = client.query_day_ahead_prices(zone, start=start_prices, end=today + pd.Timedelta(days=2))
        columns.append(price.resample("h").mean().tz_convert("UTC").rename(zone))
        print(zone, "prices done")
    except Exception as error:
        print(zone, "prices failed:", error)
if len(columns) > 0:
    new_prices = pd.concat(columns, axis=1)
    prices = new_prices.combine_first(prices)[prices.columns]

# 2. New solar, wind and consumption for every zone, until yesterday
tables = []
for zone in production_zones:
    try:
        tables.append(download_production(zone, start_production, today))
        print(zone, "production done")
    except Exception as error:
        print(zone, "production failed:", error)
if len(tables) > 0:
    new_production = pd.concat(tables, axis=1)
    production = new_production.combine_first(production)[production.columns]

# Save the two files
prices.index.name = "time_utc"
production.index.name = "time_utc"
prices.to_csv("data/europe_prices.csv", float_format="%.2f")
production.to_csv("data/europe_production.csv", float_format="%.0f")
print("Prices until", prices.index.max(), "| Production until", production.index.max())