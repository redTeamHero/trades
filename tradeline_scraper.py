# tradeline_scraper.py

import requests
from bs4 import BeautifulSoup

URL = 'https://tradelinesupply.com/pricing/'

def scrape_tradelines():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')

    tradelines = []

    for row in rows:
        try:
            product_td = row.find('td', class_='product_data')
            price_td = row.find('td', class_='product_price')
            if not product_td or not price_td:
                continue

            text = product_td.get_text(separator="\n", strip=True)
            lines = text.split('\n')

            bank = lines[0] if len(lines) > 0 else "Unknown"
            limit = int(lines[1].split(": ")[1].replace(',', '').replace('$', '')) if len(lines) > 1 else 0
            opened = lines[2].split(": ")[1] if len(lines) > 2 else "Unknown"
            deadline = lines[3].split(": ")[1] if len(lines) > 3 else "N/A"
            reporting = lines[4].split(": ")[1] if len(lines) > 4 else "N/A"
            availability = lines[5].split(": ")[1] if len(lines) > 5 else "N/A"
            price = float(price_td.get_text(strip=True).replace('$', '').replace(',', ''))

            tradelines.append({
                'bank': bank,
                'limit': limit,
                'opened': opened,
                'deadline': deadline,
                'reporting': reporting,
                'availability': availability,
                'price': price,
                'text': text
            })

        except:
            continue

    return tradelines
