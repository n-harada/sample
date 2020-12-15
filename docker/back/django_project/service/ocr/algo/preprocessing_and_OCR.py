#coding:utf-8

#必要なもののimport 
import jaconv
import numpy as np
import cv2

#別ファイルの読み込み
try:
    from algo import recieve_info
    from algo import ocr_request
except ModuleNotFoundError:
    from . import recieve_info
    from . import ocr_request
    # harada
    print('imported using old dir struct')


#params
_default_width, _default_height = 1654, 2340


#------------------------------
#前処理部分全体　

ocr_result_base={"top_band":"","top_left_1":"","top_right_2":"",
                "med":"","insurance_patient_num":"", "insurance_kigou_bangou":"",
                "kouhi_1":'','kouhi_2':''}


def preprocess_and_OCR(upload_files,save_file_name_base,resized_height=10**4,ocr_result_base=ocr_result_base,on_APP=True):
    '''upload_filesの中にlist形式に格納されたフロントからの画像情報を受け、それに対し、
    ocr_resultの要素に分けたocr結果を返す処理.'''
    #on_APP = Falseとすると, 入力にファイルのpathを受けるようになる
    #現在はresized_heightを十分大きくし, 元画像をそのまま処理するフローに設計

    #initialize
    ocr_result = ocr_result_base.copy()

    #枚数分だけfor文を回す
    for i in range(len(upload_files)):

        file_ = upload_files[i]

        #imageの読み込み
        if on_APP:
            save_file_name = save_file_name_base + '_' +str(i)
            image = recieve_info.recieve_and_save_file_storage(file_,save_file_name)
        else:
            image = recieve_info.path_to_array(file_)

        image = resize_image(image,h_after=resized_height)
        image_cut_finished, prescription_shape_type, boke = preprocess_image(image)
        ocr_result = conduct_OCR(image_cut_finished, prescription_shape_type, ocr_result)

    return ocr_result, boke

def resize_image(img,h_after):
    '''画像のアスペクト比を保ちつつ、height_resizedの大きさにresizeする処理'''

    h,w,_ = img.shape
    if h<=h_after:
        return img
    else:
        size = (int(w*h_after/h),int(h_after))
        resized_img = cv2.resize(img,size)
        return resized_img

def preprocess_image(image):
    '''np.arrayにて表されるimageを入力として受け、
    ピンぼけ判定・処方箋構造推定・歪み補正・画像領域切り取り、を行い、その結果を返す処理'''
    
    #歪み補正
    image_yugami_finished = yugami(image)

    #ボケ度を数値化（True/False)
    boke = boke_check(image_yugami_finished)

    #タイプを判別　Aが一段組、Bが2段組
    prescription_shape_type = type_check(image_yugami_finished)

    #切り取り
    #[0]基本情報部分、[1]基本情報の左上、[2]基本情報の左下、[3]基本情報の右上、[4]基本情報の右下、[5]処方情報部分、[6]処方情報の左、[7]処方情報の右、[8]保険者番号部分、[9]PHCパラメータで保険者番号を切り取った場合、[10]矢澤先生パラメータで保険者番号を切り取った場合、[11]記号番号
    image_cut_finished = cut(image_yugami_finished)

    return image_cut_finished, prescription_shape_type, boke

