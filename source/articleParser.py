import bs4
from bs4 import BeautifulSoup
from unidecode import unidecode
import urllib
import re
import datetime
import requests
import argparse

date_regex = re.compile(r"[A-Za-z]+\s*\d{1,2}\,\s*\d{4}")
end_story_regex = re.compile(r"\s*END\s*STORY\s*")
word_regex = re.compile(r"([^\s\n\r\t]+)")
gremlin_regex_1252 = re.compile(r"[\x80-\x9f]")
article_slug_regex = re.compile(r".*\/([^\/\.]+).[^\.\/]+$")

""" Code by Fredrik Lundh  http://effbot.org/zone/unicode-gremlins.htm """
cp1252 = {
    # from http://www.microsoft.com/typography/unicode/1252.htm
    u"\x80": u"\u20AC",  # EURO SIGN
    u"\x82": u"\u201A",  # SINGLE LOW-9 QUOTATION MARK
    u"\x83": u"\u0192",  # LATIN SMALL LETTER F WITH HOOK
    u"\x84": u"\u201E",  # DOUBLE LOW-9 QUOTATION MARK
    u"\x85": u"\u2026",  # HORIZONTAL ELLIPSIS
    u"\x86": u"\u2020",  # DAGGER
    u"\x87": u"\u2021",  # DOUBLE DAGGER
    u"\x88": u"\u02C6",  # MODIFIER LETTER CIRCUMFLEX ACCENT
    u"\x89": u"\u2030",  # PER MILLE SIGN
    u"\x8A": u"\u0160",  # LATIN CAPITAL LETTER S WITH CARON
    u"\x8B": u"\u2039",  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    u"\x8C": u"\u0152",  # LATIN CAPITAL LIGATURE OE
    u"\x8E": u"\u017D",  # LATIN CAPITAL LETTER Z WITH CARON
    u"\x91": u"\u2018",  # LEFT SINGLE QUOTATION MARK
    u"\x92": u"\u2019",  # RIGHT SINGLE QUOTATION MARK
    u"\x93": u"\u201C",  # LEFT DOUBLE QUOTATION MARK
    u"\x94": u"\u201D",  # RIGHT DOUBLE QUOTATION MARK
    u"\x95": u"\u2022",  # BULLET
    u"\x96": u"\u2013",  # EN DASH
    u"\x97": u"\u2014",  # EM DASH
    u"\x98": u"\u02DC",  # SMALL TILDE
    u"\x99": u"\u2122",  # TRADE MARK SIGN
    u"\x9A": u"\u0161",  # LATIN SMALL LETTER S WITH CARON
    u"\x9B": u"\u203A",  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    u"\x9C": u"\u0153",  # LATIN SMALL LIGATURE OE
    u"\x9E": u"\u017E",  # LATIN SMALL LETTER Z WITH CARON
    u"\x9F": u"\u0178",  # LATIN CAPITAL LETTER Y WITH DIAERESIS
}


def kill_gremlins(text):
    # map cp1252 gremlins to real unicode characters
    if re.search(u"[\x80-\x9f]", text):
        def fixup(m):
            s = m.group(0)
            return cp1252.get(s, s)

        if isinstance(text, type("")):
            # make sure we have a unicode string
            text = unicode(text, "iso-8859-1")
        text = re.sub(gremlin_regex_1252, fixup, text)
    return text


"""         end code        """


def zap_string(the_string):
    """
    Converts any Windows cp1252 or unicode characters in a string to ASCII equivalents
    :param the_string: the string to perform the conversion on
    :return: input string with gremlins replaced
    """
    the_string = kill_gremlins(the_string)
    if isinstance(the_string, unicode):
        the_string = unidecode(the_string)
    return the_string


def zap_tag_contents(tag):
    """
    Converts any Windows cp1252 or unicode characters in the text of
    a BeautifulSoup bs4.element.Tag Object to ASCII equivalents
    :param tag: the Tag object to convert
    :return: None
    """
    content_length = len(tag.contents)
    for x in range(0, content_length):
        if isinstance(tag.contents[x], bs4.element.NavigableString):
            unicode_entry = kill_gremlins(tag.contents[x])
            unicode_entry = unidecode(unicode_entry)
            tag.contents[x].replace_with(unicode_entry)
        elif isinstance(tag.contents[x], bs4.element.Tag):
            zap_tag_contents(tag.contents[x])


