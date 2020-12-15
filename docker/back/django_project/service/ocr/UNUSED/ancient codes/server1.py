# coding: UTF-8
from flask import Flask, render_template, request,send_file,after_this_request,make_response,jsonify,redirect, url_for, send_from_directory
import pandas as pd
import os
import requests
import vision1 as v1
import vision1_main as v1_main
import vision1_med as v1_m
import vision1_basics as v1_b
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
    

@app.route('/wait')
def wait_page():
    return render_template('wait.html')

@app.route('/camera')
def camera_page():
    return render_template('camera.html')




def allwed_file(filename):
    # .があるかどうかのチェックと、拡張子の確認
    # OKなら１、だめなら0
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/images/qrsample.png')
def uploaded_file2():
    return send_from_directory(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png")

@app.route('/uploads/images/qrsample_sj.png')
def uploaded_file5():
    return send_from_directory(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png")

@app.route('/uploads/input_data.png')
def uploaded_file3():
    return send_from_directory(app.config['UPLOAD_FOLDER'], "input_data.png")

@app.route('/uploads/images/load.gif')
def uploaded_file4():
    return send_from_directory(app.config['UPLOAD_FOLDER'] + "/images", "load.gif")


@app.route('/uploads/<path:path>')
def uploaded_file6(path):
    return send_from_directory(app.config['UPLOAD_FOLDER'], path)



# @app.route('/images/<path:path>')
# def send_input_image(path):
#     return send_from_directory(SAVE_DIR, path)

# @app.route('/uploads/images/qrsample.png')
# def uploaded_file2():
#     return send_from_directory(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png")

# @app.route('/image/<filename>')
# def send_input_image(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#複数枚対応した奴
@app.route('/result1', methods=['POST'])
def uploads_file_test1():
    print("開始時間")
    start_time=time.time()
    print(str(start_time))
    # リクエストがポストかどうかの判別
    if request.method == 'POST':
        # ファイルがなかった場合の処理
        if 'file' not in request.files:
            make_response(jsonify({'result':'uploadFile is required.'}))
            #return redirect(request.url)
        # データの取り出し
        upload_files = request.files.getlist('img[]')
        file = upload_files[0]
        
        # ファイル名がなかった時の処理
        if file.filename == '':
            make_response(jsonify({'result':'filename must not empty.'}))
            
            #return redirect(request.url)
        # ファイルのチェック
        if file and allwed_file(file.filename):
            # 危険な文字を削除（サニタイズ処理）
            #filename = secure_filename(file.filename)
            filename = file.filename
            #filename="input_data.png"
            filename=str(time.time())+".png"
            print("---------------------------------------")
            print("filename")
            print(filename)


            # ファイルの保存
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            
            print("歪み補正開始:")
            print(str(time.time()-start_time))
            #歪み修正
            image_yugami_finished = v1_main.yugami("uploads/" + filename)
            boke = v1_main.boke_check(image_yugami_finished)

            print("部分取り出し開始")
            print(str(time.time()-start_time))


            #ここにtryがあった。
            #try:


            #部分取り出し（返り値は、保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部）
            image_waku_finished = v1_b.waku(image_yugami_finished)
            
            try:
                if  image_waku_finished[0]==None:
                    
                    image_waku_finished = v1_b.waku1(image_yugami_finished)
            except:
                pass
            
            print("保険者番号取得開始")
            print(str(time.time()-start_time))

            #保険者番号を取得
            _22_insurance_patient_num = []
            
            ##そのまま突っ込む。歪み補正あり、image_waku_finished[2]（上部）
            try:
                insu_result=[]
                text = jaconv.normalize(v1_main.recognize_image1(image_waku_finished[2]))

                text = text.replace('險','険')
                raw_str = text.splitlines()
                for t in raw_str:
                    t= re.sub(r'\D', '', t)
                    if 10>len(t)>6:#7,8,9
                        insu_result.append(t)
                        break
                    if len(t)==9:
                        insu_result.append(t[:8])
                        insu_result.append(t[1:])
                if len(t) == 9:
                    insu_result.append(t[1:])
                    insu_result.append(t[:8])
                _22_insurance_patient_num.extend(insu_result)
            except:
                pass

            
            ##縦線を消去した場合
            try:
                tatesensyoukyo_num = v1_b.recognize_image2(image_waku_finished[6])
                tatesensyoukyo_num = re.sub(r'\D', '', tatesensyoukyo_num)
                _22_insurance_patient_num.append(tatesensyoukyo_num)#リストに追加
            except:
                pass
            

            ##切り出した場合（PHC用のパラメータ）
            try:
                patern1_num = v1_main.recognize_image1(image_waku_finished[0])
                patern1_num = re.sub(r'\D', '', patern1_num)
                _22_insurance_patient_num.append(patern1_num)  #リストに追加
            except:
                pass
            
            
            ##切り出した場合（矢澤先生用のパラメータ）
            try:
                patern1_num = v1_main.recognize_image1(image_waku_finished[7])
                patern1_num = re.sub(r'\D', '', patern1_num)
                _22_insurance_patient_num.append(patern1_num)#リストに追加
            except:
                pass

            #文字列長で並び替える
            _22_insurance_patient_num.sort(key=len)
            #文字列長=8で検証番号の条件を満たしているやつ
            _22_insurance_patient_num_len8_yes = [i for i in _22_insurance_patient_num if (len(i) == 8 and v1_b.checkdigit(i)==True)]
            #文字列長=8で検証番号の条件を満たしていないやつ
            _22_insurance_patient_num_len8_no = [i for i in _22_insurance_patient_num if (len(i) == 8 and v1_b.checkdigit(i)==False)]
            #文字列長=8ではないやつ
            _22_insurance_patient_num_len_not8 = [i for i in _22_insurance_patient_num if( len(i)  != 8)and(len(i)>2)]
            #以上3つのリストをくっつける
            sorted_list=_22_insurance_patient_num_len_not8
            sorted_list.extend(_22_insurance_patient_num_len8_no)
            sorted_list.extend(_22_insurance_patient_num_len8_yes)
            _22_insurance_patient_num = sorted_list
            #逆にする
            _22_insurance_patient_num.reverse()
            
            
            print(_22_insurance_patient_num)
            
            
            print("記号・番号取得開始")
            print(str(time.time()-start_time))

            #記号を取得
            hokensyanum2 = ""
            try:
                hokensyanum2 = v1_main.recognize_image1(image_waku_finished[1])
            except:
                pass
            _23_insurance_card_id=[]
            _23_insurance_card_num = []
            try:
                _23_insurance_card_id, _23_insurance_card_num = v1_b.symbol_num(hokensyanum2)
            except:
                pass
            _23_insurance_card_result=[]
            for card_id, card_num in zip(_23_insurance_card_id, _23_insurance_card_num):
                _23_insurance_card_result.append(card_id+"・"+card_num)#これは辞書にはない変数だよ！

            print("処方箋タイプ取得開始")
            print(str(time.time()-start_time))
            #re.sub(r'\D', '',文字列)

            prescription_shape_type=v1_main.type_check(image_yugami_finished)
            
            print("OCR開始")
            print(str(time.time()-start_time))
            if prescription_shape_type == "A":#一段組の時
                #上部分のOCR結果を取得
                text_top = str(v1_main.recognize_image1(image_waku_finished[2]))

                #下部全部のOCR結果
                text_bottom_all = str(v1_main.recognize_image1(image_waku_finished[5]))
                print("-----------------------------------")
                print("この処方箋は")
                print("A")

                print("-----------------------------------")
                print("基本情報読み取り結果")
                print(str(text_top))
                text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_ocr.txt"
                f = open(text_place_path, 'w')
                f.write(text_top)
                f.close()
                print("-----------------------------------")
                print("医薬品情報読み取り結果")
                print(str(text_bottom_all))
                text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                f = open(text_place_path, 'w')
                f.write(text_bottom_all)
                f.close()
                
            else:# 2段組の時
                #上部分のOCR結果を取得
                text_top = str(v1_main.recognize_image1(image_waku_finished[2]))

                #左下部分のOCR結果を取得
                text_bottom1 = str(v1_main.recognize_image1(image_waku_finished[3]))
                #右下部分のOCR結果を取得
                text_bottom2 = str(v1_main.recognize_image1(image_waku_finished[4]))
                #下部全部のOCR結果
                text_bottom_all = text_bottom1 + text_bottom2
                print("-----------------------------------")
                print("この処方箋は")
                print("B")

                print("-----------------------------------")
                print("基本情報読み取り結果")
                print(str(text_top))
                print(type(text_top))
                text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_ocr.txt"
                f = open(text_place_path, 'w')
                f.write(text_top)
                f.close()
                print("-----------------------------------")
                print("医薬品情報読み取り結果")
                print(str(text_bottom_all))
                text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                f = open(text_place_path, 'w')
                f.write(text_bottom_all)
                f.close()
            if len(upload_files) > 1:
                for im_file_num in range(len(upload_files)):
                    if im_file_num == 0:
                        pass
                    else:
                        file = upload_files[im_file_num]
                        # ファイル名がなかった時の処理
                        if file.filename == '':
                            make_response(jsonify({'result': 'filename must not empty.'}))

                        if file and allwed_file(file.filename):
                            # 危険な文字を削除（サニタイズ処理）
                            
                            # filename_=str(time.time())+".png"
                            # print("---------------------------------------")
                            # print("filename_")
                            # print(filename_)
                            # ファイルの保存
                            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename+"_"+str(im_file_num)))
                            
                            print("歪み補正開始（2枚目以降）:")
                            print(str(time.time()-start_time))
                            #歪み修正
                            image_yugami_finished = v1_main.yugami("uploads/" +filename+"_"+str(im_file_num))
                            boke = v1_main.boke_check(image_yugami_finished)

                            print("部分取り出し開始（2枚目以降）")
                            print(str(time.time() - start_time))
                            prescription_shape_type=v1_main.type_check(image_yugami_finished)
                            if prescription_shape_type=="A":
                                text_bottom_all = text_bottom_all + str(v1_main.recognize_image1(v1_m.image_cut(image_yugami_finished)[3]))
                            else:
                                text_bottom_all = text_bottom_all + str(v1_main.recognize_image1(v1_m.image_cut(image_yugami_finished)[1]))+ str(v1_main.recognize_image1(v1_m.image_cut(image_yugami_finished)[2]))
                            
                            text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                            f = open(text_place_path, 'w')
                            f.write(text_bottom_all)
                            f.close()
                            print("-------------------------")
                            print("くっつけたよ")
                            print(im_file_num+1)
                            print("枚目")
                            print("-------------------------")
                            print(text_bottom_all )
                            print("-----------------------------")



            #text_topとtext_bottom_all を以後用いる。
            
            print("基本情報読み取り開始")
            print(str(time.time()-start_time))
            basic_result = v1_b.text_processing_basic(text_top, boke)
            text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_result.txt"
            f = open(text_place_path, 'w')
            f.write(json.dumps(basic_result,ensure_ascii=False)) 
            f.close()
            print("医薬品情報読み取り開始")
            print(str(time.time()-start_time))
            med_result = v1_m.text_processing_med(text_bottom_all, boke)
            text_place_path='./ocr_results/'+str(filename[:-4])+"_med_result.txt"
            f = open(text_place_path, 'w')
            f.write(json.dumps(med_result,ensure_ascii=False)) 
            f.close()

            print("---------------------------------")
            print("basic_result:")
            print(basic_result)
            print(basic_result[17])
            print(basic_result[18])
            print(basic_result[19])
            print("---------------------------------")
            print("med_result")
            print(med_result)

            #単位のところでリストに表示する用
            units_list=["錠","枚","g","T","tab","C","カプセル"]

            path_input_image = "./uploads/"+str(filename) + "?" + str(ut)
            print("完了時間")
            print(str(time.time() - start_time))
            

            #以下基本情報をQRコード化のフォーマットに直すためのコード

            #リストとして入っていた保険者番号のうち最初の奴を変数に入れ直す
            _22_insurance_patient_num = _22_insurance_patient_num[0]
            
            #リストとして入っていたcard_idのうち最初の奴を変数に入れ直す
            _23_insurance_card_id = _23_insurance_card_id[0]
            _23_insurance_card_num= _23_insurance_card_num[0]
            
            
            _11_patient_name_kanji = basic_result[8]
            _11_patient_name_kana = basic_result[9]

            birthday_gengou = int(3)#ここは適当
            birthday=basic_result[11]

            _13_patient_birthday=basic_result[11]
            _12_patient_sex = basic_result[10]
            if _12_patient_sex == "1":
                _12_patient_sex = "1"
            else:
                _12_patient_sex = "2"
            _23_insurance_type = basic_result[14]
            if _23_insurance_type == "被保険者":
                _23_insurance_type = "1"
            else:
                _23_insurance_type = "2"
            prescription_gengou=int(3)#ここは適当
            _51_prescription_date= str(v1_b.convert_days(basic_result[16],prescription_gengou))
            _1_hospital_code_type = basic_result[0]
            _1_hospital_code = basic_result[1]
            _1_hospital_place_code = basic_result[2]
            _1_hospital_name = basic_result[3]
            _5_doctor_name_kanji = basic_result[6]
            basic_qr_text =  "JAHIS3" + "\n" +"1"+","+_1_hospital_code_type + "," + _1_hospital_code + "," + _1_hospital_place_code + "," + _1_hospital_name + "\n" +"5"+","+ "" + "," + "" + "," + _5_doctor_name_kanji + "\n" +"11"+","+ "" + "," + _11_patient_name_kanji + "," + _11_patient_name_kana + "\n" +"12"+","+ _12_patient_sex + "\n" +"13"+","+ _13_patient_birthday + "\n" + "22"+","+_22_insurance_patient_num+"\n"+"23"+","+_23_insurance_card_id+","+_23_insurance_card_num+","+_23_insurance_type+","+""+"\n"+"51"+","+_51_prescription_date+"\n"
            
            #以下処方情報をQRコード化のフォーマットに直すためのコード
            l_all=[]
            for med in med_result:
                if med["薬品名称"]!="":
                    list_ = ["", "", "", "", "", "", "", "", "", "", "", "",]
                    list_[0]=str(med["RP番号"])
                    list_[3]=str(med["RP番号"])
                    list_[5]=str(med["RP番号"])
                    list_[10] = str(med["RP番号"])

                    list_[6]=str(med["PR番号内連番"])
                    list_[11] = str(med["PR番号内連番"])
                    
                    list_[7] = str(med["薬品名称"][0])
                    
                    list_[8] = str(med["用量"])
                    try:
                        list_[9] = str(med["単位名"][0])
                    except:
                        list_[9]=str("")

                    list_[1] = str(med["剤形区分"])
                    list_[2] = str(med["調剤数量"])
                    list_[4] = str(med["用法名称"])
                    l_all.append(list_)

            med_qr_text = ''
            l_prev=[]
            for i in range(len(l_all)):
                l_now = l_all[i]
                if l_now!=[]:
                    if l_now[0]!='':

                        #101,111を生成するかの判定
                        if i==0:
                            new_101=True
                        elif l_prev[0]!=l_now[0]:
                            new_101=True
                        else:
                            new_101=False

                        if new_101:
                            med_qr_text+=("101"+","+l_now[0]+","+l_now[1]+","+""+","+l_now[2]+"\n"+
                                        "111"+","+l_now[3]+","+"1"+","+""+","+l_now[4]+","+"\n"+
                                        "201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+"XXXX"+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                        "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+"ジェネリック変更不可"+""+"\n")
                        else:
                            med_qr_text+=("201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+"XXXX"+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                        "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+"ジェネリック変更不可"+""+"\n")

                        l_prev = l_now[:]
            result_qr_text = str(basic_qr_text + med_qr_text)
            result_sj = result_qr_text.encode('shift_jis', 'replace')
            mojibake = ""
            mojibake = str(result_sj).count('?')
            qrimg = qrcode.make(result_qr_text)
            qrimg_sj = qrcode.make(result_sj)
            qrimg.save(os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png"))
            qrimg_sj.save(os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png"))

            path = os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png")
            path_sj = os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png")
            print(path)
            #ut = time.time()
            path1 = path + "?" + str(ut)
            path1_sj = path_sj + "?" + str(ut)

            return render_template('qrcode.html',ut=ut,path1=path1,result=result_qr_text,path1_sj=path1_sj,mojibake=mojibake,_11_patient_name_kanji=_11_patient_name_kanji,birthday_gengou=birthday_gengou,birthday=birthday)
            

            
                #return render_template('result.html',path_input_image=path_input_image,basic_result=basic_result,med_result=med_result,_22_insurance_patient_num=_22_insurance_patient_num,_23_insurance_card_result=_23_insurance_card_result,units_list=units_list,boke=boke) 
            
            #ここにexceptがあった。
            # except:
            #     return render_template('recept.html')

                # path_input_image = "./uploads/"+str(filename) + "?" + str(ut)
                # _22_insurance_patient_num = []
                # _23_insurance_card_result = []
                # units_list = ["錠", "枚", "g", "T", "tab", "C", "カプセル"]
                # basic_result = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
                # med_result = {1: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 2: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 3: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 4: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 5: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 6: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 7: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 8: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 9: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 10: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}}

                # return render_template('result.html',path_input_image=path_input_image,basic_result=basic_result,med_result=med_result,_22_insurance_patient_num=_22_insurance_patient_num,_23_insurance_card_result=_23_insurance_card_result,units_list=units_list,boke=boke) 
        
            
    return
    

@app.route('/result2', methods=['POST'])
def uploads_file_test2():
    try:
        print("開始時間")
        start_time=time.time()
        print(str(start_time))
        # リクエストがポストかどうかの判別
        if request.method == 'POST':
            # ファイルがなかった場合の処理
            if 'file' not in request.files:
                make_response(jsonify({'result':'uploadFile is required.'}))
                #return redirect(request.url)
            # データの取り出し
            upload_files = request.files.getlist('img[]')
            file = upload_files[0]
            
            # ファイル名がなかった時の処理
            if file.filename == '':
                make_response(jsonify({'result':'filename must not empty.'}))
                
                #return redirect(request.url)
            # ファイルのチェック
            if file and allwed_file(file.filename):
                # 危険な文字を削除（サニタイズ処理）
                #filename = secure_filename(file.filename)
                filename = file.filename
                #filename="input_data.png"
                filename=str(time.time())+".png"
                print("---------------------------------------")
                print("filename")
                print(filename)


                # ファイルの保存
                file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
                
                print("歪み補正開始:")
                print(str(time.time()-start_time))
                #歪み修正
                image_yugami_finished = v1_main.yugami("uploads/" + filename)
                boke = v1_main.boke_check(image_yugami_finished)

                print("部分取り出し開始")
                print(str(time.time()-start_time))
                try:
                    #部分取り出し（返り値は、保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部）
                    image_waku_finished = v1_b.waku(image_yugami_finished)
                    
                    try:
                        if  image_waku_finished[0]==None:
                            
                            image_waku_finished = v1_b.waku1(image_yugami_finished)
                    except:
                        pass
                    
                    print("保険者番号取得開始")
                    print(str(time.time()-start_time))

                    #保険者番号を取得
                    _22_insurance_patient_num = []
                    
                    ##そのまま突っ込む。歪み補正あり、image_waku_finished[2]（上部）
                    try:
                        insu_result=[]
                        text = jaconv.normalize(v1_main.recognize_image1(image_waku_finished[2]))

                        text = text.replace('險','険')
                        raw_str = text.splitlines()
                        for t in raw_str:
                            t= re.sub(r'\D', '', t)
                            if 10>len(t)>6:#7,8,9
                                insu_result.append(t)
                                break
                            if len(t)==9:
                                insu_result.append(t[:8])
                                insu_result.append(t[1:])
                        if len(t) == 9:
                            insu_result.append(t[1:])
                            insu_result.append(t[:8])
                        _22_insurance_patient_num.extend(insu_result)
                    except:
                        pass

                    
                    ##縦線を消去した場合
                    try:
                        tatesensyoukyo_num = v1_b.recognize_image2(image_waku_finished[6])
                        tatesensyoukyo_num = re.sub(r'\D', '', tatesensyoukyo_num)
                        _22_insurance_patient_num.append(tatesensyoukyo_num)#リストに追加
                    except:
                        pass
                    

                    ##切り出した場合（PHC用のパラメータ）
                    try:
                        patern1_num = v1_main.recognize_image1(image_waku_finished[0])
                        patern1_num = re.sub(r'\D', '', patern1_num)
                        _22_insurance_patient_num.append(patern1_num)  #リストに追加
                    except:
                        pass
                    
                    
                    ##切り出した場合（矢澤先生用のパラメータ）
                    try:
                        patern1_num = v1_main.recognize_image1(image_waku_finished[7])
                        patern1_num = re.sub(r'\D', '', patern1_num)
                        _22_insurance_patient_num.append(patern1_num)#リストに追加
                    except:
                        pass

                    #文字列長で並び替える
                    _22_insurance_patient_num.sort(key=len)
                    #文字列長=8で検証番号の条件を満たしているやつ
                    _22_insurance_patient_num_len8_yes = [i for i in _22_insurance_patient_num if (len(i) == 8 and v1_b.checkdigit(i)==True)]
                    #文字列長=8で検証番号の条件を満たしていないやつ
                    _22_insurance_patient_num_len8_no = [i for i in _22_insurance_patient_num if (len(i) == 8 and v1_b.checkdigit(i)==False)]
                    #文字列長=8ではないやつ
                    _22_insurance_patient_num_len_not8 = [i for i in _22_insurance_patient_num if( len(i)  != 8)and(len(i)>2)]
                    #以上3つのリストをくっつける
                    sorted_list=_22_insurance_patient_num_len_not8
                    sorted_list.extend(_22_insurance_patient_num_len8_no)
                    sorted_list.extend(_22_insurance_patient_num_len8_yes)
                    _22_insurance_patient_num = sorted_list
                    #逆にする
                    _22_insurance_patient_num.reverse()
                    
                    
                    print(_22_insurance_patient_num)
                    
                    
                    print("記号・番号取得開始")
                    print(str(time.time()-start_time))

                    #記号を取得
                    hokensyanum2 = ""
                    try:
                        hokensyanum2 = v1_main.recognize_image1(image_waku_finished[1])
                    except:
                        pass
                    _23_insurance_card_id=[]
                    _23_insurance_card_num = []
                    try:
                        _23_insurance_card_id, _23_insurance_card_num = v1_b.symbol_num(hokensyanum2)
                    except:
                        pass
                    _23_insurance_card_result=[]
                    for card_id, card_num in zip(_23_insurance_card_id, _23_insurance_card_num):
                        _23_insurance_card_result.append(card_id+"・"+card_num)#これは辞書にはない変数だよ！

                    print("処方箋タイプ取得開始")
                    print(str(time.time()-start_time))
                    #re.sub(r'\D', '',文字列)

                    prescription_shape_type=v1_main.type_check(image_yugami_finished)
                    
                    print("OCR開始")
                    print(str(time.time()-start_time))
                    if prescription_shape_type == "A":#一段組の時
                        #上部分のOCR結果を取得
                        text_top = str(v1_main.recognize_image1(image_waku_finished[2]))

                        #下部全部のOCR結果
                        text_bottom_all = str(v1_main.recognize_image1(image_waku_finished[5]))
                        print("-----------------------------------")
                        print("この処方箋は")
                        print("A")

                        print("-----------------------------------")
                        print("基本情報読み取り結果")
                        print(str(text_top))
                        text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_ocr.txt"
                        f = open(text_place_path, 'w')
                        f.write(text_top)
                        f.close()
                        print("-----------------------------------")
                        print("医薬品情報読み取り結果")
                        print(str(text_bottom_all))
                        text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                        f = open(text_place_path, 'w')
                        f.write(text_bottom_all)
                        f.close()
                        
                    else:# 2段組の時
                        #上部分のOCR結果を取得
                        text_top = str(v1_main.recognize_image1(image_waku_finished[2]))

                        #左下部分のOCR結果を取得
                        text_bottom1 = str(v1_main.recognize_image1(image_waku_finished[3]))
                        #右下部分のOCR結果を取得
                        text_bottom2 = str(v1_main.recognize_image1(image_waku_finished[4]))
                        #下部全部のOCR結果
                        text_bottom_all = text_bottom1 + text_bottom2
                        print("-----------------------------------")
                        print("この処方箋は")
                        print("B")

                        print("-----------------------------------")
                        print("基本情報読み取り結果")
                        print(str(text_top))
                        print(type(text_top))
                        text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_ocr.txt"
                        f = open(text_place_path, 'w')
                        f.write(text_top)
                        f.close()
                        print("-----------------------------------")
                        print("医薬品情報読み取り結果")
                        print(str(text_bottom_all))
                        text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                        f = open(text_place_path, 'w')
                        f.write(text_bottom_all)
                        f.close()
                    if len(upload_files) > 1:
                        for im_file_num in range(len(upload_files)):
                            if im_file_num == 0:
                                pass
                            else:
                                file = upload_files[im_file_num]
                                # ファイル名がなかった時の処理
                                if file.filename == '':
                                    make_response(jsonify({'result': 'filename must not empty.'}))

                                if file and allwed_file(file.filename):
                                    # 危険な文字を削除（サニタイズ処理）
                                    
                                    # filename_=str(time.time())+".png"
                                    # print("---------------------------------------")
                                    # print("filename_")
                                    # print(filename_)
                                    # ファイルの保存
                                    file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename+"_"+str(im_file_num)))
                                    
                                    print("歪み補正開始（2枚目以降）:")
                                    print(str(time.time()-start_time))
                                    #歪み修正
                                    image_yugami_finished = v1_main.yugami("uploads/" +filename+"_"+str(im_file_num))
                                    boke = v1_main.boke_check(image_yugami_finished)

                                    print("部分取り出し開始（2枚目以降）")
                                    print(str(time.time() - start_time))
                                    prescription_shape_type=v1_main.type_check(image_yugami_finished)
                                    if prescription_shape_type=="A":
                                        text_bottom_all = text_bottom_all + str(v1_main.recognize_image1(v1_m.image_cut(image_yugami_finished)[3]))
                                    else:
                                        text_bottom_all = text_bottom_all + str(v1_main.recognize_image1(v1_m.image_cut(image_yugami_finished)[1]))+ str(v1_main.recognize_image1(v1_m.image_cut(image_yugami_finished)[2]))
                                    
                                    text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                                    f = open(text_place_path, 'w')
                                    f.write(text_bottom_all)
                                    f.close()
                                    print("-------------------------")
                                    print("くっつけたよ")
                                    print(im_file_num+1)
                                    print("枚目")
                                    print("-------------------------")
                                    print(text_bottom_all )
                                    print("-----------------------------")



                    #text_topとtext_bottom_all を以後用いる。
                    
                    print("基本情報読み取り開始")
                    print(str(time.time()-start_time))
                    basic_result = v1_b.text_processing_basic(text_top, boke)
                    text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_result.txt"
                    f = open(text_place_path, 'w')
                    f.write(json.dumps(basic_result,ensure_ascii=False)) 
                    f.close()
                    print("医薬品情報読み取り開始")
                    print(str(time.time()-start_time))
                    med_result = v1_m.text_processing_med(text_bottom_all, boke)
                    text_place_path='./ocr_results/'+str(filename[:-4])+"_med_result.txt"
                    f = open(text_place_path, 'w')
                    f.write(json.dumps(med_result,ensure_ascii=False)) 
                    f.close()

                    print("---------------------------------")
                    print("basic_result:")
                    print(basic_result)
                    print(basic_result[17])
                    print(basic_result[18])
                    print(basic_result[19])
                    print("---------------------------------")
                    print("med_result")
                    print(med_result)

                    #単位のところでリストに表示する用
                    units_list=["錠","枚","g","T","tab","C","カプセル"]

                    path_input_image = "./uploads/"+str(filename) + "?" + str(ut)
                    print("完了時間")
                    print(str(time.time()-start_time))
                    
                    return render_template('result.html',path_input_image=path_input_image,basic_result=basic_result,med_result=med_result,_22_insurance_patient_num=_22_insurance_patient_num,_23_insurance_card_result=_23_insurance_card_result,units_list=units_list,boke=boke) 
                except:
                    path_input_image = "./uploads/"+str(filename) + "?" + str(ut)
                    _22_insurance_patient_num = []
                    _23_insurance_card_result = []
                    units_list = ["錠", "枚", "g", "T", "tab", "C", "カプセル"]
                    basic_result = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
                    med_result = {1: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 2: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 3: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 4: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 5: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 6: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 7: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 8: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 9: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 10: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}}
    
                    return render_template('result.html',path_input_image=path_input_image,basic_result=basic_result,med_result=med_result,_22_insurance_patient_num=_22_insurance_patient_num,_23_insurance_card_result=_23_insurance_card_result,units_list=units_list,boke=boke) 
            
                
        return
    except:
        return render_template('result3.html') 
    
