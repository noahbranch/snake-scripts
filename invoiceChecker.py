import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

img1 = cv2.imread('480DOC.png')
img2 = cv2.imread('480PDF.png')

# convert the images to grayscale
img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

# apply Gaussian blur to reduce small differences
# img1 = cv2.GaussianBlur(img1, (5, 5), 0)
# img2 = cv2.GaussianBlur(img2, (5, 5), 0)

# compute SSIM between two images
score, diff = ssim(img1, img2, full=True)
diff = (diff * 255).astype("uint8")  # scale the diff image for visualization

print("SSIM score between the two images:", score)

cv2.imshow("SSIM Difference Image", diff)
cv2.waitKey(0)
cv2.destroyAllWindows()