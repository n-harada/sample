#coding:utf-8
#必要なもののimport
import os
from warnings import warn
import datetime as dt
import Levenshtein as L
import qrcode
from PIL import Image, ImageDraw, ImageFilter
import smtplib
from email.mime.text import MIMEText
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from django.core.files.storage import default_storage
from django.core.files.images import ImageFile
from config.const import TEMPORARY_DIR


#別ファイルの読み込み
try:
    from algo import basic_info as bi
    from algo import med_info as mi
except ModuleNotFoundError:
    from . import basic_info as bi
    from . import med_info as mi
    print('imported using old dir struct')

#basic_result, med_resultの雛形を読み込み
_basic_result_base = bi.basic_result_base.copy()
_med_result_base = mi.dict_medInfo_base.copy()

#gmailへアクセス
HOST, PORT = 'smtp.gmail.com', 465 #using ssl
SENDER, PASSWORD = 'yuki-matsuda@g.ecc.u-tokyo.ac.jp', 'knmwtiktwmnykwcb' # 送信元メールアドレスとgmailへのログイン情報 

def load_gmail_obj(host=HOST,port=PORT,sender=SENDER,password=PASSWORD):
    '''XXXX'''

    print('logging in to mail...')
    gmail_obj = smtplib.SMTP_SSL(host,port)
    gmail_obj.ehlo()
    gmail_obj.login(sender, password)

    return gmail_obj

#----------<main処理>----------------------------------------------------------------
def make_qrcode(basic_result, med_result, save_file_name_base, out_dir='./uploads/QR_images',EOL = "\r\n",version="JAHIS7",return_image=False,):
    '''XXXX'''

    if basic_result is None:
        basic_result, med_result = create_dummy_results()

    result, len_dict_med_info = create_JAHIS_str(basic_result, med_result)

    result_sj = result.encode('shift_jis', 'replace')
    mojibake = 0
    mojibake = str(result_sj).count('?')

    print("result")
    print(result)
    #print("----------------")
    #print(result_sj)
    
    qr = qrcode.QRCode(version=2, box_size=50)
    qr.add_data(result_sj)
    qr.make()
    img = qr.make_image()

    if return_image:
        #DEBUG用に, return_imageを行う場合の処理系統
        return img
    else:
        file_name = save_file_name_base + '_for_main_qrcode.jpeg'
        save_dir = os.path.join(out_dir, file_name)
        os.makedirs(out_dir, exist_ok=True)
        img.save(save_dir)
        with open(save_dir, 'rb') as f:
            qr_file = ImageFile(f)
            storage_save_dir = save_dir.replace(TEMPORARY_DIR + "/", "")
            path = default_storage.save(storage_save_dir, qr_file)
            os.remove(save_dir)

        return (path, mojibake), len_dict_med_info, basic_result, med_result, result

#----------<以上、main処理>----------------------------------------------------------------

#----------<QRコードをPDF送付するための処理>----------------------------------------------------------------

def process_QRimg_for_print(save_file_name_base,raw_img_base_dir='./uploads/prescription_images',QR_base_dir='./uploads/QR_images',canvas_dir='./material/A4_canvas.jpg',out_base_dir='./uploads/QR_images_A4'):
    '''XXXX'''

    prescription_size_ratio = 0.6
    prescription_pos_ratio = 0.05
    QR_size_ratio = 0.25
    QR_pos_ratio = 0.7
    
    #load A4 canvas
    canvas = Image.open(canvas_dir)

    #read paste files
    raw_prescription_file = save_file_name_base+'_0.jpeg' #初期的には1枚目だけ添付
    prescription_dir = os.path.join(raw_img_base_dir,raw_prescription_file)    
    prescription_im = Image.open(prescription_dir)

    if prescription_im.width > prescription_im.height:
        print('prescription_im.size',prescription_im.size) ##DEBUG PRINT
        prescription_im = prescription_im.rotate(270,expand=True)

    target_file = save_file_name_base+'_for_main_qrcode.jpeg'
    QR_dir = os.path.join(QR_base_dir,target_file)
    QR_im = Image.open(QR_dir)
    
    #resize and paste prescription
    h = int(canvas.height*prescription_size_ratio)
    w = int(h*(prescription_im.width/prescription_im.height))
    position = (int(canvas.width*prescription_pos_ratio),int(canvas.height*prescription_pos_ratio))
    prescription_im_resized = prescription_im.resize((w,h))
    canvas.paste(prescription_im_resized,position)
    
    #resize and paste QR code
    qr_length = int(canvas.width*QR_size_ratio)
    position = (int(canvas.width*QR_pos_ratio),int(canvas.height*QR_pos_ratio))
    QR_im_resized = QR_im.resize((qr_length,qr_length))
    canvas.paste(QR_im_resized,position)
    
    save_name = save_file_name_base+'_for_main_qrcode_A4.pdf'
    out_dir = os.path.join(out_base_dir,save_name)
    canvas.save(out_dir)

    return True

