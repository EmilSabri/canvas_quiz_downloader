import scrapy
from canvas_quiz_downloader.items import QuestionItem
import logging


class subreddit_all(scrapy.Spider):
    name = 'test'

    start_urls = [
        'file:///C:/Users/Emil%20Sabri/Desktop/Projects/canvas_quiz_downloader/canvas_quiz_downloader/test.html'
    ]

    def parse(self, response):
            qanda_item = QuestionItem()

            quiz = response.css('div.text')
            # answers = quiz.css('div.answer')
            iframe = response.css('iframe#preview_frame').xpath('@src').extract_first()

            question_list = []
            answer_list = []

            # If there are quiz questions, then extract them and their answers.
            # If there is an iframe, meaning no quiz questions, then go to the iframe's link with callback to this function.
            # If there is neither quiz questions and an iframe, then return 'None'
            if quiz:
                for i in quiz:
                    # Code for when "Answers will be shown after your last attempt"
                    # Check for point on each question
                    answers_hidden = response.css('div.alert')
                    if answers_hidden:
                        user_points = response.css('div.header').css('div.user_points::text').extract_first()
                        user_points = int(user_points.split('\n')[1])  # Finds the int in the string

                        question_points = response.css('div.header').css('span.question_points::text').extract_first()
                        question_points = int(question_points.split('/')[1])  # Finds the int in the string

                        qanda_item['user_points'] = user_points + 1
                        qanda_item['question_points'] = question_points + 2

                        if user_points == question_points:
                            question = i.css('div.user_content::text').extract_first().strip()
                            answer = i.css('div.selected_answer').css('div.answer_match_left::text').extract_first()
                            question_list.append(question)
                            answer_list.append(answer)
                            continue
                        else:
                            question = i.css('div.user_content::text').extract_first().strip()
                            # wrong answer
                            answer = i.css('div.selected_answer').css('div.answer_match_left::text').extract_first()
                            question_list.append(question)
                            answer_list.append(answer)
                            continue

                    elif not answers_hidden:
                        # Add more question types
                        # 1. Multiple elements per question
                        # 2. Question and image
                        # 3. Multiple images
                        # 4. Question and multiple images per question
                        # question = i.css('div.user_content').extract_first()

                        question = i.css('div.user_content').css('p::text').extract_first().strip()
                        answer = i.css('div.correct_answer').css('div.answer_match_left::text').extract_first()

                        # Indicate that this is the wrong answer. "Answer hasn't been submitted yet :("
                        if not answer:
                            answer = i.css('div.wrong_answer').css('div.answer_match_left::text')

                        question_list.append(question)
                        answer_list.append(answer)

                qanda_item['quiz_question'] = question_list
                qanda_item['quiz_answer'] = answer_list
                yield qanda_item
            elif iframe:
                link = self.base_url + iframe[1:]
                yield scrapy.Request(url=link, callback=self.check_quiz_validity, meta={'quiz_item': quiz_item})

            else:
                return qanda_item
