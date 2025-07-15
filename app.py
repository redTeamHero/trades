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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tradeline Catalog</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">

    <div class="max-w-7xl mx-auto px-4 py-6">
        <h1 class="text-4xl font-bold text-center mb-6">📊 Browse Tradelines</h1>

        <!-- Filters -->
        <div class="flex flex-wrap justify-between items-center mb-4">
            <input type="text" id="search" placeholder="Search by bank..." class="w-full md:w-1/3 px-4 py-2 rounded border shadow-sm">
            <select id="sort" class="w-full md:w-1/4 px-4 py-2 rounded border shadow-sm mt-2 md:mt-0">
                <option value="">Sort by</option>
                <option value="price">Price</option>
                <option value="limit">Limit</option>
                <option value="age">Age</option>
            </select>
        </div>

        <!-- Tradeline Grid -->
        <div id="tradeline-container" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {% for t in tradelines %}
            <div class="bg-white shadow-md rounded-xl p-4 hover:shadow-lg transition">
                <h2 class="text-xl font-semibold">{{ t.bank }}</h2>
                <p class="text-sm text-gray-600 mb-2">{{ t.age }} old | ${{ t.limit }} limit</p>
                <p class="text-lg font-bold text-green-600">${{ t.price }}</p>
                <p class="text-xs text-gray-400">Statement: {{ t.statement_date }}</p>
                <p class="text-xs text-gray-400">Reports to: {{ t.reporting }}</p>
                <a href="{{ t.buy_link }}" class="inline-block mt-3 bg-blue-500 text-white text-sm px-4 py-2 rounded hover:bg-blue-600">Buy Now</a>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        const searchInput = document.getElementById('search');
        const sortSelect = document.getElementById('sort');
        const container = document.getElementById('tradeline-container');
        const cards = Array.from(container.children);

        searchInput.addEventListener('input', filter);
        sortSelect.addEventListener('change', filter);

        function filter() {
            const term = searchInput.value.toLowerCase();
            const sortBy = sortSelect.value;

            let filtered = cards.filter(card => {
                return card.querySelector('h2').innerText.toLowerCase().includes(term);
            });

            if (sortBy === 'price') {
                filtered.sort((a, b) => getPrice(a) - getPrice(b));
            } else if (sortBy === 'limit') {
                filtered.sort((a, b) => getLimit(a) - getLimit(b));
            }

            container.innerHTML = '';
            filtered.forEach(card => container.appendChild(card));
        }

        function getPrice(card) {
            return parseFloat(card.querySelector('.text-green-600').innerText.replace('$', '')) || 0;
        }

        function getLimit(card) {
            const text = card.querySelector('p').innerText;
            const match = text.match(/\$([0-9,]+)/);
            return match ? parseInt(match[1].replace(',', '')) : 0;
        }
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
                "unit_amount": 100,  # $1 in cents
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
    return "❌ Purchase canceled."

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
