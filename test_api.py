import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AMBIGUOUS_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

CHANNEL_ID = "e7f59238-5029-45d4-9ce5-cfb67f7aa3aa"

url = f"https://app.ambiguous.ai/api/channels/{CHANNEL_ID}/messages"

response = requests.get(url, headers=headers)

print("STATUS:", response.status_code)
print("RESPONSE:", response.text)