from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_admin import Admin
from flask_cache import Cache
from flask_principal import Principal
from flask_login import LoginManager
from flask_wtf import CsrfProtect
from flask_socketio import SocketIO
db = SQLAlchemy()
email = Mail()
cache = Cache()
principal = Principal()
login_manager = LoginManager()
csrf = CsrfProtect()
socketio = SocketIO()


def keywords_split(keywords):
    return keywords.replace(u',', ' ') \
                   .replace(u';', ' ') \
                   .replace(u'+', ' ') \
                   .replace(u'；', ' ') \
                   .replace(u'，', ' ') \
                   .replace(u'　', ' ') \
                   .split(' ')
