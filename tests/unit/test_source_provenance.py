from apps.api.main import _source_notes


def test_week_index_benchmark_explains_synthetic_calendar_and_aggregation() -> None:
    notes = _source_notes("week-index-not-real-dates_complete-journey_product-908846.csv")

    assert len(notes) == 2
    assert "تاریخ واقعی نیستند" in notes[0]
    assert "همهٔ فروشگاه‌ها" in notes[1]
    assert "اثر علّی" not in " ".join(notes)


def test_customer_files_do_not_receive_benchmark_specific_warning() -> None:
    assert _source_notes("customer-sales.csv") == []
