import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

URL = 'https://tradelinesupply.com/pricing/'

def scrape_and_group_by_limit():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')

    buckets = {
        '0-2500': [],
        '2501-5000': [],
        '5001-10000': [],
        '10001+': []
    }

    for row in rows:
        try:
            product_td = row.find('td', class_='product_data')
            price_td = row.find('td', class_='product_price')
            if not product_td or not price_td:
                continue

            # NEW: Get age from <td class="nowrap row-click">
            date_cell = row.find('td', class_='nowrap row-click')
            date_opened = date_cell.get_text(strip=True) if date_cell else 'N/A'
            age = date_opened if date_opened else "N/A"

            bank_name = product_td.get('data-bankname', '').strip()
            credit_limit_raw = product_td.get('data-creditlimit', '').strip().replace('$', '').replace(',', '')
            credit_limit = int(credit_limit_raw) if credit_limit_raw.isdigit() else 0
            purchase_by = product_td.get('data-purchasebydate', '').strip()
            reporting_period = product_td.get('data-reportingperiod', '').strip()
            availability = product_td.get('data-availability', '').strip()

            price_text = price_td.get_text(strip=True)
            price_match = re.search(r"\$\s?(\d+(?:,\d{3})*(?:\.\d{2})?)", price_text)
            if not price_match:
                continue
            base_price = float(price_match.group(1).replace(",", ""))

            # Simple markup strategy
            if base_price < 500:
                final_price = base_price + 100
            elif base_price <= 1000:
                final_price = base_price + 200
            else:
                final_price = base_price + 300

            formatted = (
                f"🏦 Bank: {bank_name}\n"
                f"💳 Credit Limit: ${credit_limit:,}\n"
                f"📅 Date Opened: {date_opened}\n"
                f"🛒 Purchase Deadline: {purchase_by}\n"
                f"📈 Reporting Period: {reporting_period}\n"
                f"📦 Availability: {availability}\n"
                f"💰 Price: ${final_price:,.2f}"
            )

            item = {
                'bank': bank_name,
                'text': formatted,
                'price': final_price,
                'limit': credit_limit,
                'statement_date': purchase_by,
                'reporting': reporting_period,
                'age': age
            }

            if credit_limit <= 2500:
                buckets['0-2500'].append(item)
            elif credit_limit <= 5000:
                buckets['2501-5000'].append(item)
            elif credit_limit <= 10000:
                buckets['5001-10000'].append(item)
            else:
                buckets['10001+'].append(item)

        except Exception as e:
            print("Row failed:", e)
            continue

    return buckets, list(set([b['bank'] for bucket in buckets.values() for b in bucket if 'bank' in b])), []
