## Video Snapshot Generator v2
## FFMPEG 
## Multipage Snapshot
## Fix Font Setting
## Divide between working dir and tmporary dir
## Snapshot generation based on Time Interval
## bugfix: numSnapshot
## 2021/04/26 04:46

import sys
import hashlib
import os
import subprocess
import mimetypes
import json
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw

FLAGSAVEPATH = 'relative'
FONT_TYPE = "/usr/share/fonts/nanum/NanumGothicBold.ttf"
FONT_SIZE_DEFAULT = 16
FONT_SIZE_LARGE = 32
MAX_INTERVAL = 60
PAGE_SNAPSHOT = 16
SNAPSHOT_COL = 4
UNIT_WIDTH = 450
META_HEIGHT = 125
PADDING = 5
FILL_COLOR = "white"
OUTLINE_COLOR = "black"
NumTotal = 0

def ffprobe(fileName):
    cmd = ['ffprobe', '-show_format', '-show_streams', '-loglevel', 'quiet', '-print_format', 'json', fileName]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err =  p.communicate()
    if err:
        print(err)
        return None
    else:
        return json.loads(out.decode('utf-8'))

def drawText(draw, s, posX, posY, fontSize):
    fontType = ImageFont.truetype(FONT_TYPE, fontSize, encoding="unic")

    # thin border
    draw.text((posX-1, posY), s, font=fontType, fill=OUTLINE_COLOR)
    draw.text((posX+1, posY), s, font=fontType, fill=OUTLINE_COLOR)
    draw.text((posX, posY-1), s, font=fontType, fill=OUTLINE_COLOR)
    draw.text((posX, posY+1), s, font=fontType, fill=OUTLINE_COLOR)

    # thicker border
    draw.text((posX-1, posY-1), s, font=fontType, fill=OUTLINE_COLOR)
    draw.text((posX+1, posY-1), s, font=fontType, fill=OUTLINE_COLOR)
    draw.text((posX-1, posY+1), s, font=fontType, fill=OUTLINE_COLOR)
    draw.text((posX+1, posY+1), s, font=fontType, fill=OUTLINE_COLOR)

    draw.text((posX, posY), s, FILL_COLOR, font=fontType)

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
    
def timeFormat(s):
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

def gcd(a, b):
    while (b != 0):
        temp = a % b
        a = b
        b = temp
    return abs(a)

def reduceFraction(num, den):
    gcd_result = gcd(num, den)
    num = num/ gcd_result
    den = den / gcd_result
    return num, den

def calcHashMD5(path):     
    file_hash = hashlib.md5()
    with open(path, "rb") as f:                
        for kk in range(64):
            chunk = f.read(8192)
            file_hash.update(chunk)            
    return file_hash.hexdigest()

