#準備

import random
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np

#Jupyterでインライン表示するための宣言
%matplotlib inline 
import os
import shutil
from tqdm import tqdm
import base64
import json
from requests import Request, Session
from io import BytesIO
from PIL import Image
import pandas as pd
import jaconv
import re
import cv2
import numpy as np
from symspellpy.symspellpy import SymSpell, Verbosity
import pickle
from pykakasi import kakasi
import Levenshtein
from collections import OrderedDict
import itertools

from statistics import mode
import time
from janome.tokenizer import Tokenizer
import math

#-----------------------------------------------------------------
# 基本は最頻値をとる。最頻値がない時は平均をとる。numsが空の時は0にする。
def mode_average(nums):
    try:
        return mode(nums)
    except:
        if len(nums)!=0:
            return round(sum(nums) / len(nums))
        else:
            try:
                return nums[0]
            except:
                return 0  #これは危ないかも




#回転させる
def rotate3(url,n_part,start,goal,angle2):
    start_time = time.time()
    #pathからbase64にする場合
    def pil_image_to_base64(img_path):###ここは最後に消す
        pil_image = Image.open(img_path)
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return str_encode_file

    #arrayからbase64にする場合
    def array_to_base64(img_array):
        pil_image = Image.fromarray(np.uint8(img_array))
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return str_encode_file 

    def get_fullTextAnnotation(json_data):
        text_dict = json.loads(json_data)
        try:
            text = text_dict["responses"][0]["fullTextAnnotation"]["text"]
            return text
        except:
            print(None)
            return None

    #str_encode_file = pil_image_to_base64(url)  

    img = cv2.imread(url)#これは全体
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    input_image=img[start*img.shape[0]//n_part:goal*img.shape[0]//n_part ,0::]#上部のみ

    # plt.figure(figsize=[50,50])
    # plt.imshow(input_image)


    str_encode_file = array_to_base64(input_image)# input_imageがarrayの時
    str_url = "https://vision.googleapis.com/v1/images:annotate?key="
    str_api_key = "AIzaSyDlRRYrHEdjParsfRmh96_3xfafOo1crWY"
    str_headers = {'Content-Type': 'application/json'}
    str_json_data = {
        'requests': [
            {
                'image': {
                    'content': str_encode_file
                },
                'features': [
                    {
                        'type': "DOCUMENT_TEXT_DETECTION",
                        'maxResults': 1
                    }
                ],"imageContext": {
        "languageHints": ["ja"]
      },
            }
        ]
    }

    obj_session = Session()
    obj_request = Request("POST",
                            str_url + str_api_key,
                            data=json.dumps(str_json_data),
                            headers=str_headers
                            )
    obj_prepped = obj_session.prepare_request(obj_request)
    obj_response = obj_session.send(obj_prepped,
                                    verify=True,
                                    timeout=60
                                    )
    #もとの出力
    if obj_response.status_code == 200:
        text = get_fullTextAnnotation(obj_response.text)

    elapsed_time = time.time() - start_time
    print ("API終了までにかかった時間:{0}".format(elapsed_time) + "[sec]")
    #行ごとの出力    
    text_dict = json.loads(obj_response.text)
    try:
        word_list=text_dict["responses"][0]["textAnnotations"][0]["description"].split("\n")

        len_sum=0
        now_num=0
        left=[]
        right=[]
        top=[]
        bottom=[]
        dic_list=[]

        for i in range(1,len(text_dict["responses"][0]["textAnnotations"])):
            len_sum+=len(text_dict["responses"][0]["textAnnotations"][i]["description"].replace(" ",""))
            try:
                left.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][0]["x"])
            except:
                pass
            try:
                right.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][1]["x"])
            except:
                pass
            try:
                right.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][2]["x"])
            except:
                pass
            try:
                left.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][3]["x"])
            except:
                pass

            try:
                bottom.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][0]["y"])
            except:
                pass
            try:
                bottom.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][1]["y"])
            except:
                pass
            try:
                top.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][2]["y"])
            except:
                pass
            try:
                top.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][3]["y"])
            except:
                pass

            if len_sum==len(word_list[now_num].replace(" ","")):
                len_sum=0
                #print("word:   "+word_list[now_num])
                dic={"word":word_list[now_num],"文字の縦幅":mode_average(top)-mode_average(bottom),"x":round(mode_average(left)+mode_average(right)),"y":round(mode_average(top)+mode_average(bottom))}
                dic_list.append(dic)
                now_num+=1
                left=[]
                right=[]
                top=[]
                bottom=[]
        elapsed_time = time.time() - start_time
        print ("for文を回し終わるまでにかかった時間:{0}".format(elapsed_time) + "[sec]")
        df = pd.DataFrame(dic_list)
        df=df.sort_values('y')
        df.reset_index()
        print("-------------------------------------------")
        print(df[df['word'].str.contains('険者番号')].iat[0,3]-df[df['word'].str.contains('担者番号')].iat[0,3])
        print(df[df['word'].str.contains('険者番号')].iat[0,2]-df[df['word'].str.contains('担者番号')].iat[0,2])
        try:
            tate=df[df['word'].str.contains('険者番号')].iat[0,3]-df[df['word'].str.contains('担者番号')].iat[0,3]#右から左を引く
            yoko=df[df['word'].str.contains('険者番号')].iat[0,2]-df[df['word'].str.contains('担者番号')].iat[0,2]#右から左を引く
            tan=tate/yoko
            print("-------------------------------------------")
            atan = np.arctan(tan)*180/math.pi
            print("角度:"+str(atan))
            print("-------------------------------------------")
        except:
            print("初期値使った")
            atan=angle2
    except:
        print("初期値使った2")
        atan=angle2
    
    if atan>10 or atan<-10:
        print("初期値使った3")
        atan=angle2
    elapsed_time = time.time() - start_time
    print ("elapsed_time:{0}".format(elapsed_time) + "[sec]")

    
    
    # 画像読み込み
    img = cv2.imread(url)
    h, w = img.shape[:2]
    size = (w, h)

    # 回転角の指定
    angle = atan 
    print("angle:"+str(angle))
    angle_rad = angle/180.0*np.pi

    # 回転後の画像サイズを計算
    w_rot = int(np.round(h*np.absolute(np.sin(angle_rad))+w*np.absolute(np.cos(angle_rad))))
    h_rot = int(np.round(h*np.absolute(np.cos(angle_rad))+w*np.absolute(np.sin(angle_rad))))
    size_rot = (w_rot, h_rot)

    # 元画像の中心を軸に回転する
    center = (w/2, h/2)
    scale = 1.0
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)

    # 平行移動を加える (rotation + translation)
    affine_matrix = rotation_matrix.copy()
    affine_matrix[0][2] = affine_matrix[0][2] -w/2 + w_rot/2
    affine_matrix[1][2] = affine_matrix[1][2] -h/2 + h_rot/2

    img_rot = cv2.warpAffine(img, affine_matrix, size_rot, flags=cv2.INTER_CUBIC)
