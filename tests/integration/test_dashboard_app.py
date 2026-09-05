from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[2] / "apps" / "dashboard" / "app.py"


def test_dashboard_initial_render_has_no_uncaught_exception() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()

    assert not app.exception
    assert {radio.label for radio in app.radio} == {"حالت اجرا", "منبع داده"}
    assert any(button.label == "بارگذاری و کنترل کیفیت" for button in app.button)
