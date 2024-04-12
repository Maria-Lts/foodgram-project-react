import csv
import traceback

from django.core.management.base import BaseCommand, CommandError
from foodgram import settings
from foodgram.recipe.models import Ingredient


class Command(BaseCommand):

    def handle(self, *args, **options):
        file_name = settings.BASE_DIR / 'data' / 'ingredients.csv'
        try:
            with open(file_name) as file:
                self.stdout.write(f"Чтение файла {file_name}\n")
                reader = csv.DictReader(
                    file, fieldnames=['name', 'measurement_unit'])
                for row in reader:
                    obj, created = Ingredient.objects.get_or_create(
                        name=row['name'],
                        measurement_unit=row['measurement_unit'])
                    if not created:
                        self.stdout.write(
                            f"Объект {obj.measurement_unit} "
                            f"{obj.name} уже создан\n")
                    obj.save()
        except Exception:
            raise CommandError(
                f"При чтении файла {file_name} "
                f"произошла ошибка: {traceback.format_exc()}"
            )
