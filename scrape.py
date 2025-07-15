import requests
from bs4 import BeautifulSoup

def scrape_and_group_by_limit():
    URL = "https://tradelinesupply.com/inventory/"
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="tablepress")

    all_tradelines = []
    bank_options = set()
    year_options = set()

    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        try:
            bank = cols[0].text.strip()
            age_cell = row.find("td", class_="nowrap row-click")
            age = age_cell.text.strip() if age_cell else "undefined"

            limit = int(cols[3].text.strip().replace("$", "").replace(",", "") or 0)
            statement_date = cols[4].text.strip()
            reporting = cols[5].text.strip()
            price = float(cols[6].text.strip().replace("$", "").replace(",", "") or 0.0)

            if limit < 2000:
                limit_range = "Under $2,000"
            elif limit < 5000:
                limit_range = "$2,000–4,999"
            elif limit < 10000:
                limit_range = "$5,000–9,999"
            else:
                limit_range = "$10,000+"

            tradeline = {
                "bank": bank,
                "limit": limit,
                "price": price,
                "age": age,  # ← This is a date string like "2020 Jul"
                "reporting": reporting,
                "statement_date": statement_date,
                "buy_link": f"/buy?bank={bank}&price={price}"
            }

            bank_options.add(bank)
            if age and age != "undefined":
                year = age.split()[0]
                if year.isdigit():
                    year_options.add(year)

            all_tradelines.append((limit_range, tradeline))

        except Exception as e:
            print(f"[⚠️] Skipped a row due to error: {e}")
            continue

    grouped = {}
    for limit_range, tradeline in all_tradelines:
        grouped.setdefault(limit_range, []).append(tradeline)

    return grouped, sorted(bank_options), sorted(year_options)
