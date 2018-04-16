import scrapy
import logging
from canvas_quiz_downloader.items import CourseItem
from canvas_quiz_downloader.items import QuizItem
from canvas_quiz_downloader.items import QuestionItem
from canvas_quiz_downloader.items import AllItem

from loginform import fill_login_form
import json


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

                # Choose which class you want to test
                # Distinguish the section number if there are multiple course names that are the same
                course_filter = ['MCSCI', 'MANTHR', 'MPHILO', 'MENSCI', 'MART', 'MECON', 'MENGL', 'MCHEM']
                if course_filter[6] == course_name:
                    # Instantiates a course item as seen in items.py
                    course_item = CourseItem()
                    course_item['course_term'] = course_term
                    course_item['course_name'] = course_name
                    course_item['course_level'] = course_level
                    course_item['course_section'] = course_section
                    course_item['course_link'] = course_url_extension

                    # Sends a Request to the current course link with an item object
                    nav_links = scrapy.Request(url=course_link, callback=self.parse_navlinks)
                    nav_links.meta['course_item'] = course_item
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
    # Sends the filtered nav links to be searched for their questions
    def parse_navlinks(self, response):
        course_item = response.meta['course_item']
        filters = ['announcements', 'discussion', 'modules', 'quizzes', 'external_tools', 'files', 'wiki',
                   'collaborations']
        nav_links = response.css('div.ic-app-course-menu').css('li.section').css('a::attr(href)').extract()
        nav_links_filtered = []

        # Filters out certain links
        for nav_link in nav_links:
            if nav_link == course_item['course_link']:
                continue
            if nav_link == (course_item['course_link'] + '/assignments'):
                continue

            # Appends nav_link to nav_links_filtered when False
            flag = False
            for i in filters:
                if i in nav_link:
                    flag = True
                    break

            if not flag:
                nav_links_filtered.append(nav_link)

        course_item['nav_links'] = nav_links_filtered

        if course_item['nav_links']:
            for link in course_item['nav_links']:
                full_link = self.base_url + link[1:]
                yield scrapy.Request(url=full_link, callback=self.parse_quiz_links, meta={'course_item': course_item})
        else:
            return course_item

    # Gathers the potential quiz names and their links.
    # Sends them off to be validated if they actually are quizzes.
    def parse_quiz_links(self, response):
        course_item = response.meta['course_item']
        qanda_item = QuestionItem()
        quiz_item = QuizItem()

        # Check the type of link and whichever one is not empty search their elements
        grades_page = response.css('div#assignments').css('th.title').css('a')
        assignsylla_page = response.css('div#assignment_panel').css('li')
        if grades_page:
            for quiz in grades_page:
                # Grabs the name and link of the potential quiz.
                # Right now the link could either be a dud or a juicy quiz.
                name = quiz.css('a::text').extract_first()
                link = quiz.css('a::attr(href)').extract_first()
                # quiz_names.append(name)
                # quiz_links.append(link)
                link = self.base_url + link[1:]
                quiz_item['quiz_name'] = name
                quiz_item['quiz_link'] = link
                qanda_item['quiz_name'] = name
                # all_item['course_item'] = course_item['nav_links']
                # all_item['quiz_item'] = quiz_item
                # yield all_item
                yield scrapy.Request(url=link, callback=self.check_quiz_validity, meta={'quiz_item': quiz_item})

        elif assignsylla_page:
            # The first element on an assignment page is useless hence the splice [1:]
            for quiz in assignsylla_page[1:]:
                name = quiz.css('a::text').extract_first()
                link = quiz.css('a::attr(href)').extract_first()
                # quiz_names.append(name)
                # quiz_links.append(link)
                link = self.base_url + link[1:]
                quiz_item['quiz_name'] = name
                quiz_item['quiz_link'] = link
                qanda_item['quiz_name'] = name
                # all_item['course_item'] = course_item['nav_links']
                # all_item['quiz_item'] = quiz_item
                # yield all_item
                yield scrapy.Request(url=link, callback=self.check_quiz_validity, meta={'quiz_item': quiz_item})
        else:
            #yield all_item
            return quiz_item

    # Check if the page has the element that identifies as a quiz
    # If not then check for the iframe and recall check_quiz_validity
    # If it doesn't have it all, then return none
    def check_quiz_validity(self, response):
        quiz_item = response.meta['quiz_item']
        qanda_item = QuestionItem()

        all_item = AllItem()
        all_item['quiz_item'] = quiz_item

        quiz = response.css('div.text')
        points = response.css('div.header')
        #answers = quiz.css('div.answer')
        iframe = response.css('iframe#preview_frame').xpath('@src').extract_first()

        question_list = []
        answer_list = []

        # If there are quiz questions, then extract them and their answers.
        # If there is an iframe, meaning no quiz questions, then go to the iframe's link with callback to this function.
        # If there is neither quiz questions and an iframe, then return 'None'
        if quiz:
            # ans will be the counter since there are an equal number of quiz questions with their points.
            for ans_i, problem in enumerate(quiz):
                # Question scraping logic
                # Add more question types
                # 1. Multiple elements per question
                # 2. Question and image
                # 3. Multiple images
                # 4. Question and multiple images per question

                question = problem.css('div.user_content').css('p::text').extract_first()

                user_points = points[ans_i].css('div.user_points::text').extract_first()
                user_points = int(user_points.split('\n')[1])  # Finds the int in the string

                question_points = points[ans_i].css('span.question_points::text').extract_first()
                question_points = int(question_points.split('/')[1])  # Finds the int in the string

                if user_points == question_points:
                    # Answer is correct here
                    # Include answer_match_left_html for image answers
                    answer = problem.css('div.selected_answer').css('div.answer_match_left::text').extract_first()

                else:
                    # Wrong answer
                    answer = problem.css('div.correct_answer').css('div.answer_match_left::text').extract_first()

                    if not answer:
                        answer = problem.css('div.selected_answer').css('div.answer_match_left::text').extract_first()
                        answer = answer + 'WRONG'

                question_list.append(question)
                answer_list.append(answer)

            quiz_name = response.css('div.ic-app-nav-toggle-and-crumbs').css('span.ellipsible::text').extract()
            qanda_item['course_name'] = quiz_name[2]
            qanda_item['quiz_name'] = quiz_name[4]
            qanda_item['quiz_question'] = question_list
            qanda_item['quiz_answer'] = answer_list
            yield qanda_item
        elif iframe:
            link = self.base_url + iframe[1:]
            yield scrapy.Request(url=link, callback=self.check_quiz_validity,
                                 meta={'quiz_item': quiz_item})

        else:
            return qanda_item
