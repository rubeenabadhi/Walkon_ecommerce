from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader

# .env variables loading
load_dotenv()

# Cloudinary configure
cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET'),
    secure=True
)

# test.jpg upload
result = cloudinary.uploader.upload("test.jpg")  # test.jpg same folder as this script
print(result["secure_url"])
