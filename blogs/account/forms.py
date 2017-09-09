from flask_wtf import Form
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email
from flask_admin.contrib.sqla.validators import Unique


class UserForm(Form):
    username = StringField('帐号：', validators=[DataRequired(message='用户名不能为空')])
    password = PasswordField('密码：', validators=[DataRequired(message='密码不能为空')])
    passwd2 = PasswordField('重复密码：', validators=[DataRequired('不能为空')])
    email = StringField('邮箱：', validators=[Email('邮箱格式不对')])


class LoginForm(Form):
    username = StringField('帐号：', validators=[DataRequired(message='用户名不能为空')])
    password = PasswordField('密码：', validators=[DataRequired(message='密码不能为空')])
    passwd2 = PasswordField('重复密码：')
    email = StringField('邮箱：')
