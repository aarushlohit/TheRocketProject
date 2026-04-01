import os
# Skip remote model host connectivity checks during startup.
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from paddleocr import PaddleOCR

ocr = PaddleOCR(use_textline_orientation=True, lang="en")

result = ocr.predict("/home/aarush/Downloads/draw.jpg")

texts = []
for page in result:
	texts.extend(page.get("rec_texts", []))

print(texts)