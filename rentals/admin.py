from django.contrib import admin
from .models import Booking, Category, DamageReport, Item

# Register your models here.
admin.site.register(Item)
admin.site.register(Category)
admin.site.register(Booking)
admin.site.register(DamageReport)

