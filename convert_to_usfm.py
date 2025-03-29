#!/usr/bin/env python3
import json
import datetime
import os

def read_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def generate_usfm_header():
    """Generate the USFM header for Acts"""
    current_date = datetime.datetime.now().strftime("%a %b %d %Y %H:%M:%S GMT%z (%Z)")
    header = [
        f"\\id ACT EN_BSB en_English_ltr - Berean Study Bible {current_date} tc",
        "\\usfm 3.0",
        "\\h Acts",
        "\\toc1 Acts",
        "\\mt1 Acts",
    ]
    return header

def get_section_header(chapter_num, verse_num):
    """Return section headers for specific chapter/verse combinations"""
    # Map of chapter/verse combinations to section headers
    section_headers = {
        (1, 1): ["\\s1 Prologue", "\\r (Luke 1:1–4)", "\\b", "\\m"],
        (1, 6): ["\\s1 The Ascension", "\\r (Mark 16:19–20; Luke 24:50–53)", "\\b", "\\m"],
        # Add more section headers as needed
    }
    
    return section_headers.get((chapter_num, verse_num), [])

def get_footnote(chapter_num, verse_num):
    """Return footnotes for specific chapter/verse combinations"""
    # Map of chapter/verse combinations to footnotes
    footnotes = {
        (1, 4): ["\\f + \\fr 1:4 \\ft Or eating together\\f*"],
        (1, 5): ["\\f + \\fr 1:5 \\ft Or For John baptized in water, but in a few days you will be baptized in the Holy Spirit; cited in Acts 11:16\\f*"],
        # Add more footnotes as needed
    }
    
    return footnotes.get((chapter_num, verse_num), [])

def process_aligned_verse(greek_words, verse_num):
    """Process the alignment data for a verse and return USFM markup"""
    result = []
    result.append(f"\\v {verse_num} ")
    
    i = 0
    while i < len(greek_words):
        word_data = greek_words[i]
        english_word = word_data.get('word', '')
        
        # Handle words with Greek alignment
        if 'greekWords' in word_data and word_data['greekWords']:
            for greek_word in word_data['greekWords']:
                # Start alignment tag
                align_tag = f"\\zaln-s |x-strong=\"{greek_word.get('strongsNumber', '')}\" " + \
                           f"x-lemma=\"{greek_word.get('lemma', '')}\" " + \
                           f"x-morph=\"Gr,{greek_word.get('grammarType', '')},,,,,{greek_word.get('usageCode', '').split('-')[-1] if '-' in greek_word.get('usageCode', '') else greek_word.get('usageCode', '')},\" " + \
                           f"x-occurrence=\"1\" x-occurrences=\"1\" " + \
                           f"x-content=\"{greek_word.get('word', '')}\"\\*"
                result.append(align_tag)
            
            # Add the English word with occurrence info
            word_num = word_data.get('number', 1)
            result.append(f"\\w {english_word}|x-occurrence=\"1\" x-occurrences=\"1\"\\w*")
            
            # Close all alignment tags
            for _ in range(len(word_data['greekWords'])):
                result.append("\\zaln-e\\*")
        else:
            # Just add the word without alignment tags
            result.append(english_word)
        
        # Handle word groups (nextWordIsInGroup)
        if word_data.get('nextWordIsInGroup', False):
            next_idx = i + 1
            while next_idx < len(greek_words) and greek_words[next_idx-1].get('nextWordIsInGroup', False):
                next_word = greek_words[next_idx]['word'] if 'word' in greek_words[next_idx] else ""
                result.append(f" {next_word}")
                next_idx += 1
            i = next_idx
        else:
            i += 1
    
    return "".join(result)

def convert_json_to_usfm(greek_filepath, english_filepath, output_filepath):
    """
    Convert Greek alignment and English text data to USFM format
    """
    # Load the JSON data
    greek_data = read_json_file(greek_filepath)
    english_data = read_json_file(english_filepath)
    
    # Start with the header
    usfm_lines = generate_usfm_header()
    
    # Process each chapter
    for chapter_idx, greek_chapter in enumerate(greek_data['chapters']):
        chapter_num = chapter_idx + 1  # Use 1-indexed chapter numbers
        usfm_lines.append(f"\\c {chapter_num}")
        
        # Find matching chapter in English data
        english_chapter = next((ch for ch in english_data['chapters'] if ch['number'] == chapter_num), None)
        if not english_chapter:
            continue
        
        # Process each verse in the chapter
        for verse_idx, greek_verse in enumerate(greek_chapter['verses']):
            verse_num = verse_idx + 1  # Use 1-indexed verse numbers
            
            # Add section header if applicable
            section_headers = get_section_header(chapter_num, verse_num)
            usfm_lines.extend(section_headers)
            
            # Process the verse
            if 'words' in greek_verse:
                verse_text = process_aligned_verse(greek_verse['words'], verse_num)
                usfm_lines.append(verse_text)
            elif verse_idx < len(english_chapter['verses']):
                # Fallback to just using the English text
                english_verse = english_chapter['verses'][verse_idx]['text']
                usfm_lines.append(f"\\v {verse_num} {english_verse}")
            
            # Add footnote if applicable
            footnotes = get_footnote(chapter_num, verse_num)
            usfm_lines.extend(footnotes)
            
            # Add a blank line after certain verses (especially before section headers)
            if section_headers or footnotes:
                usfm_lines.append("\\b")
                usfm_lines.append("\\m")
    
    # Write the output file
    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(usfm_lines))
    
    return output_filepath

if __name__ == "__main__":
    # Define file paths
    greek_filepath = "/Users/richmahn/repos/aquifer-to-dcs/bsb_act_greek.json"
    english_filepath = "/Users/richmahn/repos/aquifer-to-dcs/bsb_act_english.json" 
    output_filepath = "/Users/richmahn/repos/aquifer-to-dcs/generated_acts.usfm"
    
    # Convert the JSON data to USFM
    result_path = convert_json_to_usfm(greek_filepath, english_filepath, output_filepath)
    print(f"USFM file generated successfully at: {result_path}")
