from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(method='filter_name')

    class Meta:
        model = Ingredient
        fields = ('name',)

    def filter_name(self, queryset, name, value):
        # названия хранятся в нижнем регистре; lower() нужен для SQLite,
        # у которой istartswith не учитывает регистр кириллицы
        return queryset.filter(name__istartswith=value.lower())


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.NumberFilter(method='filter_favorited')
    is_in_shopping_cart = filters.NumberFilter(method='filter_cart')
    author = filters.NumberFilter(field_name='author_id')

    class Meta:
        model = Recipe
        fields = ('author',)

    def _filter_by_relation(self, queryset, value, relation):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none() if value else queryset
        lookup = {f'{relation}__user': user}
        return queryset.filter(**lookup) if value else queryset.exclude(
            **lookup)

    def filter_favorited(self, queryset, name, value):
        return self._filter_by_relation(queryset, value, 'favorite_set')

    def filter_cart(self, queryset, name, value):
        return self._filter_by_relation(queryset, value, 'shoppingcart_set')
