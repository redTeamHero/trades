import os
from flask import Flask, request, redirect, render_template_string
from scrape import scrape_and_group_by_limit
import stripe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "youremail@example.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "yourusername")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "yourpassword")

# In-memory tracking list (use DB in production)
orders = []

HOMEPAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Tradeline Marketplace</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            margin: 20px;
            background-color: #f2f4f8;
        }
        h1 {
            text-align: center;
            color: #2c3e50;
        }
        .filter-box {
            background: #ffffff;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            margin-bottom: 25px;
            text-align: center;
        }
        .filter-box select, .filter-box input {
            padding: 8px;
            margin: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
        }
        th, td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }
        th {
            background-color: #34495e;
            color: white;
        }
        tr:hover {
            background-color: #f9f9f9;
        }
        .buy-btn {
            background-color: #27ae60;
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
        }
    </style>
    <script>
        function updateFilterField() {
            const filterType = document.getElementById('filter_type').value;
            const placeholderMap = {
                'bank': 'e.g., Chase',
                'price': 'e.g., < 500',
                'limit': 'e.g., > 5000',
                'age': 'e.g., 2020 or < 2019'
            };
            document.getElementById('filter_value').placeholder = placeholderMap[filterType] || '';
        }
    </script>
</head>
<body>
    <h1>Available Tradelines</h1>

    <div class="filter-box">
        <form method="get">
            <label>Filter By:
                <select name="filter_type" id="filter_type" onchange="updateValueDropdown()">
                    <option value="">-- Select --</option>
                    <option value="bank" {% if filter_type == 'bank' %}selected{% endif %}>Bank Name</option>
                    <option value="price" {% if filter_type == 'price' %}selected{% endif %}>Price</option>
                    <option value="limit" {% if filter_type == 'limit' %}selected{% endif %}>Credit Limit</option>
                    <option value="age" {% if filter_type == 'age' %}selected{% endif %}>Age</option>
                </select>
            </label>
    
            <label>
                <select name="filter_value" id="filter_value">
                    <!-- Options loaded dynamically by JS -->
                </select>
            </label>
    
            <button type="submit">Apply Filter</button>
            <a href="/" style="margin-left: 10px;">Reset</a>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>Bank Name</th>
                <th>Credit Limit</th>
                <th>Date Opened</th>
                <th>Purchase Deadline</th>
                <th>Reporting Period</th>
                <th>Availability</th>
                <th>Price</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
        {% for limit_range, tradelines in data.items() %}
            {% for item in tradelines %}
                <tr>
                    <td>{{ item['bank'] }}</td>
                    <td>${{ "{:,}".format(item['limit']) }}</td>
                    <td>{{ item['text'].split('\\n')[2].split(': ')[1] }}</td>
                    <td>{{ item['text'].split('\\n')[3].split(': ')[1] }}</td>
                    <td>{{ item['text'].split('\\n')[4].split(': ')[1] }}</td>
                    <td>{{ item['text'].split('\\n')[5].split(': ')[1] }}</td>
                    <td>${{ "%.2f"|format(item['price']) }}</td>
                    <td><a href="/buy?bank={{ item['bank'] | urlencode }}&price={{ item['price'] }}" class="buy-btn">Buy Now</a></td>
                </tr>
            {% endfor %}
        {% endfor %}
        </tbody>
    </table>
    <script>
    const bankOptions = {{ bank_options|tojson }};
    const yearOptions = {{ year_options|tojson }};

    const optionsMap = {
        'bank': bankOptions,
        'price': ['< 500', '500 - 1000', '> 1000'],
        'limit': ['< 2500', '2501 - 5000', '5001 - 10000', '> 10000'],
        'age': yearOptions.map(y => y.toString()).concat('< 2022')
    };

    function updateValueDropdown() {
        const typeSelect = document.getElementById('filter_type');
        const valueSelect = document.getElementById('filter_value');
        const selectedType = typeSelect.value;

        valueSelect.innerHTML = '';

        if (optionsMap[selectedType]) {
            optionsMap[selectedType].forEach(val => {
                const opt = document.createElement('option');
                opt.value = val.toLowerCase();
                opt.textContent = val;
                valueSelect.appendChild(opt);
            });
        }
    }

    document.addEventListener('DOMContentLoaded', updateValueDropdown);
