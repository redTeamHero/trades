
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
                    'description': f"This is an authorized user tradeline from {bank} with a limit of ${int(price):,}.",
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

@app.route('/buy/test')
def test_buy():
    bank = "TEST_BANK"
    price = 0.00

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"Test Tradeline - {bank}",
                    'description': "This is a test checkout for internal use.",
                },
                'unit_amount': 0,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://yourdomain.com/success',
        cancel_url='https://yourdomain.com/cancel',
        metadata={
            'bank': bank,
            'price': "0.00"
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

    body = f"""A new tradeline order has been placed.

Bank: {bank}
Price: ${price:.2f}

Please log in to Stripe to confirm the transaction and fulfill the order."""

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