#     plt.figure(figsize=[50,50])
#     plt.imshow(img_rot)
    return img_rot



#ただ上からOCR結果を表示する改良型関数
#最初の引数はPATHではなくarray
def recognize8(array,n_part,start,goal):
    start_time = time.time()
    #pathからbase64にする場合
    def pil_image_to_base64(img_path):###ここは最後に消す
        pil_image = Image.open(img_path)
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return str_encode_file

    #arrayからbase64にする場合
    def array_to_base64(img_array):
        pil_image = Image.fromarray(np.uint8(img_array))
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return str_encode_file 

    def get_fullTextAnnotation(json_data):
        text_dict = json.loads(json_data)
        try:
            text = text_dict["responses"][0]["fullTextAnnotation"]["text"]
            return text
        except:
            print(None)
            return None

    #str_encode_file = pil_image_to_base64(url)  
    
#     img = cv2.imread(url)
#     img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img=array
    
    input_image=img[start*img.shape[0]//n_part:goal*img.shape[0]//n_part ,0::]
#     plt.figure(figsize=[50,50])
#     plt.imshow(input_image)
    
    str_encode_file = array_to_base64(input_image)# input_imageがarrayの時
    str_url = "https://vision.googleapis.com/v1/images:annotate?key="
    str_api_key = "AIzaSyDlRRYrHEdjParsfRmh96_3xfafOo1crWY"
    str_headers = {'Content-Type': 'application/json'}
    str_json_data = {
        'requests': [
            {
                'image': {
                    'content': str_encode_file
                },
                'features': [
                    {
                        'type': "DOCUMENT_TEXT_DETECTION",
                        'maxResults': 1
                    }
                ],"imageContext": {
        "languageHints": ["ja"]
      },
            }
        ]
    }

    obj_session = Session()
    obj_request = Request("POST",
                            str_url + str_api_key,
                            data=json.dumps(str_json_data),
                            headers=str_headers
                            )
    obj_prepped = obj_session.prepare_request(obj_request)
    obj_response = obj_session.send(obj_prepped,
                                    verify=True,
                                    timeout=60
                                    )
    #もとの出力
    if obj_response.status_code == 200:
        text = get_fullTextAnnotation(obj_response.text)
        
    elapsed_time = time.time() - start_time
    print ("API終了までにかかった時間:{0}".format(elapsed_time) + "[sec]")
    #行ごとの出力    
    text_dict = json.loads(obj_response.text)
    word_list=text_dict["responses"][0]["textAnnotations"][0]["description"].split("\n")

    len_sum=0
    now_num=0
    left=[]
    right=[]
    top=[]
    bottom=[]
    dic_list=[]

    for i in range(1,len(text_dict["responses"][0]["textAnnotations"])):
        len_sum+=len(text_dict["responses"][0]["textAnnotations"][i]["description"].replace(" ",""))
        try:
            left.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][0]["x"])
        except:
            pass
        try:
            right.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][1]["x"])
        except:
            pass
        try:
            right.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][2]["x"])
        except:
            pass
        try:
            left.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][3]["x"])
        except:
            pass

        try:
            bottom.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][0]["y"])
        except:
            pass
        try:
            bottom.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][1]["y"])
        except:
            pass
        try:
            top.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][2]["y"])
        except:
            pass
        try:
            top.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][3]["y"])
        except:
            pass

        if len_sum==len(word_list[now_num].replace(" ","")):
            len_sum=0
            #print("word:   "+word_list[now_num])
            dic={"word":word_list[now_num],"文字の縦幅":mode_average(top)-mode_average(bottom),"x":round(mode_average(left)+mode_average(right)),"y":round(mode_average(top)+mode_average(bottom))}
            dic_list.append(dic)
            now_num+=1
            left=[]
            right=[]
            top=[]
            bottom=[]
    elapsed_time = time.time() - start_time
    print ("for文を回し終わるまでにかかった時間:{0}".format(elapsed_time) + "[sec]")
    df = pd.DataFrame(dic_list)
    df=df.sort_values('y')
    df.reset_index()
    tate_mean=df["文字の縦幅"].mean()

    diff_list=df["y"].diff()
    a_=0
    y_list=[]
    for a,b in zip(df["y"],diff_list):
        #print(a,b)
        if b<tate_mean:
            a=a_
        a_=a
        y_list.append(a)

    df["diff"]=diff_list
    df.loc[0,"diff"]=0
    df["y"]=y_list
    df=df.sort_values(["y","x"])
    grouped_df = df.groupby('y')
    grouped_list = [list(grouped_df["word"].get_group(word)) for word in grouped_df.groups]
    elapsed_time = time.time() - start_time
    print ("elapsed_time:{0}".format(elapsed_time) + "[sec]")
    return grouped_list