</script>


</body>
</html>
"""

@app.route('/')
def homepage():
    filter_type = request.args.get("filter_type", "")
    filter_value = request.args.get("filter_value", "").strip().lower()

    all_buckets, bank_options, year_options = scrape_and_group_by_limit()

    filtered_buckets = {}

    for limit_range, tradelines in all_buckets.items():
        filtered = []
        for t in tradelines:
            val = filter_value

            if filter_type == "bank":
                if 'bank' not in t or t['bank'].lower() != val:
                    continue

            elif filter_type == "price":
                try:
                    if val.startswith('<'):
                        if not t['price'] < float(val[1:]): continue
                    elif val.startswith('>'):
                        if not t['price'] > float(val[1:]): continue
                    elif not float(val) == t['price']:
                        continue
                except: continue
            elif filter_type == "limit":
                try:
                    if val.startswith('<'):
                        if not t['limit'] < int(val[1:]): continue
                    elif val.startswith('>'):
                        if not t['limit'] > int(val[1:]): continue
                    elif not int(val) == t['limit']:
                        continue
                except: continue
            elif filter_type == "age":
                try:
                    opened_line = t['text'].split('\n')[2]
                    opened = opened_line.split(": ")[1]  # e.g. "2020 Jun"
                    year = int(opened.split()[0])
                    if val.startswith('<'):
                        if not year < int(val[1:]): continue
                    elif val.startswith('>'):
                        if not year > int(val[1:]): continue
                    elif not int(val) == year:
                        continue
                except: continue
            filtered.append(t)
        if filtered:
            filtered_buckets[limit_range] = filtered
            
    return render_template_string(HOMEPAGE_HTML, data=filtered_buckets,
        filter_type=filter_type,
        filter_value=filter_value,
        bank_options=bank_options,
        year_options=year_options
    )


@app.route('/buy')
def buy():
    bank = request.args.get("bank")
    price_str = request.args.get("price")
    if not bank or not price_str:
        return "Missing bank or price", 400
    try:
        price = float(price_str)
    except ValueError:
        return "Invalid price format", 400

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"Tradeline - {bank}",
                    'description': f"Authorized user tradeline from {bank} with a limit of ${int(price):,}.",
                    'images': ['https://yourdomain.com/logo.png']
                },
                'unit_amount': int(price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://yourdomain.com/success',
        cancel_url='https://yourdomain.com/cancel',
        metadata={
            'bank': bank,
            'price': f"{price:.2f}"
        }
    )

    orders.append({"bank": bank, "price": price})
    send_email_notification(bank, price)
    return redirect(session.url, code=303)

@app.route('/dashboard')
def dashboard():
    html = """<html><head><title>Order Dashboard</title></head><body>
    <h1>Tradeline Orders</h1>
    <table border='1' cellpadding='8' cellspacing='0'>
        <tr><th>Bank</th><th>Price</th></tr>
        {% for order in orders %}
            <tr><td>{{ order['bank'] }}</td><td>${{ '%.2f'|format(order['price']) }}</td></tr>
        {% endfor %}
    </table>
    </body></html>"""
    return render_template_string(html, orders=orders)

def send_email_notification(bank, price):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = OWNER_EMAIL
    msg['Subject'] = f"New Tradeline Order - {bank}"
    body = f"""A new tradeline order has been placed.\n\nBank: {bank}\nPrice: ${price:.2f}\n\nPlease log in to Stripe to confirm the transaction and fulfill the order."""
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, OWNER_EMAIL, msg.as_string())
    except Exception as e:
        print("Failed to send order email:", e)

    @app.route("/buy/test")
def test_checkout():
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": 1,  # $1 in cents
                "product_data": {
                    "name": "Test Tradeline - $1",
                },
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=url_for('success', _external=True),
        cancel_url=url_for('cancel', _external=True),
    )
    return redirect(checkout_session.url, code=303)

@app.route("/success")
def success():
    return "✅ Test purchase successful."

@app.route("/cancel")
def cancel():
    return "❌ Purchase canceled.

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
