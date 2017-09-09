from wtforms.widgets import TextArea
from wtforms.fields import TextAreaField


class KindeditorWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' kindeditor'#class 之间用空格隔开
        else:
            kwargs.setdefault('class', 'kindeditor')
        return super(KindeditorWidget, self).__call__(field, **kwargs)


class KindeditorField(TextAreaField):
    widget = KindeditorWidget()


class CKeditorWidget(TextArea):

    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckditor'#class 之间用空格隔开
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKeditorWidget, self).__call__(field, **kwargs)


class CKeditorField(TextAreaField):
    widget = CKeditorWidget()
