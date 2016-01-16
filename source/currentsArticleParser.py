import bs4
from bs4 import BeautifulSoup
from unidecode import unidecode
import re
import datetime
import requests
import pprint
import curses
import time
import traceback


class NoStoryTextException(Exception):
    """
    Exception for when an article doesn't have a div of class storytext, and therefore
    is incorrectly formatted to be parsed by this application
    """
    def __init__(self):
        Exception.__init__(self, "Could not find a div of class storytext")


class ContentNotHTMLException(Exception):
    """
    Exception for when a url doesn't return html content
    """
    def __init__(self):
        Exception.__init__(self, "Content type not text/html; charset=UTF-8")


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
        self.date_from_url_regex = re.compile(r"http://www1\.ucsc\.edu/currents/(\d+)-(\d+)/(\d+)-(\d+)/")

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
        if r.headers['content-type'] != 'text/html; charset=UTF-8':
            raise ContentNotHTMLException
        return BeautifulSoup(r.content, 'lxml')

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

    def get_date_from_url(self, page_url):
        """
        Makes a guess as to the date of an article based off of its URL
        :param page_url:
        :return:
        """
        date = None
        date_matches = self.date_from_url_regex.findall(page_url)
        if date_matches:
            date_matches_tuple = date_matches[0]
            year0 = date_matches_tuple[0]
            year1 = date_matches_tuple[1]
            month = date_matches_tuple[2]
            month_as_int = int(date_matches_tuple[2])
            day = date_matches_tuple[3]

            # add the first two digits of the year
            if int(date_matches_tuple[0]) > 20:
                year0 = '19' + str(year0)
            else:
                year0 = '20' + str(year0)

            if int(date_matches_tuple[1]) > 20:
                year1 = '19' + str(year1)
            else:
                year1 = '20' + str(year1)

            if month_as_int > 6:
                date = year0 + '-' + month + '-' + day
            else:
                date = year1 + '-' + month + '-' + day
        return date

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

        title = None
        author = None
        date = None
        story_string = None
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
                        if the_class == 'subhead' and title is None:
                            title = item.get_text()
                            matches = self.word_regex.findall(title)
                            title = ' '.join(matches)
                            title = gremlin_zapper.zap_string(title)
                            add_to_story = False
                elif item.string:
                    match = self.date_regex.match(item.string)
                    if match:
                        # Convert date from Month, Day Year to Year-Month-Day
                        try:
                            raw_date = item.string
                            raw_date = raw_date.rstrip()
                            date = datetime.datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y-%m-%d")
                            add_to_story = False
                        except ValueError:
                            add_to_story = True

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

                if story_string is None:
                    story_string = str(item)
                else:
                    story_string += str(item)

        if author is None:
            author = "Public Information Department"

        return {'title': title,
                'author': author,
                'images_dictionary': images_dictionary,
                'article_body': story_string,
                'date': date}

    def scrape_article(self, article_url, diagnostic=False):
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

        if story_text is None:
            raise NoStoryTextException()

        article_dict = self.parse_story_text(story_text)

        if article_dict['date'] is None:
            date = self.get_date_from_url(article_url)
        else:
            date = article_dict['date']

        article_body = article_dict['article_body'] or ''

        article_dict['date'] = date
        article_dict['file_name'] = date + '-' + slug + ".md"
        article_dict['source_permalink'] = "[source](" + article_url + " \"Permalink to " + slug + "\")"
        if diagnostic is False:
            article_dict['article_body'] = self.html_to_markdown(article_body)
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

        title = article_dict['title'] or ''
        author = article_dict['author'] or ''

        fo = open(article_dict['file_name'], "w")
        fo.write("---\n")
        fo.write("layout: post\n")
        fo.write("title: " + title + "\n")
        fo.write("author: " + author + "\n")
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

    def report_progress(self, stdscr, url, progress_percent):
        """
        Updates progress bar for url_list_diagnostics
        :param progress_percent:
        :param message:
        :return:
        """
        stdscr.addstr(0, 0, "Total progress: [{1:50}] {0}%".format(progress_percent, "#" * (progress_percent / 2)))
        stdscr.move(1, 0)
        stdscr.clrtoeol()
        stdscr.refresh()
        stdscr.addstr(1, 0, "Analyzing URL: {0}".format(url))
        stdscr.addstr(2, 0, "")
        stdscr.refresh()
        # print "url " + str(url)
        # print "progress percent " + str(progress_percent)

    # noinspection PyBroadException
    def url_list_diagnostics(self, article_url_list):
        """
        Provides a diagnostic report of the scrapability of a list of articles
        including:
            - The number of completeley scrapable articles
            - The number of completeley unscrapable articles
            - The number of articles missing authors
            - The number of articles missing dates
            - The number of articles missing titles
        :param article_url_list:
        :return: a dictionary of lists, where each dictionary is a list of
                 the articles missing the attributes from each key
                    - title
                    - author
                    - date
        """

        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()

        num_urls = len(article_url_list)
        current_url_num = 1
        prog_percent = 0

        missing_title = []
        missing_author = []
        missing_date = []

        missing_author_title = []
        missing_author_date = []
        missing_title_date = []

        missing_title_author_date = []

        not_article = []

        scrapable_urls = []
        unscrapable_urls = []
        partially_scrapable_urls = []

        for article_url in article_url_list:
            article_url = article_url.rstrip()
            # print article_url

            self.report_progress(stdscr, article_url, prog_percent)
            try:
                article_dictionary = self.scrape_article(article_url, diagnostic=True)

                has_title = article_dictionary['title'] is not None
                has_author = article_dictionary['author'] is not None
                has_date = article_dictionary['date'] is not None

                # print has_title, has_author, has_date

                if has_author and has_date and has_title:
                    scrapable_urls.append(article_url)
                    # print "completeley scrapable:" + article_url
                elif not has_author and not has_date and not has_title:
                    # print "unscrapeable: " + article_url
                    partially_scrapable_urls.append(article_url)
                    missing_title_author_date.append(article_url)
                else:
                    # print "partially scrapeable: " + article_url
                    partially_scrapable_urls.append(article_url)

                    if not has_author and has_title and has_date:
                        missing_author.append(article_url)

                    if has_author and not has_title and has_date:
                        missing_title.append(article_url)

                    if has_author and has_title and not has_date:
                        missing_date.append(article_url)

                    if not has_author and not has_title and has_date:
                        missing_author_title.append(article_url)

                    if not has_author and has_title and not has_date:
                        missing_author_date.append(article_url)

                    if has_author and not has_title and not has_date:
                        missing_title_date.append(article_url)

            except NoStoryTextException:
                unscrapable_urls.append(article_url)
            except requests.exceptions.HTTPError:
                unscrapable_urls.append(article_url)
            except requests.exceptions.ConnectionError:
                unscrapable_urls.append(article_url)
            except ContentNotHTMLException:
                not_article.append(article_url)
            except Exception as e:
                curses.echo()
                curses.nocbreak()
                curses.endwin()
                traceback.print_exc()
                print str(e)
                print article_url
                exit()

            prog_percent = int(((current_url_num + 0.0) / num_urls) * 100)
            current_url_num += 1

        # end curses session
        curses.echo()
        curses.nocbreak()
        curses.endwin()

        print 'Generating Scrapeability Report...'

        fo = open('scrapeability_report.txt', "w")

        # categories for all articles
        num_scrapable_urls = len(scrapable_urls)
        num_partially_scrapable_urls = len(partially_scrapable_urls)
        num_unscrapable_urls = len(unscrapable_urls)
        num_not_articles = len(not_article)

        percent_scrapable = ((num_scrapable_urls + 0.0) / num_urls) * 100
        percent_partially_scrapable = ((num_partially_scrapable_urls + 0.0) / num_urls) * 100
        percent_unscrapable = ((num_unscrapable_urls + 0.0) / num_urls) * 100
        percent_not_article = ((num_not_articles + 0.0) / num_urls) * 100

        num_possible_to_scrape = num_partially_scrapable_urls + num_scrapable_urls
        percent_possible_fully_scrapable = ((num_scrapable_urls + 0.0) / num_possible_to_scrape) * 100
        percent_possible_partially_scrapable = ((num_partially_scrapable_urls + 0.0) / num_possible_to_scrape) * 100

        fo.write("URL List Scrapeability Statistics\n\n")

        fo.write('of the ' + str(num_urls) + ' total urls,\n')
        fo.write('\t' + str(num_scrapable_urls) + ' (' + str(percent_scrapable) + '%) were completely scrapeable,\n')
        fo.write('\t' + str(num_partially_scrapable_urls) + ' (' + str(percent_partially_scrapable))
        fo.write('%) were partially scrapeable,\n')
        fo.write('\t' + str(num_unscrapable_urls) + ' (' + str(percent_unscrapable) + '%) were unscrapeable, and\n')
        fo.write('\t' + str(num_not_articles) + ' (' + str(percent_not_article) + '%) were not articles.\n\n\n')

        fo.write('of the ' + str(num_possible_to_scrape) + ' urls that were at least partially scrapable,\n')
        fo.write('\t' + str(num_scrapable_urls) + ' (' + str(percent_possible_fully_scrapable) +
                 '%) were completely scrapeable, and\n')
        fo.write('\t' + str(num_partially_scrapable_urls) + ' (' + str(percent_possible_partially_scrapable) +
                 '%) were partially scrapeable.\n\n\n')

        # categories for partially scrapable articles
        if num_partially_scrapable_urls > 0:
            num_one_missing = len(missing_author) + len(missing_title) + len(missing_date)
            num_two_missing = len(missing_title_date) + len(missing_author_date) + len(missing_author_title)
            num_three_missing = len(missing_title_author_date)

            percent_one_missing = ((num_one_missing + 0.0) / num_partially_scrapable_urls) * 100
            percent_two_missing = ((num_two_missing + 0.0) / num_partially_scrapable_urls) * 100
            percent_three_missing = ((num_three_missing + 0.0) / num_partially_scrapable_urls) * 100

            fo.write("of the " + str(num_partially_scrapable_urls) + " partially scrapeable urls,\n")
            fo.write('\t' + str(num_one_missing) + ' (' + str(percent_one_missing) + '%) were missing one attribute,\n')
            fo.write('\t' + str(num_two_missing) + ' (' + str(percent_two_missing) + '%) were missing two attributes, '
                                                                                     'and\n')
            fo.write('\t' + str(num_three_missing) + ' (' + str(percent_three_missing) + '%) were missing three attributes')

            # categories for one_missing
            if num_one_missing > 0:
                percent_missing_author = ((len(missing_author) + 0.0) / num_one_missing) * 100
                percent_missing_title = ((len(missing_title) + 0.0) / num_one_missing) * 100
                percent_missing_date = ((len(missing_date) + 0.0) / num_one_missing) * 100

                fo.write("\n\n\nof the " + str(num_one_missing) + " articles missing one attribute,\n")
                fo.write('\t' + str(len(missing_author)) + ' (' + str(percent_missing_author) +
                         '%) were missing an author,\n')
                fo.write('\t' + str(len(missing_title)) + ' (' + str(percent_missing_title) +
                         '%) were missing a title, and\n')
                fo.write('\t' + str(len(missing_date)) + ' (' + str(percent_missing_date) +
                         '%) were missing a date\n')

            # categories for two_missing
            if num_two_missing:
                percent_missing_author_title = ((len(missing_author_title) + 0.0) / num_two_missing) * 100
                percent_missing_author_date = ((len(missing_author_date) + 0.0) / num_two_missing) * 100
                percent_missing_title_date = ((len(missing_title_date) + 0.0) / num_two_missing) * 100

                fo.write("\n\nof the " + str(num_two_missing) + " articles missing two attributes,\n")
                fo.write('\t' + str(len(missing_author_title)) + ' (' + str(percent_missing_author_title) +
                         '%) were missing an author and a title,\n')
                fo.write('\t' + str(len(missing_author_date)) + ' (' + str(percent_missing_author_date) +
                         '%) were missing an author and a date, and\n')
                fo.write('\t' + str(len(missing_title_date)) + ' (' + str(percent_missing_title_date) +
                         '%) were missing a title and a date\n')

        fo.write("\n\nURLs placed into relevant categories: \n\n")

        fo.write("\n\nLists of which articles are missing which attributes:\n\n")
        fo.write("Missing Author: " + str(len(missing_author)) + " articles\n")
        fo.write(pprint.pformat(missing_author, indent=4))
        fo.write("\n\nMissing Date: " + str(len(missing_date)) + " articles\n")
        fo.write(pprint.pformat(missing_date, indent=4))
        fo.write("\n\nMissing Title: " + str(len(missing_title)) + " articles\n")
        fo.write(pprint.pformat(missing_title, indent=4))
        fo.write("\n\nMissing Author and Title: " + str(len(missing_author_title)) + " articles\n")
        fo.write(pprint.pformat(missing_author_title, indent=4))
        fo.write("\n\nMissing Author and Date: " + str(len(missing_author_date)) + " articles\n")
        fo.write(pprint.pformat(missing_author_date, indent=4))
        fo.write("\n\nMissing Date and Title: " + str(len(missing_title_date)) + " articles\n")
        fo.write(pprint.pformat(missing_title_date, indent=4))
        fo.write("\n\nMissing Author and Date and Title: " + str(len(missing_title_author_date)) + " articles\n")
        fo.write(pprint.pformat(missing_title_author_date, indent=4))

        fo.write("\n\nUnscrapeable URLs:\n")
        fo.write(pprint.pformat(unscrapable_urls, indent=4))
        fo.write("\n\nPartially Scrapeable URLs:\n")
        fo.write(pprint.pformat(partially_scrapable_urls, indent=4))
        fo.write("\n\nCompleteley Scrapeable URLs:\n")
        fo.write(pprint.pformat(scrapable_urls, indent=4))

        fo.close

        print 'Done'

    def scrape_url(self, article_url):
        """
        Scrapes a single UCSC Currents magazine article
        :param article_url:
        :return:
        """
        article_url = article_url.rstrip()
        print article_url
        try:
            article_dictionary = self.scrape_article(article_url)

            for key in article_dictionary:
                if key in article_dictionary and article_dictionary[key] is not None:
                    print key + ' found'

            self.write_article(article_dictionary)
        except NoStoryTextException:
            print "No storytext div found, parsing cancelled"


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

