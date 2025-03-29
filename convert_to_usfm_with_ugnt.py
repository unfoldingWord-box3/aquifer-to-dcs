#!/usr/bin/env python3
# /Users/richmahn/repos/aquifer-to-dcs/convert_to_usfm_with_ugnt.py

import json
import csv
import os
import sys

def usfm_escape(text):
    """
    Escape special characters for USFM compatibility.
    Handles backslashes and other special characters.
    """
    # Replace backslash with double backslash if needed
    text = text.replace('\\', '\\\\')
    # Add other escape sequences as needed
    
    return text

def load_greek_mapping(csv_path):
    """
    Load mapping between SBLGNT and UGNT Greek from CSV.
    If either column is empty, use the Greek column value.
    """
    mapping = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sblgnt = row.get('SBLGNT:Greek', '') or row.get('Greek', '')
                ugnt = row.get('UGNT:Greek', '') or row.get('Greek', '')
                if sblgnt:
                    mapping[sblgnt] = ugnt
        
        if not mapping:
            print(f"Warning: No Greek mappings found in {csv_path}")
    except Exception as e:
        print(f"Error loading Greek mapping: {e}")
        sys.exit(1)
    
    return mapping

def process_aligned_json(json_path, greek_mapping):
    """Process JSON and convert SBLGNT Greek to UGNT Greek."""
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Print structure to debug
        if not data.get('chapters'):
            print("Warning: No 'chapters' found in JSON data")
            print(f"JSON keys: {data.keys()}")
            return data
        
        for chapter in data['chapters']:
            if not chapter.get('verses'):
                print(f"Warning: No verses found in chapter {chapter.get('number', 'unknown')}")
                continue
                
            for verse in chapter['verses']:
                # Handle different possible structures
                
                # Case 1: If there are alignments
                if 'alignments' in verse:
                    for alignment in verse['alignments']:
                        if 'sourceNgram' in alignment:
                            for token in alignment['sourceNgram']:
                                if token['text'] in greek_mapping:
                                    token['text'] = greek_mapping[token['text']]
                
                # Case 2: If there's direct Greek text in the verse
                if 'greek' in verse:
                    words = verse['greek'].split()
                    converted_words = []
                    for word in words:
                        converted_words.append(greek_mapping.get(word, word))
                    verse['greek'] = ' '.join(converted_words)
                
                # Case 3: If there are tokens directly in the verse
                if 'tokens' in verse:
                    for token in verse['tokens']:
                        if 'text' in token and token['text'] in greek_mapping:
                            token['text'] = greek_mapping[token['text']]
        
        return data
    
    except Exception as e:
        print(f"Error processing JSON: {e}")
        sys.exit(1)

def generate_usfm(data):
    """Generate USFM content from processed data."""
    usfm_lines = [
        "\\id ACT Unlocked Greek New Testament",
        "\\ide UTF-8",
        "\\h Acts",
        "\\toc1 The Acts of the Apostles",
        "\\toc2 Acts",
        "\\toc3 Act",
        "\\mt1 Acts"
    ]
    
    for chapter in data.get('chapters', []):
        chapter_num = chapter.get('number', '?')
        usfm_lines.append(f"\\c {chapter_num}")
        
        for verse in chapter.get('verses', []):
            verse_num = verse.get('number', '?')
            verse_text = ""
            
            # Try different ways to get the Greek text
            
            # Method 1: From alignments
            if 'alignments' in verse:
                for alignment in verse['alignments']:
                    source_tokens = alignment.get('sourceNgram', [])
                    source_text = " ".join([token.get('text', '') for token in source_tokens])
                    if source_text.strip():
                        verse_text += source_text + " "
            
            # Method 2: Direct Greek text
            elif 'greek' in verse:
                verse_text += verse['greek'] + " "
            
            # Method 3: From tokens
            elif 'tokens' in verse:
                for token in verse['tokens']:
                    verse_text += token.get('text', '') + " "
            
            # Method 4: Direct text field
            elif 'text' in verse:
                verse_text += verse['text'] + " "
            
            # If we still have no verse text, try a fallback method or warn
            if not verse_text.strip():
                print(f"Warning: No Greek text found for chapter {chapter_num}, verse {verse_num}")
                verse_text = "[No Greek text found]"
            
            usfm_lines.append(f"\\v {verse_num} {usfm_escape(verse_text.strip())}")
    
    return "\n".join(usfm_lines)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'bsb_act_greek.json')
    csv_path = os.path.join(script_dir, 'greek_mini.csv')
    output_path = os.path.join(script_dir, 'generated_acts_ugnt_aligned.usfm')
    
    # Verify input files exist
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        sys.exit(1)
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    # Load the Greek mapping
    print(f"Loading Greek mapping from {csv_path}...")
    greek_mapping = load_greek_mapping(csv_path)
    print(f"Loaded {len(greek_mapping)} Greek mappings")
    
    # Process the JSON file with the mapping
    print(f"Processing JSON data from {json_path}...")
    processed_data = process_aligned_json(json_path, greek_mapping)
    
    # Generate the USFM content
    print("Generating USFM content...")
    usfm_content = generate_usfm(processed_data)
    
    # Write to output file
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(usfm_content)
    
    print(f"Successfully generated UGNT-aligned USFM at {output_path}")

if __name__ == "__main__":
    main()