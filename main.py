from typing import Optional
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from PIL import Image, ImageDraw, ImageFont
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2
import urllib.request
import base64
import string
import random

app = FastAPI()
allData = {}
filename = []
DATABASE_URL = os.environ['DATABASE_URL']

RED_COLOR = int(os.environ['RED_COLOR'])
GREEN_COLOR = int(os.environ['GREEN_COLOR'])
BLUE_COLOR = int(os.environ['BLUE_COLOR'])
NOTFOUND_URL = os.environ['NOTFOUND_URL']
RESOURCE_URL = os.environ['RESOURCE_URL']
HOMEPAGE_URL = os.environ['HOMEPAGE_URL']
CREATE_TOKEN = os.environ['CREATE_TOKEN']
GET_TOKEN = os.environ['GET_TOKEN']
DELETE_TOKEN = os.environ['DELETE_TOKEN']
MAX_WATERMARK = int(os.environ['MAX_WATERMARK'])
OPACITY = int(os.environ['OPACITY'])
TEXT_SIZE = int(os.environ['TEXT_SIZE'])
ROTATE = int(os.environ['ROTATE'])
PASSWORD_LENGTH = min(int(os.environ['PASSWORD_LENGTH']), 50)

font = ImageFont.truetype('arial.ttf', TEXT_SIZE)
resourceUrl = ''
if RESOURCE_URL.endswith('/'):
    resourceUrl = RESOURCE_URL
else:
    resourceUrl = RESOURCE_URL + '/'
    
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
cur.execute('SELECT * FROM m_password')
rows = cur.fetchall()
for row in rows:
    allData[row[0]] = row[1]
cur.close()
conn.close()

urllib.request.urlretrieve(NOTFOUND_URL,"404.jpg")

@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Congratulation ! Setup successfully !"

@app.get("/get", response_class=PlainTextResponse)
def read_item(key: str):
    if key == GET_TOKEN:
        respo = ''
        for key, value in allData.items():
            respo = respo + key + ', facebook: ' + value + '\n'
        return respo
    else:
        return "Error !"
    
@app.get("/create", response_class=PlainTextResponse)
def create_item(key: str, user: str):
    if key == CREATE_TOKEN:
        password = ''
        for key, value in allData.items():
            if value == user:
                password = key
                break
                
        if password == '':
            password = ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=PASSWORD_LENGTH))
            while password in allData:
                password = ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=PASSWORD_LENGTH))
            allData[password] = user
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
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute('DELETE FROM m_password WHERE password = %s', (password))
        conn.commit()
        cur.close()
        conn.close()
        return "Delete password of facebook " + str(user)
    else:
        return "Error !"

@app.get("/image/{item_id:path}", response_class=PlainTextResponse)
def get_item(item_id: str, q: Optional[str] = None):
    if q and q in allData:
        tmpname = ''.join(random.sample(string.ascii_lowercase, 10))
        while tmpname in filename:
            tmpname = ''.join(random.sample(string.ascii_lowercase, 10))
        filename.append(tmpname)
            
        urllib.request.urlretrieve(resourceUrl + item_id, tmpname + ".png")
        # --- original image ---
        original_image = Image.open(tmpname + ".png").convert("RGBA")
        original_image_size = original_image.size

        # calculate text size in pixels (width, height)
        text_size = font.getsize(q) 

        # create image for text
        text_image = Image.new('RGBA', text_size, (255,255,255,0))
        text_draw = ImageDraw.Draw(text_image)

        # draw text on image
        text_draw.text((0, 0), q, (RED_COLOR, GREEN_COLOR, BLUE_COLOR, OPACITY), font=font)

        # rotate text image and fill with transparent color
        rotated_text_image = text_image.rotate(ROTATE, expand=True, fillcolor=(0,0,0,0))
        rotated_text_image_size = rotated_text_image.size

        # --- watermarks image ---
        combined_image = original_image

        defiX1 = []
        defiY1 = []
        defiX2 = []
        defiY2 = []

        for x in range(0, MAX_WATERMARK):
            offsetX = 0
            offsetY = 0
            checkOverlap = True
            while checkOverlap:
                offsetX = random.randint(0, original_image_size[0] - rotated_text_image_size[0])
                offsetY = random.randint(0, original_image_size[1] - rotated_text_image_size[1])
                checkOverlap = False
                for k in range(0, len(defiX1)):
                    if (offsetX >= defiX2[k]) or (offsetX + rotated_text_image_size[0] <= defiX1[k]) or (offsetY + rotated_text_image_size[1] <= defiY1[k]) or (offsetY >= defiY2[k]):
                        checkOverlap = False
                    else:
                        checkOverlap = True
                        break

            defiX1.append(offsetX)
            defiY1.append(offsetY)
            defiX2.append(offsetX + rotated_text_image_size[0])
            defiY2.append(offsetY + rotated_text_image_size[1])

            watermarks_image = Image.new('RGBA', original_image_size, (255,255,255,0))
            watermarks_image.paste(rotated_text_image, (offsetX, offsetY))
            combined_image = Image.alpha_composite(combined_image, watermarks_image)

        # --- result ---
        combined_image.save(tmpname + ".png")
        resdata = 'data:image/png;base64,' + base64.b64encode(open(tmpname + ".png", "rb").read()).decode('utf-8')
        os.remove(tmpname + ".png")
        filename.remove(tmpname)
        return resdata
    else:
        return 'data:image/jpg;base64,' + base64.b64encode(open("404.jpg", "rb").read()).decode('utf-8')
