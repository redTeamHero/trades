import os
from flask import Flask, request, redirect
from scrape import scrape_and_group_by_limit
import stripe
import math

app = Flask(__name__)
stripe.api_key = "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"

limit_buckets = {
    '0-2500': (0, 2500),
    '2501-5000': (2501, 5000),
    '5001-10000': (5001, 10000),
    '10001+': (10001, float('inf'))
}

@app.route('/')
def index():
    html = """
    <html>
    <head>
        <meta charset='UTF-8'>
        <title>Select a Credit Limit Range</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background-color: #f4f6f8; padding: 60px 20px; text-align: center; }
            h1 { font-size: 32px; margin-bottom: 40px; }
            .range-options { display: flex; justify-content: center; flex-wrap: wrap; gap: 20px; }
            .range-box { background: white; border: 2px solid #4a90e2; border-radius: 10px; padding: 25px 40px; font-size: 18px; color: #4a90e2; text-decoration: none; transition: 0.2s; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
            .range-box:hover { background-color: #4a90e2; color: white; transform: translateY(-4px); }
        </style>
    </head>
    <body>
        <h1>Select a Credit Limit Range</h1>
        <div class='range-options'>
            <a href='/banks?range=0-2500' class='range-box'>$0 – $2,500</a>
            <a href='/banks?range=2501-5000' class='range-box'>$2,501 – $5,000</a>
            <a href='/banks?range=5001-10000' class='range-box'>$5,001 – $10,000</a>
            <a href='/banks?range=10001+' class='range-box'>$10,001+</a>
        </div>
    </body></html>
    """
    return html

@app.route('/banks')
def select_bank():
    selected_range = request.args.get('range')
    buckets = scrape_and_group_by_limit()
    items = buckets.get(selected_range, [])
    banks = sorted(set(item['bank'] for item in items))
    html = f"<html><body><h1>Choose a Bank in Credit Limit Range: {selected_range}</h1><ul>"
    for bank in banks:
        html += f"<li><a href='/tradelines?range={selected_range}&bank={bank}'>{bank}</a></li>"
    html += "</ul><a href='/'>⬅ Back</a></body></html>"
    return html

@app.route('/tradelines')
def show_tradelines():
    selected_range = request.args.get('range')
    bank = request.args.get('bank')
    page = int(request.args.get('page', 1))

    buckets = scrape_and_group_by_limit()
    all_items = [item for item in buckets.get(selected_range, []) if item['bank'] == bank]
    start = (page - 1) * 20
    end = start + 20
    items = all_items[start:end]

    html = f"""
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f5f8fa; padding: 30px; }}
        h1 {{ color: #333; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }}
        .card {{ background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.07); transition: 0.3s; }}
        .card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }}
        .card h3 {{ margin-top: 0; font-size: 20px; color: #0070f3; }}
        .card p {{ margin: 5px 0; color: #444; font-size: 15px; }}
        .card a {{ display: inline-block; margin-top: 10px; padding: 10px 16px; background: #0070f3; color: #fff; border-radius: 6px; text-decoration: none; font-weight: bold; }}
        .card a:hover {{ background: #005dc1; }}
    </style>
</head>
<body>
    <h1>{bank} Tradelines in {selected_range}</h1>
    <div class='grid'>
"""
<head>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f5f8fa; padding: 30px; }
        h1 { color: #333; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }
        .card { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.07); transition: 0.3s; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; font-size: 20px; color: #0070f3; }
        .card p { margin: 5px 0; color: #444; font-size: 15px; }
        .card a { display: inline-block; margin-top: 10px; padding: 10px 16px; background: #0070f3; color: #fff; border-radius: 6px; text-decoration: none; font-weight: bold; }
        .card a:hover { background: #005dc1; }
    </style>
</head>
<body>
    <h1>{bank} Tradelines in {selected_range}</h1>
    <div class='grid'>
"""
<head>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background-color: #f5f8fa; padding: 30px; }}
        h1 {{ color: #333; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }}
        .card {{ background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.07); transition: 0.3s; }}
        .card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }}
        .card h3 {{ margin-top: 0; font-size: 20px; color: #0070f3; }}
        .card p {{ margin: 5px 0; color: #444; font-size: 15px; }}
        .card a {{ display: inline-block; margin-top: 10px; padding: 10px 16px; background: #0070f3; color: #fff; border-radius: 6px; text-decoration: none; font-weight: bold; }}
        .card a:hover {{ background: #005dc1; }}
    </style>
</head>
<body>
    <h1>{{bank}} Tradelines in {{selected_range}}</h1>
    <div class='grid'>
"""
<head>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f5f8fa; padding: 30px; }
        h1 { color: #333; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; }
        .card { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.07); transition: 0.3s; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; font-size: 20px; color: #0070f3; }
        .card p { margin: 5px 0; color: #444; font-size: 15px; }
        .card a { display: inline-block; margin-top: 10px; padding: 10px 16px; background: #0070f3; color: #fff; border-radius: 6px; text-decoration: none; font-weight: bold; }
        .card a:hover { background: #005dc1; }
    </style>
</head>
<body>
    <h1>{bank} Tradelines in {selected_range}</h1>
    <div class='grid'>
"
    for item in items:
        html += "<div style='border:1px solid #ccc;padding:15px;border-radius:10px;background:#fff;'>"
        html += f"<h3>{item['bank']}</h3>"
        for line in item['text'].split('\n'):
            html += f"<p>{line}</p>"
        html += f"<a href='/buy?bank={item['bank']}&price={item['price']:.2f}' target='_blank'>Buy Now</a>"
        html += "</div>"
    html += "</div></body></html>"
    return html

@app.route('/buy')
def buy():
    bank = request.args.get("bank")
    price = float(request.args.get("price", 0))
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': { 'name': f"Tradeline - {bank}" },
                'unit_amount': int(price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://example.com/success',
        cancel_url='https://example.com/cancel',
    )
    return redirect(session.url, code=303)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
