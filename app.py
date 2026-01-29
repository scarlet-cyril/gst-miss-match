import re
import streamlit as st
from PIL import Image
import pytesseract

st.set_page_config(page_title="GST ITC Mismatch", layout="centered")

st.title("Snap Invoice → Instant ITC Mismatch")
st.write("Upload supplier and buyer invoices to detect mismatch")

# ---------- Helpers ----------
def clean_text(t: str) -> str:
    return " ".join(t.replace("\n", " ").split())

def find_gstin(t: str):
    m = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", t)
    return m.group(0) if m else ""

def find_invoice_no(t: str):
    patterns = [
        r"\bINV[- ]?\d+\b",
        r"Invoice\s*No\.?\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        r"Inv\.?\s*No\.?\s*[:\-]?\s*([A-Z0-9\-\/]+)",
    ]
    for p in patterns:
        m = re.search(p, t, re.IGNORECASE)
        if m:
            return m.group(1) if m.groups() else m.group(0)
    return ""

def find_total_tax(t: str):
    m = re.search(
        r"(Total\s*Tax|GST\s*Total|Tax\s*Total)\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d{1,2})?)",
        t,
        re.IGNORECASE,
    )
    if m:
        return m.group(2).replace(",", "")
    return ""

def to_number(x: str):
    try:
        x = str(x).replace("₹", "").replace(",", "").strip()
        if x == "":
            return None
        return float(x)
    except:
        return None

def ocr_image(file):
    img = Image.open(file)
    text = pytesseract.image_to_string(img)
    return clean_text(text)

# ---------- Uploads ----------
st.subheader("Supplier Invoice")
supplier_file = st.file_uploader(
    "Upload supplier invoice (GSTR-1 side)",
    type=["png", "jpg", "jpeg"],
    key="supplier"
)

st.subheader("Buyer Invoice")
buyer_file = st.file_uploader(
    "Upload buyer invoice (GSTR-2B side)",
    type=["png", "jpg", "jpeg"],
    key="buyer"
)

st.divider()

# ---------- Action ----------
if st.button("Find ITC Mismatch"):
    if not supplier_file or not buyer_file:
        st.error("Please upload BOTH invoices.")
        st.stop()

    st.success("Invoices uploaded ✅")

    # OCR both invoices
    sup_text = ocr_image(supplier_file)
    buy_text = ocr_image(buyer_file)

    # Auto-extract (may be blank)
    sup_gstin_guess = find_gstin(sup_text)
    buy_gstin_guess = find_gstin(buy_text)

    sup_inv_guess = find_invoice_no(sup_text)
    buy_inv_guess = find_invoice_no(buy_text)

    sup_tax_guess = find_total_tax(sup_text)
    buy_tax_guess = find_total_tax(buy_text)

    st.write("### Confirm / Edit extracted values (important)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Supplier Extracted")
        sup_gstin = st.text_input("Supplier GSTIN", value=sup_gstin_guess)
        sup_inv = st.text_input("Supplier Invoice No", value=sup_inv_guess)
        sup_tax = st.text_input("Supplier Tax Total (₹)", value=sup_tax_guess)

    with col2:
        st.subheader("Buyer Extracted")
        buy_gstin = st.text_input("Buyer GSTIN", value=buy_gstin_guess)
        buy_inv = st.text_input("Buyer Invoice No", value=buy_inv_guess)
        buy_tax = st.text_input("Buyer Tax Total (₹)", value=buy_tax_guess)

    st.divider()

    if st.button("Confirm & Compare"):
        # Basic validations
        if sup_gstin and len(sup_gstin) != 15:
            st.warning("Supplier GSTIN looks wrong (must be 15 characters). Please correct.")
            st.stop()
        if buy_gstin and len(buy_gstin) != 15:
            st.warning("Buyer GSTIN looks wrong (must be 15 characters). Please correct.")
            st.stop()

        sup_tax_num = to_number(sup_tax)
        buy_tax_num = to_number(buy_tax)

        if sup_tax_num is None or buy_tax_num is None:
            st.error("Please enter valid numbers for both Tax Totals (example: 17100).")
            st.stop()

        diff = abs(buy_tax_num - sup_tax_num)

        # Show comparison result
        st.subheader("Result")

        if diff == 0:
            st.success("✅ No mismatch: Tax totals match exactly.")
        else:
            st.error(f"🚨 ITC mismatch detected: ₹{diff:,.0f} difference")

        # Helpful details
        st.write("**Supplier Tax Total:**", f"₹{sup_tax_num:,.0f}")
        st.write("**Buyer Tax Total:**", f"₹{buy_tax_num:,.0f}")

        # Extra checks (optional but useful)
        if sup_inv and buy_inv and sup_inv.strip().lower() != buy_inv.strip().lower():
            st.warning("Invoice number mismatch between Supplier and Buyer. Check invoice number.")

        if sup_gstin and buy_gstin and sup_gstin.strip().upper() == buy_gstin.strip().upper():
            st.warning("Supplier GSTIN and Buyer GSTIN are the same. Usually they should be different.")
