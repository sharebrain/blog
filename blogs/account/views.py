from flask import request,current_app, render_template, url_for,abort, flash,get_flashed_messages, session, redirect
from ..ext import login_manager, principal,db
from flask_login import login_required, current_user,login_user,logout_user,login_fresh
from flask_principal import Identity, identity_changed, identity_loaded,AnonymousIdentity
from ..models import AnonymousUser, User, EditBlogPostNeed,UploadNeed, RoleNeed,UserNeed
from . import account
from .forms import UserForm, LoginForm
import datetime
login_manager.anonymous_user = AnonymousUser
login_manager.login_view = 'account.login'


@account.route('/logout', endpoint='logout')
@login_required
def logout():
    logout_user()
    for key in ('indentity_name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())
    next_url = request.args.get('next', '/')
    return redirect(next_url)


@account.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            message, user = User.authenticate(form.username.data, form.password.data)
            if user:
                login_user(user, True)
                user.last_seen = datetime.datetime.now()
                db.session.commit()
                next_url = request.args.get('next') or '/'
                identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
                return redirect(next_url)
            else:
                flash('用户名或密码错误')
    return render_template('login2.html', form=form)


@account.route('/regist', methods=['GET', 'POST'], endpoint='regist')
def regist():
    form = UserForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(name=form.username.data).first()
            if user:
                flash('用户名已经存在')
                return render_template('login2.html', form=form)
            user = User()
            form.populate_obj(user)
            db.session.add(user)
            db.session.commit()
            return redirect('/')
    return render_template('login2.html', form=form)

