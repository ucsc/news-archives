from unittest import TestCase
import bs4
from bs4 import BeautifulSoup
from currentsArticleParser import GremlinZapper
from currentsArticleParser import CurrentsArticleParser
from requests.exceptions import HTTPError
import random


class TestGremlinZapper(TestCase):

    def test_cp1252(self):

        gzapper = GremlinZapper()

        result = gzapper.zap_string(u'\x80\x82\x83\x84\x85\x86\x87\x88\x89\x8A\x8B\x8C' +
                                    u'\x8E\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9A\x9B\x9C\x9E\x9F')

        try:
            result.decode('ascii')
        except UnicodeDecodeError:
            print "it was not a ascii-encoded unicode string"
            self.fail()
        else:
            print "It may have been an ascii-encoded unicode string"

    def test_unicode(self):
        gzapper = GremlinZapper()

        result = gzapper.zap_string(Utils.get_random_unicode(10))

        try:
            result.decode('ascii')
        except UnicodeDecodeError:
            print "it was not a ascii-encoded unicode string"
            self.fail()
        except UnicodeEncodeError:
            print "it was not a ascii-encoded unicode string"
            self.fail()
        else:
            print "It may have been an ascii-encoded unicode string"


class TestCurrentsArticleParser(TestCase):

    def test_zap_tag_contents(self):
        """
        Tests the conversion of Unicode and windows cp1252 characters to
        ascii equivalents within a bs4.BeautifulSoup.Tag object
        :return:
        """
        parser = CurrentsArticleParser()
        soup = BeautifulSoup('<b class="boldest">' +
                             u'\x80\x82\x83\x84\x85\x86\x87\x88\x89\x8A\x8B\x8C' +
                             u'\x8E\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9A\x9B\x9C\x9E\x9F' +
                             '<p>Back to the <a rel="index">' + Utils.get_random_unicode(10) +
                             '</a></p></b>', "html.parser")
        tag = soup.b
        parser.zap_tag_contents(tag)
        self.zap_tag_contents_test_helper(tag)

    def zap_tag_contents_test_helper(self, tag):
        """
        Helper function for zap_tag_contents_tester
        Recursively tests sub tags for non-ascii characters
        and fails if any are found
        :param tag:
        :return:
        """
        content_length = len(tag.contents)

        for x in range(0, content_length):
            if isinstance(tag.contents[x], bs4.element.NavigableString):
                try:
                    tag.contents[x].decode('ascii')
                except UnicodeDecodeError:
                    print "it was not a ascii-encoded unicode string"
                    self.fail()
                except UnicodeEncodeError:
                    print "it was not a ascii-encoded unicode string"
                    self.fail()
                else:
                    print "It may have been an ascii-encoded unicode string"
            elif isinstance(tag.contents[x], bs4.element.Tag):
                self.zap_tag_contents_test_helper(tag.contents[x])

    def test_get_soup_from_url(self):
        """
        tests that a bs4.BeautifulSoup.Soup object is created from a url
        :return:
        """
        parser = CurrentsArticleParser()
        try:
            parser.get_soup_from_url('http://google.com')
        except HTTPError:
            print "Soup was not created due to HTTPError"
            self.fail()
        else:
            print 'Soup was created'

    def test_get_url_slug(self):

        parser = CurrentsArticleParser()

        test_url_a = 'http://www.example.com:8080/sources/test'
        test_url_a_slug = 'test'
        test_url_b = 'http://hello.net/slug.pdf'
        test_url_b_slug = 'slug'

        if test_url_a_slug != parser.get_url_slug(test_url_a):
            print "slug A did not match"
            self.fail()
        if test_url_b_slug != parser.get_url_slug(test_url_b):
            print "slug B did not match"
            self.fail()

    def test_html_to_markdown(self):
        parser = CurrentsArticleParser()
        test_html = '<b class="boldest">' + \
                    'THIS IS TEST HTML and' + \
                    'SOME MORE TEST HTML' + \
                    '<p>Back to the <a rel="index">' + 'INSIDE A LINK' + \
                    '</a></p></b>', "html.parser"
        try:
            parser.html_to_markdown(test_html)
        except HTTPError:
            print "Could not convert HTML to markdown"
            self.fail()


class Utils(object):

    @staticmethod
    def get_random_unicode(length):

        try:
            get_char = unichr
        except NameError:
            get_char = chr

        # Update this to include code point ranges to be sampled
        include_ranges = [
            (0x0021, 0x0021),
            (0x0023, 0x0026),
            (0x0028, 0x007E),
            (0x00A1, 0x00AC),
            (0x00AE, 0x00FF),
            (0x0100, 0x017F),
            (0x0180, 0x024F),
            (0x2C60, 0x2C7F),
            (0x16A0, 0x16F0),
            (0x0370, 0x0377),
            (0x037A, 0x037E),
            (0x0384, 0x038A),
            (0x038C, 0x038C),
        ]

        alphabet = [
            get_char(code_point) for current_range in include_ranges
                for code_point in range(current_range[0], current_range[1] + 1)
        ]
        return ''.join(random.choice(alphabet) for i in range(length))