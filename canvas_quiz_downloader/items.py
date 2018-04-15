# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class CourseItem(scrapy.Item):
    # Important Course Info
    # Use later for categorizing the types of questions found and other stats related usage
    course_term = scrapy.Field()
    course_name = scrapy.Field()
    course_level = scrapy.Field()
    course_section = scrapy.Field()

    # Course and nav links are the extension url only.
    course_link = scrapy.Field()   # The link to a student's course
    nav_links = scrapy.Field()      # List of navigational links from each course page

    # Quiz questions and answers
    quiz_question = scrapy.Field()
    quiz_question_image = scrapy.Field()
    quiz_answer = scrapy.Field()
    quiz_answer_image = scrapy.Field()

    user_points = scrapy.Field()
    question_points = scrapy.Field()

    pass


class QuizItem(scrapy.Item):
    quiz_name = scrapy.Field()
    quiz_link = scrapy.Field()

    pass


class QuestionItem(scrapy.Item):
    quiz_question = scrapy.Field()
    quiz_question_image = scrapy.Field()
    quiz_answer = scrapy.Field()
    quiz_answer_image = scrapy.Field()

    user_points = scrapy.Field()
    question_points = scrapy.Field()
    pass
