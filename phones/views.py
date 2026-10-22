import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db.models import Min
from django.shortcuts import render

from phones.models import Phone, Processor, PerformanceTest


BRANDS = [
    "Samsung", "vivo", "iQOO", "Motorola", "realme",
    "POCO", "Redmi", "Xiaomi", "Apple", "Google",
    "OnePlus",
]

PRIORITIES = [
    ("balanced", "Balanced"),
    ("performance", "Gaming & performance"),
    ("camera", "Camera"),
    ("battery", "Battery"),
    ("display", "Display"),
]



def has_value(value):
    """Return True when a field contains useful recorded information."""
    return value is not None and str(value).strip() != ""


def is_smartphone_model(model_name):
    """Exclude known tablet and non-phone product families."""
    name = (model_name or "").strip().lower()

    excluded_terms = (
        "ipad",
        "galaxy tab",
        "oneplus pad",
        "xiaomi pad",
        "redmi pad",
        "lenovo tab",
        "matepad",
        "honor pad",
        "realme pad",
        "oppo pad",
        "tablet",
        "smartwatch",
        "laptop",
        "notebook",
        "airpods",
        "galaxy buds",
    )

    return not any(term in name for term in excluded_terms)


def get_reference_price(phone):
    """Return the lowest recorded variant launch price, or phone price."""
    prices = [
        variant.launch_price_inr
        for variant in phone.variants.all()
        if variant.launch_price_inr is not None
    ]

    if prices:
        return min(prices)

    return phone.launch_price_inr


def get_processor_details(phone, reference_price):
    """Get processor details from the cheapest priced variant when possible."""
    variants = list(phone.variants.all())

    variant = next(
        (
            item for item in variants
            if item.launch_price_inr == reference_price
            and item.processor is not None
        ),
        None,
    )

    if variant is None:
        variant = next(
            (item for item in variants if item.processor is not None),
            None,
        )

    processor = variant.processor if variant else None

    return {
        "processor": processor.name if processor else "Not recorded",
        "cpu_details": processor.cpu_details if processor else "",
        "gpu_name": processor.gpu_name if processor else "",
        "architecture": processor.architecture if processor else "",
    }


def get_latest_gaming_test(phone):
    """
    Return the latest recorded game FPS result.

    Results are shown as evidence, not treated as universally comparable
    across different games, settings, devices, or test conditions.
    """
    tests = []

    for variant in phone.variants.all():
        for test in variant.performance_tests.all():
            if test.average_fps is not None and has_value(test.game_name):
                tests.append(test)

    if not tests:
        return None

    tests.sort(
        key=lambda test: test.tested_at or date.min,
        reverse=True,
    )

    test = tests[0]

    return {
        "game_name": test.game_name,
        "average_fps": test.average_fps,
        "test_name": test.test_name,
        "tested_at": test.tested_at,
        "test_conditions": test.test_conditions,
        "source_name": test.source.name if test.source else "",
        "source_url": test.source.url if test.source else "",
    }


def get_recommendation_data(phone, reference_price):
    """Collect recorded specifications used by the priority rankings."""
    processor_data = get_processor_details(phone, reference_price)

    variants = list(phone.variants.all())

    charging_values = [
        variant.phone.charging_watts
        for variant in []
    ]

    # Use phone-level specifications for display, camera, and battery.
    display_size = phone.display_size_inches
    refresh_rate = phone.refresh_rate_hz
    resolution = phone.resolution
    display_type = phone.display_type
    battery = phone.battery_mah
    charging = phone.charging_watts
    rear_camera = phone.rear_camera_details
    front_camera = phone.front_camera_details

    gaming_test = get_latest_gaming_test(phone)

    # Count recorded fields, not performance or quality scores.
    balanced_completeness = sum([
        has_value(processor_data["processor"])
        and processor_data["processor"] != "Not recorded",
        has_value(display_size),
        has_value(refresh_rate),
        has_value(resolution),
        has_value(display_type),
        has_value(battery),
        has_value(charging),
        has_value(rear_camera),
        has_value(front_camera),
    ])

    camera_completeness = sum([
        has_value(rear_camera),
        has_value(front_camera),
    ])

    display_completeness = sum([
        has_value(display_size),
        has_value(refresh_rate),
        has_value(resolution),
        has_value(display_type),
    ])

    return {
        "brand": phone.brand,
        "name": phone.model_name,
        "price": reference_price,
        "processor": processor_data["processor"],
        "cpu_details": processor_data["cpu_details"],
        "gpu_name": processor_data["gpu_name"],
        "architecture": processor_data["architecture"],
        "display": display_size,
        "display_type": display_type,
        "resolution": resolution,
        "refresh_rate": refresh_rate,
        "battery": battery,
        "charging": charging,
        "rear_camera": rear_camera,
        "front_camera": front_camera,
        "image_url": phone.image_url,
        "priority": "",
        "gaming_test": gaming_test,
        "has_gaming_test": gaming_test is not None,
        "balanced_completeness": balanced_completeness,
        "camera_completeness": camera_completeness,
        "display_completeness": display_completeness,
    }


