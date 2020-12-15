# coding: UTF-8
from flask import Flask, render_template, request,send_file,after_this_request,make_response,jsonify,redirect, url_for, send_from_directory
import pandas as pd
import os
import requests
import base64
import json
from requests import Request, Session
from io import BytesIO
from PIL import Image
import jaconv
import re
import numpy as np
import time
import qrcode


app = Flask(__name__)

UPLOAD_DIR = './uploads'
ALLOWED_EXTENSIONS = set(['png','jpg','jpeg',])
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

SAVE_DIR='./uploads'

ut = time.time()

@app.route('/')
def hello():
    #return render_template('index.html')
    return render_template('basic_design.html')

@app.route('/result1', methods=['POST'])
def hello_test():
    upload_files = request.files.getlist('img[]')
    file = upload_files[0]
    filename=str(time.time())+".png"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
    val = input('Enter number: ')
    val=int(val)
    time.sleep(4)
    return render_template('qrcode3.html',val=val)

    #return render_template('qrcode2.html',ut=ut,path1=path1,result=result,path1_sj=path1_sj,mojibake=mojibake,_11_patient_name_kanji=_11_patient_name_kanji,birthday_gengou=birthday_gengou,birthday=birthday)



@app.route('/wait')
def wait_page():
    return render_template('wait.html')




def allwed_file(filename):
    # .があるかどうかのチェックと、拡張子の確認
    # OKなら１、だめなら0
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/images/qrsample.png')
def uploaded_file2():
    return send_from_directory(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png")

@app.route('/uploads/images/qrsample_sj.png')
def uploaded_file5():
    return send_from_directory(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png")

@app.route('/uploads/input_data.png')
def uploaded_file3():
    return send_from_directory(app.config['UPLOAD_FOLDER'], "input_data.png")

@app.route('/uploads/images/load.gif')
def uploaded_file4():
    return send_from_directory(app.config['UPLOAD_FOLDER'] + "/images", "load.gif")


@app.route('/uploads/<path:path>')
def uploaded_file6(path):
    return send_from_directory(app.config['UPLOAD_FOLDER'], path)


## おまじない
if __name__ == "__main__":
    app.run(debug=True)