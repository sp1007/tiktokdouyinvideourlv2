from flask import Flask, render_template, json, request #, jsonify
import os

import threading
import time

from asyncio import CancelledError
import asyncio

from src.application import TikTokDownloader
from src.application.main_complete import TikTok

downloader = TikTokDownloader()
tiktok_downloader = None
cancelled = False
queued_urls = []

async def init_downloader():
    global downloader
    global tiktok_downloader
    downloader.project_info()
    await downloader.database.__aenter__()
    await downloader.read_config()
    downloader.check_config()
    await downloader.check_settings(False, )
    tiktok_downloader = TikTok(
            downloader.parameter,
            downloader.database,
        )
    print('init downloader done')

app = Flask(__name__, template_folder=None)

@app.route('/douyin/cookies/update/', methods=['POST'])
async def updateDouyinCookies():
    global downloader
    data = request.json
    resData = {"error":"EMPTY_CONTENT"}
    if "cookie" in data and len(data["cookie"])>0:
        #print(data['cookie'])
        downloader.cookie.extract(data['cookie'], True, 'cookie')
        await downloader.check_settings(restart=False)
        resData = {'status': 'Updated cookies'}
        #print('Updated cookies')
    response = app.response_class(
        response=json.dumps(resData),
        mimetype='application/json; charset=UTF-8',
        status=200
    )
    return response

@app.route('/tiktok/cookies/update/', methods=['POST'])
async def updateTiktokCookies():
    global downloader
    data = request.json
    resData = {"error":"EMPTY_CONTENT"}
    if "cookie" in data and len(data["cookie"])>0:
        #print(data['cookie'])
        downloader.cookie.extract(data['cookie'], True, 'cookie_tiktok')
        await downloader.check_settings(restart=False)
        resData = {'status': 'Updated cookies'}
        #print('Updated cookies')
    response = app.response_class(
        response=json.dumps(resData),
        mimetype='application/json; charset=UTF-8',
        status=200
    )
    return response

@app.route('/douyin/video/download/<id>', methods=['GET'])
def addedDownloadingDouyinVideo(id):
    resData = {"error":"EMPTY_CONTENT"}
    if id and len(id)>0:
        queued_urls.append({'id': id, 'tiktok': False})
        resData = {'status': 'Added to queue', 'id': id, 'tiktok': False}
    response = app.response_class(
        response=json.dumps(resData),
        mimetype='application/json; charset=UTF-8',
        status=200
    )
    return response

@app.route('/tiktok/video/download/<id>', methods=['GET'])
def addedDownloadingTiktokVideo(id):
    resData = {"error":"EMPTY_CONTENT"}
    if id and len(id)>0:
        queued_urls.append({'id': id, 'tiktok': True})
        resData = {'status': 'Added to queue', 'id': id, 'tiktok': True}
    response = app.response_class(
        response=json.dumps(resData),
        mimetype='application/json; charset=UTF-8',
        status=200
    )
    return response

async def background_task_async():
    global cancelled
    global tiktok_downloader
    global queued_urls
    while True and not cancelled: # and not empty id
        if tiktok_downloader!=None and tiktok_downloader.running and len(queued_urls)>0:
            id_info = queued_urls[0]
            queued_urls.pop(0)
            root, params, logger = tiktok_downloader.record.run(tiktok_downloader.parameter)
            # link_obj = tiktok_downloader.links #links_tiktok
            # ids = await link_obj.run(url)
            ids = [id_info['id']]
            async with logger(root, console=tiktok_downloader.console, **params) as record:
                await tiktok_downloader._handle_detail(
                    ids,
                    id_info['tiktok'],
                    record,
                )
        #print('background_task, ', tiktok_downloader, tiktok_downloader.running)
        time.sleep(1)

def background_thread():
    asyncio.run(background_task_async())

# main driver function
if __name__ == '__main__':
    
    asyncio.run(init_downloader())

    # Start the background task in a separate thread
    thread = threading.Thread(target=background_thread)
    thread.daemon = True  # This ensures the thread will exit when the main program exits
    thread.start()
    
    # scriptPath = os.path.dirname(__file__)
    # # run() method of Flask class runs the application
    # # on the local development server.
    app.run(host='0.0.0.0', port=3939) 
    cancelled = True
    print('Server stopped!')