import bs4
from bs4 import BeautifulSoup
from unidecode import unidecode
import urllib
import re
import datetime
import requests
import argparse


class GremlinZapper(object):
    """
    Class to convert windows cp1252 characters to unicode characters or
    to convert cp1252 and unicode characters to their ascii equivalents
    """

    def __init__(self):
        self.gremlin_regex_1252 = re.compile(r"[\x80-\x9f]")
        """ From http://effbot.org/zone/unicode-gremlins.htm """
        self.cp1252 = {
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

    def kill_gremlins(self, text):
        """
        From http://effbot.org/zone/unicode-gremlins.htm
        map cp1252 gremlins to real unicode characters
        :return:
        """

        if re.search(u"[\x80-\x9f]", text):
            def fixup(m):
                s = m.group(0)
                return self.cp1252.get(s, s)

            if isinstance(text, type("")):
                # make sure we have a unicode string
                text = unicode(text, "iso-8859-1")
            text = re.sub(self.gremlin_regex_1252, fixup, text)
        return text

    def zap_string(self, the_string):
        """
        Converts any Windows cp1252 or unicode characters in a string to ASCII equivalents
        :param the_string: the string to perform the conversion on
        :return: input string with gremlins replaced
        """
        the_string = self.kill_gremlins(the_string)
        if isinstance(the_string, unicode):
            the_string = unidecode(the_string)
        return the_string


class CurrentsArticleParser(object):
    """
    Class to parse UCSC currents magazine articles and convert to markdown with yaml metadata
    """

    def __init__(self):
        self.date_regex = re.compile(r"[A-Za-z]+\s*\d{1,2}\,\s*\d{4}")
        self.end_story_regex = re.compile(r"\s*END\s*STORY\s*")
        self.word_regex = re.compile(r"([^\s\n\r\t]+)")
        self.article_slug_regex = re.compile(r".*\/([^\/\.]+)(?:.[^\.\/]+$)*")

    def zap_tag_contents(self, tag):
        """
        Converts any Windows cp1252 or unicode characters in the text of
        a BeautifulSoup bs4.element.Tag Object to ASCII equivalents
        :rtype: bs4.element.Tag
        :param tag: the Tag object to convert
        :return: None
        """
        content_length = len(tag.contents)

        gzapper = GremlinZapper()

        for x in range(0, content_length):
            if isinstance(tag.contents[x], bs4.element.NavigableString):
                unicode_entry = gzapper.kill_gremlins(tag.contents[x])
                unicode_entry = unidecode(unicode_entry)
                tag.contents[x].replace_with(unicode_entry)
            elif isinstance(tag.contents[x], bs4.element.Tag):
                self.zap_tag_contents(tag.contents[x])

    def get_soup_from_url(self, page_url):
        """
        Takes the url of a web page and returns a BeautifulSoup Soup object representation
        :param page_url: the url of the page to be parsed
        :param article_url: the url of the web page
        :raises: r.raise_for_status: if the url doesn't return an HTTP 200 response
        :return: A Soup object representing the page html
        """
        r = requests.get(page_url)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        return BeautifulSoup(r.content, 'html.parser')

    def get_url_slug(self, page_url):
        """
        Returns the last section of a url eg. 'posts' for 'wordpress.com/posts.html'
        :raises Exception: if the regex is unable to locate the url slug
        :param page_url: the page url
        :return: the url slug
        """
        slug_match = self.article_slug_regex.findall(page_url)
        if slug_match and len(slug_match) == 1:
            return slug_match[0]
        else:
            raise Exception("unable to find slug for article: " + page_url + "\n")

    def html_to_markdown(self, html_string):
        """
        converts a string of html text to markdown using heckyesmarkdown.com
        :param html_string:
        :return:
        """
        r = requests.post('http://heckyesmarkdown.com/go/#sthash.Xf1YNf4U.dpuf',
                          data={'html': html_string, })

        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        return r.text

    def parse_story_text(self, story_text):
        """
        Parses a story_text div class and finds the
            - title
            - author
            - date
            - and the html of the story body
        and returns it in dictionary form
        :param story_text: an HTML div of class story_text
        :return:
        """
        # initializing strings to empty means if a value isn't found in the HTML it simply won't be written to file
        title = ''
        author = ''
        date = ''
        story_string = ''
        images_dictionary = dict()
        gremlin_zapper = GremlinZapper()

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
                            matches = self.word_regex.findall(title)
                            title = ' '.join(matches)
                            title = gremlin_zapper.zap_string(title)
                            add_to_story = False
                elif item.string:
                    match = self.date_regex.match(item.string)
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
                                matches = self.word_regex.findall(image_text)
                                image_text = ' '.join(matches)
                                image_text = gremlin_zapper.zap_string(image_text)

                                images_dictionary[image_src] = image_text
                    else:
                        if item.contents:
                            if len(item.contents) >= 2:
                                if item.contents[0] == 'By ' and isinstance(item.contents[1], bs4.element.Tag) \
                                        and item.contents[1].name == 'a':
                                    author = item.contents[1].string
                                    author = gremlin_zapper.zap_string(author)
                                    add_to_story = False

                            for cont in item.contents:
                                if isinstance(cont, bs4.element.Comment):
                                    match = self.end_story_regex.match(cont.string)
                                    if match:
                                        story_end = True
                        if story_end:
                            break
            else:
                add_to_story = False

            if add_to_story:
                self.zap_tag_contents(item)

                story_string += str(item)

        return {'title': title,
                'author': author,
                'images_dictionary': images_dictionary,
                'article_body': story_string,
                'date': date}

    def scrape_article(self, article_url):
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

        soup = self.get_soup_from_url(article_url)

        # get the url slug for the new file name

        slug = self.get_url_slug(article_url)

        # this is the div that will hold any relevant article information
        story_text = soup.find('div', class_='storytext')

        article_dict = self.parse_story_text(story_text)

        article_dict['file_name'] = article_dict['date'] + '-' + slug + ".md"
        article_dict['source_permalink'] = "[source](" + article_url + " \"Permalink to " + slug + "\")"
        article_dict['article_body'] = self.html_to_markdown(article_dict['article_body'])
        return article_dict

    def write_article(self, article_dict):
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

    def scrape_url(self, article_url):
        """
        Scrapes a single UCSC Currents magazine article
        :param article_url:
        :return:
        """
        article_url = article_url.rstrip()
        print article_url
        article_dictionary = self.scrape_article(article_url)
        self.write_article(article_dictionary)
        print "done"

    def scrape_url_list(self, article_url_list):
        """
        Scrapes a list of UCSC Currents magazine articles
        :param article_url_list:
        :return:
        """
        for article_url in article_url_list:
            self.scrape_url(article_url)

    def scrape_from_file(self, file_name):
        """
        Scrapes all the UCSC Currents magazine articles in a file given this format:
            - one url per line
        :param file_name:
        :return:
        """
        try:
            article_list_file = open(file_name, 'r')
            for article_url in article_list_file:
                self.scrape_url(article_url)
            article_list_file.close()
        except IOError:
            print "Error: File does not appear to exist."

