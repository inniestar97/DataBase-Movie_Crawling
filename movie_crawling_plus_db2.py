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

    try:
        movie_img_url = soup.select_one("div.mv_info_area>div.poster>a>img")["src"]
    except TypeError:
        movie_img_url = soup.select_one("div.mv_info_area>div.poster>img")["src"]

    return movie_title, audiRate, criticRate, netiRate, runtime, openningYear, grade, movie_img_url

if __name__ == '__main__':

    insert_sql = """
        INSERT IGNORE INTO movie(id, title, audience_rate, critic_rate, netizen_rate, runtime, open_year, grade, imgURL)
        VALUES
        (%s ,%s ,%s ,%s ,%s ,%s ,%s, %s, %s)
    """    

    conn, cur = open_db()

    now = datetime.now() - timedelta(days=1)

    url = baseUrl + ''.join(str(now.date()).split('-'))
    # browser = set_edge_driver()
    
    for i in range(16, 40):
        page = i + 1
        print("current Page :", page)

        webpage = requests.get(url + "&page=" + str(page)).text
        soup = BeautifulSoup(webpage, "html.parser")
        a_source = soup.select("table.list_ranking>tbody>tr>td.title>div.tit5>a")

        data_list = []
        list_url = []
        for ur in a_source:
            list_url.append("https://movie.naver.com/" + ur['href'])

        movieList_recur = [] 
        for movie in list_url:
            print("current Page : ", page, ":", movie)
            in_url = movie
            webpage_re = requests.get(in_url).text
            soup = BeautifulSoup(webpage_re, "html.parser")
            a_thumb_source = soup.select("div.obj_section>div.link_movie.type2>ul.thumb_link_mv>li>a.thumb")

            for i in range(len(a_thumb_source)):
                movieList_recur.append("https://movie.naver.com/" + a_thumb_source[i]['href'])

            movie_code = movie.split('=')[1]
            data = movie_info(movie)

            if data != None:
                insert_list = list(data)
                insert_list.insert(0, movie_code)
                insert_list = tuple(insert_list)
                data_list.append(insert_list)
                if len(data_list) >= 30:
                    cur.executemany(insert_sql, data_list)
                    conn.commit()
                    data_list = []
            else:
                continue

        movieList_recur2 = []
        for movie in movieList_recur:
            print("Re: current Page : ", page, ":", movie)
            webpage_re_re = requests.get(movie).text
            soup = BeautifulSoup(webpage_re_re, "html.parser")
            a_thumb_source = soup.select("div.obj_section>div.link_movie.type2>ul.thumb_link_mv>li>a.thumb")

            for i in range(len(a_thumb_source)):
                movieList_recur2.append("https://movie.naver.com/" + a_thumb_source[i]['href'])

            movie_code = movie.split('=')[1]
            data = movie_info(movie)

            if data != None:
                insert_list = list(data)
                insert_list.insert(0, movie_code)
                insert_list = tuple(insert_list)
                data_list.append(insert_list)
                if len(data_list) >= 30:
                    cur.executemany(insert_sql, data_list)
                    conn.commit()
                    data_list = []
            else:
                continue

        for movie in movieList_recur2:
            print("Re, RE: current Page : ", page, ":", movie)
            movie_code = movie.split('=')[1]
            data = movie_info(movie)

            if data != None:
                insert_list = list(data)
                insert_list.insert(0, movie_code)
                insert_list = tuple(insert_list)
                data_list.append(insert_list)
                if len(data_list) >= 30:
                    cur.executemany(insert_sql, data_list)
                    conn.commit()
                    data_list = []
            else:
                continue
            
        cur.executemany(insert_sql, data_list)
        conn.commit()
        data_list = []
                
            
    close_db(conn, cur)
            