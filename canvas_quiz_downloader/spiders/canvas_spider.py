import scrapy
import logging
from canvas_quiz_downloader.items import CourseItem
from canvas_quiz_downloader.items import QuizItem
from canvas_quiz_downloader.items import QuestionItem

from loginform import fill_login_form


class CanvasSpider(scrapy.Spider):
    name = "canvas"

    start_urls = ['https://modesto.instructure.com/courses']

    base_url = 'https://modesto.instructure.com/'   # Used to append with extension urls for a full link

    login_url = "https://modesto.instructure.com/login/canvas"
    login_user = '***'
    login_password = '***'

    # Login setup DONT TOUCH
    def start_requests(self):
        # let's start by sending a first request to login page
        yield scrapy.Request(self.login_url, self.parse_login)

    def parse_login(self, response):
        # got the login page, let's fill the login form...
        data, url, method = fill_login_form(response.url, response.body,
                                            self.login_user, self.login_password)

        # ... and send a request with our login data
        return scrapy.FormRequest(url, formdata=dict(data),
                                  method=method, callback=self.start_crawl)

    def start_crawl(self, response):
        # OK, we're in, let's start crawling the protected pages
        for url in self.start_urls:
            yield scrapy.Request(url)
    # END Login setup

    # Grabs the class id and places it into an item
    def parse(self, response):
        for course in response.css('tr.course-list-table-row'):
            # Only grabs course info for published courses
            course_publish = course.css('td.course-list-published-column').css('span::text').extract_first()
            if course_publish == 'Yes':

                # Grabs the course link
                course_url_extension = course.css('a::attr(href)').extract_first()
                course_link = self.base_url + course_url_extension[1:]

                # Grabs the course id as seen on Canvas
                course = course.css('span.name::text').extract_first().strip()

                # Splits the course id into their respective components
                course_term, course_name, course_level, course_section = course.split('-')


                # Instantiates a course item as seen in items.py
                item = CourseItem()
                item['course_term'] = course_term
                item['course_name'] = course_name
                item['course_level'] = course_level
                item['course_section'] = course_section
                item['course_link'] = course_url_extension

                FUCK

                # Sends a Request to the current course link with an item object
                nav_links = scrapy.Request(url=course_link, callback=self.parse_navlinks)
                nav_links.meta['item'] = item
                yield nav_links

    # General Course Parse Logic
    """
        1. Go to course_link and use rule to stay in each course while navigating to quizzes
        2. Search each link in div#left=side  <nav role="navigation" aria-label... > 
        
        3. Within each link of step 2 check if the link's are quizzes. (Use notebook research for this)
            3a. If not quizzes then immediately bounce the link to the next one
            3b. If they are quizzes then send the link over to the parse quizzes
    """

    # Grabs the navigational links on each course.
    # Filters out links that are in a list.
    # Sends the filtered nav links to be searched for for questions
    def parse_navlinks(self, response):
        item = response.meta['item']
        filters = ['announcements', 'discussion', 'modules', 'quizzes', 'external_tools', 'files', 'wiki',
                   'collaborations']
        nav_links = response.css('div.ic-app-course-menu').css('li.section').css('a::attr(href)').extract()
        nav_links_filtered = []

        # Filters out certain links
        for nav_link in nav_links:
            if nav_link == item['course_link']:
                continue
            if nav_link == (item['course_link'] + '/assignments'):
                continue

            flag = False    # Appends nav_link to nav_links_filtered when False
            for i in filters:
                if i in nav_link:
                    flag = True
                    break

            if not flag:
                nav_links_filtered.append(nav_link)

        item['nav_links'] = nav_links_filtered

        for link in item['nav_links']:
            full_link = self.base_url + link[1:]
            yield scrapy.Request(url=full_link, callback=self.parse_quiz_links, meta={'item': item})

    # Gathers the potential quiz names and their links.
    # Sends them off to be validated if they actually are quizzes.
    def parse_quiz_links(self, response):
        item = response.meta['item']
        quiz_names = []
        quiz_links = []

        # Check the type of link and whichever one is not empty search their elements
        grades = response.css('div#assignments').css('th.title').css('a')
        assign_sylla = response.css('div#assignment_panel').css('li')
        if grades:
            for quiz in grades:
                name = quiz.css('a::text').extract_first()
                link = quiz.css('a::attr(href)').extract_first()
                quiz_names.append(name)
                quiz_links.append(link)
                link = self.base_url + link[1:]
                item['quiz_name'] = name
                item['quiz_link'] = link
                yield scrapy.Request(url=link, callback=self.check_quiz_validity, meta={'item': item})
        elif assign_sylla:
            for quiz in assign_sylla[1:]:
                name = quiz.css('a::text').extract_first()
                link = quiz.css('a::attr(href)').extract_first()
                quiz_names.append(name)
                quiz_links.append(link)
                link = self.base_url + link[1:]
                item['quiz_name'] = name
                item['quiz_link'] = link
                yield scrapy.Request(url=link, callback=self.check_quiz_validity, meta={'item': item})
        yield item

    """
        1. Check for div.user_content
            1a. If NOT then look for iframe#preview_frame and Request url
            1b. If YES then look for questions and answers
        2 Questions will be in 'div.user_content::text'.extract()
    """
"""
    def check_quiz_validity(self, response):
        item = response.meta['item']

        quiz = response.css('div.text')
        answers = quiz.css('div.answer')
        iframe = response.css('iframe#preview_frame').xpath('@src').extract_first()

        question_list = []
        answer_list = []

        # If there are quiz questions, then extract them and their answers.
        # If there is an iframe, meaning no quiz questions, then go to the iframe's link with callback to this function.
        # If there is neither quiz questions and an iframe, then return 'None'
        if quiz and answers:
            for i in quiz:
                # Code for when "Answers will be shown after your last attempt"
                # Check for point on each question
                answers_hidden = response.css('div.alert')
                if answers_hidden:
                    user_points = response.css('div.header').css('div.user_points::text').extract_first()
                    question_points = response.css('div.header').css('span.question_points::text').extract_first()
                    item['user_points'] = user_points
                    item['question_points'] = question_points
                    if user_points == question_points:
                        question = i.css('div.user_content::text').extract_first()
                        answer = i.css('div.selected_answer').css('div.answer_match_left::text').extract_first()
                        question_list.append(question)
                        answer_list.append(answer)
                        continue

                # Add more question types
                # 1. Multiple elements per question
                # 2. Question and image
                # 3. Multiple images
                # 4. Question and multiple images per question
                #question = i.css('div.user_content').extract_first()
                question = i.css('div.user_content').css('p::text').extract_first()



                answer = i.css('div.correct_answer').css('div.answer_match_left::text').extract_first()

                # Indicate that this is the wrong answer. "Answer hasn't been submitted yet :("
                if not answer:
                    answer = i.css('div.wrong_answer').css('div.answer_match_left::text')

                question_list.append(question)
                answer_list.append(answer)

            item['quiz_questions'] = question_list
            item['quiz_answers'] = answer_list
            yield item
        elif iframe:
            link = self.base_url + iframe[1:]
            yield scrapy.Request(url=link, callback=self.check_quiz_validity, meta={'item': item})

        else:
            item['quiz_questions'] = ['None']
            item['quiz_answers'] = ['None']
            yield item
"""

