def send_img_attatched_mail(save_file_name_base,usr_name,gmail,to,sender=SENDER,pdf_base_dir='./uploads/QR_images_A4'):
    '''XXXX'''
   
    l_dt_str = save_file_name_base.lstrip(usr_name).lstrip('_').split('-')
    Y,M,D,h,m = l_dt_str[:5]
    dt_str = h+':'+m

    sub = dt_str+'の読み取り結果を送付いたします' #メール件名
    body = dt_str+'に撮影いただいた処方箋の読み取り結果を、送付させていただきます.'  # メール本文
    
    # メールヘッダー
    msg = MIMEMultipart()
    msg['Subject'] = sub
    msg['From'] = sender
    msg['To'] = to

    # メール本文
    body = MIMEText(body)
    msg.attach(body)

    # 追加部分
    file_name = save_file_name_base+'_for_main_qrcode_A4.pdf'
    target_list = os.path.join(pdf_base_dir,file_name)

    # 添付ファイルの設定 'name': os.path.basename(target_list)
    attach_file = {
        'name': 'result_'+Y+M+D+'_'+h+'_'+m+'.pdf',
        'path': target_list
    } # nameは添付ファイル名。pathは添付ファイルの位置を指定
    attachment = MIMEBase("application", "pdf")
    file = open(attach_file['path'], 'rb+')
    attachment.set_payload(file.read())
    file.close()
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename=attach_file['name'])
    msg.attach(attachment)
    
    gmail.send_message(msg)

    return True

#----------<以上、QRコードをPDF送付するための処理>----------------------------------------------------------------

#----------<JAHIS文字列生成の処理>----------------------------------------------------------------

#入力情報が欠損であると判定する文字列の定義
l_deficit_vals = ['用法未取得','-1','ダミー','XXX']

def create_JAHIS_str(basic_result,med_result,EOL='\r\n',JAHIS_ver='JAHIS7'):
    '''input_typeに応じて入力情報を整形し、JAHIS規格の文字列を返す処理'''
    
    dict_basic_info = unpack_basic_result_2_dict(basic_result)
    dict_med_info = unpack_list_of_med_dict_2_dict(med_result)

    JAHIS_str = JAHIS_ver + EOL + create_basic_str(dict_basic_info,EOL,JAHIS_ver) + create_med_str(dict_med_info,EOL,JAHIS_ver)
        
    return JAHIS_str,len(dict_med_info)

#----------<以上、JAHIS文字列生成の処理>----------------------------------------------------------------

#----------<患者基本情報JAHIS文字列生成のための処理>----------------------------------------------------------------

#入力情報が欠損の場合のダミー値の定義
dict_dummy_basics = {}

dict_dummy_basics['1_医療機関レコード'] = {}
dict_dummy_basics['1_医療機関レコード']['医療機関コード種別'] = '1'
dict_dummy_basics['1_医療機関レコード']['医療機関コード']  = '0000000'
dict_dummy_basics['1_医療機関レコード']['医療機関都道府県コード']  = '1'
dict_dummy_basics['1_医療機関レコード']['医療機関名称'] = 'テスト医療機関'

dict_dummy_basics['5_医師レコード'] = {}
dict_dummy_basics['5_医師レコード']['医師カナ氏名'] = 'ﾃｽﾄｲｼ'
dict_dummy_basics['5_医師レコード']['医師漢字氏名'] = 'テスト医師'

dict_dummy_basics['11_患者氏名レコード'] = {}
dict_dummy_basics['11_患者氏名レコード']['患者漢字氏名'] = 'テスト患者'
dict_dummy_basics['11_患者氏名レコード']['患者カナ氏名'] = 'ﾃｽﾄｶﾝｼﾞｬ'

dict_dummy_basics['12_患者性別レコード'] = {}
dict_dummy_basics['12_患者性別レコード']['患者性別'] = '0'

