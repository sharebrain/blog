from . import chartroom
#from ..ext import socketio
from flask_socketio import send, emit, join_room, leave_room, disconnect, SocketIO
from flask_login import current_user
import functools
from flask import Flask, redirect, session, json, flash, url_for, render_template
import datetime
import time

app = Flask('blog')
app.config['SECRET_KEY'] = '123456'
socketio = SocketIO(app)

def excape_text(txt):
    return txt.replace('<', '&lt;').replace('>', '&gt;')


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


@socketio.on('connect')
def join():
    join_room()


@socketio.on('disconnect')
def leave():
    leave_room()


@app.route("/confirm/<token>")
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for("index"))
    if current_user.confirm(token):
        flash("You have already confirmed your account. Thanks!")
    else:
        flash("The confirmation link is invalid or has expired.")
    return redirect(url_for("index"))


@socketio.on("join_user")
def on_new_user(data):
    if current_user.username == data["user_name"]:
        join_room(session["room"])
    emit("new_user", {"name": data["user_name"]}, room=session["room"])


@socketio.on("leave")
def on_leave_room(data):
    leave_room(session["room"])
    session["room"] = None
    redirect(url_for("index"))


@socketio.on("post_message")
def on_new_message(message):
    data = {"user": current_user.username,
            "content": excape_text(message["data"]),
            "created": datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
            "room_id": session["room"],
            "id": rc.incr(app.config["ROOM_CONTENT_INCR_KEY"])
    }
    emit("new_message", {
        "user": current_user.username,
        "time": datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
        "data": excape_text(message["data"])
    }, room=session["room"])


@app.route("/room/<int:room_id>", methods=["GET", "POST"])
def room(room_id):
    room_online_user_channel = app.config["ROOM_ONLINE_USER_CHANNEL"].format(room=room_id)
    room_content_channel = app.config["ROOM_CONTENT_CHANNEL"].format(room=room_id)
    room_info_key = app.config["ROOM_INFO_KEY"].format(room=room_id)

    if session["room"] is not None:
        session["room"] = None
    session["room"] = str(room_id)

    room_content_list = []

    return render_template("room.html",
                           room_id=room_id,
                           users=room_online_users,
                           user_name=current_user.username,
                           messages=room_content_list)


@app.route("/rm_room/<int:room_id>", methods=["GET", "POST"])
def rm_room(room_id):
    room_info_key = app.config["ROOM_INFO_KEY"].format(room=room_id)
    room_info = json.loads(rc.get(room_info_key))
    if room_info["creator"] != current_user.username:
        flash("You are not the creator of this room!")
        return redirect(url_for("index"))
    room_content = app.config["ROOM_CONTENT_CHANNEL"].format(room=room_id)
    room_online_user_channel = app.config["ROOM_ONLINE_USER_CHANNEL"].format(room=room_id)
    flash("The room "+str(room_id)+" has been deleted.")
    return redirect(url_for("index"))