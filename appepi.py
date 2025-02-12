import json
import requests
import os
import numpy as np
import tensorflow as tf
import csv
import cv2
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# Epicollect Project Configuration
PROJECT_SLUG = "my-gis-project-12"
API_TOKEN = "your_api_token"  # Replace with actual token if needed
OUTPUT_FOLDER = "downloaded_images"

# Epicollect API URLs
ENTRIES_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json"
MEDIA_BASE_URL = "https://five.epicollect.net/api/media/"

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load trained model
MODEL_PATH = 'model.h5'
model = load_model(MODEL_PATH)
print("Model loaded successfully.")

# Load class mapping
class_mapping = {}


def load_class_mapping(file_path):
    global class_mapping
    with open(file_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            class_mapping[int(row['ClassId'])] = row['Name']
    print("Class mapping loaded successfully.")


load_class_mapping('traffic_sign.csv')


def get_class_name(class_no):
    return class_mapping.get(class_no, "Unknown Class")


def preprocessing(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.equalizeHist(img)
    img = img / 255.0  # Normalize pixel values
    return img


def model_predict(img_path, model):
    img = image.load_img(img_path, target_size=(224, 224))
    img = np.asarray(img)
    img = cv2.resize(img, (32, 32))
    img = preprocessing(img)
    img = img.reshape(1, 32, 32, 1)
    predictions = model.predict(img)
    classIndex = int(np.argmax(predictions, axis=1)[0])  # Convert to standard Python int
    return classIndex, get_class_name(classIndex)


# Fetch entries from Epicollect
headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
response = requests.get(ENTRIES_URL, headers=headers)
data = response.json()

# Save JSON response for reference
with open(f"{OUTPUT_FOLDER}/epicollect.json", "w") as f:
    json.dump(data, f)

geojson_features = []

if "data" in data and "entries" in data["data"]:
    entries = data["data"]["entries"]
    print(f"Found {len(entries)} entries.")

    for entry in entries:
        image_field = "1_Sign_board_pic"
        if image_field in entry and entry[image_field]:
            image_filename = entry[image_field].split("=")[-1]
            image_url = f"{MEDIA_BASE_URL}{PROJECT_SLUG}?type=photo&format=entry_original&name={image_filename}"

            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                image_path = os.path.join(OUTPUT_FOLDER, image_filename)
                with open(image_path, "wb") as file:
                    file.write(img_response.content)
                print(f"Downloaded: {image_filename}")

                # Predict class
                class_index, prediction = model_predict(image_path, model)
                print(f"Predicted Class for {image_filename}: {prediction} (Index: {class_index})")

                # Extract coordinates and timestamp
                coordinates_data = entry.get("2_Coordinates", {})
                latitude = coordinates_data.get("latitude")
                longitude = coordinates_data.get("longitude")
                coordinates = [longitude, latitude] if latitude and longitude else [None, None]
                timestamp = entry.get("created_at", "Unknown Time")

                # Create GeoJSON feature
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
                print(f"Failed to download {image_filename}")

    # Save as GeoJSON
    geojson_data = {
        "type": "FeatureCollection",
        "features": geojson_features
    }
    with open("predictions.geojson", "w") as f:
        json.dump(geojson_data, f, indent=4)
else:
    print("No entries found or incorrect JSON format.")
