"""scripts/show_preprocessing.py — Save each preprocessing stage as an image."""
import sys
from pathlib import Path
sys.path.insert(0, ".")

import cv2
import numpy as np
from packages.ocr.preprocess import (
    load_image, to_grayscale, deskew_image,
    remove_noise, binarize, crop_borders, _quality_score
)

src = Path("data/samples/sample_answer_sheet.png")
out = Path("data/samples/preprocessing_stages")
out.mkdir(parents=True, exist_ok=True)

print("Saving preprocessing stages to:", out)

img = load_image(src)
cv2.imwrite(str(out / "01_original.png"), img)
print(f"01_original        {img.shape}")

gray = to_grayscale(img)
cv2.imwrite(str(out / "02_grayscale.png"), gray)
print(f"02_grayscale       {gray.shape}")

deskewed, angle = deskew_image(img)
cv2.imwrite(str(out / "03_deskewed.png"), deskewed)
print(f"03_deskewed        {deskewed.shape}  rotation={angle}deg")

denoised = remove_noise(deskewed)
cv2.imwrite(str(out / "04_denoised.png"), denoised)
print(f"04_denoised        {denoised.shape}")

binary = binarize(denoised)
cv2.imwrite(str(out / "05_binarized.png"), binary)
print(f"05_binarized       {binary.shape}")

cropped = crop_borders(binary)
cv2.imwrite(str(out / "06_cropped.png"), cropped)
print(f"06_cropped         {cropped.shape}")

q = _quality_score(cropped)
print(f"Quality score:     {q:.4f}")
print("\nDone! Open data/samples/preprocessing_stages/ to view all stages.")
