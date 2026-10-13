import io
import random

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from recipes.models import Ingredient, Recipe, RecipeIngredient
from users.models import User

PASSWORD = 'Foodgram123'
USERS_COUNT = 20
RECIPES_COUNT = 50

FIRST_NAMES = ['Александр', 'Дмитрий', 'Максим', 'Сергей', 'Андрей',
               'Алексей', 'Елена', 'Ольга', 'Наталья', 'Анна']
LAST_NAMES = ['Смирнов', 'Кузнецов', 'Попов', 'Васильев', 'Соколов',
              'Михайлов', 'Новиков', 'Фёдоров', 'Морозов', 'Волков']
DISHES = ['Борщ', 'Щи', 'Солянка', 'Окрошка', 'Рассольник', 'Плов',
          'Пельмени', 'Блины', 'Сырники', 'Оладьи', 'Омлет',
          'Яичница с беконом',
          'Греческий салат', 'Оливье', 'Винегрет', 'Цезарь',
          'Пюре с котлетой', 'Жареная картошка', 'Гречка с грибами',
          'Макароны по-флотски', 'Котлеты', 'Тефтели', 'Голубцы',
          'Запечённая курица', 'Куриный суп', 'Рыба в духовке',
          'Уха', 'Пицца', 'Лазанья', 'Спагетти карбонара', 'Шашлык',
          'Шарлотка', 'Медовик', 'Наполеон', 'Чизкейк', 'Брауни',
          'Овсяное печенье', 'Банановый хлеб', 'Манник', 'Кекс',
          'Смузи', 'Морс', 'Компот', 'Какао', 'Тосты с авокадо',
          'Бутерброды', 'Хумус', 'Гуакамоле', 'Рагу', 'Жаркое']
STEPS = [
    'Подготовьте все ингредиенты и тщательно вымойте продукты.',
    'Нарежьте ингредиенты небольшими кусочками.',
    'Разогрейте сковороду или кастрюлю на среднем огне.',
    'Выложите основные ингредиенты и готовьте, периодически помешивая.',
    'Добавьте специи и соль по вкусу.',
    'Доведите блюдо до готовности и дайте ему немного настояться.',
    'Подавайте горячим, украсив зеленью.',
]


def make_image(rng):
    """Генерирует простую картинку-заглушку: градиент и круги."""
    width, height = 600, 400
    top = tuple(rng.randint(80, 255) for _ in range(3))
    bottom = tuple(rng.randint(0, 160) for _ in range(3))
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / height
        color = tuple(int(t + (b - t) * ratio) for t, b in zip(top, bottom))
        draw.line([(0, y), (width, y)], fill=color)
    for _ in range(rng.randint(4, 8)):
        x, y = rng.randint(0, width), rng.randint(0, height)
        r = rng.randint(20, 90)
        fill = tuple(rng.randint(120, 255) for _ in range(3))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=80)
    return buffer.getvalue()


class Command(BaseCommand):
    help = (f'Создаёт {USERS_COUNT} пользователей и {RECIPES_COUNT} рецептов '
            f'с картинками (пароль: {PASSWORD}). Повторный запуск безопасен.')

    def handle(self, *args, **options):
        rng = random.Random(42)
        ingredients = list(Ingredient.objects.all())
        if not ingredients:
            self.stderr.write(self.style.ERROR(
                'Сначала загрузите ингредиенты: load_ingredients'))
            return

        users = []
        for number in range(1, USERS_COUNT + 1):
            user, created = User.objects.get_or_create(
                username=f'user{number:02d}',
                defaults={
                    'email': f'user{number:02d}@foodgram.ru',
                    'first_name': FIRST_NAMES[number % len(FIRST_NAMES)],
                    'last_name': LAST_NAMES[(number * 3) % len(LAST_NAMES)],
                })
            if created:
                user.set_password(PASSWORD)
                user.save()
            users.append(user)

        created_recipes = 0
        for number in range(RECIPES_COUNT):
            name = DISHES[number % len(DISHES)]
            if Recipe.objects.filter(name=name).exists():
                continue
            recipe = Recipe(
                author=users[number % len(users)],
                name=name,
                text=' '.join(rng.sample(STEPS, k=5)),
                cooking_time=rng.choice([5, 10, 15, 20, 30, 45, 60, 90]),
            )
            recipe.image.save(f'demo_{number + 1}.jpg',
                              ContentFile(make_image(rng)), save=True)
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(recipe=recipe, ingredient=ingredient,
                                 amount=rng.randint(1, 500))
                for ingredient in rng.sample(ingredients, k=rng.randint(3, 7))
            ])
            created_recipes += 1

        self.stdout.write(self.style.SUCCESS(
            f'Пользователей: {len(users)}, новых рецептов: {created_recipes}'))