dict_dummy_basics['13_患者生年月日レコード'] = {}
dict_dummy_basics['13_患者生年月日レコード']['患者生年月日'] = '1360101'

dict_dummy_basics['22_保険者番号レコード'] = {}
dict_dummy_basics['22_保険者番号レコード']['保険者番号'] = '00000000'
    
dict_dummy_basics['23_記号番号レコード'] = {}
dict_dummy_basics['23_記号番号レコード']['被保険者証記号'] = 'XX'
dict_dummy_basics['23_記号番号レコード']['被保険者証番号'] = 'XX'
dict_dummy_basics['23_記号番号レコード']['被保険者/被扶養者'] = '0'

dict_dummy_basics['27_第一公費レコード'] = {}
dict_dummy_basics['27_第一公費レコード']['第一公費負担者番号'] = ''
dict_dummy_basics['27_第一公費レコード']['第一公費受給者番号'] = ''

dict_dummy_basics['51_処方箋交付年月日レコード'] = {}
dummy_date = dt.datetime.now() - dt.timedelta(days=7)
y,m,d = bi.assert_digit_nums(str(dummy_date.year-bi._dict_era_start['令和']+1))[0], bi.assert_digit_nums(str(dummy_date.month))[0], bi.assert_digit_nums(str(dummy_date.day))[0]
dict_dummy_basics['51_処方箋交付年月日レコード']['処方箋交付年月日'] = '5'+y+m+d

def unpack_basic_result_2_dict(basic_result):
    '''basic_resultをJAHIS規格文字列に変換するコードに受取可能な形に
    成形する処理'''

    dict_basic_info = {}

    dict_basic_info['1_医療機関レコード'] = {}
    dict_basic_info['1_医療機関レコード']['医療機関コード種別'] = basic_result["_1_hospital_code_type"]
    dict_basic_info['1_医療機関レコード']['医療機関コード']  = basic_result["_1_hospital_code"]
    dict_basic_info['1_医療機関レコード']['医療機関都道府県コード']  = basic_result["_1_hospital_place_code"]
    dict_basic_info['1_医療機関レコード']['医療機関名称'] = basic_result["id_1_hospital_name"]

    dict_basic_info['5_医師レコード'] = {}
    dict_basic_info['5_医師レコード']['医師漢字氏名'] = basic_result['_5_doctor_name_kanji']
    dict_basic_info['5_医師レコード']['医師カナ氏名'] = basic_result['_5_doctor_name_kana']

    dict_basic_info['11_患者氏名レコード'] = {}
    dict_basic_info['11_患者氏名レコード']['患者漢字氏名'] = basic_result["id_11_patient_name_kanji"]
    dict_basic_info['11_患者氏名レコード']['患者カナ氏名'] = basic_result["id_11_patient_name_kana"]
        
    dict_basic_info['12_患者性別レコード'] = {}
    dict_basic_info['12_患者性別レコード']['患者性別'] = basic_result["id_12_patient_sex"]

    dict_basic_info['13_患者生年月日レコード'] = {}
    dict_basic_info['13_患者生年月日レコード']['患者生年月日'] = basic_result['_13_patient_birthday']

    dict_basic_info['22_保険者番号レコード'] = {}
    dict_basic_info['22_保険者番号レコード']['保険者番号'] = basic_result["id_22_insurance_patient_num"]
        
    dict_basic_info['23_記号番号レコード'] = {}
    dict_basic_info['23_記号番号レコード']['被保険者証記号'] = basic_result["id_23_insurance_card_id"]
    dict_basic_info['23_記号番号レコード']['被保険者証番号'] = basic_result["id_23_insurance_card_num"]
    dict_basic_info['23_記号番号レコード']['被保険者/被扶養者'] = basic_result["_23_insurance_type"]

    dict_basic_info['27_第一公費レコード'] = {}
    dict_basic_info['27_第一公費レコード']['第一公費負担者番号'] = basic_result["_27_1st_kouhi_futansha_num"]
    dict_basic_info['27_第一公費レコード']['第一公費受給者番号'] = basic_result["_27_1st_kouhi_jukyuusha_num"]

    dict_basic_info['51_処方箋交付年月日レコード'] = {}
    dict_basic_info['51_処方箋交付年月日レコード']['処方箋交付年月日'] = basic_result['_51_prescription_date']

    return dict_basic_info

