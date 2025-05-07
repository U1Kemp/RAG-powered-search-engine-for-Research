from Helper4 import *
import pytest

# Load the model and tokenizer for summary generation
model_name = "sshleifer/distilbart-cnn-12-6"
tokenizer = AutoTokenizer.from_pretrained(model_name)

def test_keyword_extraction():
    query = "Who is the CEO of DeepSeek? What does DeepSeek do? And when was it founded?"
    keywords = extract_keywords(query, threshold=0.50)
    print(keywords)
    assert isinstance(keywords, list)
    assert "deepseek" in [k.lower() for k in keywords]
    assert "ceo" in [k.lower() for k in keywords]

def test_wikipedia_retrieval():
    query = "Who is the CEO of DeepSeek? What does DeepSeek do? And when was it founded?"
    content = get_wiki_page_sync(query)
    assert isinstance(content, list)
    assert any("liang wenfeng" in (c['title'].lower() or c['text'].lower()) for c in content)
    assert any("deepseek" in (c['title'].lower() or c['text'].lower()) for c in content)

    keywords = extract_keywords(query, threshold=0.50)
    content = get_wiki_page_sync(keywords[0])
    assert isinstance(content, list)
    assert any("liang wenfeng" in (c['title'].lower() or c['text'].lower()) for c in content)
    assert any("deepseek" in (c['title'].lower() or c['text'].lower()) for c in content)

def async_test_wikipedia_retrieval():
    query = ["Python programming language", "Java programming language"]
    content = fetch_wikipedia_content(query)
    assert isinstance(content, list)
    assert any("java" in (c['title'].lower() or c['text'].lower()) for c in content)
    assert any("python" in (c['title'].lower() or c['text'].lower()) for c in content)
    assert any("programming" in (c['title'].lower() or c['text'].lower()) for c in content)

def test_wikipedia_no_result():
    query = "asdkjhaskjdhaksjd"  # nonsense
    content = get_wiki_page_sync(query)
    assert content == [] or content is None

def test_arxiv_retrieval():
    query = "transformer neural networks"
    papers = get_arxiv_paper_sync(subject="Computer Science", subtopic="Artificial Intelligence", query=query, max_results=3)
    assert isinstance(papers, list)
    assert len(papers) > 0
    assert all("title" in paper for paper in papers)

def async_test_arxiv_retrieval():
    query = ["transformer neural networks", "attention mechanism"]
    papers = fetch_arxiv_papers("Computer Science", "Artificial Intelligence", query)
    assert isinstance(papers, list)
    assert len(papers) > 0
    assert all("title" in paper for paper in papers)

def test_arxiv_no_result():
    query = "asdkjhaskjdhaksjd"  # nonsense
    papers = get_arxiv_paper_sync(subject="Computer Science", subtopic="Artificial Intelligence", query=query, max_results=3)
    assert papers == []

