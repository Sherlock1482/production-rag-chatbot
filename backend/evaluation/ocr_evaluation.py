import sys
from pathlib import Path

# Add backend folder to Python path
sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

from jiwer import wer
from utils.image_processor import extract_text_from_image


def evaluate_ocr(image_path: str, ground_truth: str):

    extracted_text = extract_text_from_image(image_path)

    error_rate = wer(
        ground_truth,
        extracted_text
    )

    accuracy = (1 - error_rate) * 100

    print("\n===== OCR EVALUATION =====")
    print(f"Image: {image_path}")
    print(f"WER: {error_rate:.2%}")
    print(f"Approximate OCR Accuracy: {accuracy:.2f}%")

    print("\n===== OCR OUTPUT =====")
    print(extracted_text)


if __name__ == "__main__":

    image_path = "data/uploads/2.png"

    ground_truth = """
    Sam Taylor | Backend Engineer
    sam.taylor@example.com | github.com/samtaylor
    Skills: Python, Java, Spring Boot, PostgreSQL, Docker, Redis, REST APIs
    Projects:
    Inventory Microservice: Developed a scalable inventory management backend using Spring Boot and PostgreSQL, containerized with Docker.
    URL Shortener Service: Built a high-performance redirect service in Go/Python backed by Redis for fast cache lookups and tracking.
    """

    evaluate_ocr(
        image_path,
        ground_truth
    )