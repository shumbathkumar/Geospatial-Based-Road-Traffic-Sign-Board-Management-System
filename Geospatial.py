import json
import requests
import os
import numpy as np
import tensorflow as tf
import csv
import cv2
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from datetime import datetime

# Configurations
PROJECT_SLUG = "traffic-signboard-database"
API_TOKEN = ""  # Optional: put your token here if required
OUTPUT_FOLDER = "docs/data/images"
CROPPED_FOLDER = "docs/data/cropped_32x32"
ENTRIES_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json"
MEDIA_BASE_URL = "https://five.epicollect.net/api/media/"
MODEL_PATH = 'model.h5'
CLASS_MAPPING_CSV = 'traffic_sign.csv'
GEOJSON_OUTPUT_PATH = "docs/data/predictions.geojson"

# Create output folders if not exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CROPPED_FOLDER, exist_ok=True)

# Load model
model = load_model(MODEL_PATH)
print("✅ Model loaded successfully.")

# Load class mapping
class_mapping = {}
def load_class_mapping(file_path):
    global class_mapping
    with open(file_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            class_mapping[int(row['ClassId'])] = row['Name']
    print("✅ Class mapping loaded successfully.")

load_class_mapping(CLASS_MAPPING_CSV)

def get_class_name(class_no):
    return class_mapping.get(class_no, "Unknown Class")

# Red-border sign detection, shape masking, and preprocessing
def extract_sign(img_path):
    img = cv2.imread(img_path)
    orig = img.copy()
    if img is None:
        print(f"❌ Failed to load image at {img_path}")
        return None

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Red color masks (for red-bordered signs)
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    red_mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1),
                              cv2.inRange(hsv, lower_red2, upper_red2))

    # Blue color mask (for blue signs like parking)
    lower_blue = np.array([100, 100, 50])
    upper_blue = np.array([140, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Combine red and blue masks
    combined_mask = cv2.bitwise_or(red_mask, blue_mask)

    # Clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print("⚠️ No red or blue contour found.")
        return None

    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    cropped = orig[y:y+h, x:x+w]

    # Save cropped image
    cropped_path = os.path.join(CROPPED_FOLDER, os.path.basename(img_path))
    cv2.imwrite(cropped_path, cropped)

    resized = cv2.resize(cropped, (32, 32))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    normalized = equalized / 255.0

    return normalized.reshape(1, 32, 32, 1)

def model_predict(img_path, model):
    img = extract_sign(img_path)
    if img is None:
        return -1, "Detection Failed"
    predictions = model.predict(img)
    classIndex = int(np.argmax(predictions, axis=1)[0])
    return classIndex, get_class_name(classIndex)

# Download all entries with pagination
headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
all_entries = []
next_url = ENTRIES_URL

print("🔁 Fetching entries with pagination...")
while next_url:
    print(f"➡️  Fetching: {next_url}")
    response = requests.get(next_url, headers=headers)
    data = response.json()
    if "data" in data and "entries" in data["data"]:
        all_entries.extend(data["data"]["entries"])
        next_url = data.get("links", {}).get("next")
    else:
        print("⚠️  Unexpected format or no entries found.")
        break

# Save raw JSON
with open(f"{OUTPUT_FOLDER}/epicollect.json", "w") as f:
    json.dump(all_entries, f)

print(f"📦 Total entries fetched: {len(all_entries)}")

geojson_features = []

for entry in all_entries:
    image_field = "1_Signboard_Image"
    if image_field in entry and entry[image_field]:
        image_filename = entry[image_field].split("=")[-1]
        image_url = f"{MEDIA_BASE_URL}{PROJECT_SLUG}?type=photo&format=entry_original&name={image_filename}"

        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            image_path = os.path.join(OUTPUT_FOLDER, image_filename)
            with open(image_path, "wb") as file:
                file.write(img_response.content)
            print(f"✅ Downloaded: {image_filename}")

            class_index, prediction = model_predict(image_path, model)
            print(f"🧠 Predicted Class: {prediction} (Index: {class_index})")

            coordinates_data = entry.get("3_Coordinates", {})
            latitude = coordinates_data.get("latitude")
            longitude = coordinates_data.get("longitude")
            coordinates = [longitude, latitude] if latitude and longitude else [None, None]
            timestamp = entry.get("created_at", "Unknown Time")

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coordinates
                },
                "properties": {
                    "image_name": image_filename,
                    "predicted_class": prediction,
                    "class_index": class_index,
                    "timestamp": timestamp
                }
            }
            geojson_features.append(feature)
        else:
            print(f"❌ Failed to download: {image_filename}")

# Save GeoJSON
geojson_data = {
    "type": "FeatureCollection",
    "features": geojson_features
}
with open(GEOJSON_OUTPUT_PATH, "w") as f:
    json.dump(geojson_data, f, indent=4)

print(f"🌍 GeoJSON saved to {GEOJSON_OUTPUT_PATH}")
