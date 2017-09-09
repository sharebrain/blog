from flask import Flask
import platform
from blogs.models import User
from blogs import create_app
from flask import request, url_for, render_template, make_response
import time
import os
from werkzeug.utils import secure_filename
from flask_login import current_user
from blogs.ext import csrf
application = create_app()

@application.route('/index')
@application.route("/")
def index():
    return render_template('index2.html')


@application.route("/info")
def info():
    return platform.python_version()


@csrf.exempt
@application.route('/uploadImg', methods=['GET', 'POST', 'OPTIONS'])
def upload():
    error = ''
    url = ''
    callback = request.args.get("CKEditorFuncNum")

    if not isinstance(current_user._get_current_object(), User) or not current_user.can_upload():
        error = '对不起你没有权限，请联系管理员'
    elif request.method == 'POST' and 'upload' in request.files:
        f = request.files['upload']
        time_format = str(time.strftime("%Y-%m-%d-%H%M%S", time.localtime()))
        file_name = 'img'+time_format+'.jpg'
        file_name = secure_filename(file_name)
        f.save(os.path.join(application.static_folder+'/images', file_name))
    else:
        error = 'post error'
    if not error:
        url = url_for('static', filename='images/'+file_name)
    res = """

<script type="text/javascript">
  window.parent.CKEDITOR.tools.callFunction(%s, '%s', '%s');
</script>

""" % (callback, url, error)
    response = make_response(res)
    response.headers["Content-Type"] = "text/html"
    return response


if __name__ == '__main__':
    application.run(debug=False)
