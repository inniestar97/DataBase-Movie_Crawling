from datetime import datetime, timedelta
from xml.dom.minidom import Attr
import requests
from bs4 import BeautifulSoup

import pymysql

baseUrl = "https://movie.naver.com/movie/sdb/rank/rmovie.naver?sel=pnt&date="

insert_sql = """
    INSERT IGNORE INTO movie(id, title, audience_rate, critic_rate, netizen_rate, runtime, open_year, grade, imgURL)
    VALUES
    (%s ,%s ,%s ,%s ,%s ,%s ,%s, %s, %s)
"""    

insert_actor = """
    INSERT IGNORE INTO movie_actor(movie_code, actor_code, actor_name, lead_or_support, part_name, actor_imgSrc)
    VALUES
    (%s, %s, %s, %s, %s, %s)
"""

insert_director = """
    INSERT IGNORE INTO movie_director(movie_code, director_code, director_name, director_imgSrc)
    VALUES
    (%s, %s, %s, %s)
"""

insert_genre = """
    INSERT IGNORE INTO movie_genre(movie_code, genre_code, genre_name)
    VALUES
    (%s, %s, %s)
"""

insert_country = """
    INSERT IGNORE INTO movie_country(movie_code, country_code, country_name)
    VALUES
    (%s, %s, %s)
"""

data_movie_list = []
data_actor_list = []
data_director_list = []
data_genre_list = []
data_country_list = []

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
        try:
            netiRate = float(rate)
        except ValueError:
            netiRate = None

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

def get_movie_actors_directors(soup: BeautifulSoup, movie_code: int):

    box = soup.select_one("div.sub_tab_area>ul#movieEndTabMenu.end_sub_tab>li>a.tab02.off")

    try:
        detail_page = "https://movie.naver.com/movie/bi/mi/" + box['href'][1:]
    except TypeError:
        return None, None
    
    response = requests.get(detail_page).text
    detail_soup = BeautifulSoup(response, "html.parser")

    actors = detail_soup.select("div.obj_section.noline>div.made_people>div.lst_people_area.height100>ul.lst_people>li")
    actor_ret = []
    if len(actors) == 0:
        actor_ret = None
    else:
        for actor in actors:
            try:
                imgSrc = actor.select_one("p.p_thumb>a>img")['src']
            except TypeError:
                imgSrc = actor.select_one("p.p_thumb>span>img")['src']
            p_info = actor.select_one("div.p_info")
            
            try:
                name = p_info.select_one("a").getText()
            except AttributeError: 
                name = actor.select_one('p.p_thumb>span>img')['alt']

            try:
                actor_code = int(p_info.select_one("a")['href'].split('=')[1])
            except TypeError:
                actor_code = None

            in_part = 0 if p_info.select_one("div.part>p.in_prt>em").getText() == "주연" else 1
            try:
                part_name = p_info.select_one("div.part>p.pe_cmt>span").getText()
            except AttributeError:
                part_name = None

            actor_ret.append((movie_code, actor_code, name, in_part, part_name, imgSrc))

    director_ret = []
    try:
        directors_box = detail_soup.select_one("div.obj_section>div.director")
        directors = directors_box.select("div.dir_obj")

        for director in directors:
            imgSrc = director.select_one("p.thumb_dir>a>img")['src']
            dir_info = director.select_one("div.dir_product")
            director_code = int(dir_info.select_one('a.k_name')['href'].split('=')[1])
            name = dir_info.select_one('a.k_name')['title']
            director_ret.append((movie_code, director_code, name, imgSrc))
    except AttributeError:
        director_ret = None

    return actor_ret, director_ret

def get_movie_genres(soup: BeautifulSoup, movie_code: int):
    box = soup.select_one("div.mv_info_area>div.mv_info>dl.info_spec")
    genre_box = box.select_one("dt.step1+dd")
    genres_ = genre_box.select_one("p>span")
    genres = genres_.select("a")

    ret = []
    try:
        for genre in genres:
            genre_code = int(genre['href'].split('=')[1])
            genre_name = genre.getText()
            ret.append((movie_code, genre_code, genre_name))
    except ValueError:
        ret = None
    
    return ret

def get_movie_country(soup: BeautifulSoup, movie_code: int, check: bool):
    box = soup.select_one("div.mv_info_area>div.mv_info>dl.info_spec")
    _box = box.select_one("dt.step1+dd")
    countries_ = _box.select("p>span")

    if check == True:
        countries = countries_[1].select('a')
    else:
        countries = countries_[0].select('a')
    
    ret = []
    for country in countries:
        country_code = country['href'].split('=')[1] 
        country_name = country.getText()
        ret.append((movie_code, country_code, country_name))
    
    return ret
    

