from flask import Blueprint
chartroom =Blueprint('chartroom', __name__)
from .views import *
