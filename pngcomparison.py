from itertools import combinations
import os
import cv2
from networkx import sigma
from skimage.metrics import structural_similarity as ssim
from skimage.color import rgb2gray
import numpy as np

def main():
    folder_path = "C:\\temp\\InvoiceTemplateTestPngs"

    id_to_files = {}

    for filename in os.listdir(folder_path):
        if filename.endswith('png'):
            parts = filename.split('-')
            if len(parts) < 3:
                continue
            file_id = parts[0]
            if file_id not in id_to_files:
                id_to_files[file_id] = []
            id_to_files[file_id].append(filename)


    with open("ssim_scores.txt", "w") as f:
        f.write("PairName,diff\n")
        for group_id, filenames in id_to_files.items():
            for pair in combinations(filenames, 2):
                img1_name = pair[0]
                img2_name = pair[1]

                img1_path = os.path.join(folder_path, img1_name)
                img2_path = os.path.join(folder_path, img2_name)

                try:
                    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
                    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)

                    height = min(img1.shape[0], img2.shape[0])
                    width = min(img1.shape[1], img2.shape[1])

                    # resize both images to the smallest dimensions
                    img1 = cv2.resize(img1, (width, height), interpolation=cv2.INTER_AREA)
                    img2 = cv2.resize(img2, (width, height), interpolation=cv2.INTER_AREA)
                    
                    img1 = cv2.GaussianBlur(img1, (5, 5), 0)
                    img2 = cv2.GaussianBlur(img2, (5, 5), 0)

                    if img1 is None or img2 is None:
                        continue

                    # s = structural_similarity(img1, img2, multichannel=True, gaussian_weights=True, sigma=1.5, use_sample_covariance=False, data_range=255)
                    
                    score, diff = ssim(img1, img2, full=True)
                    diff = (diff * 255).astype("uint8")  # scale the diff image for visualization


                    f.write(f"{img1_name} {img2_name},{score:.4f}\n")
                except Exception as e:
                    print(f"Error processing images {img1_name} and {img2_name}: {str(e)}")
                    continue

if __name__ == "__main__":
    main()
