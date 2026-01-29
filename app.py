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

st.divider()

# Button
find_btn = st.button("Find ITC Mismatch")

if find_btn:
    if not supplier_file or not buyer_file:
        st.error("Please upload BOTH supplier and buyer invoices first.")
    else:
        st.success("Files received ✅")

        st.write("### Supplier file")
        st.write(supplier_file.name)

        st.write("### Buyer file")
        st.write(buyer_file.name)

        # Placeholder result (we will replace with OCR/LLM next)
        st.info("Next: Extract GSTIN / Invoice No / Tax totals using OCR (LLM) and compare.")