#一部のみしか選択しないタイプ 画像を表示しない場合
def recognize5(url,n_part,start,goal):
    start_time = time.time()
    #pathからbase64にする場合
    def pil_image_to_base64(img_path):###ここは最後に消す
        pil_image = Image.open(img_path)
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return str_encode_file

    #arrayからbase64にする場合
    def array_to_base64(img_array):
        pil_image = Image.fromarray(np.uint8(img_array))
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return str_encode_file 

    def get_fullTextAnnotation(json_data):
        text_dict = json.loads(json_data)
        try:
            text = text_dict["responses"][0]["fullTextAnnotation"]["text"]
            return text
        except:
            print(None)
            return None

    #str_encode_file = pil_image_to_base64(url)  
    
    img = cv2.imread(url)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    input_image=img[start*img.shape[0]//n_part:goal*img.shape[0]//n_part ,0::]
#     plt.figure(figsize=[50,50])
#     plt.imshow(input_image)
    
    str_encode_file = array_to_base64(input_image)# input_imageがarrayの時
    str_url = "https://vision.googleapis.com/v1/images:annotate?key="
    str_api_key = "AIzaSyDlRRYrHEdjParsfRmh96_3xfafOo1crWY"
    str_headers = {'Content-Type': 'application/json'}
    str_json_data = {
        'requests': [
            {
                'image': {
                    'content': str_encode_file
                },
                'features': [
                    {
                        'type': "DOCUMENT_TEXT_DETECTION",
                        'maxResults': 1
                    }
                ],"imageContext": {
        "languageHints": ["ja"]
      },
            }
        ]
    }

    obj_session = Session()
    obj_request = Request("POST",
                            str_url + str_api_key,
                            data=json.dumps(str_json_data),
                            headers=str_headers
                            )
    obj_prepped = obj_session.prepare_request(obj_request)
    obj_response = obj_session.send(obj_prepped,
                                    verify=True,
                                    timeout=60
                                    )
    #もとの出力
    if obj_response.status_code == 200:
        text = get_fullTextAnnotation(obj_response.text)
        
    elapsed_time = time.time() - start_time
    print ("API終了までにかかった時間:{0}".format(elapsed_time) + "[sec]")
    #行ごとの出力    
    text_dict = json.loads(obj_response.text)
    word_list=text_dict["responses"][0]["textAnnotations"][0]["description"].split("\n")

    len_sum=0
    now_num=0
    left=[]
    right=[]
    top=[]
    bottom=[]
    dic_list=[]

    for i in range(1,len(text_dict["responses"][0]["textAnnotations"])):
        len_sum+=len(text_dict["responses"][0]["textAnnotations"][i]["description"].replace(" ",""))
        try:
            left.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][0]["x"])
        except:
            pass
        try:
            right.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][1]["x"])
        except:
            pass
        try:
            right.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][2]["x"])
        except:
            pass
        try:
            left.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][3]["x"])
        except:
            pass

        try:
            bottom.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][0]["y"])
        except:
            pass
        try:
            bottom.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][1]["y"])
        except:
            pass
        try:
            top.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][2]["y"])
        except:
            pass
        try:
            top.append(text_dict["responses"][0]["textAnnotations"][i]["boundingPoly"]["vertices"][3]["y"])
        except:
            pass

        if len_sum==len(word_list[now_num].replace(" ","")):
            len_sum=0
            #print("word:   "+word_list[now_num])
            dic={"word":word_list[now_num],"文字の縦幅":mode_average(top)-mode_average(bottom),"x":round(mode_average(left)+mode_average(right)),"y":round(mode_average(top)+mode_average(bottom))}
            dic_list.append(dic)
            now_num+=1
            left=[]
            right=[]
            top=[]
            bottom=[]
    elapsed_time = time.time() - start_time
    print ("for文を回し終わるまでにかかった時間:{0}".format(elapsed_time) + "[sec]")
    df = pd.DataFrame(dic_list)
    df=df.sort_values('y')
    df.reset_index()
    tate_mean=df["文字の縦幅"].mean()

    diff_list=df["y"].diff()
    a_=0
    y_list=[]
    for a,b in zip(df["y"],diff_list):
        #print(a,b)
        if b<tate_mean:
            a=a_
        a_=a
        y_list.append(a)

    df["diff"]=diff_list
    df.loc[0,"diff"]=0
    df["y"]=y_list
    df=df.sort_values(["y","x"])
    grouped_df = df.groupby('y')
    grouped_list = [list(grouped_df["word"].get_group(word)) for word in grouped_df.groups]
    elapsed_time = time.time() - start_time
    print ("elapsed_time:{0}".format(elapsed_time) + "[sec]")
    return grouped_list
        
        
        


# 左半分の指定範囲を切り抜いて保存する。
def image_check(url,n_part,start,goal):
    img = cv2.imread(url)
    #img = plt.imread(url)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    #plt.imshow(img)
    input_image=img[start*img.shape[0]//n_part:goal*img.shape[0]//n_part ,0:img.shape[1]//2]
    #plt.figure(figsize=[50,50])
    #plt.imshow(input_image)
    plt.imsave("/Users/obara/Downloads/prescription_data_jpeg_8/photo-"+str(num)+".jpeg",input_image)
    return

#textの中に氏名っぽい文字列が入っていれば取り出す関数。
t = Tokenizer("merge.csv", udic_enc="utf-8")
def wakati(text):
    sei=""
    mei=""
    for token in t.tokenize(text):
        if token.part_of_speech.split(",")[2]=="人名" and (token.part_of_speech.split(",")[3]=="姓" or token.part_of_speech.split(",")[3]=="性"):
            sei=token.surface
        if token.part_of_speech.split(",")[2]=="人名" and token.part_of_speech.split(",")[3]=="名":
            mei=token.surface
    return sei, mei

