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
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body class="bg-gray-100">
  <div class="max-w-7xl mx-auto px-4 py-6">
    <h1 class="text-4xl font-bold text-center mb-6">📊 Browse Tradelines</h1>

    <!-- Filters -->
    <div class="flex flex-wrap justify-between items-center mb-4 gap-4">
      <input type="text" id="search" placeholder="Search by bank..." class="flex-1 min-w-[200px] px-4 py-2 rounded border shadow-sm focus:ring-2 focus:ring-blue-500">
      <select id="sort" class="flex-1 min-w-[150px] px-4 py-2 rounded border shadow-sm focus:ring-2 focus:ring-blue-500">
        <option value="">Sort by</option>
        <option value="price-asc">Price ↑</option>
        <option value="price-desc">Price ↓</option>
        <option value="limit-asc">Limit ↑</option>
        <option value="limit-desc">Limit ↓</option>
        <option value="age-asc">Age ↑</option>
        <option value="age-desc">Age ↓</option>
      </select>
    </div>

    <!-- Bank List -->
    <div id="bank-list" class="mb-4 text-sm text-gray-600 italic"></div>

    <!-- Tradeline Grid -->
    <div id="tradeline-container" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3"></div>

    <!-- Pagination -->
    <div class="flex justify-center mt-6">
      <button id="prev" class="px-4 py-2 mx-1 bg-gray-300 hover:bg-gray-400 transition rounded">Prev</button>
      <button id="next" class="px-4 py-2 mx-1 bg-gray-300 hover:bg-gray-400 transition rounded">Next</button>
    </div>
  </div>

  <!-- Floating Buy Button on Mobile -->
  <a href="#" id="mobile-buy" class="fixed bottom-5 right-5 bg-blue-600 text-white text-sm px-4 py-2 rounded-full shadow-lg block md:hidden hidden z-50">Buy Now</a>

  <script>
    const tradelines = {{ tradelines|tojson }};
    const container = document.getElementById('tradeline-container');
    const searchInput = document.getElementById('search');
    const sortSelect = document.getElementById('sort');
    const mobileBuy = document.getElementById('mobile-buy');
    const bankList = document.getElementById('bank-list');

    let currentPage = 1;
    const perPage = 10;
    let filteredData = tradelines;

    function renderBankList(data) {
      const banks = [...new Set(data.map(t => t.bank))].sort();
      bankList.textContent = `Available Banks: ${banks.join(', ')}`;
    }

    function renderTradelines(data) {
      container.innerHTML = '';
      const paginated = data.slice((currentPage - 1) * perPage, currentPage * perPage);

      if (paginated.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center text-gray-500 text-lg py-10">🔍 No tradelines found. Try a different search or filter.</div>`;
        mobileBuy.classList.add('hidden');
        return;
      }

      paginated.forEach(t => {
        const el = document.createElement('div');
        el.className = "bg-white shadow-md rounded-xl p-4 hover:shadow-lg transition transform hover:scale-[1.01] duration-200";
        el.innerHTML = `
          <h2 class="text-xl font-semibold">${t.bank}</h2>
          <p class="text-sm text-gray-600 mb-2">${t.age} | $${t.limit} limit</p>
          <p class="text-lg font-bold text-green-600">$${t.price}</p>
          <p class="text-xs text-gray-400">Statement: ${t.statement_date}</p>
          <p class="text-xs text-gray-400">Reports to: ${t.reporting}</p>
          <a href="${t.buy_link}" class="inline-block mt-3 bg-blue-500 text-white text-sm px-4 py-2 rounded hover:bg-blue-600 transition">Buy Now</a>
        `;
        container.appendChild(el);
      });

      mobileBuy.href = paginated[0].buy_link || '#';
      mobileBuy.classList.remove('hidden');
    }

    function filterAndSort() {
      filteredData = tradelines.filter(t => t.bank.toLowerCase().includes(searchInput.value.toLowerCase()));
      const sortBy = sortSelect.value;

      if (sortBy === 'price-asc') filteredData.sort((a, b) => a.price - b.price);
      if (sortBy === 'price-desc') filteredData.sort((a, b) => b.price - a.price);
      if (sortBy === 'limit-asc') filteredData.sort((a, b) => a.limit - b.limit);
      if (sortBy === 'limit-desc') filteredData.sort((a, b) => b.limit - a.limit);
      if (sortBy === 'age-asc') filteredData.sort((a, b) => a.age.localeCompare(b.age));
      if (sortBy === 'age-desc') filteredData.sort((a, b) => b.age.localeCompare(a.age));

      renderBankList(filteredData);
      renderTradelines(filteredData);
    }

    document.getElementById('prev').addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        renderTradelines(filteredData);
      }
    });

    document.getElementById('next').addEventListener('click', () => {
      if ((currentPage * perPage) < filteredData.length) {
        currentPage++;
        renderTradelines(filteredData);
      }
    });

    searchInput.addEventListener('input', () => { currentPage = 1; filterAndSort(); });
    sortSelect.addEventListener('change', () => { currentPage = 1; filterAndSort(); });

    filterAndSort();
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
    all_tradelines = []

    for limit_range, tradelines in all_buckets.items():
        filtered = []
        for t in tradelines:
            val = filter_value

            if filter_type == "bank":
                if 'bank' not in t or t['bank'].lower() != val:
                    continue

            elif filter_type == "price":
                try:
                    if val.startswith('<') and not t['price'] < float(val[1:]): continue
                    elif val.startswith('>') and not t['price'] > float(val[1:]): continue
                    elif float(val) != t['price']: continue
                except: continue

            elif filter_type == "limit":
                try:
                    if val.startswith('<') and not t['limit'] < int(val[1:]): continue
                    elif val.startswith('>') and not t['limit'] > int(val[1:]): continue
                    elif int(val) != t['limit']: continue
                except: continue

            elif filter_type == "age":
                try:
                    opened_line = t['text'].split('\n')[2]
                    opened = opened_line.split(": ")[1]  # e.g. "2020 Jun"
                    year = int(opened.split()[0])
                    if val.startswith('<') and not year < int(val[1:]): continue
                    elif val.startswith('>') and not year > int(val[1:]): continue
                    elif int(val) != year: continue
                except: continue

            filtered.append(t)
        if filtered:
            filtered_buckets[limit_range] = filtered
            all_tradelines.extend(filtered)

    return render_template_string(
        HOMEPAGE_HTML,
        tradelines=all_tradelines,
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
