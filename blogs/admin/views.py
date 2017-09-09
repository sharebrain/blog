from ..ext import db, csrf, cache
from flask_admin import expose, AdminIndexView, Admin
from flask_admin.contrib.sqla import ModelView
from ..models import Article, User, Role, Category, FriendLink, Tag, admin_permission
from flask_admin.contrib.fileadmin import FileAdmin
from flask_login import login_required,current_user
from wtforms import TextAreaField
from flask_wtf import Form
from flask_admin.contrib.sqla.form import AdminModelConverter
import os
from sqlalchemy.orm.exc import NoResultFound
from wtforms import ValidationError
import datetime
import warnings
from wtforms import fields, validators
from sqlalchemy import Boolean, Column
from flask_admin import form
from flask_admin.model.form import FieldPlaceholder
from flask_admin.contrib.sqla.validators import Unique
from flask_admin.contrib.sqla.tools import (has_multiple_pks, filter_foreign_columns,)
from ..utils.widget import KindeditorField,CKeditorField


def cache_delete():
    cache.clear()


def format_datetime(self, request, obj, fieldname, *args, **kwargs):
    return getattr(obj, fieldname).strftime("%Y-%m-%d %H:%M")


class AdminForm(Form):

    def __init__(self, formdata=None, obj=None, prefix='', csrf_context=None,
                 secret_key=None, csrf_enabled=None, *args, **kwargs):
        self._obj = obj
        super(AdminForm, self).__init__(formdata=formdata, obj=obj, prefix=prefix, csrf_context=csrf_context,
                 secret_key=secret_key, csrf_enabled=csrf_enabled, *args, **kwargs)


class UserUnique(Unique):
    def __call__(self, form, field):
                # databases allow multiple NULL values for unique columns
        if field.data is None:
            return

        try:
            obj = (self.db_session.query(self.model)
                   .filter(self.column == field.data)
                   .one())
            if not hasattr(form, '_obj') or not form._obj == obj:
                if self.message is None:
                    self.message = field.gettext(u'Already exists.')
                raise ValidationError(self.message)
        except NoResultFound:
            pass


class UserModelConveter(AdminModelConverter):
    def convert(self, model, mapper, prop, field_args, hidden_pk):
                # Properly handle forced fields
        if isinstance(prop, FieldPlaceholder):
            return form.recreate_field(prop.field)

        kwargs = {
            'validators': [],
            'filters': []
        }

        if field_args:
            kwargs.update(field_args)

        if kwargs['validators']:
            # Create a copy of the list since we will be modifying it.
            kwargs['validators'] = list(kwargs['validators'])

        # Check if it is relation or property
        if hasattr(prop, 'direction'):
            return self._convert_relation(prop, kwargs)
        elif hasattr(prop, 'columns'):  # Ignore pk/fk
            # Check if more than one column mapped to the property
            if len(prop.columns) > 1:
                columns = filter_foreign_columns(model.__table__, prop.columns)

                if len(columns) > 1:
                    warnings.warn('Can not convert multiple-column properties (%s.%s)' % (model, prop.key))
                    return None

                column = columns[0]
            else:
                # Grab column
                column = prop.columns[0]

            form_columns = getattr(self.view, 'form_columns', None) or ()

            # Do not display foreign keys - use relations, except when explicitly instructed
            if column.foreign_keys and prop.key not in form_columns:
                return None

            # Only display "real" columns
            if not isinstance(column, Column):
                return None

            unique = False

            if column.primary_key:
                if hidden_pk:
                    # If requested to add hidden field, show it
                    return fields.HiddenField()
                else:
                    # By default, don't show primary keys either
                    # If PK is not explicitly allowed, ignore it
                    if prop.key not in form_columns:
                        return None

                    # Current Unique Validator does not work with multicolumns-pks
                    if not has_multiple_pks(model):
                        kwargs['validators'].append(UserUnique(self.session,
                                                           model,
                                                           column))
                        unique = True

            # If field is unique, validate it
            if column.unique and not unique:
                kwargs['validators'].append(UserUnique(self.session,
                                                   model,
                                                   column))

            optional_types = getattr(self.view, 'form_optional_types', (Boolean,))

            if (
                not column.nullable
                and not isinstance(column.type, optional_types)
                and not column.default
                and not column.server_default
            ):
                kwargs['validators'].append(validators.InputRequired())

            # Apply label and description if it isn't inline form field
            if self.view.model == mapper.class_:
                kwargs['label'] = self._get_label(prop.key, kwargs)
                kwargs['description'] = self._get_description(prop.key, kwargs)

            # Figure out default value
            default = getattr(column, 'default', None)
            value = None

            if default is not None:
                value = getattr(default, 'arg', None)

                if value is not None:
                    if getattr(default, 'is_callable', False):
                        value = lambda: default.arg(None)
                    else:
                        if not getattr(default, 'is_scalar', True):
                            value = None

            if value is not None:
                kwargs['default'] = value

            # Check nullable
            if column.nullable:
                kwargs['validators'].append(validators.Optional())

            # Override field type if necessary
            override = self._get_field_override(prop.key)
            if override:
                return override(**kwargs)

            # Check choices
            form_choices = getattr(self.view, 'form_choices', None)

            if mapper.class_ == self.view.model and form_choices:
                choices = form_choices.get(column.key)
                if choices:
                    return form.Select2Field(
                        choices=choices,
                        allow_blank=column.nullable,
                        **kwargs
                    )

            # Run converter
            converter = self.get_converter(column)

            if converter is None:
                return None

            return converter(model=model, mapper=mapper, prop=prop,
                             column=column, field_args=kwargs)

        return None


