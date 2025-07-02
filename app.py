import streamlit as st
import requests
import time
from fpdf import FPDF
import io
from PIL import Image
import os

# === 🔑 Replace these with your Azure OCR credentials ==
subscription_key = os.getenv("AZURE_KEY")

endpoint = os.getenv("AZURE_ENDPOINT")

# === 🎨 Unicode-capable PDF class ===
class UnicodePDF(FPDF):
    def __init__(self):
        super().__init__()
        font_path = "DejaVuSans.ttf"

        if not os.path.exists(font_path):
            st.error(f"⚠️ Font not found: {font_path}")
            st.stop()
        self.add_font("DejaVu", "", font_path, uni=True)
        self.set_font("DejaVu", "", 12)
        self.set_auto_page_break(auto=True, margin=15)

# === 🚀 Streamlit App ===
st.set_page_config(page_title="Handwritten OCR to PDF", layout="centered")
st.title("📝 Convert Handwritten Text to PDF using Azure OCR")

uploaded_files = st.file_uploader(
    "Upload one or more handwritten/printed images (JPEG/PNG/PDF, < 4MB each):",
    type=["jpg", "jpeg", "png", "pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.divider()
        st.subheader(f"📄 {uploaded_file.name}")

        image_bytes = uploaded_file.read()

        if len(image_bytes) > 4 * 1024 * 1024:
            st.error("❌ Image too large (must be < 4MB). Please resize and try again.")
            continue

        # Show preview (if image)
        if uploaded_file.type != "application/pdf":
            st.image(uploaded_file, use_column_width=True)

        # === 🧠 Azure OCR ===
        headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "Content-Type": "application/octet-stream"
        }

        with st.spinner("🧠 Processing with Azure OCR..."):
            try:
                response = requests.post(endpoint, headers=headers, data=image_bytes)
                if response.status_code != 202:
                    st.error(f"❌ Azure error: {response.status_code}")
                    st.text(response.text)
                    continue

                operation_url = response.headers.get("Operation-Location")
                if not operation_url:
                    st.error("❌ No Operation-Location found.")
                    continue

                # Poll result
                for _ in range(20):
                    result = requests.get(operation_url, headers=headers).json()
                    if result.get("status") == "succeeded":
                        break
                    elif result.get("status") == "failed":
                        st.error("❌ Azure OCR failed.")
                        break
                    time.sleep(2)
                else:
                    st.warning("⚠️ Azure OCR timed out.")
                    continue

                # Extract text
                lines = []
                for page in result["analyzeResult"]["readResults"]:
                    for line in page["lines"]:
                        lines.append(line["text"])
                extracted_text = "\n".join(lines)

                st.success("✅ Text Extracted:")
                st.text(extracted_text)

                # === 📝 Create PDF ===
                pdf = UnicodePDF()
                pdf.add_page()
                pdf.set_font("DejaVu", size=14)
                pdf.cell(0, 10, uploaded_file.name, ln=True)
                pdf.set_font("DejaVu", size=12)
                pdf.multi_cell(0, 10, extracted_text)

                pdf_buffer = io.BytesIO()
                pdf.output(pdf_buffer)
                pdf_buffer.seek(0)

                st.download_button(
                    label=f"📥 Download PDF for {uploaded_file.name}",
                    data=pdf_buffer,
                    file_name=f"{uploaded_file.name}_ocr.pdf",
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
