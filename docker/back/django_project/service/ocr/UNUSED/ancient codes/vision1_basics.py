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

    return str(genngou) + str(l[0]) + str(l[1]) + str(l[2])
    

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
#---------------------------------------------------------------------