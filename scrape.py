# Updated homepage route: supports dropdown preset values for price, limit, and age

from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.route('/')
def homepage():
    filter_type = request.args.get("filter_type", "")
    filter_value = request.args.get("filter_value", "").strip().lower()

    all_buckets = scrape_and_group_by_limit()
    filtered_buckets = {}

    for limit_range, tradelines in all_buckets.items():
        filtered = []
        for t in tradelines:
            if not filter_type or not filter_value:
                filtered.append(t)
                continue

            # BANK NAME
            if filter_type == "bank":
                if filter_value == t['bank'].lower():
                    filtered.append(t)

            # PRICE RANGE
            elif filter_type == "price":
                p = t['price']
                if filter_value == "< 500" and p < 500:
                    filtered.append(t)
                elif filter_value == "500 - 1000" and 500 <= p <= 1000:
                    filtered.append(t)
                elif filter_value == "> 1000" and p > 1000:
                    filtered.append(t)

            # CREDIT LIMIT RANGE
            elif filter_type == "limit":
                l = t['limit']
                if filter_value == "< 2500" and l < 2500:
                    filtered.append(t)
                elif filter_value == "2501 - 5000" and 2501 <= l <= 5000:
                    filtered.append(t)
                elif filter_value == "5001 - 10000" and 5001 <= l <= 10000:
                    filtered.append(t)
                elif filter_value == "> 10000" and l > 10000:
                    filtered.append(t)

            # AGE / DATE OPENED YEAR
            elif filter_type == "age":
                try:
                    year = int(t['opened'].split()[0])
                    if filter_value == "2024" and year == 2024:
                        filtered.append(t)
                    elif filter_value == "2023" and year == 2023:
                        filtered.append(t)
                    elif filter_value == "2022" and year == 2022:
                        filtered.append(t)
                    elif filter_value == "< 2022" and year < 2022:
                        filtered.append(t)
                except:
                    continue

        if filtered:
            filtered_buckets[limit_range] = filtered

    return render_template_string("FILTER UI WILL BE INSERTED HERE", data=filtered_buckets, filter_type=filter_type, filter_value=filter_value)
