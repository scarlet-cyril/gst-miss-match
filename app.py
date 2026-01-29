import streamlit as st
from PIL import Image
import pytesseract

st.set_page_config(page_title="GST ITC Mismatch", layout="centered")

st.title("Snap Invoice → Instant ITC Mismatch")
st.write("Upload supplier and buyer invoices to detect mismatch")

# Upload sections
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
        st.success("Invoices uploaded successfully ✅")

        # Read supplier invoice
        supplier_image = Image.open(supplier_file)
        supplier_text = pytesseract.image_to_string(supplier_image)

        st.subheader("Supplier Invoice - Extracted Text")
        st.text(supplier_text)
