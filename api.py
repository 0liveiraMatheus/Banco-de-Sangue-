from flask import Flask
from routes.doadores import doadores_bp
from routes.bolsas import bolsas_bp
from flask_cors import CORS

app = Flask(__name__)
CORS = CORS(app)

app.json.sort_keys = False

app.register_blueprint(doadores_bp)
app.register_blueprint(bolsas_bp)

app.run(debug = True)