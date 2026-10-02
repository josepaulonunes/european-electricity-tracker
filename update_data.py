import requests
import pandas as pd

PRICES_FILE = "data/prices_hourly.csv"
PRODUCTION_FILE = "data/production_hourly.csv"


# Download one day of OMIE prices (day as YYYYMMDD): one row per 15-minute period
def read_omie_day(day):
    url = "https://www.omie.es/en/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_" + day + ".1"
    response = requests.get(url)
    rows = []
    for line in response.text.splitlines():
        parts = line.split(";")
        if len(parts) >= 6 and parts[0].isdigit():
            rows.append({
                "date": parts[0] + "-" + parts[1] + "-" + parts[2],
                "period": int(parts[3]),
                "price_pt": float(parts[4]),
                "price_es": float(parts[5]),
            })
    return pd.DataFrame(rows)


# Download one day of REN production (day as YYYY-MM-DD): one row per 15 minutes
def read_ren_production_day(day):
    url = "https://servicebus.ren.pt/datahubapi/electricity/ElectricityProductionBreakdownDaily"
    response = requests.get(url, params={"culture": "en-US", "date": day})
    if response.status_code != 200:
        return pd.DataFrame()
    data = response.json()
    table = pd.DataFrame({"time": data["xAxis"]["categories"]})
    for serie in data["series"]:
        table[serie["name"]] = serie["data"]
    table["date"] = day
    return table


# Load the data we already have
prices = pd.read_csv(PRICES_FILE)
production = pd.read_csv(PRODUCTION_FILE)
tomorrow = pd.Timestamp.today() + pd.Timedelta(days=1)
yesterday = pd.Timestamp.today() - pd.Timedelta(days=1)

# Prices: download OMIE again from 2 days before the last day until tomorrow
start_prices = pd.to_datetime(prices["date"].max()) - pd.Timedelta(days=2)
omie_days = []
for day in pd.date_range(start_prices, tomorrow):
    omie_day = read_omie_day(day.strftime("%Y%m%d"))
    if len(omie_day) > 0:
        omie_days.append(omie_day)
    print("OMIE", day.strftime("%Y-%m-%d"), len(omie_day), "periods")

if len(omie_days) > 0:
    omie = pd.concat(omie_days)

    # Turn the 15-minute periods into hours of the Spanish day (0 to 22, 23 or 24)
    omie["hour"] = (omie["period"] - 1) // 4
    omie = omie.groupby(["date", "hour"])[["price_pt", "price_es"]].mean().reset_index()

    # Spanish time to Portuguese time, with the real time zones (handles the clock change days)
    spanish_midnight = pd.to_datetime(omie["date"]).dt.tz_localize("Europe/Madrid")
    portuguese_time = (spanish_midnight + pd.to_timedelta(omie["hour"], unit="h")).dt.tz_convert("Europe/Lisbon")
    omie["date"] = portuguese_time.dt.strftime("%Y-%m-%d")
    omie["hour"] = portuguese_time.dt.hour
    omie = omie.groupby(["date", "hour"])[["price_pt", "price_es"]].mean().round(2).reset_index()
    omie["source"] = "OMIE"

    # Replace those days in the file (the first day only has 23:00, already in the file)
    first_day = start_prices.strftime("%Y-%m-%d")
    omie = omie[omie["date"] >= first_day]
    prices = prices[prices["date"] < first_day]
    prices = pd.concat([prices, omie]).sort_values(["date", "hour"])
    prices.to_csv(PRICES_FILE, index=False)
    print("Prices updated until", prices["date"].max())

# Production: download REN again from the last day in the file until yesterday
start_production = pd.to_datetime(production["date"].max())
production_days = []
for day in pd.date_range(start_production, yesterday):
    production_day = read_ren_production_day(day.strftime("%Y-%m-%d"))
    if len(production_day) > 0:
        production_days.append(production_day)
    print("REN", day.strftime("%Y-%m-%d"), len(production_day), "values")

if len(production_days) > 0:
    new_production = pd.concat(production_days)

    # 15-minute values to hourly averages
    new_production["hour"] = new_production["time"].str[:2].astype(int)
    new_production = new_production.drop(columns=["time"])
    new_production = new_production.groupby(["date", "hour"]).mean().round(1).reset_index()

    # Same simple column names as in the file (e.g. "Natural Gas" becomes "natural_gas")
    new_names = {}
    for col in new_production.columns:
        new_names[col] = col.lower().replace(" + ", "_plus_").replace(" ", "_")
    new_production = new_production.rename(columns=new_names)

    # Replace those days in the file
    first_day = start_production.strftime("%Y-%m-%d")
    production = production[production["date"] < first_day]
    production = pd.concat([production, new_production]).sort_values(["date", "hour"])
    production.to_csv(PRODUCTION_FILE, index=False)
    print("Production updated until", production["date"].max())
