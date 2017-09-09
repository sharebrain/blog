from .ext import db, keywords_split
from werkzeug.utils import cached_property
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from flask_principal import RoleNeed, Identity, AnonymousIdentity,UserNeed, Permission
from collections import namedtuple
from functools import partial
from itsdangerous import URLSafeTimedSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import hashlib
from flask_sqlalchemy import BaseQuery
from functools import reduce
from .utils.filters import markdown_filter
from jinja2.filters import do_striptags, do_truncate
import re


BlogPostNeed = namedtuple('blog_post', ['method', 'value'])
EditBlogPostNeed = partial(BlogPostNeed, 'edit')
admin_permission = Permission(RoleNeed('admin'))
UploadNeed = RoleNeed('upload')
upload_permission = Permission(UploadNeed)


class EditBlogPostPermission(Permission):
    def __init__(self, post_id):
        need = EditBlogPostNeed(str(post_id))
        super(EditBlogPostNeed, self).__init__(need)

pattern_hasmore = re.compile(r'<!--more-->', re.I)
user_roles_table = db.Table(
    'user_roles',
    db.Model.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey("users.id", ondelete='CASCADE')),
    db.Column('role_id', db.Integer, db.ForeignKey("roles.id", ondelete='CASCADE')),
)


def markitup(text):
    """
    把Markdown转换为HTML

    默认不生成高亮代码。

    若需要生成高亮代码，需在Setting增加codehilite设置值，类型为int，
    值大于0. 另外需要安装Pygments。
    """
    try:
        _flag = current_app._get_current_object().config.get('CODEHILITE', False) and True
    except:
        _flag = False
    return markdown_filter(text, codehilite=_flag)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), unique=True)
    __mapper_args__ = {'order_by': [id.desc()]}

    def __str__(self):
        return self.name


class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64))
    roles = db.relationship(Role, secondary='user_roles')
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    member_since = db.Column(db.DateTime(), default=datetime.datetime.now())
    last_seen = db.Column(db.DateTime(), default=datetime.datetime.now())

    __mapper_args__ = {'order_by': [confirmed.desc(), id.desc()]}

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()

    @staticmethod
    def authenticate(username, password):
        """
        验证用户

        :param username: 用户名或者电子邮件地址
        :param password: 用户密码
        """
        user = User.query.filter(db.or_(User.username == username,
                                        User.email == username)).first()
        if isinstance(user, User):
            if user.verify_password(password):
                return None, user
            else:
                return 'Invalid Password', None
        return 'Invalid Username', None

    @staticmethod
    def make_unique_username(username):
        if User.query.filter_by(username=username).first() is None:
            return username
        version = 2
        while True:
            new_username = '%s%s' % (username, str(version))
            if User.query.filter_by(username=new_username).first() is None:
                break
            version += 1
        return new_username

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        #_hash = to_bytes(self.password_hash)
        _hash = self.password_hash
        return check_password_hash(_hash, password)

    def generate_confirmation_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'confirm': self.id})

    def confirm(self, token, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def generate_reset_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        db.session.commit()
        return True

    def generate_email_change_token(self, new_email):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        db.session.commit()
        return True

    def is_administrator(self):
        return self.email == '1261931128@qq.com'

    def can_upload(self):
        return True if 'upload' in [r.name for r in self.roles] else False

    def ping(self):
        self.last_seen = datetime.datetime.now()
        db.session.add(self)
        db.session.commit()

    def __str__(self):
        return '<User %r>' % (self.name or self.username)


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


article_tags_table = db.Table(
    'article_tags',
    db.Model.metadata,
    db.Column('article_id', db.Integer, db.ForeignKey("articles.id", ondelete='CASCADE')),
    db.Column('tag_id', db.Integer, db.ForeignKey("tags.id", ondelete='CASCADE')),
)


class TagQuery(BaseQuery):

    def search(self, keyword):
        keyword = u'%{0}%'.format(keyword.strip())
        return self.filter(Tag.name.ilike(keyword))


class Tag(db.Model):
    """标签"""

    __tablename__ = "tags"

    query_class = TagQuery

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)
    thumbnail = db.Column(db.String(255))
    template = db.Column(db.String(255))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)

    __mapper_args__ = {'order_by': [id.desc()]}

    def __repr__(self):
        return '<Tag %r>' % (self.name)

    def __unicode__(self):
        return self.name

    @cached_property
    def link(self):
        return url_for('main.tag', name=self.name.lower(), _external=True)

    @cached_property
    def shortlink(self):
        return url_for('main.tag', name=self.name.lower())

    @cached_property
    def count(self):
        return Article.query.public().filter(Article.tags.any(id=self.id)).count()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        if current_app._get_current_object().config.get('BODY_FORMAT', 'html') == 'html':
            target.body_html = value
        else:
            target.body_html = markitup(value)

