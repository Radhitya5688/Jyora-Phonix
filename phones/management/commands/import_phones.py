
import csv
import re
from collections import OrderedDict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from phones.models import Phone, PhoneVariant, Processor


def clean_text(value):
    return (value or "").strip()


def parse_number(value):
    """Extract a decimal number from values such as '174g' or '6.1 inches'."""
    if not value:
        return None

    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", str(value))
    if not match:
        return None

    try:
        return Decimal(match.group().replace(",", ""))
    except InvalidOperation:
        return None


def parse_price(value):
    """Parse an Indian launch price such as 'INR 79,999'."""
    if not value:
        return None

    match = re.search(r"[\d,]+(?:\.\d+)?", str(value))
    if not match:
        return None

    try:
        return Decimal(match.group().replace(",", ""))
    except InvalidOperation:
        return None


def parse_integer(value):
    number = parse_number(value)
    return int(number) if number is not None else None


def parse_storage(model_name):
    """Extract storage from model names ending in 128GB, 256GB, or 1TB."""
    match = re.search(
        r"\b(\d+)\s*(GB|TB)\s*$",
        model_name,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).upper()

    return amount * 1024 if unit == "TB" else amount


def get_family_name(model_name):
    """Remove a trailing storage size to identify the phone model family."""
    return re.sub(
        r"\s+\d+\s*(?:GB|TB)\s*$",
        "",
        clean_text(model_name),
        flags=re.IGNORECASE,
    ).strip()


def processor_manufacturer(chip_name):
    """Use conservative manufacturer labels based on the chip name."""
    name = chip_name.lower()

    if any(term in name for term in ("snapdragon", "qualcomm")):
        return "Qualcomm"
    if any(term in name for term in ("dimensity", "helio", "mediatek")):
        return "MediaTek"
    if name.startswith(("apple ", "a17", "a18", "a19", "m1", "m2", "m3", "m4")):
        return "Apple"
    if any(term in name for term in ("tensor", "google")):
        return "Google"
    if any(term in name for term in ("exynos", "samsung")):
        return "Samsung"
    if "kirin" in name:
        return "Huawei"

    return "Not specified"


