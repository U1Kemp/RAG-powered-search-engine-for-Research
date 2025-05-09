import arxiv
import json

with open('sub2tag.json', 'r') as f:
    sub2tag = json.load(f)

with open('tag2sub.json', 'r') as f:
    tag2sub = json.load(f)

def get_sub(tag):
    """
    Join the subject and subtopic for a given tag.
    """
    return ' '.join(tag2sub[tag])

def fetch(subject:str, subtopic:str, keyword:None, max_results=10):
    """
    Fetch metadata for recent papers from arXiv based on subject and subtopic.

    Parameters
    ----

    subject: `str`
        The main subject (e.g., Mathematics).
    subtopic: `str`
        The subtopic (e.g., Probability).
    keyword: `str`
        (Optional) A keyword to search for in the paper titles.
    max_results: `int`
        (Optional) Number of papers to fetch.

    Returns
    ----
        list: A list of dictionaries containing metadata for each paper.
    """

    
    # Construct the query
    if keyword is None:
        query = f"cat:{sub2tag[subject][subtopic]}"
        print(f"Fetching recent papers on {subject} - {subtopic}\n")
    else:
        query = f"cat:{sub2tag[subject][subtopic]} AND abs:{keyword}"
        print(f"Fetching recent papers on {subject} - {subtopic} ({keyword})\n")

    print(f'Query: {query}')

    # Create a client and execute the search
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    # Fetch metadata for each result
    papers_metadata = []
    for result in client.results(search):
        paper_data = {
            "title": result.title,
            "authors": [author.name for author in result.authors],
            "abstract": result.summary,
            "published_date": result.published.strftime("%Y-%m-%d"),
            "pdf_url": result.pdf_url,
            "primary_category": get_sub(result.primary_category),
            "categories": [', '.join([get_sub(tag) for tag in result.categories])],
            "doi": ''.join([result.doi if result.doi else 'N/A']),
            "journal_ref": ''.join([result.journal_ref if result.journal_ref else 'N/A']),
            "comment": ''.join([result.comment if result.comment else 'N/A']),
        }

        papers_metadata.append(paper_data)

    return papers_metadata

# Example usage
if __name__ == "__main__":

    subject = "Mathematics"
    subtopic = "Probability"
    keyword = "Markov Chains"

    metadata = fetch(subject, subtopic, keyword, max_results=3)

    for index, paper in enumerate(metadata, start=1):
        print(f"Paper {index}:")
        print(f"Title: {paper['title']}")
        print(f"Authors: {', '.join(paper['authors'])}")
        print(f"Abstract: {paper['abstract']}")
        print(f"Published Date: {paper['published_date']}")
        print(f"PDF URL: {paper['pdf_url']}")
        print(f"Primary Category: {paper['primary_category']}")
        print(f"Categories: {paper['categories']}")
        print(f"DOI: {paper['doi']}")
        print(f"Journal Reference: {paper['journal_ref']}")
        print(f"Comment: {paper['comment']}")
        print()