def rank_recommendations(recommendations, selected_priority):
    """
    Rank phones differently for each selected priority.

    Ranking uses available specifications and recorded test evidence.
    It does not create synthetic benchmark or camera-quality scores.
    """
    if selected_priority == "performance":
        # Sourced game FPS evidence first, then processor-data completeness.
        # FPS values from different games are deliberately not compared.
        recommendations.sort(
            key=lambda item: (
                not item["has_gaming_test"],
                item["processor"] == "Not recorded",
                not has_value(item["cpu_details"]),
                not has_value(item["gpu_name"]),
                item["price"],
                item["brand"],
                item["name"],
            )
        )

    elif selected_priority == "battery":
        # Battery capacity is a specification, not a battery-life result.
        recommendations.sort(
            key=lambda item: (
                item["battery"] is None,
                -(item["battery"] or 0),
                item["charging"] is None,
                -(item["charging"] or 0),
                item["price"],
                item["brand"],
                item["name"],
            )
        )

    elif selected_priority == "camera":
        # Prefer phones with recorded rear and front camera information.
        # This measures specification coverage, not actual camera quality.
        recommendations.sort(
            key=lambda item: (
                -item["camera_completeness"],
                not has_value(item["rear_camera"]),
                not has_value(item["front_camera"]),
                item["price"],
                item["brand"],
                item["name"],
            )
        )

    elif selected_priority == "display":
        # Prefer higher recorded refresh rates, then available display details.
        recommendations.sort(
            key=lambda item: (
                item["refresh_rate"] is None,
                -(item["refresh_rate"] or 0),
                -item["display_completeness"],
                item["display"] is None,
                -(item["display"] or Decimal("0")),
                item["price"],
                item["brand"],
                item["name"],
            )
        )

    else:
        # Balanced: specification coverage first, then reference price.
        recommendations.sort(
            key=lambda item: (
                -item["balanced_completeness"],
                item["price"],
                item["brand"],
                item["name"],
            )
        )

    return recommendations


def home(request):
    featured_phones = Phone.objects.filter(
        is_active=True
    ).order_by("-launch_date", "brand", "model_name")[:2]

    return render(
        request,
        "phones/home.html",
        {
            "demo_phones": featured_phones,
            "featured_phones": featured_phones,
        },
    )


