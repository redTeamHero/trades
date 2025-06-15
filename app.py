
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
        body { font-family: 'Segoe UI', sans-serif; margin: 20px; background-color: #f2f4f8; }
        h1 { text-align: center; color: #2c3e50; }
        table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.05); }
        th, td { padding: 12px; text-align: center; border-bottom: 1px solid #eee; }
        th { background-color: #34495e; color: white; cursor: pointer; }
        tr:hover { background-color: #f9f9f9; }
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
</head>
<body>
    <h1>Available Tradelines</h1>
    <table>
        <thead>
            <tr>
                {% for col, label in headers.items() %}
                    <th onclick="window.location.href='/?sort={{ col }}&order={{ 'desc' if sort==col and order=='asc' else 'asc' }}'">
                        {{ label }} {% if sort == col %}{{ '▲' if order == 'asc' else '▼' }}{% endif %}
                    </th>
                {% endfor %}
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
        {% for item in all_items %}
            <tr>
                <td>{{ item['bank'] }}</td>
                <td>${{ "{:,}".format(item['limit']) }}</td>
                <td>{{ item['opened'] }}</td>
                <td>{{ item['deadline'] }}</td>
                <td>{{ item['reporting'] }}</td>
                <td>{{ item['availability'] }}</td>
                <td>${{ "%.2f"|format(item['price']) }}</td>
                <td><a href="/buy?bank={{ item['bank'] | urlencode }}&price={{ item['price'] }}" class="buy-btn">Buy Now</a></td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route('/')
def homepage():
    sort = request.args.get("sort", "price")
    order = request.args.get("order", "asc")
    buckets = scrape_and_group_by_limit()

    all_items = []
    for items in buckets.values():
        all_items.extend(items)

    if sort in {"bank", "price", "limit", "opened", "deadline", "reporting", "availability"}:
        reverse = order == "desc"
        try:
            if sort in {"price", "limit"}:
                all_items.sort(key=lambda x: float(x[sort]), reverse=reverse)
            else:
                all_items.sort(key=lambda x: str(x[sort]).lower(), reverse=reverse)
        except Exception as e:
            print("Sorting error:", e)

    headers = {
        "bank": "Bank Name",
        "limit": "Credit Limit",
        "opened": "Date Opened",
        "deadline": "Purchase Deadline",
        "reporting": "Reporting Period",
        "availability": "Availability",
        "price": "Price"
    }

    return render_template_string(HOMEPAGE_HTML, all_items=all_items, sort=sort, order=order, headers=headers)

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
