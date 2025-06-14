from flask import Flask, Response
from scrape import export_tradelines_to_html

app = Flask(__name__)

@app.route('/')
def index():
    html = export_tradelines_to_html(return_string=True)
    return Response(html, mimetype='text/html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
