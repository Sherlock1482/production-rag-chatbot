import os

# Disable oneDNN
os.environ["FLAGS_use_mkldnn"] = "0"

from paddleocr import PaddleOCR


ocr = PaddleOCR(
    lang="en"
)


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from an image using PaddleOCR.
    """
    result = ocr.predict(image_path)

    extracted_text = []

    for page in result:
        if "rec_texts" in page:
            extracted_text.extend(page["rec_texts"])

    return "\n".join(extracted_text)