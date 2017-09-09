from flask import Markup
from ..ext import keywords_split
import re
import datetime
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html
__all__ = ['register_filters', 'markdown_filter']


_pre_re = re.compile(r'<pre (?=l=[\'"]?\w+[\'"]?).*?>(?P<code>[\w\W]+?)</pre>')
_lang_re = re.compile(r'l=[\'"]?(?P<lang>\w+)[\'"]?')


def markdown_filter(text, codehilite=True):
    """
    代码高亮可选，有的场合不需要高亮，高亮会生成很多代码
    但是fenced_code生成的代码是<pre><code>~~~</code></code>包围的
    """
    exts = [
        'abbr', 'attr_list', 'def_list', 'sane_lists', 'fenced_code',
        'tables', 'toc', 'wikilinks',
    ]

    if codehilite:
        exts.append('codehilite(guess_lang=True,linenums=True)')

    return Markup(markdown.markdown(
        text,
        extensions=exts,
        safe_mode=False,
    ))


def code_highlight(value):
    f_list = _pre_re.findall(value)

    if f_list:
        s_list = _pre_re.split(value)

        for code_block in _pre_re.finditer(value):

            lang = _lang_re.search(code_block.group()).group('lang')
            code = code_block.group('code')

            index = s_list.index(code)
            s_list[index] = code2html(code, lang)

        return u''.join(s_list)

    return value


def code2html(code, lang):
    lexer = get_lexer_by_name(lang, stripall=True)
    formatter = html.HtmlFormatter()
    return highlight(code, lexer, formatter)


def date_filter(dt, fmt='%Y-%m-%d'):
    return dt.strftime(fmt)


def timestamp_filter(stamp, fmt='%Y-%m-%d %H:%M'):
    return datetime.datetime.fromtimestamp(int(stamp)).strftime(fmt)


def emphasis(text, keyword=None):
    if keyword is not None:
        for _keyword in keywords_split(keyword):
            _pattern = re.compile(r'(%s)' % _keyword, flags=re.I)
            text = _pattern.sub(r'<em>\1</em>', text)
    return text


def author_name(name):
    if not name:
        return '佚名'
    else:
        return name


def register_filters(app):
    app.jinja_env.filters['markdown'] = markdown_filter
    app.jinja_env.filters['date'] = date_filter
    app.jinja_env.filters['timestamp'] = timestamp_filter
    app.jinja_env.filters['emphasis'] = emphasis
    app.jinja_env.filters['author'] = author_name
    app.jinja_env.filters['code'] = code_highlight
