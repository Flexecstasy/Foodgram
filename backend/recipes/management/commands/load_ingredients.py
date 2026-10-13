import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из data/ingredients.json'

    def add_arguments(self, parser):
        parser.add_argument('--path', default=None)

    def handle(self, *args, **options):
        default = settings.BASE_DIR.parent / 'data' / 'ingredients.json'
        path = Path(options['path'] or default)
        with open(path, encoding='utf-8') as file:
            items = json.load(file)
        Ingredient.objects.bulk_create(
            [Ingredient(**item) for item in items], ignore_conflicts=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Ингредиентов в базе: {Ingredient.objects.count()}'))