def conduct_OCR(image_cut_finished, prescription_shape_type,ocr_result,empty_detection_key='med'):
    '''領域切り取り・処方箋構造判定結果・現状ocr_result, を受け、必要なOCR requestを行い
    その結果をocr_resultに結合する処理'''

    def normalize_dict(dict_):
        '''OCR結果の2次元listのdictの各要素をnormalizeする処理'''

        dict_out = {}
        for key in dict_.keys():
            lists = dict_[key]
            l_out = []
            for l in lists:
                l_out.extend([jaconv.normalize(i)] for i in l)
            dict_out[key] = l_out[:]
        return dict_out

    #1枚目
    if len(ocr_result[empty_detection_key])==0:
        dict_ = image_cut_finished
        #処方箋タイプがA（一段組）の時
        if prescription_shape_type=="A":
            kinds=[
                dict_['top_band'], dict_['top_left_1'], dict_['top_right_2'],
                dict_['bottom_all'],
                dict_['hokensha_num'], dict_['kigou_bangou'],
                dict_['kouhi_num_1'], dict_['kouhi_num_2']
                ]

            result_dic = ocr_request.api_pararel(kinds)
            result_dic = normalize_dict(result_dic)

            ocr_result['top_band'] = result_dic[0]
            ocr_result["top_left_1"] = result_dic[1]
            ocr_result["top_right_2"] = result_dic[2]
            ocr_result["med"]=result_dic[3]
            ocr_result["insurance_patient_num"]=result_dic[4]
            ocr_result["insurance_kigou_bangou"]=result_dic[5]
            ocr_result['kouhi_1'] = result_dic[6]
            ocr_result['kouhi_2'] = result_dic[7]

        #処方箋タイプがB（2段組）の時
        elif prescription_shape_type=='B':
            kinds=[
                dict_['top_band'], dict_['top_left_1'], dict_['top_right_2'],
                dict_['bottom_l'],dict_['bottom_r'],
                dict_['hokensha_num'], dict_['kigou_bangou'],
                dict_['kouhi_num_1'], dict_['kouhi_num_2']
                ]
            
            result_dic = ocr_request.api_pararel(kinds)
            result_dic = normalize_dict(result_dic)

            ocr_result['top_band'] = result_dic[0]
            ocr_result["top_left_1"] = result_dic[1]
            ocr_result["top_right_2"] = result_dic[2]
            ocr_result["med"] = result_dic[3] + result_dic[4]
            ocr_result["insurance_patient_num"]=result_dic[5]
            ocr_result["insurance_kigou_bangou"]=result_dic[6]
            ocr_result['kouhi_1'] = result_dic[7]
            ocr_result['kouhi_2'] = result_dic[8]


        
    #2枚目以降
    else:
        #処方箋タイプがA（一段組）の時
        if prescription_shape_type == "A":
            kinds = [image_cut_finished['bottom_all']]
            result_dic = ocr_request.api_pararel(kinds)
            result_dic = normalize_dict(result_dic)
            med_text = result_dic[0]

        #処方箋タイプがB（2段組）の時
        elif prescription_shape_type=='B':
            kinds = [image_cut_finished['bottom_l'], image_cut_finished['bottom_r']]
            result_dic = ocr_request.api_pararel(kinds)
            result_dic = normalize_dict(result_dic)
            med_text = result_dic[0] + result_dic[1]
        ocr_result["med"] = ocr_result["med"] + med_text

    return ocr_result.copy()

#------------------------------
ALLOWED_EXTENSIONS = set(['png','jpg','jpeg'])
def allwed_file(filename):
    ''' .があるかどうかのチェックと、拡張子の確認
    # OKなら１、だめなら0'''
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#------------------------------
#ピンボケ検出
def boke(image):
    '''ピンボケ度を数値で返す
    input:array
    ooutput:数値
    '''
    return cv2.Laplacian(image, cv2.CV_64F).var()

def boke_check(image,thresh=200):
    '''ピンボケ度の数値を閾値で評価
    input:array
    output:ピンぼけしている: True/ピンぼけしていない: False
    '''
    if boke(image)<thresh:
        return True
    else:
        return False


