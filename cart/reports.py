from calendar import month_abbr
from dataclasses import dataclass
from datetime import date

from catalog.models import Product

from .models import Rental, local_rental_date
from .catalog import daily_rent


def format_rupiah(amount):
    return "Rp " + f"{int(amount):,}".replace(",", ".")


@dataclass
class MonthlyBar:
    label: str
    amount: int
    percent: int = 0

    @property
    def amount_display(self):
        return format_rupiah(self.amount)


@dataclass
class TopItem:
    name: str
    rentals: int


@dataclass
class RecentRental:
    item: str
    renter: str
    date: date
    status: str
    amount: int

    @property
    def amount_display(self):
        return format_rupiah(self.amount)

    @property
    def status_slug(self):
        return self.status.lower()


@dataclass
class SellerProduct:
    id: object
    name: str
    image: str
    daily_price: int
    is_rented: bool

    @property
    def daily_price_display(self):
        return format_rupiah(self.daily_price)


@dataclass
class SellerReport:
    products_listed: int
    active_rentals: int
    total_rentals: int
    total_earnings: int
    monthly_bars: list
    top_items: list
    recent_rentals: list
    products: list

    @property
    def total_earnings_display(self):
        return format_rupiah(self.total_earnings)

    @property
    def has_data(self):
        return bool(self.products_listed or self.total_rentals)


def _six_months(today):
    months = []
    year, month = today.year, today.month
    for _ in range(6):
        months.append((year, month))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return list(reversed(months))


def _is_active(rental, today):
    return rental.rental_date <= today < rental.rental_date.fromordinal(
        rental.rental_date.toordinal() + rental.days
    )


def get_seller_report(user):
    """Build report values from products owned and completed Cart checkouts."""
    today = local_rental_date()
    rentals = list(
        Rental.objects.filter(seller_id=user.pk)
        .select_related("buyer")
        .order_by("-rental_date", "-created_at")
    )
    active_product_ids = {r.product_uuid for r in rentals if _is_active(r, today)}
    monthly = {key: 0 for key in _six_months(today)}
    by_item = {}
    active = 0

    for rental in rentals:
        key = (rental.rental_date.year, rental.rental_date.month)
        if key in monthly:
            monthly[key] += rental.total
        item = by_item.setdefault(rental.product_uuid, {"name": rental.product_name, "rentals": 0})
        item["rentals"] += 1
        if _is_active(rental, today):
            active += 1

    bars = [MonthlyBar(month_abbr[month], amount) for (_, month), amount in monthly.items()]
    peak = max((bar.amount for bar in bars), default=0)
    for bar in bars:
        bar.percent = round(bar.amount / peak * 100) if peak else 0

    top_items = sorted(
        (TopItem(value["name"], value["rentals"]) for value in by_item.values()),
        key=lambda item: (-item.rentals, item.name.lower()),
    )[:5]
    recent = [
        RecentRental(
            item=rental.product_name,
            renter=rental.buyer.get_full_name() or rental.buyer.get_username(),
            date=rental.rental_date,
            status="Active" if _is_active(rental, today) else "Returned",
            amount=rental.total,
        )
        for rental in rentals[:5]
    ]

    return SellerReport(
        products_listed=Product.objects.filter(seller_id=user.pk).count(),
        active_rentals=active,
        total_rentals=len(rentals),
        total_earnings=sum(rental.total for rental in rentals),
        monthly_bars=bars,
        top_items=top_items,
        recent_rentals=recent,
        products=[
            SellerProduct(
                id=product.pk,
                name=product.name,
                image=product.image or "",
                daily_price=daily_rent(product.price),
                is_rented=product.pk in active_product_ids,
            )
            for product in Product.objects.filter(seller_id=user.pk).order_by("name")
        ],
    )