def scrape_article(article_url):
    """
    Gets HTML for a UCSC Currents online magazine article url, attempts to find:
        - title
        - author
        - date published
        - image links and captions (dictionary format ie: {img_link1: caption1, img_link2: caption2}
        - article body
    converts the article body to Markdown (https://daringfireball.net/projects/markdown/)
    then returns a dictionary of the above values

    :param article_url: the url to a UCSC Currents online magazine article
    :return: a dictionary of scraped values
    """
    r = requests.get(article_url)
    if r.status_code != requests.codes.ok:
        r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')

    # initializing strings to empty means if a value isn't found in the HTML it simply won't be written to file
    slug = ''
    title = ''
    author = ''
    date = ''
    story_string = ''
    images_dictionary = dict()

    # get the url slug for the new file name
    slug_match = article_slug_regex.findall(article_url)
    if slug_match and len(slug_match) == 1:
        slug = slug_match[0]
    else:
        raise Exception("unable to find slug for article: " + article_url + "\n")

    # this is the div that will hold any relevant article information
    story_text = soup.find('div', class_='storytext')

    '''for item in storyText.contents:
        print item'''

    """
    iterate through the divs containing story content (there should be only 1)
    any metadata value found is assigned to the relevant variable and excluded from
    the article body
    """
    for item in story_text.contents:
        # print type(item)
        add_to_story = True

        if isinstance(item, bs4.element.Tag):
            # print item
            if 'class' in item.attrs:
                classes = item['class']
                for the_class in classes:
                    if the_class == 'storyhead':
                        title = item.get_text()
                        matches = word_regex.findall(title)
                        title = ' '.join(matches)
                        title = zap_string(title)
                        add_to_story = False
            elif item.string:
                match = date_regex.match(item.string)
                if match:
                    # Convert date from Month, Day Year to Year-Month-Day
                    date = datetime.datetime.strptime(item.string, "%B %d, %Y").strftime("%Y-%m-%d")
                    add_to_story = False
            else:
                story_end = False

                if item.name == 'table':

                    images = item.find_all('img')
                    if images:
                        add_to_story = False

                        for image in images:
                            image_src = image['src']
                            image_text = image.get_text()
                            matches = word_regex.findall(image_text)
                            image_text = ' '.join(matches)
                            image_text = zap_string(image_text)

                            images_dictionary[image_src] = image_text
                else:
                    if item.contents:
                        if len(item.contents) >= 2:
                            if item.contents[0] == 'By ' and isinstance(item.contents[1], bs4.element.Tag) \
                                    and item.contents[1].name == 'a':
                                author = item.contents[1].string
                                author = zap_string(author)
                                add_to_story = False

                        for cont in item.contents:
                            if isinstance(cont, bs4.element.Comment):
                                match = end_story_regex.match(cont.string)
                                if match:
                                    story_end = True
                    if story_end:
                        break
        else:
            add_to_story = False

        if add_to_story:
            zap_tag_contents(item)

            story_string += str(item)

    # convert article body to Markdown
    r = requests.post('http://heckyesmarkdown.com/go/#sthash.Xf1YNf4U.dpuf', data={'html': story_string, })
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    """
    # debug information
    print "slug: " + slug
    print "title: " + title
    print "date: " + date
    print "author: " + author
    print "images:"
    # print images_dictionary

    for key in images_dictionary:
        print "    " + key + ":"
        print images_dictionary[key] + "\n"
        print r.text
    """

    # create new file name in the format year-month-day-url_slug.md
    file_name = date + '-' + slug + ".md"

    # create the source permalink
    source_permalink = "[source](" + article_url + " \"Permalink to " + slug + "\")"

    return {'file_name': file_name,
            'source_permalink': source_permalink,
            'title': title,
            'author': author,
            'images_dictionary': images_dictionary,
            'article_body': r.text}


def write_article(article_dict):
    """
    Given a dictionary of article values:
    creates a new file in the current directory with title, author, date, and images in YAML format metadata
    followed by the Markdown format article body
    and finally a permalink to the article source link

    currently overwrites existing files if generated filenames are the same

    :param article_dict: A dictionary of scraped values for a UCSC Currents online magazine article
    :return None
    """
    fo = open(article_dict['file_name'], "w")
    fo.write("---\n")
    fo.write("layout: post\n")
    fo.write("title: " + article_dict['title'] + "\n")
    fo.write("author: " + article_dict['author'] + "\n")
    fo.write("images:\n")

    for key in article_dict['images_dictionary']:
        fo.write("  -\n")
        fo.write("    - file: " + key + "\n")
        fo.write("    - caption: " + article_dict['images_dictionary'][key] + "\n")

    fo.write("---\n\n")
    fo.write(article_dict['article_body'])
    fo.write("\n")
    fo.write(article_dict['source_permalink'] + "\n")
    fo.close()

""" ==================== Begin Main Code =================== """

parser = argparse.ArgumentParser()

parser.add_argument('-i', metavar='input_file', type=argparse.FileType('r'))



try:
    results = parser.parse_args()
    if not results.i:
        parser.error('No input file specified, -i input_file')
except IOError, msg:
    parser.error(str(msg))

for article_url in results.i:
    article_url = article_url.rstrip()
    print article_url
    article_dictionary = scrape_article(article_url)
    write_article(article_dictionary)
    print "done"

results.i.close()
