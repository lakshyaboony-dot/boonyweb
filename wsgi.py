# wsgi.py
from app import app   # agar aapka Flask file ka naam app.py hai aur usme app = Flask(__name__) hai

application = app    # waitress/gunicorn 'application' ko dhundte hain
