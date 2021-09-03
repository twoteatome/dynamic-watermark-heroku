from typing import Optional
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import cv2
import random
import numpy as np
import os
import re
import psycopg2
import urllib.request
import string

description = """
Dynamic Password Watermark API Document helps you to create, delete and get password of facebook id. 🚀

You will be able to:

* **Create password for user** (Required CREATE_TOKEN as key and facebook id as user, if password of this user existed, it will return password, otherwise create new password).
* **Delete password** (Required DELETE_TOKEN as key and password as password).
* **Get password of all user** (Required GET_TOKEN, return all facebook id and password).
* **Refresh to get newest data from database** (Required REFRESH_TOKEN).
* **Create HTML code for imgur album** (Required CODE_GENERATE_TOKEN).
"""

allData = {}
allImage = {}
filename = []
DATABASE_URL = os.environ['DATABASE_URL']

RED_COLOR = int(os.environ['RED_COLOR'])
GREEN_COLOR = int(os.environ['GREEN_COLOR'])
BLUE_COLOR = int(os.environ['BLUE_COLOR'])
NOTFOUND_URL = os.environ['NOTFOUND_URL']
HEROKU_APP_NAME = os.environ['HEROKU_APP_NAME']
ADMIN_TOKEN = os.environ['ADMIN_TOKEN']
REFRESH_TOKEN = os.environ['REFRESH_TOKEN']
HOMEPAGE_URL = os.environ['HOMEPAGE_URL']
CREATE_TOKEN = os.environ['CREATE_TOKEN']
CODE_GENERATE_TOKEN = os.environ['CODE_GENERATE_TOKEN']
GET_TOKEN = os.environ['GET_TOKEN']
DELETE_TOKEN = os.environ['DELETE_TOKEN']
MAX_WATERMARK = int(os.environ['MAX_WATERMARK'])
OPACITY = float(os.environ['OPACITY'])
FONT_SCALE = float(os.environ['FONT_SCALE'])
THICKNESS = int(os.environ['THICKNESS'])
PASSWORD_LENGTH = max(min(int(os.environ['PASSWORD_LENGTH']), 50), 1)

app = FastAPI(
    title="Dynamic Password Watermark",
    description=description,
    version="1.0",
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    docs_url="/" + ADMIN_TOKEN + "/admin",
    redoc_url=None
)

homepageUrl = HOMEPAGE_URL.replace('https://', '').replace('http://', '')

origins = [
    "http://" + homepageUrl,
    "https://" + homepageUrl,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
)

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS m_password (password VARCHAR(50) PRIMARY KEY, username VARCHAR UNIQUE NOT NULL)')
conn.commit()
cur.execute('CREATE TABLE IF NOT EXISTS m_imgur (imageid VARCHAR(50) PRIMARY KEY, link VARCHAR UNIQUE NOT NULL)')
conn.commit()
cur.execute('SELECT * FROM m_password')
rows = cur.fetchall()
for row in rows:
    (w, h), b = cv2.getTextSize(text=row[0], fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=FONT_SCALE, thickness=THICKNESS)
    allData[row[0]] = {"user": row[1], "width": w, "height": h, "bound": b}
cur.execute('SELECT * FROM m_imgur')
rows1 = cur.fetchall()
for row1 in rows1:
    allImage[row1[0]] = row1[1]
cur.close()
conn.close()

urllib.request.urlretrieve(NOTFOUND_URL, "404.jpg")


def remove_file(name: str):
    os.remove(name + ".webp")
    filename.remove(name)


@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Congratulation ! Setup successfully !"


@app.get("/get", response_class=PlainTextResponse)
def read_item(key: str, password: Optional[str] = None, user: Optional[str] = None):
    if key == GET_TOKEN:
        respo = ''

        if password and user is None:
            for key, value in allData.items():
                if password in key:
                    respo = respo + key + ', facebook: ' + value["user"] + '\n'
        elif user and password is None:
            for key, value in allData.items():
                if user in value["user"]:
                    respo = respo + key + ', facebook: ' + value["user"] + '\n'
        else:
            for key, value in allData.items():
                respo = respo + key + ', facebook: ' + value["user"] + '\n'

        return respo
    else:
        return "Error !"


@app.get("/refresh", response_class=PlainTextResponse)
def refresh_item(key: str):
    if key == REFRESH_TOKEN:
        allData = {}
        allImage = {}
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute('SELECT * FROM m_password')
        rows = cur.fetchall()
        for row in rows:
            (w, h), b = cv2.getTextSize(text=row[0], fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=FONT_SCALE, thickness=THICKNESS)
            allData[row[0]] = {"user": row[1], "width": w, "height": h, "bound": b}
        cur.execute('SELECT * FROM m_imgur')
        rows1 = cur.fetchall()
        for row1 in rows1:
            allImage[row1[0]] = row1[1]
        cur.close()
        conn.close()
        return "OK " + str(len(allData)) + ", " + str(len(allImage))
    else:
        return "Error !"


