from colorfield.fields import ColorField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from foodgram.user.models import User


class Ingredient(models.Model):
    name = models.CharField(max_length=200)
    measurement_unit = models.CharField(max_length=200)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=200)
    color = ColorField(max_length=7, format='hex')
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class IngredientAmount(models.Model):
    ingredient = models.ForeignKey(Ingredient,
                                   on_delete=models.CASCADE,
                                   related_name='ingredient_amount',)
    recipe = models.ForeignKey('Recipe',
                               on_delete=models.CASCADE,
                               related_name='ingredient_amount',)
    amount = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(5000), MinValueValidator(1)])

    class Meta:
        verbose_name = 'Ингридиент для рецепта'
        verbose_name_plural = 'Ингриденты для рецепта'

    def __str__(self):
        return (f'{self.ingredient} {self.amount}')


class Recipe(models.Model):
    name = models.CharField(max_length=200)
    ingredients = models.ManyToManyField(
        IngredientAmount,
        related_name='recipe_ingredients')
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               related_name='recipes',)
    tags = models.ManyToManyField(Tag)
    image = models.ImageField(
        upload_to='recipe/', null=True, blank=True)
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        error_messages={
            "min_value": "Время готовки не может быть указано меньше минуты"})
    pub_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    def __str__(self):
        return self.name


class BaseUserListModel(models.Model):
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='%(class)s')
    recipe = models.ForeignKey(Recipe,
                               on_delete=models.CASCADE,
                               related_name='%(class)s')

    class Meta:
        abstract = True


class Favorite(BaseUserListModel):

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        ordering = ('-id',)
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_recipe',
            ),
        )

    def __str__(self):
        return (f'{self.user} {self.recipe}')


class ShoppingList(BaseUserListModel):

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        ordering = ('-id',)
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shopping_cart',),)
