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

@app.route('/camera')
def camera_page():
    return render_template('camera2.html')


@app.route('/result1', methods=['GET','POST'])
def hello_test():
    upload_files = request.files.getlist('img[]')
    # file = upload_files[0]
    # filename=str(time.time())+".png"
    # file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
    
    #val = input('Enter number: ')
    val=1011
    # with codecs.open(str(val)+".csv", "r", "Shift-JIS", "ignore") as file:
    #     csv_input = pd.read_table(file, delimiter=",")

    # base_data = pd.read_csv("csv_data/"+str(val)+"_base.csv",encoding='cp932').set_index('item')
    # _1_hospital_code_type=base_data.loc['_1_hospital_code_type'][0]
    # _1_hospital_code=base_data.loc['_1_hospital_code'][0]
    # _1_hospital_place_code=base_data.loc['_1_hospital_place_code'][0]
    # _1_hospital_name=base_data.loc['_1_hospital_name'][0]
    # _5_doctor_name_kanji=base_data.loc['_5_doctor_name_kanji'][0]
    # _11_patient_name_kanji=base_data.loc['_11_patient_name_kanji'][0]
    # _11_patient_name_kana=base_data.loc['_11_patient_name_kana'][0]
    # _12_patient_sex=base_data.loc['_12_patient_sex'][0]
    # _13_patient_birthday=base_data.loc['_13_patient_birthday'][0]
    # _22_insurance_patient_num = base_data.loc['_22_insurance_patient_num'][0]
    # _23_insurance_card_id=base_data.loc['_23_insurance_card_id'][0].replace("?", "-")
    # _23_insurance_card_num=base_data.loc['_23_insurance_card_num'][0]
    # _23_insurance_type=base_data.loc['_23_insurance_type'][0]
    # _51_prescription_date = base_data.loc['_51_prescription_date'][0]
    
    base_data = pd.read_csv("csv_data/"+str(val)+"_base.csv",encoding='cp932').set_index('item')
    #base_data = pd.read_csv("csv_data/"+str(val)+"_base.csv",encoding='utf-8').set_index('item')
    _1_hospital_code_type=base_data.loc['_1_hospital_code_type'][0]
    _1_hospital_code=base_data.loc['_1_hospital_code'][0]
    _1_hospital_place_code=base_data.loc['_1_hospital_place_code'][0]
    _1_hospital_name=base_data.loc['_1_hospital_name'][0]
    _5_doctor_name_kanji=""
    _11_patient_name_kanji=""
    _11_patient_name_kana=""
    _12_patient_sex=""
    _13_patient_birthday=""
    _22_insurance_patient_num = base_data.loc['_22_insurance_patient_num'][0]
    _23_insurance_card_id = jaconv.h2z(base_data.loc['_23_insurance_card_id'][0].replace("?", "-"),digit=True, ascii=True)
    _23_insurance_card_num=jaconv.h2z(base_data.loc['_23_insurance_card_num'][0],digit=True, ascii=True)
    _23_insurance_type=""
    _51_prescription_date = ""
    
    basic_result =  "JAHIS3" + "\n" +"1"+","+_1_hospital_code_type + "," + _1_hospital_code + "," + _1_hospital_place_code + "," + _1_hospital_name + "\n" +"5"+","+ "" + "," + "" + "," + _5_doctor_name_kanji + "\n" +"11"+","+ "" + "," + _11_patient_name_kanji + "," + _11_patient_name_kana + "\n" +"12"+","+ _12_patient_sex + "\n" +"13"+","+ _13_patient_birthday + "\n" + "22"+","+_22_insurance_patient_num+"\n"+"23"+","+_23_insurance_card_id+","+_23_insurance_card_num+","+_23_insurance_type+","+""+"\n"+"51"+","+_51_prescription_date+"\n"

    #med_data = pd.read_csv("csv_data/" + str(val) + "_medi.csv", encoding='cp932')
    med_data = pd.read_csv("csv_data/" + str(val) + "_medi.csv", encoding='utf-8')
    l_all=[]
    for row in med_data.itertuples():
        #print([row[1], row[7], row[6], row[1], row[5], row[1], row[2], row[3],int(row[4]), row[8], row[1], row[2]])
        #l_all.append([str(row[1]), str(row[7]), str(row[6]), str(row[1]), str(row[5]), str(row[1]), str(row[2]),str(row[3]),str(int(row[4])), str(row[8]), str(row[1]), str(row[2])])
        l_all.append([str(row[1]), str(""), str(""), str(row[1]), str(row[5]), str(row[1]), str(row[2]),str(row[3]),str(int(row[4])), str(""), str(row[1]), str(row[2])])



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
                                "201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+""+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+""+""+"\n")
                else:
                    med_result+=("201"+","+l_now[5]+","+l_now[6]+",,"+"8"+","+""+","+l_now[7]+","+l_now[8]+","+"1"+","+l_now[9]+"\n"+
                                "281"+","+l_now[10]+","+l_now[11]+","+"1"+","+"3"+","+""+""+"\n")

                l_prev = l_now[:]

    result = basic_result + med_result
    result_list=med_result.split("\n")

    result_sj = result.encode('shift_jis', 'replace')
    mojibake = 0
    mojibake = int(str(result_sj).count('?'))

    qrimg_sj = qrcode.make(result_sj)
    
    qrimg_sj.save(os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png"))
    
    path_sj = os.path.join(app.config['UPLOAD_FOLDER'] + "/images", "qrsample_sj.png")
    path1_sj = path_sj + "?" + str(ut)
    time.sleep(4)
    return render_template('qrcode2.html',l_all=l_all,ut=ut,result_list=result_list,path1_sj=path1_sj,mojibake=mojibake,_22_insurance_patient_num=jaconv.z2h(_22_insurance_patient_num,digit=True, ascii=True),_23_insurance_card_id=jaconv.z2h(_23_insurance_card_id,digit=True, ascii=True),_23_insurance_card_num=jaconv.z2h(_23_insurance_card_num,digit=True, ascii=True),result_sj=result_list)

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