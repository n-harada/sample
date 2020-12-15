#coding:utf-8
#必要なもののimport 
import base64
import json
from io import BytesIO
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from requests import Request, Session
from PIL import Image
import pandas as pd
import numpy as np

#for debugging imports
import threading


#GOOGLE API KEY
'''STR_API_KEY = "AIzaSyDlRRYrHEdjParsfRmh96_3xfafOo1crWY" #obara account'''
STR_API_KEY = 'AIzaSyDicW0IZtWAxOTd8JdhV2XIqqpmMLKyvnQ' # mzd account


#-OCRs--------------------------------------------------------------------------------
#recognize_image1:一番初期の関数（気が利く関数）
#recognize_image2:上からOCRする関数
#input:array
#output:recognize_image1は文字列、recognize_image2はリスト内包リスト


def recognize_image1(input_image):  #最後にstr_encode_fileに変える
    '''
    気が利くタイプのOCR
    input:画像のarray
    output:文字列
    '''    


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
                            str_url + STR_API_KEY,
                            data=json.dumps(str_json_data),
                            headers=str_headers
                            )
    obj_prepped = obj_session.prepare_request(obj_request)
    obj_response = obj_session.send(obj_prepped,
                                    verify=True,
                                    timeout=60
                                    )

    '''
    if obj_response.status_code == 200:
        text = get_fullTextAnnotation(obj_response.text)
        
        return text
    else:
        return "error"
    '''

    return obj_response


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


#一部のみしか選択しないタイプ 画像を表示しない場合
def recognize2(img_array, request_flag='No-Flag',n_part=10, start=0, goal=10,ERROR_RETURN=[['was_empty_img']]):
    '''
    上から順番に取得するタイプのOCR
    input:画像のarray,何分割するか,上から何割の部分より下をOCRしたいか？,,上から何割の部分より上をOCRしたいか？
    output:文字列
    '''

    ''' #CURRENTLY UNUSED FUNCTION#
    def get_fullTextAnnotation(json_data):
        text_dict = json.loads(json_data)
        try:
            text = text_dict["responses"][0]["fullTextAnnotation"]["text"]
            return text
        except:
            print(None)
            return None'''

    #str_encode_file = pil_image_to_base64(url)  
    
    #img = cv2.imread(url)
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    #input_image=img[start*img.shape[0]//n_part:goal*img.shape[0]//n_part ,0::]
    #plt.figure(figsize=[50,50])
    #plt.imshow(input_image)

    #入力がAPIリクエストを行ってもエラーを出してしまうものの場合、ここで弾く
    if len(img_array)==0:
        print('request was not sent',request_flag,dt.datetime.now()) ##DEBUG_PRINT
        return ERROR_RETURN
    
    #convert image
    print('converting image',request_flag,dt.datetime.now()) ##DEBUG PRINT
    str_encode_file = array_to_base64(img_array)# input_imageがarrayの時
    print('converting done',request_flag,dt.datetime.now()) ##DEBUG PRINT
    
    #send API request    
    str_url = "https://vision.googleapis.com/v1/images:annotate?key="
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

    print('sending request',request_flag,dt.datetime.now()) ##DEBUG PRINT

    obj_session = Session()
    obj_request = Request("POST",
                            str_url + STR_API_KEY,
                            data=json.dumps(str_json_data),
                            headers=str_headers
                            )
    obj_prepped = obj_session.prepare_request(obj_request)
    obj_response = obj_session.send(obj_prepped,
                                    verify=True,
                                    timeout=60
                                    )

    print('result fetched',request_flag, dt.datetime.now()) ##DEBUG PRINT

    '''
    #もとの出力
    if obj_response.status_code == 200:
        text = get_fullTextAnnotation(obj_response.text)
    '''
    
    #行ごとの出力
    text_dict = json.loads(obj_response.text)
    if len(text_dict["responses"][0])==0:
        print('request',request_flag,'was an empty image') ##DEBUG PRINT
        return [['']]
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
    return grouped_list


#---------------------------------------------------------------------------------
def array_to_base64(img_array):
    '''
    arrayをbase64にする
    input:array
    output:base64
    '''
    pil_image = Image.fromarray(np.uint8(img_array))
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return str_encode_file
    
#---------------------------------------------------------------------------------
def pil_image_to_base64(img_path):
    '''
    pathからbase64にする
    input:画像のpath
    output:base64
    '''
    pil_image = Image.open(img_path)
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    str_encode_file = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return str_encode_file



#---------------------------------------------------------------------------------
def api_pararel(kinds,workers=8,testing_speed=False):
    '''
    1枚目においてAPIの部分を並列処理する
    処方箋タイプがAの時は5個だけarrayを入れて、処方箋タイプがBの時は6個入れる
    inputの形式:[array,array,,,,,,]
    output:{0:ocr結果text,1:ocr結果text,,,,,,}
    '''
    def api_def(img_array,num):
        return {num:recognize2(img_array,request_flag=num)}

    ##FOR TESTING
    time_start = dt.datetime.now() 

    #Main Paralell Flow
    executor = ThreadPoolExecutor(max_workers=workers)
    futures = []

    for num in range(len(kinds)):
        
        '''##DEBUG PRINTS
        print("Threads: {}".format(len(executor._threads))) 
        print('others-inLoop',num,dt.datetime.now())

        try:
            plt.imshow(kinds[num])
            plt.show()
        except:
            print('cannot plot image',kinds[num],type(kinds[num]),len(kinds[num]))
        '''
        
        future = executor.submit(api_def, img_array=kinds[num],num=num)
        futures.append(future)
    executor.shutdown()    

    ##FOR TESTING
    if testing_speed:
        return (dt.datetime.now() - time_start).total_seconds()

    #Main Paralell Flow
    result_list=[]
    for i in futures:
        result_list.append(i.result())
    dic={}
    for result in result_list:
        dic.update(result)
    return dic
    