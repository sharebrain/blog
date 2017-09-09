import os
base_path ='//'.join( os.path.dirname(__file__).split('\\')[:-1])
print(base_path)
SECRET_KEY = '123456789'
CODEHILITE = True
BODY_FORMAT = 'html'
#配置 SqlAlchemy
#mysql+pymysql://username:password@server/db
#SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://adminTzcJzbW:ujhNWqBkhYuq@$OPENSHIFT_MYSQL_DB_HOST:$OPENSHIFT_MYSQL_DB_PORT/blog'
SQLALCHEMY_DATABASE_URI ='sqlite:///'+os.path.join(base_path, 'blog.db')
print(SQLALCHEMY_DATABASE_URI)
SQLALCHEMY_ECHO = False

#配置Email
MAIL_SERVER = 'mail.qq.com'
MAIL_USERNAME = '1261931128@qq.com'
MAIL_PASSWORD  = 'ligang19890308'

#配置cache
CACHE_TYPE = 'simple'
CACHE_KEY_PREFIX = 'blog'
CACHE_KEY = ''

#配置loginmanager
PER_PAGE = 5