
import bs4
from bs4 import BeautifulSoup
from unidecode import unidecode
import urllib
import re
import datetime
import requests

date_regex = re.compile(r"[A-Za-z]+\s*\d{1,2}\,\s*\d{4}")
end_story_regex = re.compile(r"\s*END\s*STORY\s*")
word_regex = re.compile(r"([^\s\n\r\t]+)")
gremlin_regex = re.compile(u"[\x80-\x9f]")

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
        text = re.sub(u"[\x80-\x9f]", fixup, text)
    return text

"""         end code        """


def zap_helper(content_item):
    if isinstance(content_item, bs4.element.NavigableString):
        unicode_entry = kill_gremlins(content_item)
        content_item = unidecode(unicode_entry)
    elif isinstance(content_item, bs4.element.Tag):
        [zap_helper(sub_item) for sub_item in content_item.contents]

    return content_item


def zap_tag_contents(tag):
    tag.contents = [zap_helper(content_item) for content_item in tag.contents]
    return tag


r = urllib.urlopen('http://currents.ucsc.edu/04-05/04-25/tobar.asp').read()
soup = BeautifulSoup(r, 'html.parser')

'''print(soup.prettify())'''

title = ''
author = ''
date = ''
images_dictionary = dict()

story_text = soup.find('div', class_='storytext')

'''for item in storyText.contents:
    print item'''

paragraphs = story_text.find_all('li')


story_string = ""

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

                    add_to_story = False
        elif item.string:
            match = date_regex.match(item.string)
            if match:
                '''print "match found abracadabra"'''
                date = datetime.datetime.strptime(item.string, "%B %d, %Y").strftime("%Y-%m-%d")
                add_to_story = False
        else:
            story_end = False
            # print item.contents
            # print item.name

            if item.name == 'table':
                # print "found a table"
                images = item.find_all('img')
                if images:
                    add_to_story = False
                    print "item has images"
                    # print item
                    for image in images:
                        image_src = image['src']
                        image_text = image.get_text()
                        matches = word_regex.findall(image_text)
                        image_text = ' '.join(matches)
                        # image_src = unicodedata.normalize('NFKD', image_src).encode('ascii','ignore')
                        # unicodedata.normalize('NFKD', image_text).encode('ascii','ignore')
                        images_dictionary[image_src] = image_text
            else:
                if item.contents:
                    if len(item.contents) >= 2:
                        if item.contents[0] == 'By ' and isinstance(item.contents[1], bs4.element.Tag) \
                                and item.contents[1].name == 'a':
                            author = item.contents[1].string
                            add_to_story = False

                    for cont in item.contents:
                        if isinstance(cont, bs4.element.Comment):
                            match = end_story_regex.match(cont.string)
                            if match:
                                # print "found end of story"
                                story_end = True
                if story_end:
                    break
    else:
        add_to_story = False

    if add_to_story:
        item = zap_tag_contents(item)
        for i in item.contents:
            print item
            print type(i)
        story_string += str(item)

# r = requests.post('http://heckyesmarkdown.com/go/#sthash.Xf1YNf4U.dpuf', data={'html':story_string, })

print story_string

'''
story = unidecode(r.text)

print "title: " + title
print "date: " + date
print "author: " + author
print "images:"
# print images_dictionary

for key in images_dictionary:
    print "    " + key + ":"
    print images_dictionary[key] + "\n"

print story
'''
