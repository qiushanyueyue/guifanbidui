import pytesseract
from PIL import Image
import os
from app.models.base import SessionLocal
from app.repositories.standard_repo import StandardRepo
from app.models.schemas import SearchResult
import re

IMAGE_PATHS = [
    "/Users/qiushanyueyue/.gemini/antigravity/brain/bbaeac4e-8e60-40fe-8cdb-8d618ebc311a/uploaded_media_1_1769752662593.jpg",
    "/Users/qiushanyueyue/.gemini/antigravity/brain/bbaeac4e-8e60-40fe-8cdb-8d618ebc311a/uploaded_media_2_1769752662593.png"
]

def ocr_and_extract(image_path):
    print(f"OCR Processing {image_path}...")
    try:
        text = pytesseract.image_to_string(Image.open(image_path), lang='chi_sim+eng')
        print(f"Extracted Text:\n{text}")
        return text
    except Exception as e:
        print(f"OCR Failed: {e}")
        return None

def parse_text_to_standard(text):
    # Heuristic parsing
    code_match = re.search(r"[A-Z]{2,}\/?\s*[A-Z]?\s*\d+(?:\.\d+)?-\d{4}", text)
    # Name often comes before or after code, tricky with raw OCR
    # Let's try to pass OCR text to DeepSeek for parsing!
    return text

def parse_with_deepseek(ocr_text):
    import requests
    import json
    
    api_key = os.getenv("DEEPSEEK_API_KEY") or "sk-e78399716a1f4878ac764f6dc87b238e"
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    prompt = f"""
    Analyze the following OCR text from a standard cover. Extract:
    1. Code (e.g. GB 50016-2014)
    2. Name (e.g. 建筑设计防火规范)
    
    OCR Text:
    {ocr_text}
    
    Return JSON: {{"code": "...", "name": "..."}}
    """
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        content = resp.json()['choices'][0]['message']['content']
        content = content.replace('```json', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        print(f"DeepSeek Parse Failed: {e}")
        return None

def main():
    db = SessionLocal()
    for img in IMAGE_PATHS:
        if not os.path.exists(img): continue
        text = ocr_and_extract(img)
        if text:
            data = parse_with_deepseek(text)
            if data and data.get('code'):
                print(f"Parsed: {data}")
                year_match = re.search(r"-(\d{4})", data['code'])
                year = year_match.group(1) if year_match else None
                
                sr = SearchResult(
                    code=data['code'], 
                    name=data['name'], 
                    status="现行", 
                    url="", 
                    source="ocr_deepseek"
                )
                StandardRepo.create_or_update(db, sr, year)
                print("Saved to DB")
            else:
                print("Failed to parse OCR text")
        else:
            print("No OCR text")
    db.close()

if __name__ == "__main__":
    main()