def test_summarize_function():
    assert isinstance(summarize("This is a test string"), str)
    pytest.raises(TypeError, match="Input text must be a string.")

    long_text = "Python's development is conducted largely through the Python Enhancement Proposal (PEP) process, the primary mechanism for proposing major new features, collecting community input on issues, and documenting Python design decisions. Python coding style is covered in PEP 8. Outstanding PEPs are reviewed and commented on by the Python community and the steering council.Enhancement of the language corresponds with the development of the CPython reference implementation. The mailing list python-dev is the primary forum for the language's development. Specific issues were originally discussed in the Roundup bug tracker hosted at by the foundation. In 2022, all issues and discussions were migrated to GitHub. Development originally took place on a self-hosted source-code repository running Mercurial, until Python moved to GitHub in January 2017.Since 2003, Python has consistently ranked in the top ten most popular programming languages in the TIOBE Programming Community Index where as of December 2022 it was the most popular language (ahead of C, C++, and Java). It was selected as Programming Language of the Year (for 'the highest rise in ratings in a year') in 2007, 2010, 2018, and 2020 (the only language to have done so four times as of 2020).Large organizations that use Python include Wikipedia, Google, Yahoo!, CERN, NASA, Facebook, Amazon, Instagram, Spotify, and some smaller entities like Industrial Light & Magic and ITA. The social news networking site Reddit was written mostly in Python. Organizations that partially use Python include Discord and Baidu.Python can serve as a scripting language for web applications, e.g. via mod_wsgi for the Apache webserver. With Web Server Gateway Interface, a standard API has evolved to facilitate these applications. Web frameworks like Django, Pylons, Pyramid, TurboGears, web2py, Tornado, Flask, Bottle, and Zope support developers in the design and maintenance of complex applications. Pyjs and IronPython can be used to develop the client-side of Ajax-based applications. SQLAlchemy can be used as a data mapper to a relational database. Twisted is a framework to program communications between computers, and is used (for example) by Dropbox."
    assert isinstance(summarize(long_text), str)
    assert len(tokenizer.encode(summarize(long_text))) <= 512

    very_long_text = """
    Web development tools:
    Web development tools (often abbreviated to dev tools) allow web developers to test, modify and debug their websites. They are different from website builders and integrated development environments (IDEs) in that they do not assist in the direct creation of a webpage, rather they are tools used for testing the user interface of a website or web application.
    Web development tools come as browser add-ons or built-in features in modern web browsers. Browsers such as Google Chrome, Firefox, Safari, Microsoft Edge, and Opera have built-in tools to help web developers, and many additional add-ons can be found in their respective plugin download centers.
    Web development tools allow developers to work with a variety of web technologies, including HTML, CSS, the DOM, JavaScript, and other components that are handled by the web browser.
    ==========================================================================================

    Web framework:
    A web framework (WF) or web application framework (WAF) is a software framework that is designed to support the development of web applications including web services, web resources, and web APIs. Web frameworks provide a standard way to build and deploy web applications on the World Wide Web. Web frameworks aim to automate the overhead associated with common activities performed in web development. For example, many web frameworks provide libraries for database access, templating frameworks, and session management, and they often promote code reuse. Although they often target development of dynamic web sites, they are also applicable to static websites.
    ==========================================================================================

    Front-end web development:
    Front-end web development is the development of the graphical user interface of a website through the use of HTML, CSS, and JavaScript so users can view and interact with that website.


    == Tools used for front-end development ==
    There are several tools and platforms, such as WordPress, Joomla, and Drupal, available that can be used to develop the front end of a website.


    === HyperText Markup Language ===

    HyperText Markup Language (HTML) is the modern standard for displaying and structuring web content across the internet. HTML defines what elements will be displayed on a website, and how they will be arranged. All major web browsers are designed to interpret HTML, and most modern websites serve HTML to the user.
    ==========================================================================================

    Style sheet (web development):
    A web style sheet is a form of separation of content and presentation for web design in which the markup (i.e., HTML or XHTML) of a webpage contains the page's semantic content and structure, but does not define its visual layout (style). Instead, the style is defined in an external style sheet file using a style sheet language such as CSS or XSLT. This design approach is identified as a "separation" because it largely supersedes the antecedent methodology in which a page's markup defined both style and structure.
    The philosophy underlying this methodology is a specific case of separation of concerns.


    == Benefits ==
    Separation of style and content has advantages, but has only become practical after improvements in popular web browsers' CSS implementations.


    === Speed ===
    Overall, users experience of a site utilising style sheets will generally be quicker than sites that don’t use the technology."""
    assert isinstance(summarize(very_long_text), str)
    assert len(tokenizer.encode(summarize(very_long_text))) <= 512

    short_text = "This is a short text"
    assert isinstance(summarize(short_text), str)
    assert len(tokenizer.encode(summarize(short_text))) <= 512

    text = "This is a very long text that needs to be summarized"
    assert isinstance(summarize(text), str)
    assert len(tokenizer.encode(summarize(text))) <= 512

def test_remove_duplicate_dicts():
    assert remove_duplicate_dicts([{"a": 1, "b": 2}, {"a": 1, "b": 2}, {"c": 3, "d": 4}]) == [{"a": 1, "b": 2}, {"c": 3, "d": 4}]
    pytest.raises(TypeError, remove_duplicate_dicts, [{"a": 1, "b": 2}, "not a dict", {"c": 3, "d": 4}])
    pytest.raises(TypeError, remove_duplicate_dicts, "not a list")