def buy(request):
    context = {
        "phones": [],
        "budget": request.GET.get("budget", "").strip(),
        "error": "",
        "brands": BRANDS,
        "submitted": False,
        "bank_selected": False,
        "exchange_selected": False,
        "demo_mode": False,
    }

    if request.method == "POST":
        context["submitted"] = True
        raw_budget = request.POST.get("budget", "").strip()
        context["budget"] = raw_budget
        context["bank_selected"] = (
            request.POST.get("use_bank_offers") == "on"
        )
        context["exchange_selected"] = (
            request.POST.get("use_exchange") == "on"
        )

        try:
            budget = Decimal(raw_budget)
            if not budget.is_finite() or budget <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            context["error"] = "Enter a valid budget greater than ₹0."
            return render(request, "phones/buy.html", context)

        selected_brands = request.POST.getlist("brand")
        selected_priorities = request.POST.getlist("priority")
        context["selected_brands"] = selected_brands
        context["selected_priorities"] = selected_priorities
        context["budget_value"] = budget

        phones = (
            Phone.objects.filter(is_active=True)
            .annotate(
                lowest_variant_launch_price=Min(
                    "variants__launch_price_inr"
                )
            )
            .prefetch_related("variants")
        )

        if selected_brands:
            phones = phones.filter(brand__in=selected_brands)

        results = []

        for phone in phones:
            variant_prices = [
                variant.launch_price_inr
                for variant in phone.variants.all()
                if variant.launch_price_inr is not None
            ]

            reference_prices = variant_prices or (
                [phone.launch_price_inr]
                if phone.launch_price_inr is not None
                else []
            )

            if not reference_prices:
                continue

            reference_price = min(reference_prices)

            if reference_price > budget:
                continue

            results.append({
                "name": phone.model_name,
                "brand": phone.brand,
                "price": reference_price,
                "image_url": phone.image_url,
                "price_label": "Launch-price reference",
                "tag": "Specifications available",
                "description": (
                    "Listed launch price reference, not a verified "
                    "current selling price."
                ),
                "specs": [
                    (
                        f"{phone.display_size_inches} inch display"
                        if phone.display_size_inches
                        else "Display size not recorded"
                    ),
                    (
                        f"{phone.refresh_rate_hz} Hz display"
                        if phone.refresh_rate_hz
                        else "Refresh rate not recorded"
                    ),
                    (
                        f"{phone.battery_mah} mAh battery"
                        if phone.battery_mah
                        else "Battery capacity not recorded"
                    ),
                ],
                "demo": False,
                "phone_id": phone.pk,
            })

        context["phones"] = results

        if context["bank_selected"] or context["exchange_selected"]:
            context["offer_note"] = (
                "Bank and exchange discounts are not connected yet. "
                "Displayed reference prices do not include unverified offers."
            )

        context["price_note"] = (
            "Prices shown are launch-price references, not current retail "
            "offers. Verify current prices with the retailer before buying."
        )

    return render(request, "phones/buy.html", context)


def placeholder_page(request, page_name):
    details = {
        "Compare": (
            "Compare at least three phones side by side, including chipset, "
            "RAM type, benchmarks, cameras, battery, dimensions and durability."
        ),
        "Processor Lab": (
            "Explore CPU/GPU architecture, version-labelled benchmarks, "
            "sustained gaming, thermals and battery drain."
        ),
        "Suggest Me a Phone": (
            "Tell Jyora your budget and priorities to receive a transparent, "
            "ranked shortlist."
        ),
        "About Jyora Phonix": (
            "Jyora Phonix brings effective-price discovery, hardware "
            "intelligence and personalized recommendations into one place."
        ),
    }

    return render(
        request,
        "phones/placeholder.html",
        {
            "page_name": page_name,
            "description": details.get(page_name, ""),
        },
    )


