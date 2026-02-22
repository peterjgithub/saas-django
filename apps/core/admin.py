from django.contrib import admin

from .models import Country, Currency, Language, Timezone


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "code3")
    search_fields = ("code", "name")


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")
    filter_horizontal = ("countries",)


@admin.register(Timezone)
class TimezoneAdmin(admin.ModelAdmin):
    list_display = ("name", "label", "offset_seconds")
    search_fields = ("name",)
    filter_horizontal = ("countries",)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")
    filter_horizontal = ("countries",)
