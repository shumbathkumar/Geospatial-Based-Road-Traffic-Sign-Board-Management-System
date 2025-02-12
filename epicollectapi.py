import json

import requests
import os

# Replace with your project slug
PROJECT_SLUG = "my-gis-project-12"
API_TOKEN = "your_api_token"  # If project is private, add your token
OUTPUT_FOLDER = "downloaded_images"

# Epicollect API URLs
ENTRIES_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json"
MEDIA_BASE_URL = "https://five.epicollect.net/api/media/"

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Headers for private projects
headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}

# Fetch entries
response = requests.get(ENTRIES_URL, headers=headers)
data = response.json()

with open(f"{OUTPUT_FOLDER}/epicollect.json", "w") as f:
    json.dump(data, f)

# Check if the response contains data
if "data" in data and "entries" in data["data"]:
    entries = data["data"]["entries"]
    print(f"Found {len(entries)} entries.")

    for entry in entries:
        # Extract image field (Modify this key if necessary)
        image_field = "1_Sign_board_pic"  # This comes from the `map_to` field in your JSON

        if image_field in entry and entry[image_field]:
            image_filename = entry[image_field].split("=")[-1]  # Extract only the file name
            image_url = f"{MEDIA_BASE_URL}{PROJECT_SLUG}?type=photo&format=entry_original&name={image_filename}"

            # Download image
            img_response = requests.get(image_url)

            if img_response.status_code == 200:
                image_path = os.path.join(OUTPUT_FOLDER, image_filename)
                with open(image_path, "wb") as file:
                    file.write(img_response.content)
                print(f"Downloaded: {image_filename}")
            else:
                print(f"Failed to download {image_filename}")

else:
    print("No entries found or incorrect JSON format.")
