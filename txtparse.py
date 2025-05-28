import sys, os, json
import fitz  # For reading PDFs (PyMuPDF)
from ebooklib import epub
from bs4 import BeautifulSoup

# Clean each line: strip whitespace, merge hyphenated words

def clean_page_text(text):
    lines = text.splitlines()
    cleaned = []
    buffer = ''
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            # Skip lines that are only numbers (page numbers)
            continue
        if line.endswith('-'):
            buffer += line[:-1]
        else:
            cleaned.append(buffer + line)
            buffer = ''
    if buffer:
        cleaned.append(buffer)
    return ' '.join(cleaned)

# Process PDF using table of contents

def process_pdf(file):
    doc = fitz.open(file)
    toc = doc.get_toc()
    if not toc:
        print("This PDF has no table of contents.")
        return []

    chapters = []
    for i in range(len(toc)):
        level, title, start = toc[i]
        if not title.strip() or not title.strip()[0].isdigit():
            # Skip chapters whose title doesn't start with a digit
            continue
        start -= 1  # Convert to 0-based index
        end = toc[i + 1][2] - 1 if i + 1 < len(toc) else len(doc)

        text = ''
        for page_num in range(start, end):
            text += doc.load_page(page_num).get_text()

        chapter_text = clean_page_text(text)
        chapters.append({"title": title, "text": chapter_text})

    return chapters

# Process EPUB using spine order

def process_epub(file):
    book = epub.read_epub(file)
    chapters = []
    chapter_num = 1

    for item in book.get_items():
        if item.get_type() == epub.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text()
            chapter_text = clean_page_text(text)
            title = item.get_name()
            if chapter_text and title.strip() and title.strip()[0].isdigit():
                chapters.append({"title": title, "text": chapter_text})
                chapter_num += 1

    return chapters

# Remove repeated titles from chapter text
def remove_repeated_titles(text, title):
    import re

    # Extract phrase after leading digits and spaces
    phrase = title.lstrip(' 0123456789')
    phrase = phrase.strip()
    if not phrase:
        return text

    # Find first occurrence index of phrase in text
    first_pos = text.find(phrase)
    if first_pos == -1:
        return text  # phrase not found, return original

    before = text[:first_pos + len(phrase)]
    after = text[first_pos + len(phrase):]

    # Regex pattern to find phrase with optional space before or after
    escaped_phrase = re.escape(phrase)
    pattern = re.compile(r'(\s?)' + escaped_phrase + r'(\s?)')

    # Replace all occurrences except first with a single space
    def replacer(match):
        return ' '

    after_cleaned = pattern.sub(replacer, after)

    # Collapse multiple spaces
    after_cleaned = re.sub(r'\s+', ' ', after_cleaned).strip()

    return before + ' ' + after_cleaned if after_cleaned else before

# Main function
def main(file):
    ext = os.path.splitext(file)[1].lower()

    if ext == '.pdf':
        chapters = process_pdf(file)
    elif ext == '.epub':
        chapters = process_epub(file)
    else:
        print('Only PDF and EPUB are supported.')
        return

    # Optionally clean repeated titles
    for chapter in chapters:
        chapter['text'] = remove_repeated_titles(chapter['text'], chapter['title'])

    with open('chapters.json', 'w', encoding='utf-8') as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

# Run the script
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python script.py book.pdf|book.epub')
    else:
        main(sys.argv[1])