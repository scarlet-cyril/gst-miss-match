import re
import streamlit as st
from PIL import Image
import pytesseract

st.set_page_config(page_title="GST ITC Mismatch", layout="centered")

st.title("Snap Invoice → Instant ITC Mismatch")
st.write("Upload supplier and buyer invoices to detect mismatch")

# ----------------- Helpers -----------------
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

# ----------------- Session State (THE FIX) -----------------
if "step" not in st.session_state:
    st.session_state.step = "upload"   # upload -> confirm -> result

if "sup_guess" not in st.session_state:
    st.session_state.sup_guess = {"gstin": "", "inv": "", "tax": ""}

if "buy_guess" not in st.session_state:
    st.session_state.buy_guess = {"gstin": "", "inv": "", "tax": ""}

if "result" not in st.session_state:
    st.session_state.result = None

# ----------------- Upload UI -----------------
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

# ----------------- Button: Find ITC Mismatch -----------------
# IMPORTANT: This button moves the user to the next step and stores OCR results.
if st.button("Find ITC Mismatch"):
    if not supplier_file or not buyer_file:
        st.error("Please upload BOTH invoices.")
    else:
        st.success("Invoices uploaded ✅ Reading invoices now...")

        sup_text = ocr_image(supplier_file)
        buy_text = ocr_image(buyer_file)

        st.session_state.sup_guess = {
            "gstin": find_gstin(sup_text),
            "inv": find_invoice_no(sup_text),
            "tax": find_total_tax(sup_text),
        }
        st.session_state.buy_guess = {
            "gstin": find_gstin(buy_text),
            "inv": find_invoice_no(buy_text),
            "tax": find_total_tax(buy_text),
        }

        st.session_state.step = "confirm"
        st.session_state.result = None
        st.rerun()

# ----------------- Confirm step (STAYS VISIBLE) -----------------
if st.session_state.step in ["confirm", "result"]:
    st.write("### Confirm / Edit extracted values (important)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Supplier Extracted")
        sup_gstin = st.text_input("Supplier GSTIN", value=st.session_state.sup_guess["gstin"])
        sup_inv = st.text_input("Supplier Invoice No", value=st.session_state.sup_guess["inv"])
        sup_tax = st.text_input("Supplier Tax Total (₹)", value=st.session_state.sup_guess["tax"])

    with col2:
        st.subheader("Buyer Extracted")
        buy_gstin = st.text_input("Buyer GSTIN", value=st.session_state.buy_guess["gstin"])
        buy_inv = st.text_input("Buyer Invoice No", value=st.session_state.buy_guess["inv"])
        buy_tax = st.text_input("Buyer Tax Total (₹)", value=st.session_state.buy_guess["tax"])

    st.divider()

    # Button: Confirm & Compare
    if st.button("Confirm & Compare"):
        # Basic validations
        if sup_gstin and len(sup_gstin.strip()) != 15:
            st.warning("Supplier GSTIN looks wrong (must be 15 characters). Please correct.")
            st.stop()
        if buy_gstin and len(buy_gstin.strip()) != 15:
            st.warning("Buyer GSTIN looks wrong (must be 15 characters). Please correct.")
            st.stop()

        sup_tax_num = to_number(sup_tax)
        buy_tax_num = to_number(buy_tax)

        if sup_tax_num is None or buy_tax_num is None:
            st.error("Please enter valid numbers for both Tax Totals (example: 17100).")
            st.stop()

        diff = abs(buy_tax_num - sup_tax_num)

        st.session_state.result = {
            "sup_tax": sup_tax_num,
            "buy_tax": buy_tax_num,
            "diff": diff,
            "sup_inv": sup_inv,
            "buy_inv": buy_inv,
            "sup_gstin": sup_gstin,
            "buy_gstin": buy_gstin,
        }
        st.session_state.step = "result"
        st.rerun()

# ----------------- Result step (STAYS VISIBLE) -----------------
if st.session_state.step == "result" and st.session_state.result:
    r = st.session_state.result

    st.subheader("Result")

    if r["diff"] == 0:
        st.success("✅ No mismatch: Tax totals match exactly.")
    else:
        st.error(f"🚨 ITC mismatch detected: ₹{r['diff']:,.0f} difference")

    st.write("**Supplier Tax Total:**", f"₹{r['sup_tax']:,.0f}")
    st.write("**Buyer Tax Total:**", f"₹{r['buy_tax']:,.0f}")

    if r["sup_inv"] and r["buy_inv"] and r["sup_inv"].strip().lower() != r["buy_inv"].strip().lower():
        st.warning("Invoice number mismatch between Supplier and Buyer. Check invoice number.")

    if r["sup_gstin"] and r["buy_gstin"] and r["sup_gstin"].strip().upper() == r["buy_gstin"].strip().upper():
        st.warning("Supplier GSTIN and Buyer GSTIN are the same. Usually they should be different.")

    # Optional: Reset button
    if st.button("Start New Check"):
        st.session_state.step = "upload"
        st.session_state.result = None
        st.session_state.sup_guess = {"gstin": "", "inv": "", "tax": ""}
        st.session_state.buy_guess = {"gstin": "", "inv": "", "tax": ""}
        st.rerun()
