from blogs.models import Category



def get_category_ids(longslug=''):
    """"返回指定longslug开头的所有栏目的ID列表"""
    cates = Category.query.filter(Category.longslug.startswith(longslug))
    if cates:
        return [cate.id for cate in cates.all()]
    else:
        return []