db.event.listen(Tag.body, 'set', Tag.on_changed_body)


class Category(db.Model):
    """目录"""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.String(64), nullable=False)
    longslug = db.Column(db.String(255), unique=True, index=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    parent_id = db.Column(db.Integer(), db.ForeignKey('categories.id'))
    parent = db.relationship('Category',
                             primaryjoin=('Category.parent_id == Category.id'),
                             remote_side=id, backref=db.backref("children"))
    thumbnail = db.Column(db.String(255))
    template = db.Column(db.String(255))
    article_template = db.Column(db.String(255))

    body = db.Column(db.Text)
    body_html = db.Column(db.Text)

    __mapper_args__ = {'order_by': [longslug]}

    def __repr__(self):
        return '<Category %r>' % (self.name)

    @cached_property
    def link(self):
        return url_for('main.category', longslug=self.longslug, _external=True)

    @cached_property
    def shortlink(self):
        return url_for('main.category', longslug=self.longslug)

    @cached_property
    def count(self):
        cates = db.session.query(Category.id).filter(Category.longslug.startswith(self.longslug)).all()
        cate_ids = [cate.id for cate in cates]
        return Article.query.public().filter(Article.category_id.in_(cate_ids)).count()

    @cached_property
    def parents(self):
        lst = []
        lst.append(self)
        c = self.parent
        while c is not None:
            lst.append(c)
            c = c.parent
        lst.reverse()
        return lst

    @staticmethod
    def tree():
        """树形列表"""
        cates = Category.query.all()
        out = []
        for cate in cates:
            indent = len(cate.longslug.split('/')) - 1
            out.append((indent, cate))
        return out

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        if current_app._get_current_object().config.get('','html') == 'html':
            target.body_html = value
        else:
            target.body_html = markitup(value)

    def on_changed_longslug(target, value, oldvalue, initiator):
        '''如果栏目有子栏目，则不允许更改longslug，因为会造成longslug不一致'''
        if target.children and value != oldvalue:
            raise Exception('Category has children, longslug can not be change!')

    def gen_longslug(self):
        '''生成longslug'''
        if self.parent:
            _longslug = '/'.join([self.parent.longslug, self.slug]).lower()
        else:
            _longslug = self.slug.lower()
        self.longslug = _longslug

    @staticmethod
    def before_insert(mapper, connection, target):
        target.gen_longslug()

        _c = Category.query.filter_by(longslug=target.longslug).first()
        # 新增时判断longslug是否重复
        if _c:
            raise Exception('Category longslug "%s" already exist' % _c.longslug)

    @staticmethod
    def before_update(mapper, connection, target):
        target.gen_longslug()

        _c = Category.query.filter_by(longslug=target.longslug).first()
        # 更新时判断longslug是否重复
        if _c and _c.id != target.id:
            raise Exception('Category longslug "%s" already exist' % _c.longslug)

db.event.listen(Category.body, 'set', Category.on_changed_body)
db.event.listen(Category.longslug, 'set', Category.on_changed_longslug)
db.event.listen(Category, 'before_insert', Category.before_insert)
db.event.listen(Category, 'before_update', Category.before_update)


class ArticleQuery(BaseQuery):

    def public(self):
        return self.filter_by(published=True)

    def search(self, keyword):
        criteria = []

        for keyword in keywords_split(keyword):
            keyword = u'%{0}%'.format(keyword)
            criteria.append(db.or_(Article.title.ilike(keyword),))

        q = reduce(db.or_, criteria)
        return self.public().filter(q)

    def archives(self, year, month):
        if not year:
            return self

        criteria = []
        criteria.append(db.extract('year', Article.created) == year)
        if month:
            criteria.append(db.extract('month', Article.created) == month)

        q = reduce(db.and_, criteria)
        return self.public().filter(q)


class Article(db.Model):
    """贴文"""

    __tablename__ = "articles"

    query_class = ArticleQuery

    PER_PAGE = 10
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.String(200))
    title = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey(Category.id), nullable=False,)
    category = db.relationship(Category, backref=db.backref("articles"))
    tags = db.relationship(Tag, secondary=article_tags_table, backref=db.backref("articles"))
    thumbnail = db.Column(db.String(255))
    thumbnail_big = db.Column(db.String(255))
    summary = db.Column(db.String(500))
    body = db.Column(db.Text, nullable=False)
    body_html = db.Column(db.Text)
    published = db.Column(db.Boolean, default=True)
    ontop = db.Column(db.Boolean, default=False)
    recommend = db.Column(db.Boolean, default=False)
    hits = db.Column(db.Integer, default=0)
    author_id = db.Column(db.Integer, db.ForeignKey(User.id))
    author = db.relationship(User, backref=db.backref("articles"))
    created = db.Column(db.DateTime(), default=datetime.datetime.now())
    last_modified = db.Column(db.DateTime(), default=datetime.datetime.now())

    __mapper_args__ = {'order_by': [ontop.desc(), id.desc()]}

    def __repr__(self):
        return '<Post %r>' % (self.title)

    def __str__(self):
        return self.title

    @cached_property
    def has_more(self):
        return pattern_hasmore.search(self.body) is not None or \
            self.summary.find('...') >= 0

    @cached_property
    def link(self):
        return url_for('main.article', article_id=self.id, _external=True)

    @cached_property
    def shortlink(self):
        return url_for('main.article', article_id=self.id)

    @cached_property
    def get_next(self):
        _query = db.and_(Article.category_id.in_([self.category.id]),
                         Article.id > self.id)
        return self.query.public().filter(_query) \
                         .order_by(Article.id.asc()) \
                         .first()

    @cached_property
    def get_prev(self):
        _query = db.and_(Article.category_id.in_([self.category.id]),
                         Article.id < self.id)
        return self.query.public().filter(_query) \
                         .order_by(Article.id.desc()) \
                         .first()

    @staticmethod
    def before_insert(mapper, connection, target):
        def _format(_html):
            return do_truncate(do_striptags(_html), length=500)

        value = target.body
        if target.summary is None or target.summary.strip() == '':
            # 新增文章时，如果 summary 为空，则自动生成
            if current_app._get_current_object().config.get('BODY_FORMAT', 'html') == 'html':
                target.summary = _format(value)
            else:
                _match = pattern_hasmore.search(value)
                if _match is not None:
                    more_start = _match.start()
                    target.summary = _format(markitup(value[:more_start]))
                else:
                    target.summary = _format(target.body_html)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        if current_app._get_current_object().config.get('BODY_FORMAT', 'html') == 'html':
            target.body_html = value
        else:
            target.body_html = markitup(value)

db.event.listen(Article.body, 'set', Article.on_changed_body)
db.event.listen(Article, 'before_insert', Article.before_insert)


class FriendLink(db.Model):
    """友情链接"""

    __tablename__ = 'friendlinks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    anchor = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(128))
    url = db.Column(db.String(255), nullable=False)
    actived = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=1)
    note = db.Column(db.String(400))

    __mapper_args__ = {'order_by': [actived.desc(), order.asc()]}

    def __repr__(self):
        return '<FriendLink %r>' % (self.anchor)



