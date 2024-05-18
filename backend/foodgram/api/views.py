from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
# from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsOwnerOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          ShoppingCartRecipeSerializer,
                          SubscribeUserSerializer,
                          SubscriptionCreateSerializer, TagSerializer,
                          UserChangePasswordSerializer, UserCreateSerializer)
from foodgram.recipe.models import (Favorite, Ingredient, IngredientAmount,
                                    Recipe, ShoppingList, Tag)
from foodgram.user.models import Subscription, User


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny, ]
    pagination_class = LimitOffsetPagination
    # serializer_class = SubscribeUserSerializer

    # def get_serializer_class(self):
    #     if self.action in ('subscribe', 'subscriptions'):
    #         return UserCreateSerializer

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return SubscribeUserSerializer
        return UserCreateSerializer

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Текущий пользователь"""
        serializer = SubscribeUserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'],
            permission_classes=(IsAuthenticated,))
    def set_password(self, request):
        serializer = UserChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user.check_password(
                serializer.validated_data['current_password']):
            request.user.set_password(
                serializer.validated_data['new_password'])
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """Подписки пользователя"""
        subscriptions = Subscription.objects.filter(user=request.user)
        page_qs = self.paginate_queryset(subscriptions)
        serializer = SubscriptionCreateSerializer(page_qs, many=True,
                                                  context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, **kwargs):
        """Подписаться/отписаться"""
        author = get_object_or_404(User, id=kwargs['pk'])
        if request.method == 'POST':
            serializer = SubscriptionCreateSerializer(
                data=request.data, context={'request': request,
                                            'author': author.id})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        try:
            subscription = Subscription.objects.get(user=request.user,
                                                    author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Subscription.DoesNotExist:
            msg = {'detail': 'Подписка не существует'}
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsOwnerOrReadOnly, ]
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, ]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_queryset(self):
        recipes = Recipe.objects.select_related('author').prefetch_related(
            'tags', 'ingredients')
        return recipes

    def create(self, request):
        serializer = RecipeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def check_recipe_owner(self, recipe):
        user = self.request.user
        if user != recipe.author:
            raise PermissionDenied('Нельзя изменить чужой рецепт')

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_recipe_owner(instance)
        serializer = RecipeWriteSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        instance = self.get_object()
        self.check_recipe_owner(instance)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, **kwargs):
        user = self.request.user
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        if request.method == 'POST':
            favorite, created = Favorite.objects.get_or_create(
                user=user, recipe=recipe)
            if not created:
                msg = {
                    'detail': 'Рецепт уже есть в избранном'
                }
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
            serializer = FavoriteSerializer(recipe,
                                            context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        favorite = Favorite.objects.get(user=user, recipe=recipe)
        if not favorite:
            msg = {
                'detail': 'Нет в избранном'
            }
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, **kwargs):
        user = self.request.user
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        if request.method == 'POST':
            shopping_cart_recipe, created = ShoppingList.objects.get_or_create(
                user=user, recipe=recipe)
            if not created:
                msg = {
                    'detail': 'Рецепт уже есть в корзине'
                }
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
            serializer = ShoppingCartRecipeSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            shopping_list = ShoppingList.objects.get(
                user=user, recipe=recipe)
            shopping_list.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        msg = {
            'detail': 'Неверный запрос'
        }
        return Response(msg, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        shopping_cart = ShoppingList.objects.filter(user=self.request.user)
        recipes = [item.recipe.id for item in shopping_cart]
        ingredients_amount = IngredientAmount.objects.filter(
            recipe__in=recipes).values('ingredient').annotate(
                amount=Sum('amount'))
        text = 'Список покупок\n'
        for item in ingredients_amount:
            ingredient = Ingredient.objects.get(pk=item['ingredient'])
            amount = item['amount']
            text += (f'{ingredient.name}: {amount} '
                     f'({ingredient.measurement_unit})\n')
        filename = 'shopping_cart.txt'
        request = HttpResponse(text, content_type='text/plain')
        request['Content-Disposition'] = f'attachment; filename={filename}'
        return request


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    filter_backends = [DjangoFilterBackend, ]
