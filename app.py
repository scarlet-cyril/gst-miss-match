import re
import streamlit as st
from PIL import Image
import pytesseract

st.set_page_config(page_title="GST ITC Mismatch", layout="centered")

st.title("Snap Invoice → Instant ITC Mismatch")
st.write("Upload supplier and buyer invoices to detect mismatch")

def clean_text(t: str) -> str:
    # make OCR text easier to search
    return " ".join(t.replace("\n", " ").split())

def find_gstin(t: str):
    # GSTIN format: 15 characters
    m = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", t)
    return m.group(0) if m else ""

def find_invoice_no(t: str):
    # looks for common patterns like INV-001, INV001, Invoice No: ...
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
    # tries to find something like "Total Tax 17,100" or "GST 17,100"
    m = re.search(r"(Total\s*Tax|GST\s*Total|Tax\s*Total)\s*[:\-]?\s*₹?\s*([\d,]+\.\d{0,2}|\d{1,3}(?:,\d{3})+|\d+)", t, re.IGNORECASE)
    if m:
        return m.group(2).replace(",", "")
    return ""

def ocr_image(file):
    img = Image.open(file)
    text = pytesseract.image_to_string(img)
    return clean_text(text)

# Uploads
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

if st.button("Find ITC Mismatch"):
    if not supplier_file or not buyer_file:
        st.error("Please upload BOTH invoices.")
    else:
        st.success("Invoices uploaded ✅")

        # OCR both
        sup_text = ocr_image(supplier_file)
        buy_text = ocr_image(buyer_file)

        # Extract fields
        sup_gstin = find_gstin(sup_text)
        buy_gstin = find_gstin(buy_text)

        sup_inv = find_invoice_no(sup_text)
        buy_inv = find_invoice_no(buy_text)

        sup_tax = find_total_tax(sup_text)
        buy_tax = find_total_tax(buy_text)

        # Show extracted (simple)
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Supplier Extracted")
            st.write("GSTIN:", sup_gstin or "Not found")
            st.write("Invoice No:", sup_inv or "Not found")
            st.write("Tax Total:", sup_tax or "Not found")

        with col2:
            st.subheader("Buyer Extracted")
            st.write("GSTIN:", buy_gstin or "Not found")
            st.write("Invoice No:", buy_inv or "Not found")
            st.write("Tax Total:", buy_tax or "Not found")

        st.caption("Next step: add ‘Edit’ boxes so you can fix OCR mistakes, then we compare and show mismatch.")
