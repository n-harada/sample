#coding:utf-8
#必要なもののimport 
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

#---------------------------------------------------------------------------------
#歪みを修正する。imageにはpathが入る。
def yugami(image):
    img = cv2.imread(image)
    #画像をグレースケール化
    img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    #閾値を180にして2値化
    threshold = 105
    ret, img_thresh = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)

    #輪郭を取り出している
    img_1, contours, hierarchy = cv2.findContours(img_thresh , cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    #mensekiリストに輪郭を追加していっている。
    menseki=[ ]

    for i in range(0, len(contours)):
        menseki.append([contours[i],cv2.contourArea(contours[i])])

    menseki.sort(key=lambda x: x[1], reverse=True)

    #一番面積が大きいものを取り出している。
    cnt = menseki[0][0]

    #輪郭のギザギザを無くしている
    epsilon = 0.1*cv2.arcLength(cnt,True)
    #approxに隅の四点の座標が入っている
    approx = cv2.approxPolyDP(cnt,epsilon,True)

    #ギザギザをなくした後の描画
    #img3=cv2.drawContours(img, approx, 0,(0, 0, 255),10)

    #輪郭の表をリストにして、順番を整理
    approx=approx.tolist()

    left = sorted(approx,key=lambda x:x[0]) [:2]
    right = sorted(approx, key=lambda x: x[0])[2:]
    
    left_down= sorted(left,key=lambda x:x[0][1]) [0]
    left_up= sorted(left,key=lambda x:x[0][1]) [1]

    right_down= sorted(right,key=lambda x:x[0][1]) [0]
    right_up= sorted(right,key=lambda x:x[0][1]) [1]


    #補正前の角の座標
    perspective1 = np.float32([left_down,right_down,right_up,left_up])
    #A4の場合の補正後の角の座標
    width = right_down[0][0]-left_down[0][0]
    height=width*2340//1654
    #perspective2 = np.float32([[0, 0], [1654, 0], [1654, 2340], [0, 2340]])
    perspective2 = np.float32([[0, 0],[width, 0],[width, height],[0, height]])

    #変換に必要な行列
    psp_matrix = cv2.getPerspectiveTransform(perspective1,perspective2)
    #変換後
    #img_psp = cv2.warpPerspective(img, psp_matrix, (1654, 2340))
    img_psp = cv2.warpPerspective(img, psp_matrix, (width, height))
    return img_psp
    #cv2.imwrite("yugami-modified2/"+str(num)+".png",img_psp)

#---------------------------------------------------------------------------------
#一番単純なOCRコード　投げたarrayをOCRする。
#画像をCloud Vision APIに投げる
def recognize_image1(input_image):#最後にstr_encode_fileに変える
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

    #str_encode_file = pil_image_to_base64(input_image)  
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
                ]
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

    if obj_response.status_code == 200:
        text = get_fullTextAnnotation(obj_response.text)
        
        return text
    else:
        return "error"

def type_check(img):
    height=img.shape[0]
    width=img.shape[1]

    img=img[height//2: 5 * height // 8, width*2//5:width*3//5]
    #img = cv2.resize(img,(int(img.shape[1]/5),int(img.shape[0]/5)))
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    #gray = cv2.GaussianBlur(gray,(5,5),5)
    
#     plt.gray()
#     plt.imshow(gray)

    edges = cv2.Canny(gray,50,150,apertureSize = 3)

    linesH = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 360, threshold=50, minLineLength=50, maxLineGap=10)
    try:
        if len(linesH)!=0:
            for line in linesH:
                x1, y1, x2, y2 = line[0]
                if (x1-x2)**2<(y1-y2)**2:
                    return "B"
                else:
                    return "A"
            
        else:
            return "A"
    except:
        return "A"


    
#ピンボケ検出
def boke(image):
    return cv2.Laplacian(image, cv2.CV_64F).var()
def boke_check(image):
    if boke(image)<200:
        return True
    else:
        return False
#---------------------------------------------------------------------