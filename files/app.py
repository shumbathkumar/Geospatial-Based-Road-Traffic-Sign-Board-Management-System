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

# Load trained model
MODEL_PATH = '../model.h5'
try:
    model = load_model(MODEL_PATH)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit(1)


class_mapping = {}


def grayscale(img):
    """Convert image to grayscale"""
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def equalize(img):
    """Apply histogram equalization"""
    return cv2.equalizeHist(img)


def preprocessing(img):
    """Preprocess image (grayscale, histogram equalization, normalization)"""
    img = grayscale(img)
    img = equalize(img)
    img = img / 255.0  # Normalize pixel values
    return img


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
        img = image.load_img(img_path, target_size=(224, 224))  # Ensure PIL is installed
        img = np.asarray(img)
        img = cv2.resize(img, (32, 32))  # Resize for the model
        img = preprocessing(img)

        cv2.imwrite("processed_image.png", (img * 255).astype(np.uint8))
        print("Processed image saved as 'processed_image.png'")

        img = img.reshape(1, 32, 32, 1)

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