class BlogAdminIndexView(AdminIndexView):
    @expose('/')
    @login_required
    @admin_permission.require()
    def index(self):
        return super(BlogAdminIndexView, self).index()


class AdminFileAdmin(FileAdmin):
    form_base_class = AdminForm

    def is_accessible_path(self, path):
        return admin_permission.can()

    def is_accessible(self):
        return admin_permission.can()

    @expose('/delete/', methods=['POST', ])
    @csrf.exempt
    def delete(self):
        return super(AdminFileAdmin, self).delete()


class PostModelView(ModelView):
    create_template = 'admin/create.html'
    edit_template = 'admin/edit.html'
    form_base_class = AdminForm

    @expose('/')
    @login_required
    @admin_permission.require()
    def index(self):
        return super(PostModelView, self).index_view()
    column_list = ('title', 'category', 'tags', 'created', 'hits',)
    column_searchable_list = ('title',)
    form_overrides = dict(body=CKeditorField, summary=TextAreaField)
    form_excluded_columns = ('csrf_token',)
    form_create_rules = ('title', 'summary', 'tags', 'category', 'published', 'ontop', 'recommend', 'thumbnail', 'thumbnail_big', 'body', 'csrf_token')

    form_edit_rules = form_create_rules
    column_labels = {'body': 'Content'}

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.author_id = current_user.id
            model.created = datetime.datetime.now()
            model.last_modified = model.created
        else:
            model.last_modified = datetime.datetime.now()

    def after_model_change(self, form, model, is_created):
        cache_delete()


class UserModelView(ModelView):
    #model_form_converter = UserModelConveter
    form_base_class = AdminForm
    column_list = ('email', 'username', 'roles', 'confirmed')
    form_excluded_columns = ('password_hash', 'articles', 'member_since', 'last_seen')
    column_searchable_list = ('email', 'username', 'name')

    def is_accessible(self):
        return admin_permission.can()

    def get_edit_form(self):
        form = super(UserModelView, self).get_edit_form()
        #id = get_mdict_item_or_list(request.args, 'id')
        #form._obj = self.get_one(id)
        return form

    @expose('/')
    @login_required
    @admin_permission.require()
    def index(self):
        return super(UserModelView, self).index_view()


class RoleModelView(ModelView):
    form_base_class = AdminForm

    def is_accessible(self):
        return admin_permission.can()

    @expose('/')
    @login_required
    @admin_permission.require()
    def index(self):
        return super(RoleModelView, self).index_view()


class TagModelView(ModelView):
    form_base_class = AdminForm
    column_list = ('name',)
    column_searchable_list = ('name',)
    form_columns = ('name', 'thumbnail')

    def is_accessible(self):
        return admin_permission.can()


class CategoryModelView(ModelView):
    form_base_class = AdminForm
    column_list = ('name', 'longslug',)
    column_searchable_list = ('name', 'slug', 'longslug',)
    form_excluded_columns = ('articles', 'body_html', 'longslug', 'template', 'children', 'article_template', 'body',)

    def is_accessible(self):
        return admin_permission.can()


class FriendLinkModelView(ModelView):
    form_base_class = AdminForm
    form_excluded_columns = ('note',)
    column_searchable_list = ('title', 'url', 'anchor',)

    def is_accessible(self):
        return admin_permission.can()

admin = Admin(index_view=BlogAdminIndexView(), name='Admin')
admin.add_view(PostModelView(Article, db.session, name='articles'))
admin.add_view(UserModelView(User, db.session, name='users'))
admin.add_view(RoleModelView(Role, db.session, name='roles'))
admin.add_view(CategoryModelView(Category, db.session, name='categories'))
admin.add_view(TagModelView(Tag, db.session, name='tags'))
admin.add_view(FriendLinkModelView(FriendLink, db.session, name='friendlinks'))
admin.add_view(AdminFileAdmin(os.path.join(os.path.dirname(__file__)+'//..', 'static'), name='file'))