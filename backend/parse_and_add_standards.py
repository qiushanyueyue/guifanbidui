import os
from dotenv import load_dotenv
from app.models.base import SessionLocal
from app.repositories.standard_repo import StandardRepo
from app.models.schemas import SearchResult
import re
from PIL import Image

# Load env from backend/.env
load_dotenv(".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

IMAGE_PATHS = [
    "/Users/qiushanyueyue/.gemini/antigravity/brain/bbaeac4e-8e60-40fe-8cdb-8d618ebc311a/uploaded_media_1_1769752662593.jpg",
    "/Users/qiushanyueyue/.gemini/antigravity/brain/bbaeac4e-8e60-40fe-8cdb-8d618ebc311a/uploaded_media_2_1769752662593.png"
]

def extract_info_from_image(image_path):
    print(f"Processing {image_path}...")
    if os.getenv("ENABLE_REMOTE_EXTRACTION", "false").lower() != "true":
        print("Remote extraction is disabled; keeping image processing local.")
        return None
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY is not configured.")
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('models/gemini-2.0-flash-lite-001')
        # Load image
        img = Image.open(image_path)
        
        prompt = """
        Please analyze this image, which is a cover or page of a Chinese Standard.
        Extract the following information:
        1. Standard Code (e.g., GB 50016-2014, DB13(J) 8330-2019)
        2. Standard Name (e.g., 建筑设计防火规范, 雄安新区地下空间消防安全技术标准)
        
        Return ONLY a JSON object with keys "code" and "name".
        Example: {"code": "GB 50016-2014", "name": "建筑设计防火规范"}
        """
        
        response = model.generate_content([prompt, img])
        text = response.text
        # Clean markdown
        text = text.replace('```json', '').replace('```', '').strip()
        import json
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def main():
    db = SessionLocal()
    try:
        for img_path in IMAGE_PATHS:
            if not os.path.exists(img_path):
                print(f"File not found: {img_path}")
                continue
                
            data = extract_info_from_image(img_path)
            if data:
                print(f"Extracted: {data}")
                code = data.get("code")
                name = data.get("name")
                
                if code and name:
                    # Clean code
                    code = code.strip()
                    name = name.strip()
                    
                    # Extract year
                    year_match = re.search(r"-(\d{4})", code)
                    year = year_match.group(1) if year_match else None
                    
                    sr = SearchResult(
                        code=code,
                        name=name,
                        status="unknown", # New legacy records require verification
                        url="", # No URL known yet
                        source="manual_image_add"
                    )
                    
                    std = StandardRepo.create_or_update(db, sr, year)
                    print(f"Successfully added/updated: {std.code} - {std.name}")
                else:
                    print("Incomplete data extracted.")
            else:
                print("Failed to extract data.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
