from django.core.validators import MaxValueValidator, MinValueValidator
from djoser.serializers import \
    UserCreateSerializer as DjoserUserCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from foodgram.recipe.models import (Favorite, Ingredient, IngredientAmount,
                                    Recipe, ShoppingList, Tag)
from foodgram.user.models import Subscription, User
from rest_framework import serializers
from rest_framework.generics import get_object_or_404


class UserSerializer(DjoserUserSerializer):

    class Meta:
        fields = ('username', 'first_name', 'last_name',
                  'email', 'id',)
        model = User


class SubscribeUserSerializer(DjoserUserSerializer):
    '''Пользователь и его подписки'''
    is_subscribed = serializers.SerializerMethodField(
        read_only=True, method_name='get_is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        return (request.user.is_authenticated
                and Subscription.objects.filter(
                    user=request.user, author=obj).exists())

    class Meta:
        fields = ('username', 'first_name', 'last_name',
                  'email', 'id', 'is_subscribed',)
        model = User


class UserCreateSerializer(DjoserUserCreateSerializer):
    '''Создание пользователя'''
    username = serializers.RegexField(r'^[\w.@+-]+\Z',
                                      max_length=150, required=True)
    email = serializers.EmailField(max_length=254, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(max_length=150,
                                     required=True, write_only=True)

    class Meta:
        fields = ('username', 'first_name', 'last_name',
                  'email', 'id', 'password',)
        model = User
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Email уже занят')
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError('Имя пользователя уже занято')
        return data


class UserChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class IngredientsAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField(
        validators=[MaxValueValidator(5000), MinValueValidator(1)])

    class Meta:
        fields = ('id', 'amount', 'measurement_unit', 'name',)
        model = IngredientAmount


class IngredientAmountWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=[MaxValueValidator(5000), MinValueValidator(1)])

    class Meta:
        fields = ('id', 'amount',)
        model = IngredientAmount


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientAmountWriteSerializer(required=True, many=True)
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), required=True,
        many=True)
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(
        validators=[MaxValueValidator(5000), MinValueValidator(1)])

    def validate(self, data):
        cooking_time = data.get('cooking_time')
        if cooking_time <= 0:
            raise serializers.ValidationError(
                'Время готовки должно быть больше 1'
            )
        ingredients_id_list = []
        ingredients = data.get('ingredients')
        for ingredient in ingredients:
            if ingredient.get('amount') <= 0:
                raise serializers.ValidationError(
                    'Количество ингридиента должно быть больше 1'
                )
            ingredient_id = ingredient['id']
            if not Ingredient.objects.filter(pk=ingredient_id).exists():
                raise serializers.ValidationError(
                    'Ингредиент не существует')
            ingredients_id_list.append(ingredient['id'])
        if len(ingredients_id_list) > len(set(ingredients_id_list)):
            raise serializers.ValidationError(
                'Указаны повторяющиеся ингридиенты')
        if not data.get('image'):
            raise serializers.ValidationError(
                'Добавьте изображение'
            )
        if not data.get('ingredients'):
            raise serializers.ValidationError(
                'В рецепте должны присутствовать ингридиенты'
            )
        if not data.get('tags'):
            raise serializers.ValidationError(
                'Укажите тег(и)'
            )
        tags = data.get('tags')
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                'Теги не должны повторяться'
            )
        return data

    def create_ingredients(self, ingredient, recipe):
        for ingredient_list in ingredient:
            amount = ingredient_list['amount']
            ingredient_id = ingredient_list['id']
            if ingredient_id:
                ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
                ingredient_amount = IngredientAmount.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=amount
                )
                ingredient_amount.save()

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        # request = self.context.get('request')
        # recipe.author = request.user
        recipe.save()
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        instance.tags.clear()
        instance.tags.add(*tags)
        recipe = instance
        self.create_ingredients(ingredients, recipe)
        instance.save()
        return instance

    def to_representation(self, instance):
        serializer = RecipeReadSerializer(
            instance,
            context={'request': self.context.get('request')})
        return serializer.data

    class Meta:
        fields = ('id', 'name', 'ingredients',
                  'author', 'tags', 'image',
                  'text', 'cooking_time',)
        model = Recipe


class FavoriteSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField()
    image = Base64ImageField(read_only=True)
    cooking_time = serializers.ReadOnlyField()

    def validate(self, data):
        recipe = data.get('recipe')
        if len(recipe) != len(set(recipe)):
            raise serializers.ValidationError(
                'Рецепт уже добавлен в избранное'
            )
        recipe_id = recipe['id']
        if not Recipe.objects.filter(pk=recipe_id).exists():
            raise serializers.ValidationError(
                'Рецепт не существует')
        return data

    class Meta:
        # fields = ('recipe', 'user')
        fields = ('id', 'name', 'image',
                  'cooking_time',)
        model = Recipe


class SubscriptionRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('id', 'name', 'image',
                  'cooking_time',)
        model = Recipe


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    '''Для подписок'''
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField(
        read_only=True, method_name='get_is_subscribed')
    recipes = serializers.SerializerMethodField(method_name='get_recipes')
    recipes_count = serializers.SerializerMethodField(
        method_name='get_recipes_count')

    def validate(self, data):
        request = self.context.get('request')
        user_id = request.user.id
        author_id = self.context.get('author')
        if Subscription.objects.filter(author=author_id,
                                       user=user_id).exists():
            raise serializers.ValidationError('Вы уже подписаны')
        if user_id == author_id:
            raise serializers.ValidationError(
                'Нельзя подписаться на себя'
            )
        return data

    def create(self, validated_data):
        subscription = Subscription(user=self.context.get('request').user,
                                    author=User.objects.get(
                                        id=self.context.get('author')))
        subscription.save()
        self.instance = subscription
        return subscription

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(user=request.user,
                                               author=obj.author).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.author)
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return SubscriptionRecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()

    class Meta:
        fields = ('email', 'username',
                  'first_name', 'last_name',
                  'is_subscribed', 'recipes',
                  'recipes_count', 'id',)
        model = Subscription


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('id', 'name', 'measurement_unit',)
        model = Ingredient


class TagSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField('^[-a-zA-Z0-9_]+$',
                                 max_length=200, required=True)

    class Meta:
        fields = ('id', 'name', 'color', 'slug',)
        model = Tag


class RecipeReadSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField()
    ingredients = IngredientsAmountSerializer(many=True)
    author = SubscribeUserSerializer()
    tags = TagSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user,
                                           recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingList.objects.filter(user=request.user,
                                               recipe=obj).exists()
        return False

    class Meta:
        fields = ('id', 'name', 'ingredients',
                  'text', 'cooking_time',
                  'is_favorited', 'is_in_shopping_cart', 'tags',
                  'image', 'author',)
        model = Recipe


class ShoppingCartRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('id', 'name',
                  'image', 'cooking_time')
        model = Recipe
 