def snapshot(fileName):
    sPath = Path(fileName)
    metaInfo = ffprobe(fileName)
    metaFormat = metaInfo['format']

    metaVid = {}
    metaAud = {}
    for item in metaInfo['streams']:
        if item['codec_type'] == 'video':
            metaVid = item
        if item['codec_type'] == 'audio':
            metaAud = item

    if not metaAud:
        metaAud['codec_name'] = 'N/A'

    num, den = metaVid['avg_frame_rate'].split('/')
    if den == '0':
        num, den = metaVid['r_frame_rate'].split('/')
    if den == '0':
        fps = 'N/A'
    else:
        fps = f'{(int(num) / int(den)):.2f}'
    duration = float(metaFormat['duration'])

    num, den = reduceFraction(int(metaVid['width']), int(metaVid['height']))

    metaInfo = f'File Name: {fileName}\n'
    metaInfo = metaInfo + f"Size: {sizeof_fmt(int(metaFormat['size']))}\n"
    metaInfo = metaInfo + f"Resolution: {metaVid['width']}×{metaVid['height']}({num:.0f}:{den:.0f}), Bitrate: {float(metaFormat['bit_rate'])/1000000:.2f} Mbit/s\n"
    metaInfo = metaInfo + f"Video Codec: {metaVid['codec_name']}, Audio Codec: {metaAud['codec_name']}\n"
    metaInfo = metaInfo + f"Duration: {timeFormat(duration)}, FPS: {fps}"
    print(metaInfo)

    numSnapshot =  int(duration / MAX_INTERVAL)
    if numSnapshot < PAGE_SNAPSHOT:
        numSnapshot = PAGE_SNAPSHOT
    else:
        numSnapshot = (int(numSnapshot / 16) + 1) * 16

    timestep = duration / (numSnapshot + 1)

    width = int(UNIT_WIDTH - PADDING*2)
    height = int(width * metaVid['height'] / metaVid['width'])
    
    ss = 0
    for num in range(numSnapshot):
        ss = ss + timestep
        cmd = ['ffmpeg', '-y', '-loglevel', 'quiet', '-ss', f'{ss:.3f}','-i', fileName, '-frames:v', '1', '-vf', f'scale={width}:-1', f'/tmp/tmp_{num:03d}.bmp']
        subprocess.call(cmd)

    fullWidth = int(UNIT_WIDTH * SNAPSHOT_COL) + 10
    fullHeight = int((height + PADDING*2) * (PAGE_SNAPSHOT / SNAPSHOT_COL)) + META_HEIGHT

    pageCount = 0
    for num in range(numSnapshot):
        if num % PAGE_SNAPSHOT == 0:
            row, col = 0, 0
            fullImg = Image.new('RGB', (fullWidth, fullHeight), 'white')
            draw = ImageDraw.Draw(fullImg)
            draw.text((15, 15), metaInfo, 'black', font=ImageFont.truetype(FONT_TYPE, FONT_SIZE_DEFAULT))
            # drawText(draw, metaInfo, 15, 15, FONT_SIZE_DEFAULT)
            sPage = f'Page: {pageCount+1:02d}/{int(numSnapshot/PAGE_SNAPSHOT):02d}'
            w, h = draw.textsize(sPage, font=ImageFont.truetype(FONT_TYPE, FONT_SIZE_LARGE))
            posX = int(fullWidth - w -15)
            posY = 15
            draw.text((posX, posY), sPage, 'black', font=ImageFont.truetype(FONT_TYPE, FONT_SIZE_LARGE))
            # drawText(draw, sPage, posX, posY, FONT_SIZE_LARGE)
            
        sTime = timeFormat(timestep * (num + 1)) 

        img = Image.open(f'/tmp/tmp_{num:03d}.bmp')
        draw = ImageDraw.Draw(img)

        w, h = draw.textsize(sTime, font=ImageFont.truetype(FONT_TYPE, FONT_SIZE_DEFAULT))
        posX = int((width - w) / 2)
        posY = height-25

        drawText(draw, sTime, posX, posY, FONT_SIZE_DEFAULT)

        # background image        
        oImg = Image.new('RGB', (width+2, height+2), 'black')
        oImg.paste(img, (1, 1))
        bImg = Image.new('RGB', (width+PADDING*2, height+PADDING*2), 'white')
        sImg = Image.new('RGB', (width+2, height+2), (175,175,175))
        bImg.paste(sImg, (PADDING+3, PADDING+3))
        bImg.paste(oImg, (PADDING-1, PADDING-1))

        posX = int(UNIT_WIDTH * col) + 5
        posY = int((height + PADDING*2) * row) + META_HEIGHT

        fullImg.paste(bImg, (posX, posY))
        
        col = col + 1
        if col % 4 == 0:
            row = row + 1
            col = 0
        
        if num % PAGE_SNAPSHOT == (PAGE_SNAPSHOT-1):
            pageCount += 1  
            if FLAGSAVEPATH == 'absolute':
                sParts = sPath.parts
                if len(sParts) > 1:
                    fullImg.save(f"./0.Snapshot/{sPath.parts[-2]}ㅣ{sPath.stem}_{pageCount:02d}_{int(numSnapshot/PAGE_SNAPSHOT):02d}.jpg")
                else:
                    fullImg.save(f"./0.Snapshot/{sPath.stem}_{pageCount:02d}_{int(numSnapshot/PAGE_SNAPSHOT):02d}.jpg")
            else:
                fullImg.save(os.path.join(sPath.parent, f"0.Snapshot/{sPath.stem}_{pageCount:02d}_{int(numSnapshot/PAGE_SNAPSHOT):02d}.jpg"))

    for num in range(numSnapshot):
        os.remove(f'/tmp/tmp_{num:03d}.bmp')

def Search(dirName):
    global NumTotal
    fileNames = os.listdir(dirName)
    for fileName in fileNames:
        fullPath = os.path.join(dirName, fileName)
        if os.path.isdir(fullPath):
            if fileName[:2] != '0.' and fileName[:2] != '9.' and fileName[0] != '.':
                NumTotal = Search(fullPath)

    if FLAGSAVEPATH == 'absolute':
        sPath = './.snapshot/processed'
    else:
        sPath = os.path.join(dirName,'0.Snapshot')
        if not os.path.exists(sPath):
            os.makedirs(sPath)
        sPath = os.path.join(dirName,'.snapshot')
        if not os.path.exists(sPath):
            os.makedirs(sPath)
        sPath = os.path.join(dirName,'.snapshot/processed')
        if not os.path.isfile(sPath):
            Path(sPath).touch()

    videoFiles = {}
    for fileName in fileNames:    
        fullPath = os.path.join(dirName, fileName)
        if 'video' in str(mimetypes.guess_type(fullPath)[0]):
            videoFiles[calcHashMD5(fullPath)] = fileName        
    procFiles = {}
    with open(sPath, "r") as f:
        text = f.read()
        if len(text) > 0:
            text = text.split('\n')[:-1]
            for row in text:
                row = row.split('\t')
                procFiles[row[1]] = row[0]
    
    targetFiles = {}
    for key, value in videoFiles.items():        
        if not key in procFiles:
            targetFiles[key] = value

    nTotal = len(videoFiles)
    nProc = len(procFiles)
    nRemain = len(targetFiles)

    print(dirName)
    print(f'Total: {nTotal}')
    print(f'Processed: {nProc}')
    print(f'Remaining: {nRemain}')

    cnt = 0
    for key, value in targetFiles.items():
        fullPath = os.path.join(dirName, value)
        snapshot(fullPath)
        with open(sPath, "a") as f:
            f.write(f'{value}\t{key}\n')
        cnt += 1
        print(cnt)
    
    return NumTotal + nTotal


if __name__ == '__main__':
    args = []
    for arg in sys.argv: 
        args.append(arg)
    if len(args) == 1:
        pass
    elif args[1] == '--absolute':
        FLAGSAVEPATH = 'absolute'
        if not os.path.exists('./0.Snapshot'):
            os.makedirs('./0.Snapshot')
        if not os.path.exists('./.snapshot'):
            os.makedirs('./.snapshot')
        if not os.path.isfile('./.snapshot/processed'):
            Path('./.snapshot/processed').touch()

    NumTotal = Search('./')
    print(f'Total Number of Video: {NumTotal}')