def look_up_basic_dict(dict_basic_info,key1,key2,dict_dummy_basics=dict_dummy_basics):
    '''指定されたkeyの患者基本情報をlookupし, それが欠損情報の場合はダミー値を代入する処理'''
    
    val = dict_basic_info[key1][key2]
    if val in l_deficit_vals:
        val = dict_dummy_basics[key1][key2]
    return val


def create_basic_str(dict_basic_info,EOL,JAHIS_ver,JAHIS_ver_algo='JAHIS7'):
    '''情報が整備された患者基本情報dictを受け取り, それをJAHIS規格文字列に変換して返す処理'''
    
    #assert JAHIS_ver==JAHIS_ver_algo, 'JAHIS ver must match'

    _1_hospital_code_type=look_up_basic_dict(dict_basic_info,'1_医療機関レコード','医療機関コード種別')
    _1_hospital_code=look_up_basic_dict(dict_basic_info,'1_医療機関レコード','医療機関コード')
    _1_hospital_place_code=look_up_basic_dict(dict_basic_info,'1_医療機関レコード','医療機関都道府県コード')
    id_1_hospital_name=look_up_basic_dict(dict_basic_info,'1_医療機関レコード','医療機関名称')
    
    _5_doctor_name_kanji = look_up_basic_dict(dict_basic_info,'5_医師レコード','医師漢字氏名')
    _5_doctor_name_kana = look_up_basic_dict(dict_basic_info,'5_医師レコード','医師カナ氏名')
    
    id_11_patient_name_kanji = look_up_basic_dict(dict_basic_info,'11_患者氏名レコード','患者漢字氏名')
    id_11_patient_name_kana = look_up_basic_dict(dict_basic_info,'11_患者氏名レコード','患者カナ氏名')
    
    id_12_patient_sex = look_up_basic_dict(dict_basic_info,'12_患者性別レコード','患者性別')
    
    _13_patient_birthday = look_up_basic_dict(dict_basic_info,'13_患者生年月日レコード','患者生年月日')
     
    id_22_insurance_patient_num = look_up_basic_dict(dict_basic_info,'22_保険者番号レコード','保険者番号',)
       
    id_23_insurance_card_id = look_up_basic_dict(dict_basic_info,'23_記号番号レコード','被保険者証記号') 
    id_23_insurance_card_num = look_up_basic_dict(dict_basic_info,'23_記号番号レコード','被保険者証番号')
    _23_insurance_type = look_up_basic_dict(dict_basic_info,'23_記号番号レコード','被保険者/被扶養者')

    _27_1st_kouhi_futansha_num = look_up_basic_dict(dict_basic_info,'27_第一公費レコード','第一公費負担者番号')
    _27_1st_kouhi_jukyuusha_num = look_up_basic_dict(dict_basic_info,'27_第一公費レコード','第一公費受給者番号')

    _51_prescription_date = look_up_basic_dict(dict_basic_info,'51_処方箋交付年月日レコード','処方箋交付年月日')
    
    if _27_1st_kouhi_futansha_num != '':

        basic_result = (
            "1"+","+_1_hospital_code_type + "," + _1_hospital_code + "," + _1_hospital_place_code + "," + id_1_hospital_name + EOL
            +"5"+","+ "" + "," + _5_doctor_name_kana + "," + _5_doctor_name_kanji + EOL
            +"11"+","+ "" + "," + id_11_patient_name_kanji + "," + id_11_patient_name_kana + EOL
            +"12"+","+ id_12_patient_sex + EOL
            +"13"+","+ _13_patient_birthday + EOL
            +"22"+","+id_22_insurance_patient_num+EOL
            +"23"+","+id_23_insurance_card_id+","+id_23_insurance_card_num+","+_23_insurance_type+","+""+EOL
            +"27"+","+_27_1st_kouhi_futansha_num+","+_27_1st_kouhi_jukyuusha_num + EOL
            +"51"+","+_51_prescription_date+EOL)

    else:
        basic_result = (
            "1"+","+_1_hospital_code_type + "," + _1_hospital_code + "," + _1_hospital_place_code + "," + id_1_hospital_name + EOL
            +"5"+","+ "" + "," + _5_doctor_name_kana + "," + _5_doctor_name_kanji + EOL
            +"11"+","+ "" + "," + id_11_patient_name_kanji + "," + id_11_patient_name_kana + EOL
            +"12"+","+ id_12_patient_sex + EOL
            +"13"+","+ _13_patient_birthday + EOL
            +"22"+","+id_22_insurance_patient_num+EOL
            +"23"+","+id_23_insurance_card_id+","+id_23_insurance_card_num+","+_23_insurance_type+","+""+EOL
            +"51"+","+_51_prescription_date+EOL)
    
    return basic_result

