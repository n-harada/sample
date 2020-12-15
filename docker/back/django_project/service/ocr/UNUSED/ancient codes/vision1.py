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
#切り出す作業。返り値は、保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部
def waku(image):
    #arrayになっているものをもどす
    #img = Image.fromarray(np.uint8(image))
    #画像を読み込む（arrayに）
    #img = cv2.imread(image)
    
    #画像をグレースケール化 入れるのはarray
    img_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    #閾値を180にして2値化
    # threshold = 10
    # ret, img_thresh = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)

    #2値化後を表示
#     plt.imshow( img_gray)
#     plt.gray()

    height=img_gray.shape[0]
    width=img_gray.shape[1]
    #切り出し
    img2=image[0:612*height//2340,width//2:width]              
                     
    # BGR -> グレースケール
    gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    # エッジ抽出 (Canny)
    edges = cv2.Canny(gray, 50, 190, apertureSize=3)
    #cv2.imwrite('wakuedges.png', edges)
    # 膨張処理
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel)


    # 輪郭抽出
    _, contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 面積でフィルタリング
    rects = []
    mensekilist=[]
    for cnt, hrchy in zip(contours, hierarchy[0]):
        if cv2.contourArea(cnt) < 30:
            continue  # 面積が小さいものは除く
        if hrchy[3] == -1:
            continue  # ルートノードは除く
        # 輪郭を囲む長方形を計算する。
        rect = cv2.minAreaRect(cnt)
        rect_points = cv2.boxPoints(rect).astype(int)
        rects.append(rect_points)
        mensekilist.append(cv2.contourArea(cnt) )

    indexnum=mensekilist.index(max(mensekilist))

    # x-y 順でソート
    #rects = sorted(rects, key=lambda x: (x[0][1], x[0][0]))

    # 描画する。
    for i, rect in enumerate(rects):
        color = np.random.randint(0, 255, 3).tolist()
        #cv2.drawContours(img, rects, i, color, 2)
        #cv2.putText(img, str(i), tuple(rect[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 3)

        #print('rect:\n', rect)

    i=indexnum
    x=[rects[i][0][0],rects[i][1][0],rects[i][2][0],rects[i][3][0]]
    x1=sorted(x)
    y=[rects[i][0][1],rects[i][1][1],rects[i][2][1],rects[i][3][1]]
    y1=sorted(y)
    smallx=round((x1[1] +x1[0])//2)
    largex=round((x1[-1]+x1[-2])//2)
    smally=round((y1[0]+y1[1])//2)
    largey=round((y1[-1]+y1[-2])//2)
    sitanum=img2[smally:largey,smallx:largex]
    #cv2.imwrite('sitanum2/'+str(num)+'.png', sitanum)

    #以下PHCverのパラメータ       
    img_list=[]
    for i in range(8):
        n=i
        height1=largey-smally
        width1=int(round((largex-smallx)/8))
        difference=int(round((height1-width1)/3))
        difference2=width1//7

        if n<4:
            img3=img2[smally-height1+3*difference:largey-height1-difference,(smallx+width1*n)+0*difference2:smallx+width1*(n+1)-2*difference2]

        else:
            img3=img2[smally-height1+3*difference:largey-height1-difference,(largex-width1*(8-n))+0*difference2:largex-width1*(7-n)-2*difference2]
        img_list.append(img3)

    im_h = cv2.hconcat(img_list)

    #以下矢澤先生verのパラメータ
    img_list2=[]
    for i in range(8):
        n=i
        height1=largey-smally
        width1=int(round((largex-smallx)/8))
        difference=int(round((height1-width1)/3))
        difference2=width1//7

        if n<4:
            img3=img2[smally-height1+1*difference:largey-height1-difference,(smallx+width1*n)+1*difference2:smallx+width1*(n+1)-0*difference2]

        else:
            img3=img2[smally-height1+1*difference:largey-height1-difference,(largex-width1*(8-n))+1*difference2:largex-width1*(7-n)-0*difference2]
        img_list2.append(img3)

    im_h2 = cv2.hconcat(img_list2)


    #記号番号の上のところを取得する
    img4 = img2[smally - height1 + 3 * difference : largey - height1 - difference, smallx:largex]
    
    #矢澤先生の処方箋の時
    # top = image[0: 900 * height // 2340, 0 :width]
    # bottom1 = image[900 * height // 2340 :height, 0 :width//2]
    # bottom2 = image[900 * height // 2340 :height, width // 2 :width]
    # bottom_all=image[900 * height // 2340 :height, 0 :width]

    #PHCの処方箋の時・・・topを少し広めに取り、境界領域の情報を掬えるようにする
    top = image[0: 400 * height // 1030, 0 :width]
    bottom1 = image[300 * height // 1030 :height, 0 :width//2]
    bottom2 = image[300 * height // 1030 :height, width // 2 :width]
    bottom_all = image[300 * height // 1030 :height, 0:width]


    #保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部、縦線消去したやつ(img4)、
    return im_h, sitanum,top,bottom1,bottom2,bottom_all,img4,im_h2
#---------------------------------------------------------------------------
def waku1(image):#色が薄くて枠が取れなかった用の関数
    #画像をグレースケール化 入れるのはarray
    img_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    #閾値を200にして2値化
    threshold = 200
    ret, img_thresh = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)

    #2値化後を表示
#     plt.imshow( img_gray)
#     plt.gray()

    height=img_gray.shape[0]
    width=img_gray.shape[1]
    #切り出し
    img2 = img_thresh[0: 612 * height // 2340, width // 2 :width]
    gray=img2           
    
    # エッジ抽出 (Canny)
    edges = cv2.Canny(gray, 50, 190, apertureSize=3)
    #cv2.imwrite('wakuedges.png', edges)
    # 膨張処理
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel)


    # 輪郭抽出
    _, contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 面積でフィルタリング
    rects = []
    mensekilist=[]
    for cnt, hrchy in zip(contours, hierarchy[0]):
        if cv2.contourArea(cnt) < 30:
            continue  # 面積が小さいものは除く
        if hrchy[3] == -1:
            continue  # ルートノードは除く
        # 輪郭を囲む長方形を計算する。
        rect = cv2.minAreaRect(cnt)
        rect_points = cv2.boxPoints(rect).astype(int)
        rects.append(rect_points)
        mensekilist.append(cv2.contourArea(cnt) )

    indexnum=mensekilist.index(max(mensekilist))

    i=indexnum
    x=[rects[i][0][0],rects[i][1][0],rects[i][2][0],rects[i][3][0]]
    x1=sorted(x)
    y=[rects[i][0][1],rects[i][1][1],rects[i][2][1],rects[i][3][1]]
    y1=sorted(y)
    smallx=round((x1[1] +x1[0])//2)
    largex=round((x1[-1]+x1[-2])//2)
    smally=round((y1[0]+y1[1])//2)
    largey=round((y1[-1]+y1[-2])//2)
    sitanum=img2[smally:largey,smallx:largex]
    #cv2.imwrite('sitanum2/'+str(num)+'.png', sitanum)
                     
    #以下PHCの時のパラメータ
    img_list=[]
    for i in range(8):
        n=i
        height1=largey-smally
        width1=int(round((largex-smallx)/8))
        difference=int(round((height1-width1)/3))
        difference2=width1//7

        if n<4:
            img3=img2[smally-height1+3*difference:largey-height1-difference,(smallx+width1*n)+0*difference2:smallx+width1*(n+1)-1*difference2]

        else:
            img3=img2[smally-height1+3*difference:largey-height1-difference,(largex-width1*(8-n))+0*difference2:largex-width1*(7-n)-1*difference2]
        img_list.append(img3)

    im_h = cv2.hconcat(img_list)
    
    #以下矢澤先生verのパラメータ
    img_list2=[]
    for i in range(8):
        n=i
        height1=largey-smally
        width1=int(round((largex-smallx)/8))
        difference=int(round((height1-width1)/3))
        difference2=width1//7

        if n<4:
            img3=img2[smally-height1+3*difference:largey-height1-difference,(smallx+width1*n)+2*difference2:smallx+width1*(n+1)-0*difference2]

        else:
            img3=img2[smally-height1+3*difference:largey-height1-difference,(largex-width1*(8-n))+2*difference2:largex-width1*(7-n)-0*difference2]
        img_list2.append(img3)

    im_h2 = cv2.hconcat(img_list2)

    #記号番号の上のところを取得する
    img4 = img2[smally - height1 + 1 * difference : largey - height1 - difference, smallx:largex]
    
    #矢澤先生の処方箋の時
    # top = image[0: 900 * height // 2340, 0 :width]
    # bottom1 = image[900 * height // 2340 :height, 0 :width//2]
    # bottom2 = image[900 * height // 2340 :height, width // 2 :width]
    # bottom_all=image[900 * height // 2340 :height, 0 :width]

    #PHCの処方箋の時
    top = image[0: 350 * height // 1030, 0 :width]
    bottom1 = image[300 * height // 1030 :height, 0 :width//2]
    bottom2 = image[300 * height // 1030 :height, width // 2 :width]
    bottom_all = image[300 * height // 1030 :height, 0:width]
    
    

    #保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部、縦線消す用のやつ、
    return im_h, sitanum,top,bottom1,bottom2,bottom_all,img4,im_h2



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


def recognize_image2(img):  #縦線を消してOCRする。imgはarrayを想定
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except:
        gray=img
    edges = cv2.Canny(gray,50,150,apertureSize = 3)
    linesH = cv2.HoughLinesP(edges, rho=1, theta=np.pi/360, threshold=2, minLineLength=6*img.shape[0]//10, maxLineGap=10)
    try:
        if len(linesH)>0:
            for line in linesH:
                x1, y1, x2, y2 = line[0]
                if (x1-x2)**2<(y1-y2)**2 and (x1-x2)**2<100:
                    img2 = cv2.line(img, (x1,y1), (x2,y2), (255,255,255), 10)
                    
            threshold = 200
            ret, img_thresh = cv2.threshold(img2, threshold, 255, cv2.THRESH_BINARY)
            return recognize_image1(img_thresh)
        else:
            return
    except:
        return



#-----------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------
#基本情報の取り出しパート
#医薬品データベースの読み込みパート ※一般名含む

#symspellの準備
print('loading hospital symspell...')
with open('hospital3_8.pickle', 'rb') as f:
    sym_spell_hospital = pickle.load(f)

#symspellの関数
def symspell_hospital(_query,_max_edit_distance_lookup):
    answer=[]
    answer_distance=[]
    input_term =_query
    _max_edit_distance_lookup = _max_edit_distance_lookup
    suggestion_verbosity = Verbosity.CLOSEST  # TOP, CLOSEST, ALL
    
    suggestions = sym_spell_hospital.lookup(input_term, suggestion_verbosity,
                               _max_edit_distance_lookup)
    for suggestion in suggestions:
        answer.append(suggestion.term)
        answer_distance.append(suggestion.distance)
    return(answer,answer_distance)

#病院データベースのインポート(subは医科・歯科が併設されているケースの、sub側の医療機関のコードを格納したもの)
with open('dict_hospitalInfo.pickle', 'rb') as f:
    dict_hospitalInfo_base = pickle.load(f)
#with open('dict_hospitalInfo_sub.pickle', 'rb') as f:
#    dict_hospitalInfo_sub_base = pickle.load(f)

#病院名の表記揺れ修正してdict,listを生成
dict_hospitalInfo,l_hospital = {},[]
for key in dict_hospitalInfo_base.keys():
    normed = jaconv.normalize(key)
    dict_hospitalInfo[normed] = dict_hospitalInfo_base[key]
    l_hospital.append(normed)

#文字列長情報を付与してあげる
s_hospital_withLen = pd.Series(l_hospital,index=[len(i) for i in l_hospital])


#本筋のコード
def text_processing_basic(text,boke):
    #変数の定義
    _1_hospital_code_type,_1_hosipital_code,_1_hospital_place_code,_1_hospital_name = None,None,None,None
    _5_doctor_code, _5_docter_name_kana, _5_doctor_name_kanji = None, None, None
    _5_docter_name_kana2, _5_doctor_name_kanji2 = None, None #最初にmecabで取得する場合の変数
    _5_docter_name_kanji_list=[]#保険医氏名の候補を入れるリスト
    _11_patient_code, _11_patient_name_kanji, _11_patient_name_kana = None, None, None
    _11_patient_name_kanji2, _11_patient_name_kana2 = None, None #最初にmecabで取得する場合の変数
    _11_patient_name_kanji_list = []#患者氏名候補を入れるリスト
    _11_patient_name_kana_list = []#患者氏名候補のカナを入れるリスト
    _12_patient_sex = None
    _13_patient_birthday = None
    _22_insurance_patient_num = None,None,None,None
    _23_insurance_card_id,_23_insurance_card_num,_23_insurance_type,_23_insurance_card_branchNum = None,None,None,None
    _51_prescription_date = None

    #表記ゆれの解消
    text = jaconv.normalize(text)
    text = text.replace('險','険')
    raw_str = text.splitlines()

    #以後、ブロック一つずつ確認していく
    for num in range(len(raw_str)):
        val = raw_str[num]    
        
        #1_医療機関レコード
        if (_1_hospital_name is None) and (len(val)>6 and len(val)<24):#lenの閾値はテキトーなので今後調整
            #new
            symspell_results_2=symspell_hospital(val, 3)#symspell_results_2にはふたつのリストが入っている
            hospital = symspell_results_2[0]
            hospital2 = symspell_results_2[1]
            #hospital2_list.append(hospital2) ... この情報は取らないfor the time being

            if hospital != []:
                l_hospital,l_symspell_dist=[],[]
                #hospital_symspell_results.append(hospital[0]) ... この情報は取らないfor the time being
                for j in range(len(hospital)):
                    hospital_name = hospital[j]
                    symspell_dist = hospital2[j]
                    l_hospital_search = s_hospital_withLen[s_hospital_withLen.index>=len(hospital_name)].values.tolist()
                    for i in l_hospital_search:
                        if hospital_name in i:
                            l_hospital.append(i)
                            l_symspell_dist.append(symspell_dist)

                #l_hospitalの値をvalの値の編集距離を取得して、それに応じて並び替え. valが最長病院名より長かったらvalを短くする.
                l_leven=[]
                max_len = max([len(i) for i in l_hospital])
                if len(val)>max_len:
                    compare = val[:max_len]
                else:
                    compare = val
                for i in l_hospital:
                    l_leven.append(Levenshtein.distance(compare,i))         
                l_hospital_sorted = pd.Series(l_hospital,index=[l_symspell_dist,l_leven]).sort_index(ascending=False).values.tolist()

                #一番近しいやつを決め打ちで出力
                _1_hospital_name = l_hospital_sorted[len(l_hospital_sorted)-1]
                _1_hospital_code_type,_1_hosipital_code,_1_hospital_place_code = dict_hospitalInfo[_1_hospital_name]
        
        ##5_医師レコード
        if (_5_doctor_name_kanji is None) and (_1_hospital_name is not None) and ('保険医' in val or '保険' in val): 
            _5_doctor_name_kanji = extract_name(val)
            _5_doctor_name_kanji=kanji_name(_5_doctor_name_kanji)
            #print(5,_5_doctor_name_kanji)
        _5_doctor_name_kanji2 = get_name_by_mecab_all(text)[1]

        _5_docter_name_kanji_list = [_5_doctor_name_kanji, _5_doctor_name_kanji2]
        _5_docter_name_kanji_list = [x for x in _5_docter_name_kanji_list if x is not None]  #Noneを削除
        _5_docter_name_kanji_list = [x for x in _5_docter_name_kanji_list if x !=""]  #''を削除
        _5_docter_name_kanji_list=list(OrderedDict.fromkeys(_5_docter_name_kanji_list))
        
            
        ##11_患者氏名レコード
        if (_11_patient_name_kanji is None) and ('氏名' in val.replace(' ', '').replace('　', '') or '氏名' in raw_str[num-1].replace(' ', '').replace('　', '')or'氏名' in raw_str[num-2].replace(' ', '').replace('　', '')) and ('医' not in val):
            if extract_name(val)!=None:
                _11_patient_name_kanji=extract_name2(val)
            _11_patient_name_kanji = kanji_name(_11_patient_name_kanji)
            _11_patient_name_kana = kana_name(_11_patient_name_kanji)

        _11_patient_name_kanji2=get_name_by_mecab_all(text)[0]
        _11_patient_name_kana2 = kana_name(_11_patient_name_kanji2)

        _11_patient_name_kanji_list = [_11_patient_name_kanji, _11_patient_name_kanji2]
        _11_patient_name_kanji_list = [x for x in _11_patient_name_kanji_list if x is not None]  #Noneを削除
        _11_patient_name_kanji_list = [x for x in _11_patient_name_kanji_list if x !=""]  # ''を削除
        _11_patient_name_kanji_list = list(OrderedDict.fromkeys(_11_patient_name_kanji_list))
        
        _11_patient_name_kana_list = [_11_patient_name_kana, _11_patient_name_kana2]
        _11_patient_name_kana_list = [x for x in _11_patient_name_kana_list if x is not None]  #Noneを削除
        _11_patient_name_kana_list = [x for x in _11_patient_name_kana_list if x != ""]  # ''を削除
        _11_patient_name_kana_list=list(OrderedDict.fromkeys(_11_patient_name_kana_list))
        
         #12_患者性別レコード
        if _11_patient_name_kana:
            _12_patient_sex = kata2gender(_11_patient_name_kana)
        else:
            _12_patient_sex="女"
        # if '女' in text:
        #     _12_patient_sex='男'
        # else:
        #     _12_patient_sex='女'
            
        ##13_患者生年月日レコード
        if '生年' in val:
            #year, month, dateの検索結果格納変数・検索行数count変数の定義
            birth_year,birth_month,birth_date,cnt = None,None,None,0
            
            #year,month,dateすべてが検索完了 or countが一定数overまで検索を行う
            while ((birth_year is None) or (birth_month is None) or (birth_date is None)) and cnt<10:
                
                #indexがoverflowの場合はbreakする
                if num+cnt>=(len(raw_str)):
                    break
                
                val_nxt = raw_str[num+cnt]
                if birth_year is None:
                    birth_year = re.search(r'([1-9, ]+)年',val_nxt)
                if birth_month is None:
                    birth_month = re.search(r'([1-9, ]+)月',val_nxt)
                if birth_date is None:
                    birth_date = re.search(r'([1-9, ]+)日',val_nxt)
                cnt+=1

            if (birth_year is None) or (birth_month is None) or (birth_date is None):
                _13_patient_birthday=''
            else:
                y,m,d = birth_year.group(),birth_month.group(),birth_date.group()
                y,m,d = re.sub(' ','',y),re.sub(' ','',m),re.sub(' ','',d)
                _13_patient_birthday = y+m+d
                
            
        ##22_保険者番号レコードは枠で個別で取得

        ##23_記号番号レコードの番号は枠で個別で取得
        
        '''
        if ('号' in val) and (_23_insurance_card_id is None):
            searchMin,searchMax = max(num-5,0),min(num+5,len(raw_str)-1)
            for i in range(searchMin,searchMax+1):
                search = re.search('[0-9,.,・]{8,20}',raw_str[i])
                if search is not None:
                    str_ = search.group()
                    split_search = re.search('[.,・]',str_)
                    if split_search is not None:
                        _23_insurance_card_id,_23_insurance_card_num = search.group().split(split_search.group())
                    else:
                        _23_insurance_card_id,_23_insurance_card_num = search.group(),None
                        
                    #print(23,_23_insurance_card_id,_23_insurance_card_num)
                    break
        '''
        _23_insurance_type = 'PLEASE SELECT'
    
    
        ##51_処方箋交付年月日レコード
        if '交付年' in val:
            #year, month, dateの検索結果格納変数・検索行数count変数の定義
            koufu_year,koufu_month,koufu_date,cnt = None,None,None,0
            
            #year,month,dateすべてが検索完了 or countが一定数overまで検索を行う
            while ((koufu_year is None) or (koufu_month is None) or (koufu_date is None)) and cnt<10:

                #indexがoverflowの場合はbreakする
                if num+cnt>=(len(raw_str)):
                    break
                
                val_nxt = raw_str[num+cnt]
                print(val_nxt)
                if koufu_year is None:
                    koufu_year = re.search(r'([1-9, ]+)年',val_nxt)
                if koufu_month is None:
                    koufu_month = re.search(r'([1-9, ]+)月',val_nxt)
                if koufu_date is None:
                    koufu_date = re.search(r'([1-9, ]+)日',val_nxt) 
                cnt+=1

            if (koufu_year is None) or (koufu_month is None) or (koufu_date is None):
                _51_prescription_date=''
            else:
                y,m,d = koufu_year.group(),koufu_month.group(),koufu_date.group()
                y,m,d = re.sub(' ','',y),re.sub(' ','',m),re.sub(' ','',d)
                _51_prescription_date = y+m+d
                
        info_list=[_1_hospital_code_type, _1_hosipital_code, _1_hospital_place_code, _1_hospital_name, _5_doctor_code, _5_docter_name_kana, _5_doctor_name_kanji, _11_patient_code, _11_patient_name_kanji, _11_patient_name_kana, _12_patient_sex, _13_patient_birthday, _23_insurance_card_id, _23_insurance_card_num, _23_insurance_type, _23_insurance_card_branchNum, _51_prescription_date,_11_patient_name_kanji_list,_11_patient_name_kana_list,_5_docter_name_kanji_list]
    return info_list
    


'''   
print(_1_hospital_code_type,_1_hosipital_code,_1_hospital_place_code,_1_hospital_name)
print(_5_doctor_code,_5_docter_name_kana,_5_doctor_name_kanji )
print(_11_patient_code,_11_patient_name_kanji,_11_patient_name_kana)
print(_12_patient_sex)
print(_13_patient_birthday)
print(_22_insurance_patient_num)
print(_23_insurance_card_id,_23_insurance_card_num,_23_insurance_type,_23_insurance_card_branchNum)
print(_51_prescription_date)
'''
#このうち確認するのは、_1_hospital_name, _5_doctor_name_kanji,_11_patient_name_kanji,_12_patient_sex,_13_patient_birthday,_23_insurance_card_id,_23_insurance_type（選択),_51_prescription_date
#それプラスで_22_insurance_patient_numも確認する。

#保険医氏名用の関数
def extract_name(str_):
    '''文字列の中から、名前に明らかに関係ない文字列を落として、返す処理'''
    #transcribe系のAIを使いたい気持ちもある
    
    def drop_single(condition,str_name):
        
        '''conditionにて表される文字列種別が単発で生じている場合、
        それを落としたものを返す処理'''
        cnt=0
        while cnt<len(str_name)-1:
            val = str_name[cnt]
            if re.match(condition,val) is not None:
                #先頭文字の判定の場合
                if cnt==0:
                    if re.match(condition,str_name[cnt+1]) is None:
                        str_name = str_name.replace(str_name[cnt],'',1)
                    else:
                        cnt+=1
                #それ以外の文字の判定の場合
                else:
                    if (re.match(condition,str_name[cnt-1]) is None) and (re.match(condition,str_name[cnt+1]) is None):
                        str_name = str_name.replace(str_name[cnt],'',1)
                    else:
                        cnt+=1
            else:
                cnt+=1
            return str_name
    name = re.sub('保険医','',str_) #保険医,という文字列を落とす
    name = re.sub('氏名','',name) #氏名,という文字列を落とす
    name = re.sub('[A-Z]+', '', name)  #アルファベットをすべて落とす
    try:
        name = drop_single('[\u3041-\u309F]', name)  #単発で生じているひらがなを落とす
    except:
        pass
    try:
        name = drop_single('[\u30A1-\u30FF]', name)  #単発で生じているカタカナを落とす
    except:
        pass
    
    return name

#患者氏名取得用の関数
def extract_name2(str_):
    str_=str_.replace(' ', '').replace('　', '')
    if ("都" not in str_) and ("県" not in str_)and ("区" not in str_) and ("市" not in str_)and ("所在" not in str_)  and ("名称" not in str_)   and ("在地" not in str_)   and ("明大" not in str_) and ("クリニッ" not in str_) and ("リニッ" not in str_) and ("病院" not in str_)and ("医" not in str_)and ("生年月" not in str_)and ("年月日" not in str_)and (not ("大" in str_ and "平" in str_)) and ("電話" not in str_)and ("番号" not in str_):
        #print ("ない")
        name = re.sub('保険医','',str_) #保険医,という文字列を落とす
        name = re.sub('氏名','',name) #氏名,という文字列を落とす
        name = re.sub('[A-z]+', '', name)  #アルファベットをすべて落とす
        name = re.sub('[0-9]+', '', name)#数字をすべて落とす
        name=re.sub(r'[!-~]', "", name)#半角記号,数字,英字をすべて落とす
        name=re.sub(r'[︰-＠]', "", name)#全角記号をすべて落とす
        if len(name)>2:
            return name
        else:
            return None
    else:
        return None

#人名をgetする
import MeCab

#tagger = MeCab.Tagger("-d /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd")
tagger = MeCab.Tagger ("-Ochasen")
# 初期化しないとエラーになる
tagger.parse("")
# 文字列を単語で分割しリストに格納する
def kanji_name(doc):
    if doc:
        doc = doc.replace("年", "", 1).replace("月", "", 1).replace("日", "", 1)
        node = tagger.parseToNode(doc)

        result = []
        while node:
            hinshi = node.feature.split(",")[0]
            if hinshi == '名詞':
                result.append(node.feature.split(",")[6])
            node = node.next
        mojiretsu = ''.join(result)
        mojiretsu=mojiretsu.replace("*", "")
        return mojiretsu
    else:
        return
#以上漢字氏名

#以下カナ氏名
def kana_name(text):
    if text:
        tagger = MeCab.Tagger("-Ochasen")
        tagger.parse('')
        node = tagger.parseToNode(text)
        word_class = []
        while node:
            wclass = node.feature.split(',')
            if wclass[0] != u'BOS/EOS':
                if wclass[6] == None:
                    word_class.append((wclass[7]))
                else:
                    word_class.append((wclass[7]))
            node = node.next
        mojiretsu=''.join(word_class) #性と名の間で半角空白を開ける
        return mojiretsu
    else:
        return



#記号番号の文字列を綺麗にidとnumに分ける。出力はリスト形式
def symbol_num(text,connect_str='[.,・,-]'):
    
    _23_insurance_card_id=[]
    _23_insurance_card_num=[]
    init_search=re.search('([0-9]+)('+connect_str+'*)([0-9]+)',text) #数値, 中間のコネクタ,以外のノイズを落とす
    
    #そもそも、数値情報がない場合はreturn
    if init_search is None:
        return _23_insurance_card_id,_23_insurance_card_num
    else:
        text = init_search.group()
    
    #中間のコネクタを取得する
    split_search = re.search(connect_str,text) 
    
    #中間コネクタが存在した場合
    if split_search is not None:
        card_id,card_num = text.split(split_search.group())[0],text.split(split_search.group())[1]
        
        #まずは、生の取得情報を第一候補としてappend
        _23_insurance_card_id.append(card_id)
        _23_insurance_card_num.append(card_num)
        
        #記号の先頭に1が存在 & 記号の文字列長い場合、おそらくミスなのでパースして第二候補を導出
        if (card_id[0]=='1') and (len(card_id)>=9):
            _23_insurance_card_id.append(card_id[1:])
            _23_insurance_card_num.append(card_num)
        
        #記号の先頭に1が存在のみの場合もミスの可能性があるので、パースして第三候補を導出
        elif card_id[0]=='1':
            _23_insurance_card_id.append(card_id[1:])
            _23_insurance_card_num.append(card_num)
        
        #続いて、記号がの文字列が単純に長い場合、それを先頭から縮めたものを第四候補群として取得
        if len(card_id)>=9:
            for i in range(len(card_id)-8):
                _23_insurance_card_id.append(card_id[(len(card_id)-8-i):])
                _23_insurance_card_num.append(card_num)
        
        #重複しているものは、index若い方を残してsetする
        _23_insurance_card_id = sorted(set(_23_insurance_card_id), key=_23_insurance_card_id.index)
        
        return _23_insurance_card_id,_23_insurance_card_num
    
    #中間コネクタが存在しない場合
    else:
        #推定される記号の長さに切り分け、listに格納
        raw=text
        l_card_id_lengthCandidates= [7,8,4]
        for length in l_card_id_lengthCandidates:
            if length<=len(raw):
                _23_insurance_card_id.append(raw[:length])
                _23_insurance_card_num.append(raw[length:])
            else:
                continue
                
        #頭文字が1の場合、それを取り除いた場合もlistに格納
        ##ここまで処理を行うと、記号・番号の組み合わせ数が爆発する潜在リスクが存在することに留意
        if text[0]=='1':
            raw=raw[1:]
            for length in l_card_id_lengthCandidates:
                if length<=len(raw):
                    _23_insurance_card_id.append(raw[:length])
                    _23_insurance_card_num.append(raw[length:])
                else:
                    continue
        return _23_insurance_card_id,_23_insurance_card_num


def symbol_num2(text):  #123・456みたいなのを123と456に分ける
    text=re.sub('[^0-9.,・-]', '', text)
    split_search = re.search('[.,・-]', text)
    if split_search is not None:
        _23_insurance_card_id=text.split(split_search.group())[0]
        _23_insurance_card_num=text.split(split_search.group())[1]
        return _23_insurance_card_id, _23_insurance_card_num
    else:
        return "??","??"


#日本語をローマ字に
kakasi = kakasi()
def jp2rome(text):
    #kakasi.setMode("H", "a")  # Hiragana to ascii
    kakasi.setMode("K", "a")  # Katakana to ascii
    #kakasi.setMode("J", "a")  # Japanese(kanji) to ascii
    #kakasi.setMode("r", "Hepburn")  # Use Hepburn romanization
    conv = kakasi.getConverter()
    result = conv.do(text)
    return(result)

#後ろ3文字を取り出す関数
def feature_extraction(word):
    return {"lastcharacter":word[-3:]}

#カタカナの氏名から性別を推定する関数
def kata2gender(text):
    text1=jp2rome(text)
    f = open('my_classifier.pickle', 'rb')
    classifier = pickle.load(f)
    f.close()
    if classifier.classify(feature_extraction(text1))=="female":
        return "女"
    else:
        return "男"

#OCR結果の基本情報部分を患者氏名を含んでいそうな部分と保険医氏名を含んでいそうな部分で2分割する
def split_text(text):
    name_in_text_list=[]
    name_in_text_list.extend(text.split('所在地', 1))
    if len(name_in_text_list)==0:
        name_in_text_list.append(text.split('電話番号', 1))
    if len(name_in_text_list)==0:
        name_in_text_list.append(text.split('生年月日', 1))
    if len(name_in_text_list)<2:
        return name_in_text_list #length=1のリストを返す
    else:
        #患者氏名が含まれていそうな文字列,保険医氏名が含まれていそうな文字列を出力
        return name_in_text_list[0], name_in_text_list[1]
        
#textから人名部分を取得する関数
from collections import OrderedDict
def get_name_by_mecab(text):
    import MeCab
    t = MeCab.Tagger('')
    #t = MeCab.Tagger('-d /usr/local/lib/mecab/dic/mecab-ipadic-neologd')
    t.parse('')
    m = t.parseToNode(text)
    keywords = []

    while m:
        if m.feature.split(',')[2] == '人名' and m.feature.split(',')[0] == '名詞' and m.feature.split(',')[1] == '固有名詞' :
            keywords.append(m.surface)
        m = m.next
    keywords=OrderedDict.fromkeys(keywords)
    return ''.join(keywords)

#上の2つを合体させたもの
def get_name_by_mecab_all(text):
    text=text.strip("処方箋").strip("方箋").strip("処方せん").strip("方せん")
    modified_text=split_text(text)
    if len(modified_text)==2:
        kanja_text=modified_text[0]
        hokeni_text=modified_text[1]
        return get_name_by_mecab(kanja_text),get_name_by_mecab(hokeni_text)
    else:
        kanja_text=modified_text[0]
        return get_name_by_mecab(kanja_text),""


#--------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------
#薬情報の取得パート
#symspellの準備
print('loading med symspells...')
with open('medicine7_8.pickle', 'rb') as f:
    sym_spell_med_long = pickle.load(f)

with open('medicine1_5.pickle', 'rb') as f:
    sym_spell_med_short = pickle.load(f)

#symspellの関数
def symspell_med(_query,_max_edit_distance_lookup,_sym_module):
    answer=[]
    answer_distance=[]
    input_term =_query
    _max_edit_distance_lookup = _max_edit_distance_lookup
    suggestion_verbosity = Verbosity.CLOSEST  # TOP, CLOSEST, ALL
    
    suggestions = _sym_module.lookup(input_term, suggestion_verbosity,
                               _max_edit_distance_lookup)
    for suggestion in suggestions:
        answer.append(suggestion.term)
        answer_distance.append(suggestion.distance)
    return(answer,answer_distance)


#医薬品データベースの読み込み ※一般名含む
print('loading medicine DB...')
with open('df_medicineInfo.pickle', 'rb') as f:
    df_medicineInfo = pickle.load(f)
df_medicineInfo = df_medicineInfo.rename(columns={'name':'品名'})

#一般名~特定銘柄, 先発薬~特定銘柄, 辞書の読み込み
with open('dict_ippan2specific.pickle','rb') as f:
    dict_ippan2specific = pickle.load(f)
with open('dict_branded2GE.pickle','rb') as f:
    dict_branded2GE = pickle.load(f)

'''
#test_data1 ニフェジピン
dict_ippan2specific['ニフェジピン徐放錠20mg(24時間持続)'] = ['ニフェジピンCR錠20mg「日医工」','ニフェジピンCR錠20mg「トーワ」','アダラートCR錠20mg']
dict_branded2GE['アダラートCR錠20mg'] = ['ニフェジピンCR錠20mg「日医工」','ニフェジピンCR錠20mg「トーワ」']

#test_data2 カルボシステイン, L-カルボシステインとの違いが不明であり、もしかしたらこの紐付けは間違っているかもしれない.
dict_ippan2specific['カルボシステイン錠250mg'] = ['カルボシステイン錠250mg「サワイ」','カルボシステイン錠250mg「TCK」','ムコダイン錠250mg']
dict_branded2GE['ムコダイン錠250mg'] = ['カルボシステイン錠250mg「サワイ」','カルボシステイン錠250mg「TCK」'] 
'''

#表記揺れの修正
for index in df_medicineInfo.index:
    df_medicineInfo.at[index,'品名'] = jaconv.normalize(df_medicineInfo.at[index,'品名'])

#薬リストの作成
l_meds = df_medicineInfo['品名'].values.tolist()
s_meds_withLen = pd.Series(l_meds,index=[len(i) for i in l_meds])
l_meds_ippan = df_medicineInfo[df_medicineInfo.GE_Branded_ippan=='ippan']['品名'].values.tolist()
l_meds_GE = df_medicineInfo[df_medicineInfo.GE_Branded_ippan=='GE']['品名'].values.tolist()

#OCR結果から医薬品名称を名寄せする関数
def parse_med_txt(_txt,_patient_GE_OK=True,_val_len_min=4,_val_len_max=27,_max_edit_distance_lookup=3,_sym_spell_med_long=sym_spell_med_long,_sym_spell_med_short=sym_spell_med_short):
    '''あるvalおよび全体の文字列を受け, 医薬品名称の名寄せ・調剤確定処理・紐づく文字列情報の切り取り、を行いそれを返す処理'''
        
    medi_list = [] #医薬品読み取り結果を格納するlist
    medi_list_raw = [] #調剤確定前の読み取り結果を格納するlist
    l_ge_switch_OK = [] #ジェネリック変更可否情報を保持するlist(bools, True:変更可, False:変更不可)
    l_base_val = [] #test用に元のvalを保持しておくlist
    l_confidence = [] #各医薬品名称についてのシステムとしてのconfidenceを格納するlist
    l_prev_vals = [] #処理済みのvalを格納しておくlist

    #テキストブロックを入れる場所
    medi_info = {1: "", 2: "", 3: "", 4: "", 5: "", 6: "", 7: "", 8: "", 9: "", 10: ""}

    #splitlines of text
    raw_str1 = _txt.splitlines()
    
    for num in range(len(raw_str1)):

        #検索対象文字列の取得
        val = raw_str1[num] 

        #文字列から読み取れる一般名情報の保持
        if re.search('【.*般.*】',val) is not None:
            bool_ippan = True
        else:
            bool_ippan = False

        #文字列のクレンジング
        val = val.strip() #文字列の前後に存在する改行スペースやを除去
        val = re.sub('【.+】','',val) #【】及びそれに囲まれた文字を除去
        val = re.sub('x|X|×','',val) #xっぽい文字を除去
        val = re.sub(list2str(l_units_med),'',val) #用量, 単位名情報っぽい文字列をここで落とす
        val = val.strip('|') #文字列の前後に存在する縦棒を除去
        val = val.strip('*') #文字列の前後に存在するアスタリスクマークを除去
        val = val.strip() #文字列の前後に存在する改行スペースやを除去

        #医薬品結果の格納先初期化
        medi = [] 

        #特定文字列長に対し、処理実行
        if  len(val)>_val_len_min and len(val)<_val_len_max:
            symspell_results_2=symspell_med(val, _max_edit_distance_lookup, _sym_spell_med_long)#symspell_results_2にはふたつのリストが入っている
            medi = symspell_results_2[0]
            medi2 = symspell_results_2[1]

        elif len(val)<=_val_len_min and len(val)>2:
            symspell_results_2=symspell_med(val, 1, _sym_spell_med_short)
            medi = symspell_results_2[0]
            medi2 = symspell_results_2[1]

        if medi != []:

            #test用に元のvalを保持しておく
            l_base_val.append(val) 

            #医薬品候補, symspell_distを取得する
            l_medi,l_symspell_dist=[],[]
            for j in range(len(medi)):
                medi_name = medi[j]
                symspell_dist = medi2[j]
                l_meds_search = s_meds_withLen[s_meds_withLen.index>=len(medi_name)].values.tolist()
                for i in l_meds_search:
                    if medi_name in i:
                        l_medi.append(i)
                        l_symspell_dist.append(symspell_dist)

            #l_medi内の医薬品名~1行分のval, の編集距離を取得
            l_leven_1=[]
            for i in l_medi:
                l_leven_1.append(Levenshtein.distance(val,i))         
                        
            #l_medi内の医薬品名~2行分のval, の編集距離を取得
            l_leven_2=[]
            max_len = max([len(i) for i in l_medi])
            try:
                compare = val+raw_str1[num+1]
                if len(compare)>max_len:
                    compare = compare[:max_len]
            except IndexError:
                compare = val
            for i in l_medi:
                l_leven_2.append(Levenshtein.distance(compare,i))
                
            #base_val近いl_levenを採用する
            if min(l_leven_1)<=min(l_leven_2):
                l_leven=l_leven_1[:]
            else:
                l_leven=l_leven_2[:]
                
            #薬品名候補をsymspell_dist, leven_distでソート
            l_medi_sorted = pd.Series(l_medi,index=[l_leven,l_symspell_dist]).sort_index(ascending=False).values.tolist()
            
            #取得医薬品名称の自信を離散化する ... 現状,キメの閾値で3段階表示(2>1>0)
            if boke==True:
                confidence='0'
            else:
                min_dist=min(l_leven)
                if min_dist==0:
                    confidence='2'
                elif min_dist<=2:
                    confidence='1'
                else:
                    confidence='0'
            l_confidence.append(confidence)

            #ジェネリック変更可否を取得する...ここでのTrueは"本当にGE変更OK","本当はGE変更ダメだけどOCRできてない"の2パターンあることに留意
            if re.search('x|X|×',val[:4]) is None:
                ge_switch_OK = True
            else:
                ge_switch_OK = False
            l_ge_switch_OK.append(ge_switch_OK)
               
            #調剤確定処理を行う
            ##必要な情報・変数の定義
            search_length = 2
            search_length = min(search_length,len(l_medi_sorted))

            ##調剤確定が必要なケースを判別,listを更新
            l_medi_sorted_secured = []
            bool_ippan_converted = False
            for i in range(search_length):
                med_selected = l_medi_sorted[-(i+1)]
                
                ##先発薬かつGE変更可の場合
                if _patient_GE_OK and ge_switch_OK and med_selected in dict_branded2GE.keys():
                    l_medi_sorted_secured.extend(dict_branded2GE[med_selected])
                    
                ##一般名処方の場合
                elif med_selected in dict_ippan2specific:
                    l_extend = dict_ippan2specific[med_selected]
                    if _patient_GE_OK==False:
                        l_extend = [j for j in l_extend if j not in l_meds_GE]
                    l_medi_sorted_secured.extend(l_extend)
                    bool_ippan_converted = True
                    
                l_medi_sorted_secured.append(med_selected)
            
            ##表記上は一般名なのに, 一般名変換が働いていない場合は知らせてもらう
            if bool_ippan is True and bool_ippan_converted is False:
                print(val,compare,'seems to be ippan. ippan2specific dict maybe incomplete.')
            
            ##l_medi_sortedの残りの要素を取得する
            l_tmp = l_medi_sorted[:-search_length]
            l_tmp.reverse()
            l_medi_sorted_secured.extend(l_tmp)
            
            ##重複している薬は、index若い方を残してsetする
            l_medi_sorted_secured = sorted(set(l_medi_sorted_secured), key=l_medi_sorted_secured.index)
            
            ##listを見やすい長さに切り、interface用に順番を逆順にする(今は切らずにそのまま)
            l_medi_sorted_secured = l_medi_sorted_secured[:]
            l_medi_sorted_secured.reverse()
            
            ##一般名には【般】をheadしてあげる
            for i in range(len(l_medi_sorted_secured)):
                if l_medi_sorted_secured[i] in l_meds_ippan:
                    l_medi_sorted_secured[i] = '【般】'+l_medi_sorted_secured[i]

            #薬品名に紐づく文字ブロックの元を取得&格納
            block = ''
            l_txt_split = _txt.split(raw_str1[num])
            for i in range(l_prev_vals.count(raw_str1[num])+1):
                if i>0:
                    block+=raw_str1[num]
                block+=l_txt_split[i]
            medi_info[len(l_prev_vals)]=block

            #調剤確定後のlist/これまで扱った医薬品文字列を格納
            medi_list.append(l_medi_sorted_secured)
            medi_list_raw.append(l_medi_sorted)
            l_prev_vals.append(raw_str1[num])

    #最後に全ての医薬品情報textを格納
    medi_info[len(l_prev_vals)]=_txt 

    return medi_list[:],medi_list_raw[:],medi_info.copy(),l_confidence[:],l_ge_switch_OK[:],l_base_val[:]

#大元のコード ... 医薬品情報取得におけるmain処理
def text_processing_med(text,boke):
    
    #結果を入れる場所
    dict_medInfo = {1: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 2: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 3: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 4: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 5: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 6: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 7: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 8: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 9: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 10: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}}
    
    #元のtextのnormalize,旧字体処理
    text = jaconv.normalize(text)
    text = text.replace('險','険')

    #医薬品名称名寄せ
    medi_list,medi_list_raw,medi_info,l_confidence,l_ge_switch_OK,l_base_val = parse_med_txt(text)    

    #辞書をリストに
    medi_text_list=[]
    for i in range(len(medi_info)):
        medi_text_list.append(medi_info[i])
        
    RP_num,RP_renbanNum = 0,0
    #それぞれ　情報取得
    for num in range(len(medi_list)):
        #dict_singleMed = {'RP番号':'','RP番号内連番':'','剤形区分':'','剤形名称':'','調剤数量':'','用法コード種別':'','用法コード':'','用法名称':'','回数':'','情報区分':'','薬品コード種別':'','薬品コード':'','薬品名称':'','用量':'','力価フラグ':'','単位名':'','薬品補足連番':'','薬品補足区分':'','薬品補足情報':'','補足用法コード':''}
        symspell_result='removed_variable_is_Left_JustinCase_of_html_issues' #dummy変数化
        med = medi_list[num] 
        med_specific = medi_list[num][0].strip('【般】') #最も確からしいmedをkeyとして設定する
        med2=[3] #dummy変数化
        ge_switch_OK = l_ge_switch_OK[num]
        
        #ひとつ前のstepのtext blockを取得
        if num==0:
            text_block_prev = ''
        else:
            text_block_prev = text_block
            
        #2つのmedi_textの差分を取って、該当text_blockを取得
        text_block = medi_text_list[num+1].split(medi_text_list[num])[1]
            
        #RP番号・RP番号内連番の更新
        RP_num,RP_renbanNum = update_RPNum(RP_num,RP_renbanNum,text_block_prev)
        dict_medInfo[num + 1]['RP番号'] = RP_num
        
        #101_剤形レコード
        chouzaiNum, zaikeiKubun,zaikeiKubunNum = func_101(text_block,med_specific)
        dict_medInfo[num+1]['剤形区分'] = zaikeiKubun ##ここ, 反映お願いしまーす！！
        dict_medInfo[num+1]['調剤数量'] = chouzaiNum
        
        #111_用法レコード    
        youhou = func_111(text_block)
        dict_medInfo[num+1]['用法名称'] = youhou
        dict_medInfo[num+1]['用法コード種別'] = 1 #基本1でOKなはず。コードなしを示す。今後要確認。
        
        #201_薬品レコード
        med_codeType,med_code,youryou_num,unit = func_201(text_block,med_specific)
        dict_medInfo[num+1]['PR番号内連番'] = RP_renbanNum
        dict_medInfo[num+1]['薬品コード種別'] = med_codeType
        dict_medInfo[num+1]['薬品コード'] = med_code
        dict_medInfo[num + 1]['薬品名称'] = med
        dict_medInfo[num + 1]['symspell結果']=symspell_result
        dict_medInfo[num+1]['用量'] = youryou_num
        dict_medInfo[num+1]['力価フラグ'] = 1
        dict_medInfo[num+1]['単位名'] = unit
        
        #281_薬品補足レコード
        bool_generics_changeOK = False
        list_of_l_hosoku = func_281(ge_switch_OK)
        
        dict_medInfo[num+1]['RP番号'] = RP_num
        dict_medInfo[num+1]['PR番号内連番'] = RP_renbanNum
        dict_medInfo[num+1]['薬品補足連番'] = list_of_l_hosoku[0] #一応、281領域だけ1薬品に対して複数存在しうる
        dict_medInfo[num+1]['薬品補足区分'] = list_of_l_hosoku[1]
        dict_medInfo[num+1]['薬品補足情報'] = list_of_l_hosoku[2]

        #MEMO of マツダ: この部分, もうちょい精緻化していきたいね〜〜
        if (3 in med2)or (4 in med2):
            dict_medInfo[num + 1]['accuracy_check'] = "あった"
        else:
            dict_medInfo[num + 1]['accuracy_check'] = "なかった"
        
    #     dict_medInfo[insert_index] = dict_singleMed
    #     insert_index+=1
        
    #     #print('')
        
    # #N個の医薬品の口を設けるとしたので、足りないやつを補う
    # for i in range(1,N+1):
    #     if i not in dict_medInfo.keys():
    #         dict_medInfo[i] = dict_singleMed.copy()
    
    return dict_medInfo[1],dict_medInfo[2],dict_medInfo[3],dict_medInfo[4],dict_medInfo[5],dict_medInfo[6],dict_medInfo[7],dict_medInfo[8],dict_medInfo[9],dict_medInfo[10]

#--------------------------------------------------------------------------------------
##############諸関数・正規表現の元の定義#######################
#調剤数量の正規表現list生成
l_chozaiNum_units = ['X日分','XTD','Xds','Xdays','XTH','XTM'] #'(X)'の形は話をややこしくするのでいったんpop

#用法の正規表現list生成
##pattern 1
l_1_times = ['分X','']
l_1_when = ['毎食後すぐ','毎食後','各食後','各食後すぐ',
            '朝夕食後','朝夕食後すぐ','朝・夕食後','朝・夕食後すぐ','朝食後と夕食後',
            '朝食後','朝食後すぐ','昼食後','昼食後すぐ','夕食後','夕食後すぐ','']
l_1_action = ['服用','']

l_1 = [l_1_times,l_1_when,l_1_action]

##pattern 2
l_2_times = ['X日X回','']
l_2_when = ['']
l_2_action = ['塗布','貼付','']
l_2_where = ['足の裏','あしのうら','']

l_2 = [l_2_times,l_2_when,l_2_action,l_2_where]

#free strings
l_free = [['各データを比較して最良と判断した為','上記薬剤配合お願い致します','']]

##group to single list
l_youhou_parts = [l_1,l_2,l_free]
l_youhou_flat = []
for list_ in l_youhou_parts:
    l_youhou_flat.extend(itertools.chain.from_iterable(list_))
    l_youhou_flat = [i for i in l_youhou_flat if len(i)>0]

#単位名(用量)の正規表現list生成
l_unit = list(set(list(df_medicineInfo['unit'])))
l_unit_customs = ['T','tab','C'] #正式のやつじゃないけど、よく使われる省略表現
l_unit.extend(l_unit_customs)
l_units_med = []
for val in l_unit:
    if type(val)==str:
        l_units_med.append('X'+val)


def list2str(l,numCondition='[0-9, ]+',youbiCondition='[月,火,水,木,金,土,日, ]+'):
    '''listを正規表現用の文字列に変換する処理'''
    str_=''
    for val in l:
        val = jaconv.normalize(val)
        val = re.sub('X',numCondition,val)
        val = re.sub('Y',youbiCondition,val)
        str_+=val+'|'
    str_ = str_[:-1]
    
    return str_


def update_RPNum(RP_num,RP_renbanNum,txt_prev,l1=l_chozaiNum_units,l2=l_youhou_flat):
    '''txtの中の文字列に応じて、更新されたRP番号を返す処理'''
    #調剤数量の文字列がそこに存在するか否か, 用法の文字列がそこに存在するか否か、の2点で判定
    if RP_num==0:
        return 1,1
    else:
        #調剤数量情報があるか検索
        search1 = re.search(list2str(l1),txt_prev)
        
        #用法情報があるか検索
        txt_prev = re.sub('\n','',txt_prev)
        for val in l2:
            search2 = re.search(list2str([val]),txt_prev)
            if search2 is not None:
                break

        if (search1 is not None) or (search2 is not None):
            return RP_num+1,1
        else:
            return RP_num,RP_renbanNum+1
        

def func_101(txt,med,l1=l_chozaiNum_units,l2=l_youhou_flat,df=df_medicineInfo):
    '''ある医薬品名称に紐づいた文字列ブロック及び医薬品名称を入力として、
    101_剤形レコードに関連する情報(剤形区分・調剤数量)と思われる文字列を返す処理'''
    
    #調剤数量の取得/調剤数量が存在する場合は、素直にその値を返す
    search_chouzaiNum = re.search(list2str(l1),txt)#調剤数量の単位を探す
    if search_chouzaiNum is not None:
        num = search_chouzaiNum.group()
        for val in [re.sub('X','',i) for i in l1]:
            if val in num:
                num = re.sub(val,'',num).strip(' ')

    #調剤数量は存在しないものの用法は存在する場合、JAHISのルールに乗っ取り1を記録する
    else:
        num='blank'       
        txt = re.sub('\n','',txt)
        for val in l2:
            search = re.search(list2str([val]),txt)
            if search is not None:
                num = '1'
                break
                
    #その他のケースでは-1を返す
    if num=='blank':
        num = '-1'
        
    #剤形区分の取得 ... 頓服などのケースもあるため、本来は文字列検索の上これを行うべき.
    #{内服:1, 頓服:2, 外用:3, 内服滴剤:4, 注射:5, 医療材料:6, 不明:9}
    kubun_num = df[df['品名']==med]['剤形区分'].iloc[0]
    if kubun_num == '1':
        kubun = '内服'
    elif kubun_num == '3':
        kubun = '外用'
    else:
        kubun_num = "9"
        kubun = '不明'
        
    return num,kubun,kubun_num

def func_111(txt,l=l_youhou_parts):
    '''ある医薬品名称に紐づいた文字列ブロックを入力として、
    111_用法レコードに関連する情報(用法)と思われる文字列を返す処理'''
    
    txt = re.sub('\n','',txt)
    
    str_ = ''
    for list_group in l:
        for list_ in list_group:
            for val in list_:
                if len(val)==0:
                    continue
                search = re.search(list2str([val]),txt)
                if search is not None:
                    str_+='&nbsp;'+search.group().strip(' ')
                    break
    
    if len(str_)>0:
        return str_.strip('&nbsp;')
    else:
        return '用法未取得'
    
def func_201(txt,med,l=l_units_med,df=df_medicineInfo):
    '''ある医薬品名称に紐づいた文字列ブロックを入力として
    201_薬品レコードの情報(医薬品コード種別・医薬品コード・用量・単位)を返す処理'''
    
    med_type = df[df['品名']==med]['GE_Branded_ippan'].iloc[0]

    #特定銘柄の場合、レセプト電算コードを取得する
    if med_type!='ippan':
        med_codeType = '2'
        med_code = df[df['品名']==med]['2_レセプト電算コード'].iloc[0]
    
    #一般名の場合、一般名コードを取得する
    else:
        med_codeType = '7'
        med_code = df[df['品名']==med]['7_一般名コード'].iloc[0]

    #各医薬品の単位をkeyに, 用量を取得する
    search = re.search(list2str(l),txt)
    if search is not None:
        for val in [re.sub('X','',i) for i in l]:
            if val in search.group():
                youryou_num = re.sub(val,'',search.group()).strip(' ')
                unit = val
    else:
        youryou_num = '-1'
        unit = df[df['品名']==med]['unit'].iloc[0]
    
    return med_codeType,med_code,youryou_num,unit
    
def func_281(bool_):
    '''ジェネリック医薬品変更可否を表すboolを入力とし、
    変更不可な場合はそれを表すJAHIS用の2次元listを返す処理'''
    #ユーザが確認画面でジェネリック変更可否を選択したのちに、いい感じに使う想定。
    #{1:一包化, 2:粉砕, 3:後発品変更不可, 4: 剤形変更不可, 5: 含量規格変更不可, 6: 剤形変更不可および含量規格変更不可, 7:JAMI補足用法, 省略: 不明}
    
    if bool_==False:
        return [1,3,'ジェネリック変更不可']
    else:
        return ['', '', '']
        
def convert_days(str_,genngou):
    '''XX年XX月XX日の形のstringを受取、genngouにて表された元号番号を添えて
    JAHIS規格で返す処理'''

    year = str_.split('年')[0]
    month = str_.split('年')[1].split('月')[0]
    day = str_.split('月')[1].split('日')[0]
    
    l = [re.sub(' ','',year),re.sub(' ','',month),re.sub(' ','',day)]
    
    for i in range(len(l)):
        if len(l[i])==1:
            l[i] = '0'+l[i]

    return str(genngou)+str(l[0])+str(l[1])+str(l[2])
#Aタイプの処方箋かBタイプの処方箋かを見極める関数
#Aは一段組、Bは二段組
#代入はarray
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


#保険者番号が検証番号の条件を満たしているかどうかを判別
def checkdigit(num):
    def over10(n):
        if n>9:
            n=n//10+n%10
        return n
    num_list=[int(x) for x in list(str(num))]
    if len(num_list)%2!=0:
        odd_num = [n*2 for n in num_list[1::2]]#奇数indexは二倍
        odd_num=[over10(n) for n in odd_num]
        even_num = num_list[0::2][:-1]#偶数idexはそのまま
        result=10-(sum(odd_num)+sum(even_num))%10

    else:
        even_num = [n*2 for n in num_list[0::2]]#奇数indexは二倍
        even_num=[over10(n) for n in even_num]
        odd_num = num_list[1::2][:-1]#偶数indexはそのまま
        result=10-(sum(odd_num)+sum(even_num))%10
    
    if result==10:
        result=0
    return (result == int(num[-1]))
    
#ピンボケ検出
def boke(image):
    return cv2.Laplacian(image, cv2.CV_64F).var()
def boke_check(image):
    if boke(image)<200:
        return True
    else:
        return False
#---------------------------------------------------------------------