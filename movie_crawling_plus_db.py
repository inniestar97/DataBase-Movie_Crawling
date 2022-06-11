from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

import pymysql

baseUrl = "https://movie.naver.com/movie/sdb/rank/rmovie.naver?sel=pnt&date="

def open_db():
    conn = pymysql.connect(host='localhost', user='root',
                           password='Lee12151417!', db='naver_movie', unix_socket='/tmp/mysql.sock')
    cur = conn.cursor(pymysql.cursors.DictCursor)
    return conn, cur

def close_db(conn, cur):
    cur.close()
    conn.close()


def set_edge_driver() -> WebDriver:
    op = webdriver.EdgeOptions()
    driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=op)
    return driver

def get_movie_rate(soup: BeautifulSoup):
    
    try:
        scoreDiv = soup.select_one("div.mv_info").select_one("div.main_score").select("div.star_score")
    except AttributeError:
        return (None, None, None)

    audiRate = None
    netiRate = None
    criticRate = None
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
            nums = scoreDiv[0].select('em')
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
        
        nums = scoreDiv[2].select('em')
        rate = ""
        for i in nums:
            rate += i.getText()
        netiRate = float(rate)

    return (audiRate, criticRate, netiRate)

def get_movie_abstraction(soup: BeautifulSoup):
    box = soup.select_one("dl.info_spec")
    summary = box.select_one("dt.step1+dd")
    grade_ = box.select_one("dt.step4+dd")

    span_summary = summary.select("span")
    openningYear: str = None #개봉연도
    runtime: int = None #상영시간
    try:
        runtime = int(span_summary[2].getText().strip()[0:len(span_summary[2].getText()) - 2])
        try:
            openningYear = span_summary[3].select_one('a').getText().strip()
        except IndexError:
            openningYear = None
    except ValueError:
        openningYear = span_summary[2].select_one('a').getText().strip()
        try:
            runtime = int(span_summary[1].getText().strip()[0:len(span_summary[1].getText()) - 2])
        except ValueError:
            runtime = None
    except IndexError:
        runtime = None
        openningYear = None
    
    grade = "" #영화등급
    try:
        grade = grade_.select_one('p').select_one('a').getText()
    except AttributeError:
        grade = None

    return (runtime, openningYear, grade)

def movie_info(movie_url: str):
    response = requests.get(movie_url)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    #영화제목
    try:
        movie_title = soup.select_one("h3.h_movie>a").getText()
    except AttributeError:
        return
    
    # 관람객, 평론가, 네티즌 평점
    audiRate, criticRate, netiRate = get_movie_rate(soup) 
    # 상영시간, 개봉연도, 영화등급
    runtime, openningYear, grade = get_movie_abstraction(soup)

    return movie_title, audiRate, criticRate, netiRate, runtime, openningYear, grade

def get_in_movie_url(url: str, driver: WebDriver):
    driver.get(url) 
    # 영화 코드
    movie_code = int(url.split('=')[1])
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.obj_section>div.link_movie.type2>ul.thumb_link_mv>li>a.thumb")
            )
        )
    except TimeoutException:
        return

    ret = movie_info(driver.current_url)
    if ret != None:
        return movie_code, ret[0], ret[1], ret[2], ret[3], ret[4], ret[5], ret[6]
    else:
        return

if __name__ == '__main__':

    insert_sql = """
        INSERT IGNORE INTO movie(id, title, audience_rate, critic_rate, netizen_rate, runtime, open_year, grade)
        VALUES
        (%s ,%s ,%s ,%s ,%s ,%s ,%s, %s)
    """    

    conn, cur = open_db()

    now = datetime.now() - timedelta(days=1)

    url = baseUrl + ''.join(str(now.date()).split('-'))
    browser = set_edge_driver()
    
    # TODO 24page 부터 시작하면된다.
    for i in range(0, 40):
        page = i + 1
        browser.get(url + "&page=" + str(page))
        browserMovieList = browser.find_elements(By.CSS_SELECTOR, "table.list_ranking>tbody>tr>td.title>div.tit5>a")

        movieList = [] 
        for movie in browserMovieList:
            movieList.append(movie.get_attribute("href"))

        data_list = []

        movieList_recur = [] 
        for movie in movieList:
            data = get_in_movie_url(movie, browser)
            print(data)

            if data != None:
                data_list.append(data)
            else:
                continue

            if len(data_list) >= 50:
                cur.executemany(insert_sql, data_list)
                conn.commit()
                data_list = []

            recurMovieList = browser.find_elements(By.CSS_SELECTOR, "div.obj_section>div.link_movie.type2>ul.thumb_link_mv>li>a.thumb")
            for mv in recurMovieList:
                movieList_recur.append(mv.get_attribute("href"))
        
        movieList_recur2 = []
        for movie in movieList_recur:
            data = get_in_movie_url(movie, browser)
            print(data)

            if data != None:
                data_list.append(data)
            else:
                continue

            if len(data_list) >= 50:
                cur.executemany(insert_sql, data_list)
                conn.commit()
                data_list = []

            recurMovieList2 = browser.find_elements(By.CSS_SELECTOR, "div.obj_section>div.link_movie.type2>ul.thumb_link_mv>li>a.thumb")
            for mv in recurMovieList2:
                movieList_recur2.append(mv.get_attribute("href"))

        for movie in movieList_recur2:
            data = get_in_movie_url(movie, browser)
            print(data)

            if data != None:
                data_list.append(data)
            else:
                continue

            if len(data_list) >= 50:
                cur.executemany(insert_sql, data_list)
                conn.commit()
                data_list = []


        cur.executemany(insert_sql, data_list)
        conn.commit()
    
    close_db(conn, cur)
            