#----------<医薬品JAHIS文字列生成のための処理>----------------------------------------------------------------

#入力情報が欠損の場合のダミー値の定義
dict_dummy_meds = {}
l_keys = ['RP番号','RP連番','剤形区分','調剤数量','用法名称','薬品名称','用量','単位名']
l_vals = [1,1,'0','0','ダミー用法','ダミー医薬品','0','ダミー単位']
dict_dummy_meds = dict(zip(l_keys,l_vals))


def search_df_med(med_name,l_names=mi.df_medicineInfo['品名'].values.tolist(),df=mi.df_medicineInfo):
    '''医薬品データベースを検索する処理.
    検索結果が一位に定まらない際は、warningを上げる'''

    cnt = l_names.count(med_name)
    if cnt==0:
        changed_med_name,min_dist = 'dummy',100000
        l=[]
        for medicine in l_names:
            dist = L.distance(med_name,medicine)
            l.append(dist)
            if dist<min_dist:
                changed_med_name = medicine
                min_dist = dist
        warn(med_name+'was not in DB and was changed to '+changed_med_name)
        med_name =changed_med_name            
    elif cnt>=2:
        warn(med_name+' has more than one id')
        
    target_series = df[df['品名']==med_name].iloc[0]

    zaikei_kubun = target_series['剤形区分']
    _2_rp_code = target_series['2_レセプト電算コード']
    _7_ippan_code = target_series['7_一般名コード']

    if _2_rp_code is not None:
        code_type = '2'
        code = _2_rp_code
    elif _7_ippan_code is not None:
        code_type = '7'
        code = _7_ippan_code
    else:
        raise ValueError('something is wrong.')

    return med_name,zaikei_kubun,code_type,code

def unpack_list_of_med_dict_2_dict(input_list):
    '''文字パース結果としてdictのlistを受け取り、それをJAHIS文字列化関数に投げられる形に整形する処理'''

    out_dict = {}
    for i in range(len(input_list)):
        if input_list[i]['RP番号']!='':
            dict_ = input_list[i]

            RP_num,RP_ren_num, = dict_['RP番号'],dict_['RP番号内連番']
            med_name = dict_['薬品名称'][-1]
            med_name,zaikei_kubun,_,_ = search_df_med(med_name)
            chouzai_num,youhou,youryou_num,unit = dict_['調剤数量'],dict_['用法名称'],dict_['用量'],dict_['単位名']
            RP_nxt = input_list[i+1]['RP番号']

            if RP_nxt=='':
                RP_nxt = RP_num+1
            if RP_num==RP_nxt:
                zaikei_kubun,chouzai_num,youhou = ['not RP end']*3

            l_keys = ['RP番号','RP連番','剤形区分','調剤数量','用法名称','薬品名称','用量','単位名']
            l_vals = [str(RP_num),str(RP_ren_num),str(zaikei_kubun),str(chouzai_num),youhou,med_name,str(youryou_num),unit]
            out_dict[i] = dict(zip(l_keys,l_vals))

    return out_dict

def look_up_med_dict(dict_med_info,key1,key2,dict_dummy_meds=dict_dummy_meds):
    '''指定されたkeyの医薬品情報をlookupし, それが欠損情報の場合はダミー値を代入する処理'''
    val = dict_med_info[key1][key2]
    if val in l_deficit_vals:
        val = dict_dummy_meds[key2]    
    return val

