from django_filters import rest_framework as filters

from foodgram.recipe.models import Ingredient, Recipe, Tag
from foodgram.user.models import User


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
    )
    is_favorited = filters.BooleanFilter(method='get_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='get_shopping_cart')
    author = filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        field_name='author__id',
        to_field_name='id',
    )

    def get_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(
                favorite__user=user)
        return queryset

    def get_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(
                shoppinglist__user=user)
        return queryset

    class Meta:
        model = Recipe
        fields = ('tags',
                  'is_favorited',
                  'is_in_shopping_cart',
                  'author')


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ('name',)