@app.route('/result', methods=['POST'])
def uploads_file():
    print("開始時間")
    start_time=time.time()
    print(str(start_time))
    # リクエストがポストかどうかの判別
    if request.method == 'POST':
        # ファイルがなかった場合の処理
        if 'file' not in request.files:
            make_response(jsonify({'result':'uploadFile is required.'}))
            #return redirect(request.url)
        # データの取り出し
        file = request.files['file']
        
        # ファイル名がなかった時の処理
        if file.filename == '':
            make_response(jsonify({'result':'filename must not empty.'}))
            
            #return redirect(request.url)
        # ファイルのチェック
        if file and allwed_file(file.filename):
            # 危険な文字を削除（サニタイズ処理）
            #filename = secure_filename(file.filename)
            filename = file.filename
            #filename="input_data.png"
            filename=str(time.time())+".png"
            print("---------------------------------------")
            print("filename")
            print(filename)


            # ファイルの保存
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            
            print("歪み補正開始:")
            print(str(time.time()-start_time))
            #歪み修正
            image_yugami_finished = v1_main.yugami("uploads/" + filename)
            boke = v1_main.boke_check(image_yugami_finished)

            print("部分取り出し開始")
            print(str(time.time()-start_time))
            try:
                #部分取り出し（返り値は、保険者番号、記号、基本情報の部分、左下（PHCでは不要）、右下（PHCでは不要）、下全部）
                image_waku_finished = v1_b.waku(image_yugami_finished)
                
                try:
                    if  image_waku_finished[0]==None:
                        
                        image_waku_finished = v1_b.waku1(image_yugami_finished)
                except:
                    pass
                
                print("保険者番号取得開始")
                print(str(time.time()-start_time))

                #保険者番号を取得
                _22_insurance_patient_num = []
                
                ##そのまま突っ込む。歪み補正あり、image_waku_finished[2]（上部）
                try:
                    insu_result=[]
                    text = jaconv.normalize(v1_main.recognize_image1(image_waku_finished[2]))

                    text = text.replace('險','険')
                    raw_str = text.splitlines()
                    for t in raw_str:
                        t= re.sub(r'\D', '', t)
                        if 10>len(t)>6:#7,8,9
                            insu_result.append(t)
                            break
                        if len(t)==9:
                            insu_result.append(t[:8])
                            insu_result.append(t[1:])
                    if len(t) == 9:
                        insu_result.append(t[1:])
                        insu_result.append(t[:8])
                    _22_insurance_patient_num.extend(insu_result)
                except:
                    pass

                
                ##縦線を消去した場合
                try:
                    tatesensyoukyo_num = v1_b.recognize_image2(image_waku_finished[6])
                    tatesensyoukyo_num = re.sub(r'\D', '', tatesensyoukyo_num)
                    _22_insurance_patient_num.append(tatesensyoukyo_num)#リストに追加
                except:
                    pass
                

                ##切り出した場合（PHC用のパラメータ）
                try:
                    patern1_num = v1_main.recognize_image1(image_waku_finished[0])
                    patern1_num = re.sub(r'\D', '', patern1_num)
                    _22_insurance_patient_num.append(patern1_num)  #リストに追加
                except:
                    pass
                
                
                ##切り出した場合（矢澤先生用のパラメータ）
                try:
                    patern1_num = v1_main.recognize_image1(image_waku_finished[7])
                    patern1_num = re.sub(r'\D', '', patern1_num)
                    _22_insurance_patient_num.append(patern1_num)#リストに追加
                except:
                    pass

                #文字列長で並び替える
                _22_insurance_patient_num.sort(key=len)
                #文字列長=8で検証番号の条件を満たしているやつ
                _22_insurance_patient_num_len8_yes = [i for i in _22_insurance_patient_num if (len(i) == 8 and v1_b.checkdigit(i)==True)]
                #文字列長=8で検証番号の条件を満たしていないやつ
                _22_insurance_patient_num_len8_no = [i for i in _22_insurance_patient_num if (len(i) == 8 and v1_b.checkdigit(i)==False)]
                #文字列長=8ではないやつ
                _22_insurance_patient_num_len_not8 = [i for i in _22_insurance_patient_num if( len(i)  != 8)and(len(i)>2)]
                #以上3つのリストをくっつける
                sorted_list=_22_insurance_patient_num_len_not8
                sorted_list.extend(_22_insurance_patient_num_len8_no)
                sorted_list.extend(_22_insurance_patient_num_len8_yes)
                _22_insurance_patient_num = sorted_list
                #逆にする
                _22_insurance_patient_num.reverse()
                
                
                print(_22_insurance_patient_num)
                
                
                print("記号・番号取得開始")
                print(str(time.time()-start_time))

                #記号を取得
                hokensyanum2 = ""
                try:
                    hokensyanum2 = v1_main.recognize_image1(image_waku_finished[1])
                except:
                    pass
                _23_insurance_card_id=[]
                _23_insurance_card_num = []
                try:
                    _23_insurance_card_id, _23_insurance_card_num = v1_b.symbol_num(hokensyanum2)
                except:
                    pass
                _23_insurance_card_result=[]
                for card_id, card_num in zip(_23_insurance_card_id, _23_insurance_card_num):
                    _23_insurance_card_result.append(card_id+"・"+card_num)#これは辞書にはない変数だよ！

                print("処方箋タイプ取得開始")
                print(str(time.time()-start_time))
                #re.sub(r'\D', '',文字列)

                prescription_shape_type=v1_main.type_check(image_yugami_finished)
                
                print("OCR開始")
                print(str(time.time()-start_time))
                if prescription_shape_type == "A":#一段組の時
                    #上部分のOCR結果を取得
                    text_top = str(v1_main.recognize_image1(image_waku_finished[2]))

                    #下部全部のOCR結果
                    text_bottom_all = str(v1_main.recognize_image1(image_waku_finished[5]))
                    print("-----------------------------------")
                    print("この処方箋は")
                    print("A")

                    print("-----------------------------------")
                    print("基本情報読み取り結果")
                    print(str(text_top))
                    text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_ocr.txt"
                    f = open(text_place_path, 'w')
                    f.write(text_top)
                    f.close()
                    print("-----------------------------------")
                    print("医薬品情報読み取り結果")
                    print(str(text_bottom_all))
                    text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                    f = open(text_place_path, 'w')
                    f.write(text_bottom_all)
                    f.close()
                    
                else:# 2段組の時
                    #上部分のOCR結果を取得
                    text_top = str(v1_main.recognize_image1(image_waku_finished[2]))

                    #左下部分のOCR結果を取得
                    text_bottom1 = str(v1_main.recognize_image1(image_waku_finished[3]))
                    #右下部分のOCR結果を取得
                    text_bottom2 = str(v1_main.recognize_image1(image_waku_finished[4]))
                    #下部全部のOCR結果
                    text_bottom_all = text_bottom1 + text_bottom2
                    print("-----------------------------------")
                    print("この処方箋は")
                    print("B")

                    print("-----------------------------------")
                    print("基本情報読み取り結果")
                    print(str(text_top))
                    print(type(text_top))
                    text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_ocr.txt"
                    f = open(text_place_path, 'w')
                    f.write(text_top)
                    f.close()
                    print("-----------------------------------")
                    print("医薬品情報読み取り結果")
                    print(str(text_bottom_all))
                    text_place_path='./ocr_results/'+str(filename[:-4])+"_med_ocr.txt"
                    f = open(text_place_path, 'w')
                    f.write(text_bottom_all)
                    f.close()


                #text_topとtext_bottom_all を以後用いる。
                
                print("基本情報読み取り開始")
                print(str(time.time()-start_time))
                basic_result = v1_b.text_processing_basic(text_top, boke)
                text_place_path='./ocr_results/'+str(filename[:-4])+"_basic_result.txt"
                f = open(text_place_path, 'w')
                f.write(json.dumps(basic_result,ensure_ascii=False)) 
                f.close()
                print("医薬品情報読み取り開始")
                print(str(time.time()-start_time))
                med_result = v1_m.text_processing_med(text_bottom_all, boke)
                text_place_path='./ocr_results/'+str(filename[:-4])+"_med_result.txt"
                f = open(text_place_path, 'w')
                f.write(json.dumps(med_result,ensure_ascii=False)) 
                f.close()

                print("---------------------------------")
                print("basic_result:")
                print(basic_result)
                print(basic_result[17])
                print(basic_result[18])
                print(basic_result[19])
                print("---------------------------------")
                print("med_result")
                print(med_result)

                #単位のところでリストに表示する用
                units_list=["錠","枚","g","T","tab","C","カプセル"]

                path_input_image = "./uploads/"+str(filename) + "?" + str(ut)
                print("完了時間")
                print(str(time.time()-start_time))
                
                return render_template('result.html',path_input_image=path_input_image,basic_result=basic_result,med_result=med_result,_22_insurance_patient_num=_22_insurance_patient_num,_23_insurance_card_result=_23_insurance_card_result,units_list=units_list,boke=boke) 
            except:
                path_input_image = "./uploads/"+str(filename) + "?" + str(ut)
                _22_insurance_patient_num = []
                _23_insurance_card_result = []
                units_list = ["錠", "枚", "g", "T", "tab", "C", "カプセル"]
                basic_result = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
                med_result = {1: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 2: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 3: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 4: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 5: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 6: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 7: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 8: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 9: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}, 10: {'RP番号': '', 'PR番号内連番': '', '剤形区分': '', '剤形名称': '', '調剤数量': '', '用法コード種別': '', '用法コード': '', '用法名称': '', '回数': '', '情報区分': '', '薬品コード種別': '', '薬品コード': '', '薬品名称': '', '用量': '', '力価フラグ': '', '単位名': '', '薬品補足連番': '', '薬品補足区分': '', '薬品補足情報': '', '補足用法コード': '','symspell結果': '','accuracy_check':''}}
   
                return render_template('result.html',path_input_image=path_input_image,basic_result=basic_result,med_result=med_result,_22_insurance_patient_num=_22_insurance_patient_num,_23_insurance_card_result=_23_insurance_card_result,units_list=units_list,boke=boke) 
           
            
    return  

