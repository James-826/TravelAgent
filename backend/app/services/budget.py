from decimal import Decimal

from app.models.travel import BudgetBreakdown, DayTrip, Hotel


def calculate_budget(days: list[DayTrip], hotels: list[Hotel], travelers: int) -> BudgetBreakdown:
    attraction_total = sum(
        (attraction.ticket_price for day in days for attraction in day.attractions),
        start=Decimal("0"),
    ) * travelers
    meal_total = sum((meal.price_per_person for day in days for meal in day.meals), start=Decimal("0")) * travelers
    hotel_total = sum((hotel.price_per_night for hotel in hotels), start=Decimal("0"))
    transport_total = Decimal("80") * Decimal(len(days)) * Decimal(travelers)
    subtotal = attraction_total + meal_total + hotel_total + transport_total
    buffer_total = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))

    return BudgetBreakdown(
        attraction_total=attraction_total.quantize(Decimal("0.01")),
        meal_total=meal_total.quantize(Decimal("0.01")),
        hotel_total=hotel_total.quantize(Decimal("0.01")),
        transport_total=transport_total.quantize(Decimal("0.01")),
        buffer_total=buffer_total,
    )