@app.get("/create", response_class=PlainTextResponse)
def create_item(key: str, user: str):
    if key == CREATE_TOKEN:
        password = ''
        
        if user.endswith('/'):
            user = user[:-1]
            
        for key, value in allData.items():
            if value["user"] == user:
                password = key
                break

        if password == '':
            password = ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=PASSWORD_LENGTH))
            while password in allData:
                password = ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=PASSWORD_LENGTH))
            (w, h), b = cv2.getTextSize(text=password, fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=FONT_SCALE, thickness=THICKNESS)
            allData[password] = {"user": user, "width": w, "height": h, "bound": b}
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cur = conn.cursor()
            cur.execute('INSERT INTO m_password (password, username) VALUES (%s, %s)', (password, user))
            conn.commit()
            cur.close()
            conn.close()
            return "Password cua facebook " + user + " la: " + password
        else:
            return "Password cua facebook " + user + " la: " + password
    else:
        return "Error !"


@app.get("/delete", response_class=PlainTextResponse)
def delete_item(key: str, password: str):
    if key == DELETE_TOKEN:
        user = allData.pop(password, None)
        if user is None:
            return "Error !"
        else:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cur = conn.cursor()
            cur.execute('DELETE FROM m_password WHERE password = %s', (password))
            conn.commit()
            cur.close()
            conn.close()
            return "Delete password of facebook " + str(user["user"])
    else:
        return "Error !"


@app.get("/generate", response_class=PlainTextResponse)
def generate_code(key: str, imgur: str, imagepath: str = "https://" + HEROKU_APP_NAME + ".herokuapp.com/image/"):
    if key == CODE_GENERATE_TOKEN:
        tmplink = ''
        if imgur.endswith('/'):
            tmplink = imgur + 'layout/blog'
        else:
            tmplink = imgur + '/layout/blog'

        tmplink = tmplink.replace('gallery', 'a')
        html = urllib.request.urlopen(tmplink).read().decode('utf-8')
        tmpfile = []
        for m in re.findall('.*?{"hash":"([a-zA-Z0-9]+)".*?"ext":"(\.[a-zA-Z0-9]+)".*?', html):
            if m not in tmpfile:
                tmpfile.append(m)

        insertquery = []
        codegen = '<!-- Add this code at header (inside <head> tag) <script src="https://cdn.jsdelivr.net/gh/twoteatome/dynamic-password-watermark-js@main/watermark.js"></script> -->'
        codegen = codegen + '\n\n'
        codegen = codegen + '<div id="dynamic-watermark-container"><input type="password" name="dynamic-watermark-input"><button onclick="handlePassword()">Giải mã</button></div>'
        codegen = codegen + '\n\n\n'
        for n in tmpfile:
            tmpname1 = ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=20))
            while tmpname1 in allImage:
                tmpname1 = ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=20))
            allImage[tmpname1] = n[0]
            codegen = codegen + '<figure class="wp-block-image size-large"><img src="' + imagepath + tmpname1 + '" loading="lazy" class="dynamic-watermark-image" alt=""></figure>' + '\n'
            insertquery.append((tmpname1, n[0]))

        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        sql_insert_query = """ INSERT INTO m_imgur (imageid, link) VALUES (%s,%s) """
        cur.executemany(sql_insert_query, insertquery)
#         args_str = ','.join(cur.mogrify("%s", (x, )) for x in insertquery)
#         cur.execute("INSERT INTO m_imgur (imageid, link) VALUES " + args_str)
        conn.commit()
        cur.close()
        conn.close()
        return codegen
    else:
        return "Error !"


@app.get("/image/{item_id}")
async def get_item(item_id: str, background_tasks: BackgroundTasks, q: Optional[str] = None):
    if q and q in allData and item_id in allImage:
        tmpname = ''.join(random.sample(string.ascii_lowercase, 10))
        while tmpname in filename:
            tmpname = ''.join(random.sample(string.ascii_lowercase, 10))
        filename.append(tmpname)

        urllib.request.urlretrieve("https://i.imgur.com/" + allImage[item_id] + ".webp", tmpname + ".webp")

        img = cv2.imread(tmpname + ".webp")
        height, width, channels = img.shape
        tmpvalue = allData[q]

        mark = np.zeros_like(img)

        defiX1 = []
        defiY1 = []
        defiX2 = []
        defiY2 = []

        for x in range(0, MAX_WATERMARK):
            offsetX = 0
            offsetY = 0
            checkOverlap = True
            while checkOverlap:
                offsetX = random.randint(0, width - tmpvalue["width"])
                offsetY = random.randint(tmpvalue["bound"], height - tmpvalue["height"])
                checkOverlap = False
                for k in range(0, len(defiX1)):
                    if (offsetX >= defiX2[k]) or (offsetX + tmpvalue["width"] <= defiX1[k]) or (offsetY + tmpvalue["height"] <= defiY1[k]) or (offsetY >= defiY2[k]):
                        checkOverlap = False
                    else:
                        checkOverlap = True
                        break

            defiX1.append(offsetX)
            defiY1.append(offsetY)
            defiX2.append(offsetX + tmpvalue["width"])
            defiY2.append(offsetY + tmpvalue["height"])

            cv2.putText(mark, q, (offsetX, offsetY), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=FONT_SCALE, color=(BLUE_COLOR, GREEN_COLOR, RED_COLOR), thickness=THICKNESS, lineType=cv2.LINE_AA)

        img = cv2.addWeighted(img, 1, mark, OPACITY, 0)
        cv2.imwrite(tmpname + ".webp", img)
        background_tasks.add_task(remove_file, tmpname)
        return FileResponse(tmpname + ".webp")
    else:
        return FileResponse("404.jpg")
