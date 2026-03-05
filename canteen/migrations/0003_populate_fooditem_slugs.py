from django.db import migrations
from django.utils.text import slugify


def populate_fooditem_slugs(apps, schema_editor):
    FoodItem = apps.get_model("canteen", "FoodItem")

    for item in FoodItem.objects.all():
        if item.slug:
            continue

        base_slug = slugify(item.name) or f"item-{item.pk}"
        slug = base_slug
        counter = 1

        while FoodItem.objects.filter(slug=slug).exclude(pk=item.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        item.slug = slug
        item.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("canteen", "0002_fooditem_slug"),
    ]

    operations = [
        migrations.RunPython(populate_fooditem_slugs, migrations.RunPython.noop),
    ]

