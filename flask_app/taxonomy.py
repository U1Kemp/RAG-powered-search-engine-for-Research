import requests
from bs4 import BeautifulSoup
import json

def get_map():
    """
    Fetch the arXiv category taxonomy and return a mapping of subjects to subtopics.
    """
    url = "https://arxiv.org/category_taxonomy"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: HTTP {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    mapping = {}

    # Find all subject headers (e.g., "Computer Science") inside h2 tags with class "accordion-head"
    subjects = soup.find_all("h2", class_="accordion-head")
    for subj in subjects:
        subject_name = subj.get_text(strip=True)
        mapping[subject_name] = {}

        # The subtopics are found in the following div with class "accordion-body"
        accordion_body = subj.find_next_sibling("div", class_="accordion-body")
        if not accordion_body:
            continue

        # Within accordion_body, subtopics are located in div elements with class "column is-one-fifth"
        columns = accordion_body.find_all("div", class_="column is-one-fifth")
        for col in columns:
            # Each subtopic entry is in an h4 tag
            h4_tags = col.find_all("h4")
            for h4 in h4_tags:
                text = h4.get_text(strip=True)
                # Expecting a format like "cs.AI (Artificial Intelligence)"
                if "(" in text and ")" in text:
                    parts = text.split("(", 1)
                    code = parts[0].strip()
                    desc = parts[1].strip(" )")
                else:
                    code = text.strip()
                    desc = text.strip()
                mapping[subject_name][desc] = code

    return mapping

if __name__ == "__main__":
    sub2tag = get_map()

    tag2sub = {}
    for subject, subtopics in sub2tag.items():
        for subtopic, category_tag in subtopics.items():
            tag2sub[category_tag] = [subject, subtopic]

    json.dump(sub2tag, open("sub2tag.json", "w"), indent=2)
    json.dump(tag2sub, open("tag2sub.json", "w"), indent=2)