#以下、main関数#
def create_med_str(dict_med_info,EOL,JAHIS_ver,JAHIS_ver_algo='JAHIS7'):
    '''情報が整備された処方医薬品情報dictを受け取り, それをJAHIS規格文字列に変換して返す処理
    RPの終わりではない医薬品は, 剤形区分&用法&調剤数量が'not RP end'で渡されていると想定'''
    #281_薬品補足レコードは未対応
    
    #assert JAHIS_ver==JAHIS_ver_algo, 'JAHIS ver must match'

    med_result = ''
    
    l_keys = list(dict_med_info.keys())
    l_keys.sort()
    
    l_201s = []
    for key in l_keys:
        
        RP_num,RP_ren_num = str(look_up_med_dict(dict_med_info,key,'RP番号')),str(look_up_med_dict(dict_med_info,key,'RP連番'))
        zaikei_kubun = look_up_med_dict(dict_med_info,key,'剤形区分')
        chouzai_num = look_up_med_dict(dict_med_info,key,'調剤数量')
        youhou = look_up_med_dict(dict_med_info,key,'用法名称')
        
        med_name = look_up_med_dict(dict_med_info,key,'薬品名称')
        med_name, _, med_code_type,med_code = search_df_med(med_name)
        youryou_num,youryou_unit = look_up_med_dict(dict_med_info,key,'用量'),look_up_med_dict(dict_med_info,key,'単位名')

        str_201 = (
            "201"+","+RP_num+","+RP_ren_num+",,"
            +med_code_type+","+med_code+","+med_name+","+youryou_num+","+"1"+","+youryou_unit+EOL)
            
        if youhou != 'not RP end':
            med_result += "101"+","+RP_num+","+zaikei_kubun+","+""+","+chouzai_num+EOL
            med_result += "111"+","+RP_num+","+"1"+","+""+","+youhou+","+EOL
            for str_ in l_201s:
                med_result+=str_
            med_result+=str_201
            l_201s = []
        
        else:
            l_201s.append(str_201)

        RP_num_prev = RP_num
        
    return med_result

#----------<以上、医薬品JAHIS文字列生成のための処理>----------------------------------------------------------------

#---------<ダミーQRコード情報構造生成のための処理>-----------------------------
l_target_keys = ['RP番号','RP番号内連番','薬品名称','調剤数量','用法名称','用量','単位名']
l_dummy_vals = [1,1,['ダミー医薬品'],'0','ダミー用法','0','ダミー単位']


def create_dummy_results(basic_result=_basic_result_base.copy(),med_result_base=_med_result_base.copy(),dict_dummy_basics=dict_dummy_basics,l_target_keys=l_target_keys,l_dummy_vals=l_dummy_vals):
    '''basic_info.py, med_info.pyにて定義されている情報構造に合わせ、ダミーのbasic_result, med_result
    を生成する処理'''

    basic_result["_1_hospital_code_type"] = dict_dummy_basics['1_医療機関レコード']['医療機関コード種別']
    basic_result["_1_hospital_code"] = dict_dummy_basics['1_医療機関レコード']['医療機関コード']
    basic_result["_1_hospital_place_code"] = dict_dummy_basics['1_医療機関レコード']['医療機関都道府県コード']
    basic_result["id_1_hospital_name"] = dict_dummy_basics['1_医療機関レコード']['医療機関名称']

    basic_result['_5_doctor_name_kanji'] = dict_dummy_basics['5_医師レコード']['医師漢字氏名']
    basic_result['_5_doctor_name_kana'] = dict_dummy_basics['5_医師レコード']['医師カナ氏名']

    basic_result["id_11_patient_name_kanji"] = dict_dummy_basics['11_患者氏名レコード']['患者漢字氏名']
    basic_result["id_11_patient_name_kana"] = dict_dummy_basics['11_患者氏名レコード']['患者カナ氏名']
        
    basic_result["id_12_patient_sex"] = dict_dummy_basics['12_患者性別レコード']['患者性別']

    basic_result['_13_patient_birthday'] = dict_dummy_basics['13_患者生年月日レコード']['患者生年月日']

    basic_result["id_22_insurance_patient_num"] = dict_dummy_basics['22_保険者番号レコード']['保険者番号']
        
    basic_result["id_23_insurance_card_id"] = dict_dummy_basics['23_記号番号レコード']['被保険者証記号']
    basic_result["id_23_insurance_card_num"] = dict_dummy_basics['23_記号番号レコード']['被保険者証番号']
    basic_result["_23_insurance_type"] = dict_dummy_basics['23_記号番号レコード']['被保険者/被扶養者']

    ##公費情報は現状は入れない想定

    basic_result['_51_prescription_date'] = dict_dummy_basics['51_処方箋交付年月日レコード']['処方箋交付年月日']


    dict_med_result = med_result_base.copy()
    for i in range(len(l_target_keys)):
        key = l_target_keys[i]
        val = l_dummy_vals[i]
        dict_med_result[key] = val
    med_result = [dict_med_result]
    med_result.append(med_result_base.copy())

    return basic_result, med_result

#---------<以上、ダミーQRコード情報構造生成のための処理>-----------------------------
