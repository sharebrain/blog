from . import main
from ..models import Article, Category
from flask import render_template, g ,request, abort
from ..ext import db
from flask_paginate import Pagination


@main.route('/article/<int:post_id>', endpoint='article')
def article(post_id):
    article = Article.query.filter_by(id=post_id).first_or_404()
    article.hits = article.hits+1
    db.session.commit()
    return render_template('view2.html', article=article)


@main.route('/category/<string:longslug>', endpoint='category')
def category(longslug):
    search = False
    q = request.args.get('q')
    if q:
        search = True
    page = request.args.get('page', type=int, default=1)
    category = Category.query.filter_by(longslug=longslug).first_or_404()
    count = Article.query.filter_by(category_id=category.id).count()
    articles = Article.query.filter_by(category_id=category.id).offset(page*5-5).limit(5).all()
    pagination = Pagination(page=page, total=count, per_page=5, search=search, record_name='article')
    return render_template('article_list.html', articles=articles, category=category, pagination=pagination)

@main.route('/search',methods=['GET','POST'])
def search():
    if 's' not in request.args:
        abort(404)
    keyword = request.args['s']
    return 'unavaliable'