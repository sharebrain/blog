from flask import Blueprint
account = Blueprint('account', __name__)
from .views import *