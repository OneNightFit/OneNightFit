
from dataclasses import dataclass, field
from datetime import date

from django.conf import settings
from django.utils import timezone


def format_rupiah(amount):
    return "Rp " + f"{int(amount):,}".replace(",", ".")


@dataclass
class MonthlyEarning:
    label: str
    amount: int = 0

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
    status: str          # "Pending" | "Active" | "Returned"
    amount: int = 0

    @property
    def amount_display(self):
        return format_rupiah(self.amount)

    @property
    def status_slug(self):
        return self.status.lower()


@dataclass
class SellerReport:
    products_listed: int = 0
    active_rentals: int = 0
    total_rentals: int = 0
    total_earnings: int = 0
    monthly_earnings: list = field(default_factory=list)
    top_items: list = field(default_factory=list)
    recent_rentals: list = field(default_factory=list)

    @property
    def total_earnings_display(self):
        return format_rupiah(self.total_earnings)

    @property
    def has_data(self):
        return bool(self.products_listed or self.total_rentals)

    @property
    def monthly_bars(self):
        """Tinggi batang chart dalam persen (0-100) relatif terhadap bulan tertinggi."""
        peak = max((m.amount for m in self.monthly_earnings), default=0)
        return [
            {
                "label": m.label,
                "amount_display": m.amount_display,
                "percent": round(m.amount / peak * 100) if peak else 0,
            }
            for m in self.monthly_earnings
        ]


def _last_months(count=6):
    today = timezone.localdate()
    months = []
    for i in range(count - 1, -1, -1):
        month, year = today.month - i, today.year
        while month <= 0:
            month += 12
            year -= 1
        months.append(date(year, month, 1))
    return months


def _empty_months():
    return [MonthlyEarning(label=d.strftime("%b")) for d in _last_months()]


def _demo_report():
    amounts = [650_000, 900_000, 1_250_000, 1_100_000, 1_800_000, 2_750_000]
    months = [MonthlyEarning(d.strftime("%b"), a) for d, a in zip(_last_months(), amounts)]
    today = timezone.localdate()
    return SellerReport(
        products_listed=12,
        active_rentals=3,
        total_rentals=47,
        total_earnings=sum(amounts),
        monthly_earnings=months,
        top_items=[
            TopItem("Black Satin Evening Dress", 14),
            TopItem("Classic Navy Blazer", 11),
            TopItem("Vintage Floral Kebaya", 9),
            TopItem("Minimalist Linen Set", 6),
        ],
        recent_rentals=[
            RecentRental("Black Satin Evening Dress", "Sample Buyer A", today, "Active", 250_000),
            RecentRental("Classic Navy Blazer", "Sample Buyer B", today, "Pending", 150_000),
            RecentRental("Vintage Floral Kebaya", "Sample Buyer C", today, "Returned", 200_000),
        ],
    )


def get_seller_report(user):
    """Kembalikan SellerReport untuk `user` (seller)."""
    if getattr(settings, "ONF_SHOP_REPORT_DEMO", False):
        return _demo_report()

    report = SellerReport(monthly_earnings=_empty_months())
    return report
