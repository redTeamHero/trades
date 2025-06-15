
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
<html>
<head>
    <title>Available Tradelines</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #f7f7f7; }
        h2 { margin-top: 40px; }
        .card {
            background: white;
            padding: 15px;
            margin: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            width: 300px;
            display: inline-block;
            vertical-align: top;
        }
        .card a {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 12px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        form { margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>Available Tradelines</h1>
    <form method="get">
        <label>Limit Range:
            <select name="limit_range">
                <option value="">All</option>
                <option value="0-2500">0–2500</option>
                <option value="2501-5000">2501–5000</option>
                <option value="5001-10000">5001–10000</option>
                <option value="10001+">10001+</option>
            </select>
        </label>
        <label>Bank Name: <input type="text" name="bank" /></label>
        <button type="submit">Filter</button>
    </form>

    {% for limit_range, tradelines in data.items() %}
        <h2>Limit Range: {{ limit_range }}</h2>
        {% for item in tradelines %}
            <div class="card">
                <pre>{{ item['text'] }}</pre>
                <a href="/buy?bank={{ item['bank'] | urlencode }}&price={{ item['price'] }}">Buy Now</a>
            </div>
        {% endfor %}
    {% endfor %}
</body>
</html>
"""

@app.route('/')
def homepage():
    limit_filter = request.args.get("limit_range")
    bank_filter = request.args.get("bank")
    all_buckets = scrape_and_group_by_limit()
    filtered_buckets = {}

    for limit_range, tradelines in all_buckets.items():
        if limit_filter and limit_range != limit_filter:
            continue
        filtered = []
        for t in tradelines:
            if bank_filter and bank_filter.lower() not in t['bank'].lower():
                continue
            filtered.append(t)
        if filtered:
            filtered_buckets[limit_range] = filtered

    return render_template_string(HOMEPAGE_HTML, data=filtered_buckets)

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
