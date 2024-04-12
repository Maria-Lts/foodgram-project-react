from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from foodgram import settings
import csv
from foodgram.recipe.models import Ingredient
import traceback


class Command(BaseCommand):

    def handle(self, *args, **options):
        file_name = settings.BASE_DIR / 'data' / 'ingredients.csv'
        try:
            with open(file_name) as file:
                self.stdout.write(f"Чтение файла {file_name}\n")
                reader = csv.DictReader(file, fieldnames=['name', 'measurement_unit'])
                for row in reader:
                    obj, created = Ingredient.objects.get_or_create(name=row['name'], measurement_unit=row['measurement_unit'])
                    if not created:
                        self.stdout.write(f"Объект {obj.measurement_unit} {obj.name} уже создан\n")
                    # Obj = Model()
                    # for i, field in enumerate(row.values()):
                    #     if reader.fieldnames[i] in FOREIGNKEY_FIELDS:
                    #         model = self.get_model(reader.fieldnames[i])
                    #         obj = get_object_or_404(model, id=field)
                    #         setattr(Obj, reader.fieldnames[i], obj)
                    #     else:
                    #         setattr(Obj, reader.fieldnames[i], field)
                    obj.save()
        except Exception as e:
            raise CommandError(
                f"При чтении файла {file_name} произошла ошибка: {traceback.format_exc()}"
            )