def compare(request):
    available_phones = (
        Phone.objects.filter(is_active=True)
        .prefetch_related("variants__processor")
        .order_by("brand", "model_name")
    )

    selected_ids = request.GET.getlist("phone_ids")
    selected_phones = []

    if selected_ids:
        valid_ids = [
            int(phone_id)
            for phone_id in selected_ids
            if phone_id.isdigit()
        ]

        selected_phones = list(
            Phone.objects.filter(
                pk__in=valid_ids,
                is_active=True,
            ).prefetch_related("variants__processor")
        )

        phone_by_id = {phone.pk: phone for phone in selected_phones}
        selected_phones = [
            phone_by_id[phone_id]
            for phone_id in valid_ids
            if phone_id in phone_by_id
        ]

    error = ""
    comparison_rows = []

    if selected_ids and len(selected_phones) < 3:
        error = "Please select at least 3 phones to compare."

    if len(selected_phones) >= 3:

        def display(value, suffix=""):
            if value is None or value == "":
                return "Not available"
            return f"{value}{suffix}"

        def processor_names(phone):
            names = list(dict.fromkeys(
                variant.processor.name
                for variant in phone.variants.all()
                if variant.processor
            ))
            return ", ".join(names) if names else "Not available"

        def configurations(phone):
            items = []

            for variant in phone.variants.all():
                ram = (
                    f"{variant.ram_gb} GB RAM"
                    if variant.ram_gb else None
                )
                storage = (
                    f"{variant.storage_gb} GB storage"
                    if variant.storage_gb else None
                )
                config = " / ".join(
                    value for value in [ram, storage] if value
                )

                if config and config not in items:
                    items.append(config)

            return ", ".join(items) if items else "Not available"

        def launch_price(phone):
            prices = [
                variant.launch_price_inr
                for variant in phone.variants.all()
                if variant.launch_price_inr is not None
            ]

            if prices:
                return f"₹{min(prices):,.0f} (variant launch price)"

            if phone.launch_price_inr is not None:
                return (
                    f"₹{phone.launch_price_inr:,.0f} "
                    "(phone launch price)"
                )

            return "Not available"

        rows = [
            ("Brand", lambda p: p.brand),
            ("Processor", processor_names),
            ("RAM / storage configurations", configurations),
            ("Launch-price reference", launch_price),
            ("Display", lambda p: display(p.display_size_inches, " inches")),
            ("Display type", lambda p: display(p.display_type)),
            ("Resolution", lambda p: display(p.resolution)),
            ("Refresh rate", lambda p: display(p.refresh_rate_hz, " Hz")),
            ("Rear camera", lambda p: display(p.rear_camera_details)),
            ("Front camera", lambda p: display(p.front_camera_details)),
            ("Battery", lambda p: display(p.battery_mah, " mAh")),
            ("Wired charging", lambda p: display(p.charging_watts, " W")),
            (
                "Wireless charging",
                lambda p: (
                    "Yes" if p.wireless_charging is True
                    else "No" if p.wireless_charging is False
                    else "Not available"
                ),
            ),
            ("Weight", lambda p: display(p.weight_g, " g")),
            ("Build", lambda p: display(p.build_materials)),
            ("IP rating", lambda p: display(p.ip_rating)),
            ("Operating system at launch", lambda p: display(p.os_at_launch)),
            ("5G / network support", lambda p: display(p.network_support)),
        ]

        comparison_rows = [
            {
                "label": label,
                "values": [getter(phone) for phone in selected_phones],
            }
            for label, getter in rows
        ]

    return render(
        request,
        "phones/compare.html",
        {
            "available_phones": available_phones,
            "selected_phones": selected_phones,
            "selected_ids": [str(phone.pk) for phone in selected_phones],
            "comparison_rows": comparison_rows,
            "error": error,
        },
    )


def processor_lab(request):
    processors = Processor.objects.all().order_by(
        "manufacturer", "name"
    )

    return render(
        request,
        "phones/processor_lab.html",
        {"processors": processors},
    )


def suggest_me(request):
    recommendations = []
    error = ""
    budget_text = ""
    selected_priority = "balanced"

    valid_priorities = {value for value, label in PRIORITIES}

    if request.method == "POST":
        budget_text = request.POST.get("budget", "").strip()
        requested_priority = request.POST.get("priority", "balanced")

        if requested_priority in valid_priorities:
            selected_priority = requested_priority

        try:
            budget = Decimal(budget_text)
            if not budget.is_finite() or budget <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            error = "Enter a valid budget greater than ₹0."
        else:
            phones = (
                Phone.objects.filter(is_active=True)
                .prefetch_related(
                    "variants__processor",
                    "variants__performance_tests__source",
                )
                .order_by("brand", "model_name")
            )

            for phone in phones:
                if not is_smartphone_model(phone.model_name):
                    continue

                reference_price = get_reference_price(phone)

                if reference_price is None or reference_price > budget:
                    continue

                item = get_recommendation_data(phone, reference_price)
                item["priority"] = selected_priority
                recommendations.append(item)

            recommendations = rank_recommendations(
                recommendations,
                selected_priority,
            )

            if not recommendations:
                error = (
                    "No phones with recorded launch-price references "
                    "fit this budget yet. Try a higher budget."
                )

    return render(
        request,
        "phones/suggest_me.html",
        {
            "recommendations": recommendations,
            "error": error,
            "budget": budget_text,
            "priorities": PRIORITIES,
            "selected_priority": selected_priority,
        },
    )
