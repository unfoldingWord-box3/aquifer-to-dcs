import os
import requests
import json
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("AQUIFER_API_KEY")

# Base API URL
BASE_URL = "https://api.aquifer.bible"

# Headers for requests
headers = {
    "api-key": API_KEY
}

def get_bibles_for_english():
    """Fetch all English Bibles (LanguageCode=eng)"""
    url = f"{BASE_URL}/bibles"
    params = {
        "LanguageCode": "eng"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching Bibles: {response.status_code}")
        print(response.text)
        return None

def get_bible_id_by_name(bibles, name):
    """Find the Bible ID for a given name"""
    for bible in bibles:
        if bible["name"] == name:
            return bible["id"]
    return None

def get_bible_text(bible_id, book_code):
    """Fetch the text of a specific book from a specific Bible"""
    url = f"{BASE_URL}/bibles/{bible_id}/texts"
    params = {
        "BookCode": book_code
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching Bible text: {response.status_code}")
        print(response.text)
        return None

def convert_to_usfm(bible_data, book_code):
    """Convert Bible JSON data to USFM format"""
    usfm_lines = []
    
    # Add USFM header
    usfm_lines.append("\\id ACT Acts")
    usfm_lines.append(f"\\h {bible_data['bookName']}")
    usfm_lines.append("\\mt Acts")
    usfm_lines.append(f"\\toc1 {bible_data['bookName']}")
    usfm_lines.append(f"\\toc2 {bible_data['bookName']}")
    usfm_lines.append(f"\\toc3 {book_code}")
    
    # Add USFM header with Bible information
    usfm_lines.append(f"\\rem Bible Name: {bible_data['bibleName']}")
    usfm_lines.append(f"\\rem Bible Abbreviation: {bible_data['bibleAbbreviation']}")
    usfm_lines.append(f"\\rem Bible ID: {bible_data['bibleId']}")
    
    # Process chapters and verses
    for chapter in bible_data['chapters']:
        chapter_num = chapter['number']
        usfm_lines.append(f"\n\\c {chapter_num}")
        usfm_lines.append("\\p")
        
        for verse in chapter['verses']:
            verse_num = verse['number']
            # Skip verse 0 which is often chapter intro
            if verse_num == 0:
                continue
            verse_text = verse['text']
            usfm_lines.append(f"\\v {verse_num} {verse_text}")
    
    return "\n".join(usfm_lines)

def save_to_file(content, filename):
    """Save content to a file"""
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f"Saved to {filename}")

def main():
    # Get all English Bibles
    print("Fetching English Bibles...")
    bibles = get_bibles_for_english()
    if not bibles:
        print("Failed to retrieve Bibles")
        return
    
    print(f"Found {len(bibles)} English Bibles")
    
    # Get the ID for "unfoldingWord Literal" Bible
    target_bible_name = "unfoldingWord Literal"
    bible_id = get_bible_id_by_name(bibles, target_bible_name)
    if not bible_id:
        print(f"Could not find Bible with name: {target_bible_name}")
        # List available Bibles to help the user
        print("Available Bible names:")
        for bible in bibles:
            print(f"- {bible['name']}")
        return
    
    print(f"Found Bible ID {bible_id} for {target_bible_name}")
    
    # Get the book of Acts (ACT)
    book_code = "ACT"
    print(f"Fetching the book of {book_code} from Bible ID {bible_id}...")
    bible_data = get_bible_text(bible_id, book_code)
    if not bible_data:
        print("Failed to retrieve Bible text")
        return
    
    print("Converting to USFM format...")
    usfm_content = convert_to_usfm(bible_data, book_code)
    
    # Save to file
    output_filename = "45-ACT.usfm"
    save_to_file(usfm_content, output_filename)

if __name__ == "__main__":
    main()
