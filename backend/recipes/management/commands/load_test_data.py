import base64

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from recipes.models import Ingredient, Recipe, RecipeIngredient
from users.models import User

PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0e'
    'cCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5E'
    'rkJggg==')

USERS = [
    ('admin', 'admin@foodgram.ru', 'Админ', 'Админов', True),
    ('ivan', 'ivan@foodgram.ru', 'Иван', 'Иванов', False),
    ('maria', 'maria@foodgram.ru', 'Мария', 'Петрова', False),
]

RECIPES = [
    ('ivan', 'Яичница', 'Разбить яйца на сковороду и пожарить.', 5,
     [('яйца куриные', 2), ('соль', 1)]),
    ('maria', 'Сладкий чай', 'Заварить чай и добавить сахар.', 10,
     [('сахар', 10)]),
    ('admin', 'Картофельное пюре', 'Отварить картофель и размять.', 30,
     [('картофель', 500), ('молоко', 100)]),
]


class Command(BaseCommand):
    help = 'Создаёт тестовых пользователей (пароль: Foodgram123) и рецепты'

    def handle(self, *args, **options):
        users = {}
        for username, email, first, last, is_admin in USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'first_name': first,
                          'last_name': last, 'is_staff': is_admin,
                          'is_superuser': is_admin})
            if created:
                user.set_password('Foodgram123')
                user.save()
            users[username] = user
        for author, name, text, time, items in RECIPES:
            if Recipe.objects.filter(name=name).exists():
                continue
            recipe = Recipe(author=users[author], name=name, text=text,
                            cooking_time=time)
            recipe.image.save(f'{name}.png', ContentFile(PNG), save=True)
            for ing_name, amount in items:
                ingredient = Ingredient.objects.filter(name=ing_name).first()
                if ingredient:
                    RecipeIngredient.objects.create(
                        recipe=recipe, ingredient=ingredient, amount=amount)
        self.stdout.write(self.style.SUCCESS('Тестовые данные загружены'))