def movie_info(movie_url: str, movie_code: int, cur, conn):

    global insert_sql, insert_actor, insert_director, insert_genre, insert_country
    global data_movie_list, data_actor_list, data_director_list, data_genre_list, data_country_list

    response = requests.get(movie_url)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    #영화제목
    try:
        movie_title = soup.select_one("h3.h_movie>a").getText()
    except AttributeError:
        return

    try:
        movie_img_url = soup.select_one("div.mv_info_area>div.poster>a>img")["src"]
    except TypeError:
        movie_img_url = soup.select_one("div.mv_info_area>div.poster>img")["src"]
    
    print(movie_title)    
    # 관람객, 평론가, 네티즌 평점
    audiRate, criticRate, netiRate = get_movie_rate(soup) 
    # 상영시간, 개봉연도, 영화등급
    runtime, openningYear, grade = get_movie_abstraction(soup)
    movie_abstract = (movie_code, movie_title, audiRate, criticRate, netiRate, runtime, openningYear, grade, movie_img_url)

    genres = get_movie_genres(soup, movie_code)
    if genres != None:
        countries = get_movie_country(soup, movie_code, True)
    else:
        countries = get_movie_country(soup, movie_code, False)
    actors, directors = get_movie_actors_directors(soup, movie_code)

    data_movie_list.append(movie_abstract)
    # print(data_movie_list)
    if genres != None:
        data_genre_list += genres
    data_country_list += countries
    if actors != None:
        data_actor_list += actors
    if directors != None:
        data_director_list += directors 

    if len(data_movie_list) >= 10:
        cur.executemany(insert_sql, data_movie_list)
        conn.commit()
        data_movie_list = []
    if len(data_genre_list) >= 10:
        cur.executemany(insert_genre, data_genre_list)
        conn.commit()
        data_genre_list = []
    if len(data_country_list) >= 10:
        cur.executemany(insert_country, data_country_list) 
        conn.commit()
        data_country_list = []
    if len(data_actor_list) >= 10:
        cur.executemany(insert_actor, data_actor_list)
        conn.commit()
        data_actor_list = []
    if len(data_director_list) >= 10:
        cur.executemany(insert_director, data_director_list)
        conn.commit()
        data_director_list = []

#-----------------------------------------------------------------------------
#---------------main----------------------------------------------------------
#-----------------------------------------------------------------------------

if __name__ == '__main__':

    conn, cur = open_db()

    now = datetime.now() - timedelta(days=1)

    url = baseUrl + ''.join(str(now.date()).split('-'))
    # browser = set_edge_driver()

    # for i in range(10000):
    #     mv_cd = str(18000 + i)
        
    #     mv_url = "https://movie.naver.com/movie/bi/mi/basic.naver?code=" + mv_cd

    #     wepage = requests.get(mv_url).text
    #     soup = BeautifulSoup(wepage, "html.parser")

    #     movie_info(mv_url,int(mv_cd), cur, conn)

    
    for i in range(0, 40):
        page = i + 1
        print("current Page :", page)

        webpage = requests.get(url + "&page=" + str(page)).text
        soup = BeautifulSoup(webpage, "html.parser")
        a_source = soup.select("table.list_ranking>tbody>tr>td.title>div.tit5>a")

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
            movie_info(movie, movie_code, cur, conn)


        movieList_recur2 = []
        for movie in movieList_recur:
            print("Re: current Page : ", page, ":", movie)
            webpage_re_re = requests.get(movie).text
            soup = BeautifulSoup(webpage_re_re, "html.parser")
            a_thumb_source = soup.select("div.obj_section>div.link_movie.type2>ul.thumb_link_mv>li>a.thumb")

            for i in range(len(a_thumb_source)):
                movieList_recur2.append("https://movie.naver.com/" + a_thumb_source[i]['href'])

            movie_code = movie.split('=')[1]
            movie_info(movie, movie_code, cur, conn)


        for movie in movieList_recur2:
            print("Re, RE: current Page : ", page, ":", movie)
            movie_code = movie.split('=')[1]
            movie_info(movie, movie_code, cur, conn)
            
    cur.executemany(insert_sql, data_movie_list)
    conn.commit()
    cur.executemany(insert_genre, data_genre_list)
    conn.commit()
    cur.executemany(insert_country, data_country_list)
    conn.commit()
    cur.executemany(insert_actor, data_actor_list)
    conn.commit()
    cur.executemany(insert_director, data_director_list)
    conn.commit()

    close_db(conn, cur)
            