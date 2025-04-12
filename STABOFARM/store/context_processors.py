from .models import Category, Shop


def men_link(request):
    links = Category.objects.all()
    return dict(links=links)


def get_shop(request):
    try:
        shop = Shop.objects.filter(user=request.user)
        return dict(shop=shop)
    except:
        return None