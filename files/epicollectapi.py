import json
import requests
import os

PROJECT_SLUG = "traffic-signboard-database"
API_TOKEN = ""
OUTPUT_FOLDER = "downloaded_images"

ENTRIES_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json"
MEDIA_BASE_URL = "https://five.epicollect.net/api/media/"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}

response = requests.get(ENTRIES_URL, headers=headers)
data = response.json()

with open(f"{OUTPUT_FOLDER}/epicollect.json", "w") as f:
    json.dump(data, f)

if "data" in data and "entries" in data["data"]:
    entries = data["data"]["entries"]
    print(f"Found {len(entries)} entries.")

    for entry in entries:
        image_field = "1_Sign_board_pic"

        if image_field in entry and entry[image_field]:
            image_filename = entry[image_field].split("=")[-1]  # Extract only the file name
            image_url = f"{MEDIA_BASE_URL}{PROJECT_SLUG}?type=photo&format=entry_original&name={image_filename}"

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
