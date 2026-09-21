from utils.image_processor import extract_text_from_image


image_path = "data/uploads/img1.png"

text = extract_text_from_image(image_path)

print("\n===== EXTRACTED TEXT =====")
print(text)