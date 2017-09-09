from threading import Thread
from flask import current_app,render_template
from flask_mail import Message
from ..ext import email


def send_async_email(app, msg):
    with app.app_comtex():
        email.send(msg)

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(subject, sender=app.config['APP_MAILE_SENDER'], recipients=[to])
    msg.body = render_template('%s.txt' % template, **kwargs)
    msg.html = render_template('%s.html' % template, **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
