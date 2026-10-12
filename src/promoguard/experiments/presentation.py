"""Stable Persian decision labels; presentation only, not statistical calculations."""

GOAL_LABELS = {
    "goal_supported": "به هدف تعیین‌شده رسیده",
    "goal_not_supported": "به هدف تعیین‌شده نرسیده",
    "inconclusive_vs_goal": "رسیدن به هدف هنوز روشن نیست",
    "insufficient_sample": "نمونه برای بررسی هدف کافی نیست",
    "not_set": "هدف تجاری تعیین نشده",
    "not_applicable_variant_comparison": "هدف تجاری برای مقایسهٔ مستقیم تعریف نشده",
}


def goal_label(status: str | None) -> str:
    return GOAL_LABELS.get(status or "not_set", "وضعیت هدف در این گزارش ثبت نشده")
