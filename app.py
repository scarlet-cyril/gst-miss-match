import streamlit as st

st.set_page_config(page_title="GST ITC Mismatch", layout="centered")

st.title("Snap Invoice → Instant ITC Mismatch")

st.write("Upload supplier and buyer invoices to detect mismatch")

# Upload sections
st.subheader("Supplier Invoice")
supplier_file = st.file_uploader(
    "Upload supplier invoice (GSTR-1 side)",
    type=["png", "jpg", "jpeg", "pdf"],
    key="supplier"
)

st.subheader("Buyer Invoice")
buyer_file = st.file_uploader(
    "Upload buyer invoice (GSTR-2B side)",
    type=["png", "jpg", "jpeg", "pdf"],
    key="buyer"
)

if supplier_file and buyer_file:
    st.success("Both invoices uploaded successfully ✅")
