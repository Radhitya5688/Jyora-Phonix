
from django.contrib import admin
from .models import (
    DataSource,
    Phone,
    PhoneVariant,
    PhonePrice,
    Processor,
    PerformanceTest,
    SpecificationEvidence,
)


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ("brand", "model_name", "launch_date", "is_active")
    list_filter = ("brand", "is_active")
    search_fields = ("brand", "model_name")
    ordering = ("brand", "model_name")


@admin.register(PhoneVariant)
class PhoneVariantAdmin(admin.ModelAdmin):
    list_display = ("phone", "ram_gb", "storage_gb", "processor")
    list_filter = ("phone__brand", "ram_gb", "storage_gb")
    search_fields = ("phone__model_name", "processor__name")


@admin.register(Processor)
class ProcessorAdmin(admin.ModelAdmin):
    list_display = ("name", "manufacturer", "gpu_name")
    search_fields = ("name", "manufacturer", "gpu_name")


@admin.register(PhonePrice)
class PhonePriceAdmin(admin.ModelAdmin):
    list_display = ("variant", "retailer", "price_inr", "checked_at")
    list_filter = ("retailer", "checked_at")
    search_fields = ("variant__phone__model_name", "retailer")
    ordering = ("-checked_at",)


@admin.register(PerformanceTest)
class PerformanceTestAdmin(admin.ModelAdmin):
    list_display = ("variant", "test_name", "test_version", "score", "tested_at")
    list_filter = ("test_name", "tested_at")
    search_fields = ("variant__phone__model_name", "test_name", "game_name")


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "accessed_at")
    search_fields = ("name", "url")


@admin.register(SpecificationEvidence)
class SpecificationEvidenceAdmin(admin.ModelAdmin):
    list_display = ("field_name", "recorded_value", "source", "verified_at")
    list_filter = ("field_name", "verified_at")
    search_fields = ("field_name", "recorded_value")
