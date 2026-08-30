"""Initial dashboard placeholder. Keep all calculations in src/promoguard."""

try:
    import streamlit as st
except ImportError:  # pragma: no cover - allows the API scaffold to run without dashboard extras
    st = None


if st is not None:
    st.set_page_config(page_title="PromoGuard", layout="wide")
    st.title("PromoGuard")
    st.caption("Reliable promotion-effect analysis — scaffold")
    st.info("Next vertical slice: upload sales and promotion CSV files.")
else:
    print("Install dashboard extras with: python -m pip install -e '.[dashboard]'")