class Command(BaseCommand):
    help = "Import phone models and variants from Mobiles Dataset.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="Mobiles Dataset.csv",
            help="CSV path relative to the project root, or an absolute path",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum number of distinct phone model families to import",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview the import without changing the database",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["file"])

        if not csv_path.is_absolute():
            csv_path = Path.cwd() / csv_path

        if not csv_path.exists():
            raise CommandError(
                f"CSV file not found: {csv_path}\n"
                "Place Mobiles Dataset.csv in the project root or pass --file."
            )

        limit = options["limit"]
        if limit < 1:
            raise CommandError("--limit must be at least 1.")

        # The supplied dataset contains some non-UTF-8 characters.
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
        except UnicodeDecodeError:
            with csv_path.open("r", encoding="latin-1", newline="") as file:
                rows = list(csv.DictReader(file))

        required_columns = {
            "Company Name",
            "Model Name",
            "Processor",
            "RAM",
            "Launched Price (India)",
        }

        if not rows or not required_columns.issubset(rows[0].keys()):
            raise CommandError(
                "The CSV is empty or does not contain the expected column names."
            )

        # Group storage variants under the same model family.
        families = OrderedDict()

        for row in rows:
            brand = clean_text(row.get("Company Name"))
            original_name = clean_text(row.get("Model Name"))
            family_name = get_family_name(original_name)

            if not brand or not family_name:
                continue

            key = (brand.casefold(), family_name.casefold())

            if key not in families:
                families[key] = {
                    "brand": brand,
                    "model_name": family_name,
                    "rows": [],
                }

            families[key]["rows"].append(row)

        selected_families = list(families.values())[:limit]

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN: no database changes made."))
            self.stdout.write(f"CSV rows: {len(rows)}")
            self.stdout.write(f"Distinct model families found: {len(families)}")
            self.stdout.write(
                f"Model families selected: {len(selected_families)}"
            )

            for family in selected_families[:10]:
                self.stdout.write(
                    f"  {family['brand']} {family['model_name']} "
                    f"({len(family['rows'])} CSV rows)"
                )

            if len(selected_families) > 10:
                self.stdout.write("  ...")

            self.stdout.write(
                "Run without --dry-run to perform the import."
            )
            return

        created_phones = 0
        reused_phones = 0
        created_variants = 0
        reused_variants = 0
        created_processors = 0

        with transaction.atomic():
            for family in selected_families:
                brand = family["brand"]
                model_name = family["model_name"]
                family_rows = family["rows"]

                prices = [
                    price
                    for price in (
                        parse_price(row.get("Launched Price (India)"))
                        for row in family_rows
                    )
                    if price is not None
                ]

                # Use the lowest listed Indian launch price as a reference.
                phone_price = min(prices) if prices else None

                first = family_rows[0]

                phone_defaults = {
                    "launch_price_inr": phone_price,
                    "weight_g": parse_number(first.get("Mobile Weight")),
                    "display_size_inches": parse_number(first.get("Screen Size")),
                    "battery_mah": parse_integer(first.get("Battery Capacity")),
                    "rear_camera_details": clean_text(first.get("Back Camera")),
                    "front_camera_details": clean_text(first.get("Front Camera")),
                }

                phone, was_created = Phone.objects.get_or_create(
                    brand=brand,
                    model_name=model_name,
                    defaults={
                        "launch_price_inr": phone_price,
                        "weight_g": phone_defaults["weight_g"],
                        "display_size_inches": phone_defaults["display_size_inches"],
                        "battery_mah": phone_defaults["battery_mah"],
                        "rear_camera_details": phone_defaults["rear_camera_details"],
                        "front_camera_details": phone_defaults["front_camera_details"],
                    },
                )

                if was_created:
                    created_phones += 1
                else:
                    reused_phones += 1

                    # Fill missing details without overwriting existing data.
                    changed_fields = []

                    for field, value in phone_defaults.items():
                        current_value = getattr(phone, field)

                        if value is None or value == "":
                            continue

                        if current_value is None or current_value == "":
                            setattr(phone, field, value)
                            changed_fields.append(field)

                    if changed_fields:
                        phone.save(update_fields=changed_fields)

                for row in family_rows:
                    ram_gb = parse_integer(row.get("RAM"))
                    storage_gb = parse_storage(
                        clean_text(row.get("Model Name"))
                    )
                    variant_price = parse_price(
                        row.get("Launched Price (India)")
                    )
                    chip_name = clean_text(row.get("Processor"))

                    processor = None

                    if chip_name:
                        processor, processor_created = Processor.objects.get_or_create(
                            name=chip_name,
                            defaults={
                                "manufacturer": processor_manufacturer(chip_name)
                            },
                        )

                        if processor_created:
                            created_processors += 1

                    variant = PhoneVariant.objects.filter(
                        phone=phone,
                        ram_gb=ram_gb,
                        storage_gb=storage_gb,
                        colour="",
                    ).order_by("id").first()

                    if variant is None:
                        PhoneVariant.objects.create(
                            phone=phone,
                            ram_gb=ram_gb,
                            storage_gb=storage_gb,
                            launch_price_inr=variant_price,
                            processor=processor,
                            colour="",
                        )
                        created_variants += 1
                    else:
                        reused_variants += 1
                        changed_fields = []

                        if variant.launch_price_inr is None and variant_price is not None:
                            variant.launch_price_inr = variant_price
                            changed_fields.append("launch_price_inr")

                        if variant.processor_id is None and processor is not None:
                            variant.processor = processor
                            changed_fields.append("processor")

                        if variant.ram_gb is None and ram_gb is not None:
                            variant.ram_gb = ram_gb
                            changed_fields.append("ram_gb")

                        if variant.storage_gb is None and storage_gb is not None:
                            variant.storage_gb = storage_gb
                            changed_fields.append("storage_gb")

                        if changed_fields:
                            variant.save(update_fields=changed_fields)

        self.stdout.write(self.style.SUCCESS("Phone import completed."))
        self.stdout.write(f"Model families selected: {len(selected_families)}")
        self.stdout.write(f"New phones created: {created_phones}")
        self.stdout.write(f"Existing phones reused: {reused_phones}")
        self.stdout.write(f"New variants created: {created_variants}")
        self.stdout.write(f"Existing variants reused: {reused_variants}")
        self.stdout.write(f"New processor records created: {created_processors}")
        self.stdout.write(
            "Note: prices are launch-price references, not current retail prices."
        )