#------------------------------
#輪郭を検出する。
def waku_detection(img,l_threshold,aspect_thresh=1.35,A5_aspect_ratio=1.418,crop_area_thresh=0.4,mode='tilt_support'):
    '''input:画像のarray -> output:元の画像のarray,補正前の4隅の座標,補正前の横の長さ
    modeでは, tilt_support / aspect_supportを選択し, 前者が画像の傾きを前提に, 後者は検査結果が右に添えられているようなA5サイズ以外の処方箋を前提に, 処理を行う'''

    detection_successful = False
    h,w,_ = img.shape
    base_image_area = h*w
    for threshold in l_threshold:

        try:

            #画像の外郭に存在する領域の中身を塗りつぶす
            try: #PATCH JUST IN CASE
                img_filled = fill_outerContours(img,threshold)
            except Exception as e:
                print('outer fill function FAILED. args',e.args)

            #再度画像をグレースケール化
            img_gray = cv2.cvtColor(img_filled, cv2.COLOR_RGB2GRAY)

            #閾値に対して2値化
            ret, img_thresh = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)

            #輪郭を取り出している
            contours, hierarchy = cv2.findContours(img_thresh , cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

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

            if len(approx)<=3:
                raise IndexError('approx is not square')

            left = sorted(approx,key=lambda x:x[0]) [:2]
            right = sorted(approx, key=lambda x: x[0])[2:]
            
            top_left= sorted(left,key=lambda x:x[0][1]) [0]
            bottom_left= sorted(left,key=lambda x:x[0][1]) [1]

            top_right= sorted(right,key=lambda x:x[0][1]) [0]
            bottom_right= sorted(right,key=lambda x:x[0][1]) [1]
            
            #取得領域が一定以上小さい場合はノイズを検知したと判断してcontintue
            cnt = np.array([top_left,bottom_right,bottom_right,top_right])
            area_cropped = cv2.contourArea(cnt)
            if area_cropped < base_image_area*crop_area_thresh:
                print('waku detection threshold',threshold,'was ineffective. NOIZE FETCHED') ##DEBUG PRINT
                continue

            print('waku detection threshold',threshold,'was effective') ##DEBUG PRINT
            detection_successful = True
            break
        
        except IndexError:
            print('waku detection threshold',threshold,'was ineffective') ##DEBUG PRINT
            continue

    if detection_successful==False:
        raise IndexError('all waku threshold params ineffective')

    #補正前の角の座標
    perspective1 = np.float32([top_left, top_right, bottom_right, bottom_left])

    #縦横比を取得する
    mean_y_t = int((perspective1[0][0][1] + perspective1[1][0][1])/2)
    mean_y_b = int((perspective1[2][0][1] + perspective1[3][0][1])/2)
    mean_x_l = int((perspective1[0][0][0] + perspective1[3][0][0])/2)
    mean_x_r = int((perspective1[1][0][0] + perspective1[2][0][0])/2)

    mean_height = mean_y_b - mean_y_t
    mean_width = mean_x_r - mean_x_l
    ratio = mean_height/mean_width

    #アスペクト比が一定以下の場合、補正をする
    if ratio<=aspect_thresh and mode=='aspect_support':
        print('hand adjusting aspect ratio')
        mean_x_r_corrected = int(mean_x_l + mean_height/A5_aspect_ratio)
        top_right_corrected = [[mean_x_r_corrected,top_right[0][1]]]
        bottom_right_corrected = [[mean_x_r_corrected,bottom_right[0][1]]]
        perspective1 = np.float32([top_left,top_right_corrected,bottom_right_corrected,bottom_left])

    #補正後の横の長さ
    width = top_right[0][0] - top_left[0][0]
    return img,perspective1,width

def fill_outerContours(img,binary_thresh,area_threshold_ratio=0.1,min_area_ratio=0.001):
    '''撮影画像の外角に小さな輪郭が検出された際、それを塗りつぶして返す処理'''

    #initialize
    imgContour = img.copy()
    thresh_area = img.shape[0]*img.shape[1]*area_threshold_ratio
    min_area = img.shape[0]*img.shape[1]*min_area_ratio

    #thresh-binary the image
    img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    _, img_thresh = cv2.threshold(img_gray, binary_thresh, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(img_thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area<=thresh_area and area>=min_area:
            if is_outer(cnt,img=img):
                print(area,'was outer area') ##DEBUG PRINT
                cnt = reshape_cnt(cnt)
                imgContour = cv2.fillConvexPoly(imgContour, cnt, color=(0,0,0))

    return imgContour.copy()

def reshape_cnt(cnt):
    '''fillPolyConve用にcontourを整形する処理'''
    
    l_out = []
    for val in cnt:
        l_out.append(val[0])
    return np.array(l_out)

def is_outer(cnt,img,epsilon=0.001):
    '''contourが外郭に該当するか、判定する処理'''
    
    img_width,img_height = img.shape[0],img.shape[1]
    
    x_border = img_width*epsilon
    y_border = img_height*epsilon
    
    for val in cnt:
        x = val[0][0]
        y = val[0][1]
        
        if x<=x_border or x>=img_width-x_border or y<=y_border or y>=img_height-y_border:
            return True
    
    return False


#------------------------------
def yugami(image_array,l_waku_detection_threshold=[120,130,105],default_width=_default_width, default_height =_default_height):
    '''歪み補正
    input:画像のPath ... [mzd comment]画像のarrayっぽい.
    output:歪み補正した画像のarray
    '''
    try:
        #枠検出した結果をwaku_detection_resultに格納
        waku_detection_result=waku_detection(image_array,l_threshold=l_waku_detection_threshold)
    except IndexError as e:
        #枠検出できなかった場合(IndexErrorが返ってくる想定)は、諦めてそのままの画像を返す
        print('yugami function failed','args:',e.args)
        return image_array

    #無事枠検出できた場合、その結果に沿って画像の歪み補正を実施
    img, perspective1, width = waku_detection_result
    
    #補正後の縦の長さ
    height=width*default_height//default_width

    #補正後の4点
    perspective2 = np.float32([[0, 0],[width, 0],[width, height],[0, height]])
    
    #変換に必要な行列
    psp_matrix = cv2.getPerspectiveTransform(perspective1,perspective2)
    
    #変換後
    img_psp = cv2.warpPerspective(img, psp_matrix, (width, height))
    return img_psp


#------------------------------
def type_check(img):
    '''
    2段組かどうかを判別
    input:画像のarray（歪み補正後）
    output:A（1段組）or B（2段組）
    '''
    height=img.shape[0]
    width=img.shape[1]

    img=img[height//2: 5 * height // 8, width*2//5:width*3//5]
    #img = cv2.resize(img,(int(img.shape[1]/5),int(img.shape[0]/5)))
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    #gray = cv2.GaussianBlur(gray,(5,5),5)

    #plt.gray()
    #plt.imshow(gray)

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

def cut(image,threshold_ratio=4.5):
    '''画像を領域ごとに切り取る処理'''

    #setting params
    return_top_ratio = 0.025 #処方箋の上部の余白領域
    top_start_ratio = 0.1 #患者情報領域の右下を切り取る際の、上からの起点の割合
    total_top_end_ratio = 0.4 #患者基本情報が存在するとする領域の高さend ratio
    bottom_start_ratio = 0.2 #医薬品情報が存在するとする領域の高さ start ratio
    bottom_end_ratio = 0.8 #医薬品情報がもう存在しないとする領域の高さ ratio

    confident_cutoff_divider = 1.5 #患者情報領域のうち、記号番号がないと想定する領域の定義用のparam

    #画像をグレースケール化 入れるのはarray
    img_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    height,width = img_gray.shape
    
    #保険者番号・記号番号領域の切り出し
    img_hokensha_nums=image[0:int(height*total_top_end_ratio/confident_cutoff_divider),width//2:width]     
                     
    # BGR -> グレースケール
    gray = cv2.cvtColor(img_hokensha_nums, cv2.COLOR_BGR2GRAY)

    # エッジ抽出 (Canny)
    edges = cv2.Canny(gray, 50, 190, apertureSize=3)

    # 膨張処理
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel)

    # 輪郭抽出
    contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 親要素の存在するrectのうち面積が最大のものをフィルタリング
    rects = []
    mensekilist=[]
    for cnt, hrchy in zip(contours, hierarchy[0]):
        menseki = cv2.contourArea(cnt)
        if  menseki< 30:
            continue  # 面積が小さいものは除く
        if hrchy[3] == -1:
            continue  # ルートノードは除く
        # 輪郭を囲む長方形を計算する。
        rect = cv2.minAreaRect(cnt)
        rect_points = cv2.boxPoints(rect).astype(int)
        rects.append(rect_points)
        mensekilist.append(menseki)
    max_area_index=mensekilist.index(max(mensekilist))

    # x-y 順でソート
    #rects = sorted(rects, key=lambda x: (x[0][1], x[0][0]))

    #max areaを示すrectの4点を取得する
    target_rect = order_points(rects[max_area_index][:])
    smallx=round((target_rect[0][0] +target_rect[3][0])//2)
    largex=round((target_rect[1][0] +target_rect[2][0])//2)
    smally=round((target_rect[0][1] +target_rect[1][1])//2)
    largey=round((target_rect[2][1] +target_rect[3][1])//2)

    #get features of rect
    ratio = (largex-smallx)/(largey-smally)
    delta_y = (target_rect[1][1]-target_rect[0][1])/(target_rect[1][0]-target_rect[0][0])

    #initialize
    top_band = np.empty(0)
    hokensha_num, kigou_bangou,kouhi_num_1,kouhi_num_2 = [np.empty(0)]*4

    if ratio<=threshold_ratio:
        top_band = image[int(height*return_top_ratio):int(height*total_top_end_ratio/confident_cutoff_divider),0:width]
        print('ratio:',ratio, 'probably MISS in CUT') # -> use pure OCR results to get the nums

    else:
        #記号・番号領域と思われる領域を取得する
        epsilon_x = int(height*0.005)
        kigou_bangou=img_hokensha_nums[smally:largey,smallx+epsilon_x:largex-epsilon_x]

        #get params
        kigou_bangou_height = largey - smally
        smallx = smallx + width//2
        largex = largex + width//2
        kigou_bangou_width = largex - smallx

        #記号番号の上の領域(=保険者番号領域)を取得する
        epsilon_y = int(kigou_bangou_height*0.02)
        epsilon_x = int(kigou_bangou_width*0.1)
        start_y = smally - kigou_bangou_height + epsilon_y
        end_y = largey - kigou_bangou_height - epsilon_y
        start_x = smallx-epsilon_x
        end_x = largex
        hokensha_num = image[start_y:end_y , start_x:end_x]

        #smally, largeyをベースに、公費情報領域を取得する
        buffer_yohaku = width - largex
        #corrected_smally = int(smally - delta_y*smallx)
        #corrected_largey = int(largey - delta_y*smallx)
        epsilon_y = int(kigou_bangou_height*0.1)
        corrected_smally = smally - epsilon_y
        corrected_largey = largey + epsilon_y
        kouhi_num_2 = image[corrected_smally:corrected_largey,buffer_yohaku:width//2]

        #epsilon = int(kigou_bangou_height*0.02)
        corrected_start_y = corrected_smally - kigou_bangou_height + epsilon_y
        corrected_end_y = corrected_largey - kigou_bangou_height - epsilon_y
        kouhi_num_1 = image[corrected_start_y:corrected_end_y,buffer_yohaku:width//2]

    #患者基本情報領域をルールベースで切り取る
    top_left_1 = image[int(height*top_start_ratio):int(height*total_top_end_ratio), 0:width // 2]
    top_right_2 = image[int(height*top_start_ratio):int(height*total_top_end_ratio), width//2:width]
    
    #処方情報領域も同様に、ルールベースで切り取る
    bottom_l = image[int(height*bottom_start_ratio) :int(height*bottom_end_ratio), 0 :width//2]
    bottom_r = image[int(height*bottom_start_ratio) :int(height*bottom_end_ratio), width // 2 :width]
    bottom_all = image[int(height*bottom_start_ratio) :int(height*bottom_end_ratio), 0:width]
    
    dict_out = {}

    dict_out['top_band'] = top_band
    dict_out['top_left_1'] = top_left_1
    dict_out['top_right_2'] = top_right_2
    dict_out['bottom_l'],dict_out['bottom_r'] = bottom_l,bottom_r
    dict_out['bottom_all'] = bottom_all

    dict_out['hokensha_num'],dict_out['kigou_bangou'] = hokensha_num, kigou_bangou
    dict_out['kouhi_num_1'],dict_out['kouhi_num_2'] = kouhi_num_1,kouhi_num_2
    
    return dict_out


def order_points(pts):
    # sort the points based on their x-coordinates
    xSorted = pts[np.argsort(pts[:, 0]), :]

    # grab the left-most and right-most points from the sorted
    # x-roodinate points
    leftMost = xSorted[:2, :]
    rightMost = xSorted[2:, :]

    # now, sort the left-most coordinates according to their
    # y-coordinates so we can grab the top-left and bottom-left
    # points, respectively
    leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
    (tl, bl) = leftMost

    # if use Euclidean distance, it will run in error when the object
    # is trapezoid. So we should use the same simple y-coordinates order method.

    # now, sort the right-most coordinates according to their
    # y-coordinates so we can grab the top-right and bottom-right
    # points, respectively
    rightMost = rightMost[np.argsort(rightMost[:, 1]), :]
    (tr, br) = rightMost

    # return the coordinates in top-left, top-right,
    # bottom-right, and bottom-left order
    return np.array([tl, tr, br, bl], dtype="int")
