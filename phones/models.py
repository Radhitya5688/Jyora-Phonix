
from django.db import models


class DataSource(models.Model):
    name = models.CharField(max_length=150)
    url = models.URLField(max_length=1000)
    source_type = models.CharField(max_length=50, blank=True)
    accessed_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Processor(models.Model):
    manufacturer = models.CharField(max_length=100)
    name = models.CharField(max_length=150, unique=True)
    cpu_details = models.TextField(blank=True)
    gpu_name = models.CharField(max_length=150, blank=True)
    architecture = models.CharField(max_length=150, blank=True)
    fabrication_nm = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Phone(models.Model):
    brand = models.CharField(max_length=80)
    model_name = models.CharField(max_length=150)
    launch_date = models.DateField(null=True, blank=True)
    launch_price_inr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    os_at_launch = models.CharField(max_length=100, blank=True)
    promised_os_updates = models.PositiveSmallIntegerField(null=True, blank=True)
    promised_security_updates = models.PositiveSmallIntegerField(null=True, blank=True)

    display_type = models.CharField(max_length=100, blank=True)
    display_size_inches = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    resolution = models.CharField(max_length=100, blank=True)
    refresh_rate_hz = models.PositiveSmallIntegerField(null=True, blank=True)

    rear_camera_details = models.TextField(blank=True)
    front_camera_details = models.TextField(blank=True)
    battery_mah = models.PositiveIntegerField(null=True, blank=True)
    charging_watts = models.PositiveSmallIntegerField(null=True, blank=True)
    wireless_charging = models.BooleanField(null=True, blank=True)

    dimensions_mm = models.CharField(max_length=100, blank=True)
    weight_g = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    build_materials = models.CharField(max_length=200, blank=True)
    ip_rating = models.CharField(max_length=30, blank=True)
    network_support = models.CharField(max_length=100, blank=True)

    official_url = models.URLField(max_length=1000, blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["brand", "model_name"],
                name="unique_phone_brand_model",
            )
        ]
        ordering = ["brand", "model_name"]

    def __str__(self):
        return f"{self.brand} {self.model_name}"


class PhoneVariant(models.Model):
    phone = models.ForeignKey(
        Phone, on_delete=models.CASCADE, related_name="variants"
    )
    ram_gb = models.PositiveSmallIntegerField(null=True, blank=True)
    storage_gb = models.PositiveIntegerField(null=True, blank=True)
    ram_type = models.CharField(max_length=50, blank=True)
    storage_type = models.CharField(max_length=50, blank=True)
    colour = models.CharField(max_length=100, blank=True)
    launch_price_inr = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    processor = models.ForeignKey(
        Processor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="phone_variants",
    )
    model_number = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return (
            f"{self.phone} | {self.ram_gb or '?'}GB RAM / "
            f"{self.storage_gb or '?'}GB"
        )


class PerformanceTest(models.Model):
    
    variant = models.ForeignKey(
        PhoneVariant, on_delete=models.CASCADE,
        related_name="performance_tests",
    )
    source = models.ForeignKey(
        DataSource, on_delete=models.SET_NULL, null=True, blank=True
    )
    test_name = models.CharField(max_length=100)
    test_version = models.CharField(max_length=100, blank=True)
    score = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    game_name = models.CharField(max_length=100, blank=True)
    average_fps = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    temperature_c = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    battery_drain_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    test_conditions = models.TextField(blank=True)
    tested_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-tested_at", "test_name"]

    def __str__(self):
        return f"{self.variant} | {self.test_name}"


class PhonePrice(models.Model):
    variant = models.ForeignKey(
        PhoneVariant, on_delete=models.CASCADE, related_name="prices"
    )
    retailer = models.CharField(max_length=150)
    price_inr = models.DecimalField(max_digits=12, decimal_places=2)
    product_url = models.URLField(max_length=1000, blank=True)
    checked_at = models.DateTimeField()
    in_stock = models.BooleanField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["price_inr", "-checked_at"]

    def __str__(self):
        return f"{self.retailer}: ₹{self.price_inr}"


class SpecificationEvidence(models.Model):
    phone = models.ForeignKey(
        Phone, on_delete=models.CASCADE, null=True, blank=True,
        related_name="evidence",
    )
    variant = models.ForeignKey(
        PhoneVariant, on_delete=models.CASCADE, null=True, blank=True,
        related_name="evidence",
    )
    source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, related_name="evidence"
    )
    field_name = models.CharField(max_length=100)
    recorded_value = models.TextField()
    verified_at = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.field_name}: {self.recorded_value[:60]}"

# The verified phone, variant, price, offer and test models will be added
# after the data schema is finalized. Demo cards in views.py are not live data.
