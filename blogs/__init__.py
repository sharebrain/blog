from .ext import db, csrf, cache, principal, login_manager, socketio
from . import config
from flask import Flask, send_from_directory
from flask_principal import PermissionDenied
from .main import main
from flask_principal import Identity,identity_changed,identity_loaded, RoleNeed, UserNeed
from flask_login import current_user
from .models import User, admin_permission, EditBlogPostNeed
from flask import current_app

@login_manager.user_loader
def user_loader(user_id):
    return User.query.filter_by(id=int(user_id)).first()


def create_app():
    app = Flask(__name__)
    # 只接受此app发送的信号
    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        identity.user = current_user
        if hasattr(current_user, 'id'):
            if current_user.email == '1261931128@qq.com':
                identity.provides.add(RoleNeed('admin'))
            identity.provides.add(UserNeed(current_user.id))
        if hasattr(current_user, 'roles'):
            for role in current_user.roles:
                identity.provides.add(RoleNeed(role.name))
        if hasattr(current_user, 'articles'):
            for post in current_user.articles:
                identity.provides.add(EditBlogPostNeed(post.id))

    app.config.from_object(config)
    db.init_app(app)
    db.app = app
    socketio.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    principal.init_app(app)
    login_manager.init_app(app)
    from .admin.views import admin
    admin.init_app(app)
    from .utils.filters import register_filters
    register_filters(app)
    from .utils.processors import utility_processor
    app.context_processor(utility_processor)
    from .account import account
    app.register_blueprint(account)
    from .api import api
    app.register_blueprint(api)
    from .chatroom import chartroom
    app.register_blueprint(chartroom)
    from .comment import comment
    app.register_blueprint(comment)
    from .main import main
    app.register_blueprint(main)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico',
                                   mimetype='images/vnd.microsoft.icon')

    @app.route('/robots.txt')
    def robotstxt():
        return send_from_directory(app.static_folder, 'robots.txt')

    @app.errorhandler(PermissionDenied)
    def permission_denied(error):
        return 'sorry  permission denied '
    db.create_all()
    return app


