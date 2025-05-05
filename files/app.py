from __future__ import division, print_function
import sys
import os
import numpy as np
import tensorflow as tf
import csv
import cv2
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from werkzeug.utils import secure_filename

OUTPUT_FOLDER = "output_stages"

# Load trained model
MODEL_PATH = '../model.h5'
try:
    model = load_model(MODEL_PATH)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit(1)


class_mapping = {}
def extract_sign(img_path):
    img = cv2.imread(img_path)
    orig = img.copy()
    basename = os.path.splitext(os.path.basename(img_path))[0]

    if img is None:
        print(f"❌ Failed to load image at {img_path}")
        return None

    # Create output folder for current image
    img_output_folder = os.path.join(OUTPUT_FOLDER, basename)
    os.makedirs(img_output_folder, exist_ok=True)

    # Save original image
    cv2.imwrite(os.path.join(img_output_folder, "original.jpg"), orig)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Red color masks
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1),
                              cv2.inRange(hsv, lower_red2, upper_red2))

    # Blue color mask
    lower_blue = np.array([100, 100, 50])
    upper_blue = np.array([140, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    combined_mask = cv2.bitwise_or(red_mask, blue_mask)

    # Save combined mask
    cv2.imwrite(os.path.join(img_output_folder, "mask.jpg"), combined_mask)

    kernel = np.ones((5, 5), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print("⚠️ No red or blue contour found.")
        return None

    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    cropped = orig[y:y+h, x:x+w]

    # Save cropped image
    cv2.imwrite(os.path.join(img_output_folder, "cropped.jpg"), cropped)

    sign_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(sign_mask, [largest_contour - [x, y]], -1, 255, thickness=cv2.FILLED)

    white_bg = np.ones_like(cropped) * 255
    sign_on_white = white_bg.copy()

    for c in range(3):
        sign_on_white[:, :, c] = np.where(sign_mask == 255, cropped[:, :, c], 255)

    # Save sign with white background
    cv2.imwrite(os.path.join(img_output_folder, "sign_on_white.jpg"), sign_on_white)

    # Resize and preprocess
    resized = cv2.resize(sign_on_white, (32, 32))



    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    final_img = (equalized * 255).astype(np.uint8)

    # Save final image
    cv2.imwrite(os.path.join(img_output_folder, "final_gray_resized.jpg"), final_img)

    # Normalize for model input
    normalized = equalized / 255.0
    return normalized.reshape(1, 32, 32, 1)


def load_class_mapping(file_path):
    """Load class labels from CSV"""
    global class_mapping
    try:
        with open(file_path, mode='r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                class_mapping[int(row['ClassId'])] = row['Name']
        print("Class mapping loaded successfully.")
    except Exception as e:
        print(f"Error loading class mapping file: {e}")
        sys.exit(1)  # Exit the script if the class mapping fails to load


def get_class_name(class_no):
    return class_mapping.get(class_no, "Unknown Class")


def model_predict(img_path, model):
    print(f"Processing image: {img_path}")

    try:
        img = extract_sign(img_path)  # Ensure PIL is installed




        predictions = model.predict(img)
        classIndex = np.argmax(predictions, axis=1)  # Fix deprecated predict_classes

        # print(f"Raw Model Predictions: {predictions}")
        print(f"Predicted Class Index: {classIndex[0]}")


        preds = get_class_name(classIndex[0])

        return preds

    except Exception as e:
        print(f"Error processing image: {e}")
        return "Error"


if __name__ == '__main__':
    load_class_mapping('../traffic_sign.csv')

    file_path = 'img.png'

    if not os.path.exists(file_path):
        print(f"Error: Image file '{file_path}' not found.")
        sys.exit(1)

    preds = model_predict(file_path, model)
    print(f"Predicted Class: {preds}")
