from django.contrib import admin
from .models import CustomUser, PickUpSpot

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('email',)



admin.site.register(PickUpSpot)