@app.route('/recept', methods=['GET','POST'])
def recept():
    if request.method == 'POST':
        text1 = request.form['text1']
        result=text1.split('\n')
        _22_insurance_patient_num = result[0]
        _23_insurance_card_id,_23_insurance_card_num=v1_b.symbol_num2(result[1])
        _11_patient_name_kanji = result[2]
        _11_patient_name_kana = result[3]
        if result[4]=="明治":
            birthday_gengou=1
        elif result[4]=="大正":
            birthday_gengou=2
        elif result[4]=="昭和":
            birthday_gengou=3
        elif result[4]=="平成":
            birthday_gengou=4
        else:
            birthday_gengou=5

        birthday=result[5]
        _13_patient_birthday= str(v1_b.convert_days(birthday,birthday_gengou))
        _12_patient_sex = result[6]
        if _12_patient_sex == "男":
            _12_patient_sex = "1"
        else:
            _12_patient_sex = "2"
        _23_insurance_type = result[7]
        if _23_insurance_type == "被保険者":
            _23_insurance_type = "1"
        else:
            _23_insurance_type = "2"
            
        if result[8]=="明治":
            prescription_gengou=1
        elif result[8]=="大正":
            prescription_gengou=2
        elif result[8]=="昭和":
            prescription_gengou=3
        elif result[8]=="平成":
            prescription_gengou=4
        else:
            prescription_gengou=5

        _51_prescription_date= str(v1_b.convert_days(result[9],prescription_gengou))

            
        _1_hospital_name=result[10]
        _1_hospital_code_type=result[11]
        _1_hospital_code=result[12]
        _1_hospital_place_code=result[13]

        _5_doctor_name_kanji = result[14]
        basic_result =  "JAHIS3" + "\n" +"1"+","+_1_hospital_code_type + "," + _1_hospital_code + "," + _1_hospital_place_code + "," + _1_hospital_name + "\n" +"5"+","+ "" + "," + "" + "," + _5_doctor_name_kanji + "\n" +"11"+","+ "" + "," + _11_patient_name_kanji + "," + _11_patient_name_kana + "\n" +"12"+","+ _12_patient_sex + "\n" +"13"+","+ _13_patient_birthday + "\n" + "22"+","+_22_insurance_patient_num+"\n"+"23"+","+_23_insurance_card_id+","+_23_insurance_card_num+","+_23_insurance_type+","+""+"\n"+"51"+","+_51_prescription_date+"\n"

        #-------------------------------------以下医薬品
        list_list=[]
        num_ren_sum=0
        num_sum=0
        for i in result[15:-1]:
            list_=["","","","","","","","","","","","",]
            word_list = i.split(',')
            print(word_list)
            RP_ren_num=num_sum
            num_ren_sum=num_ren_sum+1
            RP_ren_num=str(num_ren_sum)
            #RP番号
            RP_num=str(num_sum+1)
            list_[0]=RP_num
            list_[3]=RP_num
            list_[5]=RP_num
            list_[10]=RP_num
            if len(word_list)>7:
                num_ren_sum=0
                num_sum=num_sum+1
            #RP連番
            list_[6]=RP_ren_num
            list_[11]=RP_ren_num
            #名前
            list_[7]=i.split(',')[2]
            #数量
            list_[8]=i.split(',')[4]
            #単位
            list_[9]=i.split(',')[5]
            list_list.append(list_)
            
        t_list=[]
        for s, t in zip(result[::-1][:(len(result) - 15 - 1)], list_list[::-1]):
            print(s)
            words=["","",""]
            if len(s.split(","))>7:
        #         print(len(s.split(",")))
                words=[s.split(',')[8],s.split(',')[9],s.split(',')[10]]
        #     print(s)
        #     print(t)
            #print(words)
            t[1]=words[0]
            t[2]=words[2]
            t[4]=words[1]
            #print(t)
            t_list.append(t)
            #print("-----------")
        l_all=t_list[::-1]
        #new_pr,new_prrenban = False,False
        med_result = ''
        for i in range(len(l_all)):
            l_now = l_all[i]
            if l_now!=[]:
                if l_now[0]!='':

                    #101,111を生成するかの判定
                    if i==0:
                        new_101=True
                    elif l_prev[0]!=l_now[0]:
                        new_101=True
                    else:
                        new_101=False

                    if new_101:
                        med_result+=("101"+","+l_now[0]+","+l_now[1]+","+""+","+l_now[2]+"\n"+
                                    "111"+","+l_now[3]+","+"1"+","+""+","+l_now[4]+","+"\n"+
                                    "201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+"XXXX"+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                    "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+"ジェネリック変更不可"+""+"\n")
                    else:
                        med_result+=("201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+"XXXX"+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                    "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+"ジェネリック変更不可"+""+"\n")

                    l_prev = l_now[:]

        result = basic_result + med_result
        result_sj= result.encode('shift_jis', 'replace')
        mojibake = 0
        mojibake=str(result_sj).count('?')

        qrimg = qrcode.make(result)
        qrimg_sj=qrcode.make(result_sj)


        qrimg.save(os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png"))
        qrimg_sj.save(os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png"))

        path = os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png")
        path_sj = os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png")
        print(path)
        #ut = time.time()
        path1 = path + "?" + str(ut)
        path1_sj = path_sj + "?" + str(ut)

        return render_template('qrcode.html',ut=ut,path1=path1,result=result,path1_sj=path1_sj,mojibake=mojibake,_11_patient_name_kanji=_11_patient_name_kanji,birthday_gengou=birthday_gengou,birthday=birthday)
        #return render_template('recept.html')
    else:
        return render_template('recept.html')

# @app.route('/qr', methods=['GET'])
# def qr():
#     return render_template('qr.html')
    
        
       
      

    


@app.route('/qrcode', methods=['POST'])
def uploads_file1():
    # リクエストがポストかどうかの判別
    if request.method == 'POST':
        _22_insurance_patient_num = request.form['_22_insurance_patient_num']
        #_23_insurance_card_id= request.form['_23_insurance_card_id']
        
        _23_insurance_card_id,_23_insurance_card_num=v1_b.symbol_num2(request.form['_23_insurance_card_result'])
        _11_patient_name_kanji = request.form['_11_patient_name_kanji']
        _11_patient_name_kana = request.form['_11_patient_name_kana']

        birthday_gengou = int(request.form['birthday_gengou'])
        birthday=request.form['_13_patient_birthday']
        _13_patient_birthday= str(v1_b.convert_days(birthday,birthday_gengou))
        _12_patient_sex = request.form['_12_patient_sex']
        if _12_patient_sex == "1":
            _12_patient_sex = "1"
        else:
            _12_patient_sex = "2"
        _23_insurance_type = request.form['_23_insurance_type']
        if _23_insurance_type == "被保険者":
            _23_insurance_type = "1"
        else:
            _23_insurance_type = "2"
        prescription_gengou=int(request.form['prescription_gengou'])
        _51_prescription_date= str(v1_b.convert_days(request.form['_51_prescription_date'],prescription_gengou))
        _1_hospital_code_type = request.form['_1_hospital_code_type']
        _1_hospital_code = request.form['_1_hospital_code']
        _1_hospital_place_code = request.form['_1_hospital_place_code']
        _1_hospital_name = request.form['_1_hospital_name']
        _5_doctor_name_kanji = request.form['_5_doctor_name_kanji']
        basic_result =  "JAHIS3" + "\n" +"1"+","+_1_hospital_code_type + "," + _1_hospital_code + "," + _1_hospital_place_code + "," + _1_hospital_name + "\n" +"5"+","+ "" + "," + "" + "," + _5_doctor_name_kanji + "\n" +"11"+","+ "" + "," + _11_patient_name_kanji + "," + _11_patient_name_kana + "\n" +"12"+","+ _12_patient_sex + "\n" +"13"+","+ _13_patient_birthday + "\n" + "22"+","+_22_insurance_patient_num+"\n"+"23"+","+_23_insurance_card_id+","+_23_insurance_card_num+","+_23_insurance_type+","+""+"\n"+"51"+","+_51_prescription_date+"\n"
        

        med_result = ""
        name0 = ""
        name1 = ""
        name2 = ""
        name3 = ""
        name4 = ""
        name5 = ""
        name6 = ""
        name7 = ""
        name8 = ""
        name9 = ""

        name0 = ""
        zaikeikubun0 =""
        rprenban0 = ""
        rp0 = ""
        rprenban0 = ""
        suuryou0 = ""
        youhou0 = ""
        ryou0 = ""
        tanni0 =""

        result = request.form
        print("----------------------------")
        #print(result)
        print("----------------------------")
        #print(result[0])
        try:
            name0 = request.form['name0']
            zaikeikubun0 = request.form['kubun0']
            rp0 = request.form['rp0']
            rprenban0 = request.form['rprenban0']
            suuryou0 = request.form['suuryou0']
            youhou0 = request.form['youhou0']
            ryou0 = request.form['ryou0']
            tanni0 = request.form['tanni0']
            hosokurennbann0=request.form['hosokurennbann0']
            hosokukubunn0 = request.form['hosokukubunn0']
            print("1は終了")
        except:
            pass
        print("-----------------------------------")
        print(name0)
        print(rp0)

        print(rprenban0)

        try:
            name1 = request.form['name1']
            zaikeikubun1=request.form['kubun1']
            rp1 = request.form['rp1']
            rprenban1 = request.form['rprenban1']
            suuryou1 = request.form['suuryou1']
            youhou1 = request.form['youhou1']
            ryou1 = request.form['ryou1']
            tanni1 = request.form['tanni1']
            hosokurennbann1=request.form['hosokurennbann1']
            hosokukubunn1 = request.form['hosokukubunn1']
            
        except:
            pass
        
        try:
            name2 = request.form['name2']
            zaikeikubun2=request.form['kubun2']
            rp2 = request.form['rp2']
            rprenban2 = request.form['rprenban2']
            suuryou2 = request.form['suuryou2']
            youhou2 = request.form['youhou2']
            ryou2 = request.form['ryou2']
            tanni2 = request.form['tanni2']
            hosokurennbann2=request.form['hosokurennbann2']
            hosokukubunn2 = request.form['hosokukubunn2']
        except:
            pass
        print("rp2" + request.form['rp2'])
        print("name2" + request.form['name2'])
        print("kubun2" + request.form['kubun2'])
        print("rprenban2"+request.form['rprenban2'])
        print("suuryou2" + request.form['suuryou2'])
        print("youhou2"+request.form['youhou2'])
        print("ryou2"+request.form['ryou2'])
        print("tanni2"+request.form['tanni2'])
        print("hosokurennbann2"+request.form['hosokurennbann2'])
        print("hosokukubunn2"+request.form['hosokukubunn2'])
        
        try:
            name3 = request.form['name3']
            zaikeikubun3=request.form['kubun3']
            rp3 = request.form['rp3']
            rprenban3 = request.form['rprenban3']
            suuryou3 = request.form['suuryou3']
            youhou3 = request.form['youhou3']
            ryou3 = request.form['ryou3']
            tanni3 = request.form['tanni3']
            hosokurennbann3=request.form['hosokurennbann3']
            hosokukubunn3 = request.form['hosokukubunn3']
        except:
            pass
        
        try:
            name4 = request.form['name4']
            zaikeikubun4=request.form['kubun4']
            rp4 = request.form['rp4']
            rprenban4 = request.form['rprenban4']
            suuryou4 = request.form['suuryou4']
            youhou4 = request.form['youhou4']
            ryou4 = request.form['ryou4']
            tanni4 = request.form['tanni4']
            hosokurennbann4=request.form['hosokurennbann4']
            hosokukubunn4 = request.form['hosokukubunn4']
        except:
            pass
        
        try:
            name5 = request.form['name5']
            zaikeikubun5=request.form['kubun5']
            rp5 = request.form['rp5']
            rprenban5 = request.form['rprenban5']
            suuryou5 = request.form['suuryou5']
            youhou5 = request.form['youhou5']
            ryou5 = request.form['ryou5']
            tanni5 = request.form['tanni5']
            hosokurennbann5=request.form['hosokurennbann5']
            hosokukubunn5 = request.form['hosokukubunn5']
        except:
            pass
        
        try:
            name6 = request.form['name6']
            zaikeikubun6=request.form['kubun6']
            rp6 = request.form['rp6']
            rprenban6 = request.form['rprenban6']
            suuryou6 = request.form['suuryou6']
            youhou6 = request.form['youhou6']
            ryou6 = request.form['ryou6']
            tanni6 = request.form['tanni6']
            hosokurennbann6=request.form['hosokurennbann6']
            hosokukubunn6 = request.form['hosokukubunn6']
        except:
            pass
        
        try:
            name7 = request.form['name7']
            zaikeikubun7=request.form['kubun7']
            rp7 = request.form['rp7']
            rprenban7 = request.form['rprenban7']
            suuryou7 = request.form['suuryou7']
            youhou7 = request.form['youhou7']
            ryou7 = request.form['ryou7']
            tanni7 = request.form['tanni7']
            hosokurennbann7=request.form['hosokurennbann7']
            hosokukubunn7 = request.form['hosokukubunn7']
        except:
            pass
        
        try:
            name8 = request.form['name8']
            zaikeikubun8=request.form['kubun8']
            rp8 = request.form['rp8']
            rprenban8 = request.form['rprenban8']
            suuryou8 = request.form['suuryou8']
            youhou8 = request.form['youhou8']
            ryou8 = request.form['ryou8']
            tanni8 = request.form['tanni8']
            hosokurennbann8=request.form['hosokurennbann8']
            hosokukubunn8 = request.form['hosokukubunn8']
        except:
            pass
        
        try:
            
            name9 = request.form['name9']
            zaikeikubun9=request.form['kubun9']
            rp9 = request.form['rp9']
            rprenban9 = request.form['rprenban9']
            suuryou9 = request.form['suuryou9']
            youhou9 = request.form['youhou9']
            ryou9 = request.form['ryou9']
            tanni9 = request.form['tanni9']
            # hosokurennbann9=request.form['hosokurennbann9']
            # hosokukubunn9 = request.form['hosokukubunn9']
        except:
            pass
        
        l_0 = []
        l_1 = []
        l_2 = []
        l_3 = []
        l_4 = []
        l_5 = []
        l_6 = []
        l_7 = []
        l_8 = []
        l_9 = []
        
        if name0 != "":
            l_0 = [rp0, zaikeikubun0, suuryou0, rp0, youhou0, rp0, rprenban0, name0, ryou0, tanni0, rp0, rprenban0]
            print(l_0)
        if name1 != "":
            l_1 = [rp1, zaikeikubun1, suuryou1, rp1, youhou1, rp1, rprenban1, name1, ryou1, tanni1, rp1, rprenban1]
        if name2 != "":
            l_2 = [rp2, zaikeikubun2, suuryou2, rp2, youhou2, rp2, rprenban2, name2, ryou2, tanni2, rp2, rprenban2]
        if name3 != "":    
            l_3 = [rp3, zaikeikubun3, suuryou3, rp3, youhou3, rp3, rprenban3, name3, ryou3, tanni3, rp3, rprenban3]
        if name4 != "":    
            l_4 = [rp4, zaikeikubun4, suuryou4, rp4, youhou4, rp4, rprenban4, name4, ryou4, tanni4, rp4, rprenban4]
        if name5 != "":    
            l_5 = [rp5, zaikeikubun5, suuryou5, rp5, youhou5, rp5, rprenban5, name5, ryou5, tanni5, rp5, rprenban5]
        if name6 != "":    
            l_6 = [rp6, zaikeikubun6, suuryou6, rp6, youhou6, rp6, rprenban6, name6, ryou6, tanni6, rp6, rprenban6]
        if name7 != "":    
            l_7 = [rp7, zaikeikubun7, suuryou7, rp7, youhou7, rp7, rprenban7, name7, ryou7, tanni7, rp7, rprenban7]
        if name8 != "":    
            l_8 = [rp8, zaikeikubun8, suuryou8, rp8, youhou8, rp8, rprenban8, name8, ryou8, tanni8, rp8, rprenban8]
        if name9 != "":    
            l_9 = [rp9,zaikeikubun9,suuryou9,rp9,youhou9,rp9,rprenban9,name9,ryou9,tanni9,rp9,rprenban9]

        l_all = [l_0, l_1, l_2, l_3, l_4, l_5, l_6, l_7, l_8, l_9]
        print("---------------------------------------------")
        # print("l_all")
        # print(l_all)

        #new_pr,new_prrenban = False,False
        med_result = ''
        for i in range(len(l_all)):
            l_now = l_all[i]
            if l_now!=[]:
                if l_now[0]!='':
                    
                    #101,111を生成するかの判定
                    if i==0:
                        new_101=True
                    elif l_prev[0]!=l_now[0]:
                        new_101=True
                    else:
                        new_101=False
                        
                    if new_101:
                        med_result+=("101"+","+l_now[0]+","+l_now[1]+","+""+","+l_now[2]+"\n"+
                                    "111"+","+l_now[3]+","+"1"+","+""+","+l_now[4]+","+"\n"+
                                    "201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+"XXXX"+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                    "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+"ジェネリック変更不可"+""+"\n")
                    else:
                        med_result+=("201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+"XXXX"+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                    "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+"ジェネリック変更不可"+""+"\n")
                    
                    l_prev = l_now[:]
        print("-------------------------------------------------------")
        print("med_result")
        print(med_result)

        #--------------------------------------------------
        #元の
        # medi0 = ""
        # medi1=""
        # medi2=""
        # medi3=""
        # medi4=""
        # medi5=""
        # medi6=""
        # medi7=""
        # medi8 = ""
        # medi9=""
        
        # if name0 != "":
        #     medi0="101"+","+rp0+","+zaikeikubun0+","+""+","+suuryou0+"\n"+"111"+","+rp0+","+""+","+youhou0+","+""+","+"\n"+"201"+","+rp0+","+rprenban0+","+"1"+","+name0+","+ryou0+","+"1"+","+tanni0+"\n"+"281"+","+rp0+","+rprenban0+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name1 != "":
        #     medi1="101"+","+rp1+","+zaikeikubun1+","+""+","+suuryou1+"\n"+"111"+","+rp1+","+""+","+youhou1+","+""+","+"\n"+"201"+","+rp1+","+rprenban1+","+"1"+","+name1+","+ryou1+","+"1"+","+tanni1+"\n"+"281"+","+rp1+","+rprenban1+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name2 != "":
        #     medi2="101"+","+rp2+","+zaikeikubun2+","+""+","+suuryou2+"\n"+"111"+","+rp2+","+""+","+youhou2+","+""+","+"\n"+"201"+","+rp2+","+rprenban2+","+"1"+","+name2+","+ryou2+","+"1"+","+tanni2+"\n"+"281"+","+rp2+","+rprenban2+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name3 != "":
        #     medi3="101"+","+rp3+","+zaikeikubun3+","+""+","+suuryou3+"\n"+"111"+","+rp3+","+""+","+youhou3+","+""+","+"\n"+"201"+","+rp3+","+rprenban3+","+"1"+","+name3+","+ryou3+","+"1"+","+tanni3+"\n"+"281"+","+rp3+","+rprenban3+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name4 != "":
        #     medi4="101"+","+rp4+","+zaikeikubun4+","+""+","+suuryou4+"\n"+"111"+","+rp4+","+""+","+youhou4+","+""+","+"\n"+"201"+","+rp4+","+rprenban4+","+"1"+","+name4+","+ryou4+","+"1"+","+tanni4+"\n"+"281"+","+rp4+","+rprenban4+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name5 != "":
        #     medi5="101"+","+rp5+","+zaikeikubun5+","+""+","+suuryou5+"\n"+"111"+","+rp5+","+""+","+youhou5+","+""+","+"\n"+"201"+","+rp5+","+rprenban5+","+"1"+","+name5+","+ryou5+","+"1"+","+tanni5+"\n"+"281"+","+rp5+","+rprenban5+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name6 != "":
        #     medi6="101"+","+rp6+","+zaikeikubun6+","+""+","+suuryou6+"\n"+"111"+","+rp6+","+""+","+youhou6+","+""+","+"\n"+"201"+","+rp6+","+rprenban6+","+"1"+","+name6+","+ryou6+","+"1"+","+tanni6+"\n"+"281"+","+rp6+","+rprenban6+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name7 != "":
        #     medi7="101"+","+rp7+","+zaikeikubun7+","+""+","+suuryou7+"\n"+"111"+","+rp7+","+""+","+youhou7+","+""+","+"\n"+"201"+","+rp7+","+rprenban7+","+"1"+","+name7+","+ryou7+","+"1"+","+tanni7+"\n"+"281"+","+rp7+","+rprenban7+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name8 != "":
        #     medi8="101"+","+rp8+","+zaikeikubun8+","+""+","+suuryou8+"\n"+"111"+","+rp8+","+""+","+youhou8+","+""+","+"\n"+"201"+","+rp8+","+rprenban8+","+"1"+","+name8+","+ryou8+","+"1"+","+tanni8+"\n"+"281"+","+rp8+","+rprenban7+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        # if name9 != "":
        #     medi9="101"+","+rp9+","+zaikeikubun9+","+""+","+suuryou9+"\n"+"111"+","+rp9+","+""+","+youhou9+","+""+","+"\n"+"201"+","+rp9+","+rprenban9+","+"1"+","+name9+","+ryou9+","+"1"+","+tanni9+"\n"+"281"+","+rp9+","+rprenban9+","+"1"+","+"3"+","+"ジェネリック変更不可"+""
        
        
        # med_result = medi0 + medi1 + medi2+medi3 + medi4 + medi5 + medi6 + medi7 + medi8 + medi9
        #------------------------------------------------------------------------
        result = basic_result + med_result
        
        
        #result = result.encode('utf-8', 'replace')
        #result= result.encode('cp932', 'replace')
        result_sj= result.encode('shift_jis', 'replace')
        #result= result.encode('ascii', 'replace')


        #encodingを確認
        print("----------------------------------------")
        #import chardet
        #print(chardet.detect(result))
        mojibake = 0
        mojibake=str(result_sj).count('?')
        

    
        qrimg = qrcode.make(result)
        qrimg_sj=qrcode.make(result_sj)
        
        
        qrimg.save(os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png"))
        qrimg_sj.save(os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png"))
        
        path = os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample.png")
        path_sj = os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png")
        print(path)
        #ut = time.time()
        path1 = path + "?" + str(ut)
        path1_sj = path_sj + "?" + str(ut)
        
        return render_template('qrcode.html',ut=ut,path1=path1,result=result,path1_sj=path1_sj,mojibake=mojibake,_11_patient_name_kanji=_11_patient_name_kanji,birthday_gengou=birthday_gengou,birthday=birthday)

## おまじない
if __name__ == "__main__":
    app.run(debug=True)