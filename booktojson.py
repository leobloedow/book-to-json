#sys -> to read command line arguments
#os -> open file
#json -> output json format
import sys, os, json
#fitz -> handle pdf files
import fitz
#ebooklib -> handle EPUB files
from ebooklib import epub
# bs4 -> handle html content in epub files
from bs4 import BeautifulSoup

# remove empty lines and hyphenated words and join everything into a single line
def clean_page_text(text):
    # split text into lines
    lines = text.splitlines()
    cleaned = []
    buffer = ''
    for line in lines:
        #removes spaces at the beginning and end
        line = line.strip()
        # skip empty lines
        if not line:
            continue
        # skip numbers only lines (page numbers)
        if line.isdigit():
            continue
        # buffer lines ending with "-"
        if line.endswith('-'):
            buffer += line[:-1]
        else:
            cleaned.append(buffer + line)
            buffer = ''
    # join buffer with the last line
    if buffer:
        cleaned.append(buffer)
    return ' '.join(cleaned)

# process pdf table of contents
def process_pdf(file):
    doc = fitz.open(file)
    # gets table of contents
    toc = doc.get_toc()
    if not toc:
        print("no TOC found")
        return []

    chapters = []
    for i in range(len(toc)):
        level, title, start = toc[i]
        if not title.strip() or not title.strip()[0].isdigit():
            # skip titles that dont start with a digit (skip covers, flaps, etc.)
            continue
        start -= 1 # first index is 0
        end = toc[i + 1][2] - 1 if i + 1 < len(toc) else len(doc)

        text = ''
        for page_num in range(start, end):
            text += doc.load_page(page_num).get_text()

        # structure the text data
        chapter_text = clean_page_text(text)
        chapters.append({"title": title, "text": chapter_text})

    return chapters

#process epub table of contents
# AI did this i really dont know how epub works
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

# remove name of the chapter from text, if it appears in footnotes or headers
def remove_repeated_titles(text, title):
    # re -> regex support
    import re

    #remove starting numbers and spaces from title to check
    phrase = title.lstrip(' 0123456789')
    phrase = phrase.strip()
    if not phrase:
        return text

    # find the first occurrence
    first_pos = text.find(phrase)
    if first_pos == -1:
        return text

    before = text[:first_pos + len(phrase)]
    after = text[first_pos + len(phrase):]

    # find all occurrences of the phrase
    escaped_phrase = re.escape(phrase)
    pattern = re.compile(r'(\s?)' + escaped_phrase + r'(\s?)')

    # remove all occurrences
    def replacer(match):
        return ' '

    after_cleaned = pattern.sub(replacer, after)

    # remove extra spaces
    after_cleaned = re.sub(r'\s+', ' ', after_cleaned).strip()

    return before + ' ' + after_cleaned if after_cleaned else before

def main(file):
    ext = os.path.splitext(file)[1].lower()

    # decides if its pdf or epub
    if ext == '.pdf':
        chapters = process_pdf(file)
    elif ext == '.epub':
        chapters = process_epub(file)
    else:
        print('only .pdf and .epub are supported.')
        return

    # clean chapter titles
    for chapter in chapters:
        chapter['text'] = remove_repeated_titles(chapter['text'], chapter['title'])

    # output json file
    with open('out.json', 'w', encoding='utf-8') as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('use: python booktojson.py book.pdf|book.epub')
    else:
        main(sys.argv[1])