import os
import json
import requests
import random
import string
import re
from pathlib import Path
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv('AQUIFER_API_KEY')

if not API_KEY:
    raise ValueError("API_KEY not found in .env file")

# Base URL for Aquifer API
BASE_URL = "https://api.aquifer.bible"
HEADERS = {"api-key": API_KEY}

def generate_unique_id():
    """Generate a unique 4 character ID starting with lowercase letter"""
    first_char = random.choice(string.ascii_lowercase)
    rest_chars = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))
    return first_char + rest_chars

def extract_markdown_from_tiptap(content):
    """Extract markdown from the tiptap JSON structure"""
    if not content or not isinstance(content, list):
        return ""
    
    result = []
    
    for item in content:
        if item.get("type") == "paragraph":
            paragraph_text = []
            if "content" in item and isinstance(item["content"], list):
                for text_item in item["content"]:
                    if text_item.get("type") == "text":
                        text = text_item.get("text", "")
                        marks = text_item.get("marks", [])
                        
                        for mark in marks:
                            mark_type = mark.get("type")
                            if mark_type == "bold":
                                text = f"**{text}**"
                            elif mark_type == "italic":
                                text = f"*{text}*"
                            elif mark_type == "resourceReference":
                                # Note: We'll handle resource references separately for SupportReference
                                pass
                                
                        paragraph_text.append(text)
            
            result.append("".join(paragraph_text))
    
    return "\n\n".join(result)

def extract_support_reference(paragraph):
    """Extract support reference text and ID from the paragraph"""
    if not paragraph or "content" not in paragraph:
        return ""
    
    for item in paragraph.get("content", []):
        if item.get("type") == "text" and item.get("marks"):
            for mark in item.get("marks", []):
                if mark.get("type") == "resourceReference" and "attrs" in mark:
                    resource_id = mark.get("attrs", {}).get("resourceId", "")
                    text = item.get("text", "")
                    return f"{text} [{resource_id}]"
    
    return ""

def extract_reference_from_name(book_name, resource_name):
    """Extract reference (e.g., '3:13') from resource name (e.g., 'Joel 3:13 (#1)')"""
    # Remove the book name from the resource name
    name_without_book = resource_name.replace(book_name, "").strip()
    
    # Extract the reference before any parenthesis
    match = re.match(r'([0-9]+:[0-9]+(?:-[0-9]+)?)', name_without_book)
    if match:
        return match.group(1)
    return name_without_book  # Fallback if pattern doesn't match

def process_book_notes(book_code, book_name):
    """Process all translation notes for a specific book"""
    all_items = []
    offset = 0
    limit = 100
    
    while True:
        response = requests.get(
            f"{BASE_URL}/resources/search",
            params={
                "languageId": 1,
                "resourceCollectionCode": "UWTranslationNotes",
                "bookCode": book_code,
                "startChapter": 1,
                "endChapter": 150,
                "limit": limit,
                "offset": offset
            },
            headers=HEADERS
        )
        
        # Print API request details for debugging
        request_url = f"{BASE_URL}/resources/search?languageId=1&resourceCollectionCode=UWTranslationNotes&bookCode={book_code}&startChapter=1&endChapter=150&limit={limit}&offset={offset}"
        print(f"Calling: {request_url}")

        # Handle the response
        if response.status_code != 200:
          print(f"Error response: {response.text}")
        else:
          print(f"Response status: {response.status_code}, Content length: {len(response.text)} bytes")
          # Optional: print a small excerpt of the response if needed
          # print(f"Response preview: {response.text[:200]}...")

        if response.status_code != 200:
            print(f"Error fetching resources for {book_name}: {response.status_code}")
            return []
        
        data = response.json()
        items = data.get("items", [])
        all_items.extend(items)
        
        returned_count = data.get("returnedItemCount", 0)
        total_count = data.get("totalItemCount", 0)
        
        print(f"Fetched {returned_count} of {total_count} notes for {book_name} (offset: {offset})")
        
        if offset + returned_count >= total_count:
            break
        
        offset += limit
    
    return all_items

def process_resource(resource_id, book_name):
    """Process a single resource and return a TSV line"""
    response = requests.get(
        f"{BASE_URL}/resources/{resource_id}",
        headers=HEADERS
    )
    
    if response.status_code != 200:
        print(f"Error fetching resource {resource_id}: {response.status_code}")
        return None
    
    data = response.json()
    resource_name = data.get("name", "")
    reference = extract_reference_from_name(book_name, resource_name)

    print(f"Processing resource {resource_id} ({resource_name})...")
    
    # Extract the content
    content_data = data.get("content", [])
    if not content_data or not isinstance(content_data, list) or len(content_data) == 0:
        print(f"No content found for resource {resource_id}")
        return None
    
    tiptap_data = content_data[0].get("tiptap", {})
    content_blocks = tiptap_data.get("content", [])
    
    if len(content_blocks) < 2:
        print(f"Not enough content blocks for resource {resource_id}")
        return None
    
    # Extract quote from first paragraph
    quote = ""
    if content_blocks[0].get("type") == "paragraph" and "content" in content_blocks[0]:
        quote_parts = []
        for text_item in content_blocks[0].get("content", []):
            if text_item.get("type") == "text":
                quote_text = text_item.get("text", "")
                # Strip off double quotes if they exist
                quote_text = quote_text.strip('"')
                if quote_text == " - ":
                    quote_text = " & "
                quote_parts.append(quote_text)
        quote = " ".join(quote_parts)
    
    # Extract support reference from last paragraph if it has a resource reference
    support_reference = ""
    if len(content_blocks) > 2:
        support_reference = extract_support_reference(content_blocks[-1])
    
    # Extract note content (from second paragraph up to the one before last if there are more than 2)
    note_blocks = content_blocks[1:-1] if len(content_blocks) > 2 else [content_blocks[1]]
    note = extract_markdown_from_tiptap(note_blocks)
    note = note.replace('\n', '\\n')
    
    # Generate unique ID
    unique_id = generate_unique_id()
    
    # Create TSV line
    # Reference, ID, Tags, SupportReference, Quote, Occurrence, Note
    tsv_line = f"{reference}\t{unique_id}\t{resource_id}\t{support_reference}\t{quote}\t1\t{note}"

    print(tsv_line)
    
    return tsv_line

def main():
    # Create output directory
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    
    # Get Bible books
    response = requests.get(f"{BASE_URL}/bibles/books", headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Error fetching Bible books: {response.status_code}")
        return
    
    bible_books = response.json()[:66]  # Get only the first 66 books as specified
    
    for book in bible_books:
        book_code = book.get("code")
        book_name = book.get("name")

        if book_code != "ACT":
            continue
        
        print(f"\nProcessing {book_name} ({book_code})...")
        
        # Process all notes for this book
        resources = process_book_notes(book_code, book_name)
        
        if not resources:
            print(f"No translation notes found for {book_name}")
            continue
        
        # Create TSV file for this book
        tsv_file_path = output_dir / f"{book_code}.tsv"
        
        with open(tsv_file_path, 'w', encoding='utf-8') as tsv_file:
            # Write header
            tsv_file.write("Reference\tID\tTags\tSupportReference\tQuote\tOccurrence\tNote\n")
            
            # Process each resource
            for resource in resources:
                resource_id = resource.get("id")
                tsv_line = process_resource(resource_id, book_name)
                
                if tsv_line:
                    tsv_file.write(f"{tsv_line}\n")
        
        print(f"Created {tsv_file_path} with {len(resources)} translation notes")

if __name__ == "__main__":
    main()
