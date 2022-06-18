from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from datetime import datetime, timedelta

import requests

import time
from bs4 import BeautifulSoup

movieUrlRated_by_Rancking = "https://movie.naver.com/movie/sdb/rank/rmovie.naver?sel=pnt&date="
browser: WebDriver = None

def set_edge_driver(url: str) -> WebDriver:
    op = webdriver.EdgeOptions()
    driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=op)
    return driver

def get_movie_rate(soup: BeautifulSoup):

    scoreDiv = soup.select_one("div.mv_info").select_one("div.main_score").select("div.star_score")

    audiRate: float = None
    netiRate: float = None
    criticRate: float = None
    if len(scoreDiv) == 4:
        criticRate = None
        try: 
            nums = scoreDiv[0].select("em") 
            nums[0].getText()
            rate = ""
            for i in nums:
                rate += i.getText()
            audiRate = float(rate)
        except IndexError:
            audiRate = None 
        
        nums = scoreDiv[1].select("em")  
        rate = ""
        for i in nums:
            rate += i.getText()
        netiRate = float(rate)
    else:
        try:
            nums = scoreDiv[0].select("em")
            nums[0].getText()
            rate = ""
            for i in nums:
                rate += i.getText()
            audiRate = float(rate)
        except IndexError:
            audiRate = None

        try:
            nums = scoreDiv[1].select("em")
            nums[1].getText()
            rate = ""
            for i in nums:
                rate += i.getText()
            criticRate = float(rate)
        except IndexError:
            criticRate = None

        nums = scoreDiv[2].select("em")  
        rate = ""
        for i in nums:
            rate += i.getText()
        netiRate = float(rate)

    return (audiRate, criticRate, netiRate)

def get_movie_abstract(soup: BeautifulSoup):
    box = soup.select_one("dl.info_spec")
    summary = box.select_one("dt.step1+dd")
    director = box.select_one("dt.step2+dd")
    actor = box.select_one("dt.step3+dd")
    grade_ = box.select_one("dt.step4+dd")

    span_summary = summary.select("span")

    # 장르
    genres = []
    # 국가
    countries = []
    # 개봉날짜 >> 재개봉도 있음
    openningDate = []
    # 상영시간 (분)
    runtime: int
    # 감독
    directors = []
    try:
        runtime = int(span_summary[2].getText().strip()[0:len(span_summary[2].getText()) - 2])

        for a in span_summary[0].select('a'):
            genres.append(a.getText())
        genres = ','.join(genres)

        for a in span_summary[1].select('a'):
            countries.append(a.getText())
        countries = ','.join(countries)

        try:
            for a in span_summary[3].select('a'):
                openningDate.append(a.getText())
            openningDate = ''.join(openningDate).strip()
        except IndexError:
            openningDate = None

    except ValueError: 
        genres = None

        for a in span_summary[0].select('a'):
            countries.append(a.getText())
        countries = ','.join(countries)

        runtime = int(span_summary[1].getText().strip()[0:len(span_summary[1].getText()) - 2])

        try:
            for a in span_summary[2].select('a'):
                openningDate.append(a.getText())
            openningDate = ''.join(openningDate).strip()
        except IndexError:
            openningDate = None


    try:
        for d in director.select_one('p').select('a'):
            directors.append(d.getText())
        directors = ','.join(directors)
    except AttributeError:
        directors = None

    # 출연 배우
    actors = []
    try:
        for a in actor.select_one('p').select('a'):
            actors.append(a.getText())
        actors = ','.join(actors)
    except AttributeError:
        actors = None

    # 영화 등급
    grade = ""
    try:
        grade = grade_.select_one("p").select_one("a").getText()
    except AttributeError:
        grade = None

    return (genres, countries, runtime, openningDate, directors, actors, grade)
            

def get_image(soup: BeautifulSoup, url: str):

    imgBox = soup.select_one("div.photo").select_one("div.viewer").select_one("div.viewer_img").select_one("img._Img")

    return imgBox["src"]
    # img_list = []
    # i = 0
    # # while i < 10:
    # #     browser.implicitly_wait(10)

    # #     img_list.append(imgBox['src'])
    # #     nextButton[1].click()
    # #     i += 1

    # return img_list
    
def movie_info(movie_url: str):
    response = requests.get(movie_url)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # 영화 제목
    try:
        movie_title = soup.select_one("h3.h_movie>a").getText()
    except AttributeError:
        return

    print(movie_title)
    # 관람객, 평론가, 네티즌 평점
    audiRate, criticRate, netiRate = get_movie_rate(soup)
    print(audiRate, criticRate, netiRate)
    # 장르, 국가, 상영시간, 개봉날짜, 감독, 출연진, 영화등급
    genre, country, runtime, openningDate, director, actor, grade = get_movie_abstract(soup)
    imgList = get_image(soup, movie_url)
    # for i in imgList:
    #     print(i)


if __name__ == "__main__":
    now = datetime.now() - timedelta(days=1)

    baseUrl = movieUrlRated_by_Rancking + ''.join(str(now.date()).split('-')) 
    browser = set_edge_driver(baseUrl)

    for i in range(0, 40):
        page = i + 1
        browser.get(baseUrl + "&page=" + str(page))
        movie_list = browser.find_elements(By.CSS_SELECTOR, "table.list_ranking>tbody>tr>td.title>div.tit5>a") 

        for movie in movie_list:
            each_movie_url = movie.get_attribute("href")
            movie_info(each_movie_url)

            # print(browser.current_url)
            # movie_info(movie)