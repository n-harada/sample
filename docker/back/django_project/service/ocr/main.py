# coding: UTF-8
import os
from flask import Flask, render_template, request,send_file,after_this_request,make_response,jsonify,redirect, url_for, send_from_directory
import flask_login
from requests import Request, Session
import time
import datetime as dt
from warnings import warn
import os.path
import logging
from logging import getLogger, StreamHandler, FileHandler, Formatter

#別ファイルの読み込み
from algo import preprocessing_and_OCR as pp
from algo import med_info as mi
from algo import basic_info as bi
from algo import make_qr as mq
from algo import create_msg

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.secret_key = 'super secret string'  # Change this!

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
file_name_for_log = 'init'

# --------------------------------
# logger
# --------------------------------

logger = getLogger("LogBot")
logger.setLevel(logging.INFO)
handler_format = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(handler_format)

# Our mock database.
users = {'foo@bar.tld': {'password': 'secret'}}

class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    if email not in users:
        return

    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in users:
        return

    user = User()
    user.id = email

    # DO NOT ever store passwords in plaintext and always compare password
    # hashes using constant-time comparison!
    user.is_authenticated = request.form['password'] == users[email]['password']

    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'/>
                <input type='password' name='password' id='password' placeholder='password'/>
                <input type='submit' name='submit'/>
               </form>
               '''

    email = flask.request.form['email']
    if flask.request.form['password'] == users[email]['password']:
        user = User()
        user.id = email
        flask_login.login_user(user)
        return flask.redirect(flask.url_for('protected'))

    return 'Bad login'


@app.route('/protected')
@flask_login.login_required
def protected():
    return 'Logged in as: ' + flask_login.current_user.id

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out'

@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized'

@app.route('/')
def hello():
    '''
    初期画面
    '''

        
    return render_template('multi_ok.html')#複数枚対応
    #return render_template('basic_design.html')#1枚対応

@app.route('/wait')
def wait_page():
    '''
    待機中画面
    '''
    return render_template('wait.html')

@app.route('/report')
def report_page():
    '''
    報告画面
    '''
    return render_template('report.html')

@app.route('/report-now')
def report_now_page():
    logger.info('error!!')
    print("error report!!!")
    return render_template('multi_ok.html')

@app.route('/report-name')
def report_name_page():
    logger.info('【error-report】,patients name ,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-kana')
def report_kana_page():
    logger.info('【error-report】,patients name kana ,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-birth')
def report_birth_page():
    logger.info('【error-report】,birthday,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-num')
def report_num_page():
    logger.info('【error-report】,hokensha number,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-kigo')
def report_kigo_page():
    logger.info('【error-report】,kigo-bango,'+file_name_for_log)
    print("error report!!!!")
    return render_template('multi_ok.html')
@app.route('/report-hakkobi')
def report_hakkobi_page():
    logger.info('【error-report】,hakkobi,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-gender')
def report_gender_page():
    logger.info('【error-report】,gender,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-iryokikan')
def report_iryokikan_page():
    logger.info('【error-report】,iryokikan,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-iyaku')
def report_iyaku_page():
    logger.info('【error-report】,iyakuhin,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-yoho')
def report_yoho_page():
    logger.info('【error-report】,yohoyoryo,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')
@app.route('/report-no-qr')
def report_no_qr_page():
    logger.info('【error-report】,Could not read the QR,'+file_name_for_log)
    print("error report!!!")
    return render_template('multi_ok.html')

@app.route('/uploads/<path:path>')
def uploaded_file6(path):
    '''
    画像表示する際のPath
    .uploadsより下の部分を<path:path>のところに書けば良い。
    '''
    return send_from_directory(app.config['UPLOAD_FOLDER'], path)

#========<mzdによるベタ打ち, please lint>========
usr_name = 'DUMMY_USER' ##PATCHED with dummy
to_addr = 'yuki-matsuda@g.ecc.u-tokyo.ac.jp' ##CHANGE to customer addr!!!
send_MAIL = False #default is false
avoid_ERROR = True #remenber to make this True on customer APP!!!!!

#server立ち上げ時にgmail_objをglobal変数として取得する
try:
    gmail_obj = mq.load_gmail_obj()
except Exception as e:
    print('mail not loaded initially',e.args)

#avoid ERRORがoffのときは一応warnしてもらう
if avoid_ERROR==False:
    warn('======ERRORS WOULD NOT BE AVOIDED======')

#========<mzdによるベタ打ち, please lint>========

@app.route('/result1', methods=['POST'])
def processing(usr_name=usr_name,avoid_ERROR=avoid_ERROR,send_mail=send_MAIL,START_KEY_STRING='REQUEST STARTED',END_KEY_STRING='REQUEST ENDED'):
    '''処理'''

    def assert_dir_struct():
        '''消去されている可能性のある, 前提としている相対dir構造が存在するかを確認し, なければ構築する処理'''

        l_assumed_dirs = ['./uploads/QR_images','./uploads/QR_images_A4','./uploads/prescription_images']
        for dir_ in l_assumed_dirs:
            try:
                dir_ = os.path.abspath(dir_)
                os.makedirs(dir_)
                print(dir_,'newly made') ##DEBUG PRINT
            except FileExistsError:
                pass


    def main_flow_toParse(save_file_name_base,start):

        '''文字パース完了までの実行し切りたいmain処理を定義'''

        now = dt.datetime.now()
        path = "uploads/{0:%Y%m%d}.log".format(now)

        if os.path.exists(path):
            print ("file found uploads/{0:%Y%m%d}.log".format(now))
        else:
            print ("file file found uploads/{0:%Y%m%d}.log created".format(now))
            f = open(path, 'w')
            f.write('')  # 何も書き込まなくてファイルは作成されました
            f.close()

        # ---- 2-2.テキスト出力のhandler ----
        # handlerの生成
        file_handler = FileHandler(path, 'a')
        # handlerのログレベル設定(ハンドラが出力するエラーメッセージのレベル)
        file_handler.setLevel(logging.INFO)
        # ログ出力フォーマット設定
        file_handler.setFormatter(handler_format)

        # --------------------------------
        # 3.loggerにhandlerをセット
        # --------------------------------
        # 標準出力のhandlerをセット
        logger.addHandler(stream_handler)
        # テキスト出力のhandlerをセット
        logger.addHandler(file_handler)
        logger.info("new session started")

        #フロントから送られたファイルの受け取り
        upload_files = request.files.getlist('img[]')
        print('upload_files',upload_files,'len(upload_files)',len(upload_files),save_file_name_base) ##DEBUG PRINT

        #フロントから送られてきた画像ファイルを前処理し、OCRする
        print('uploading files DONE, preprocessing and doing OCR...', (dt.datetime.now()-start).total_seconds(),save_file_name_base) #DEBUG PRINT
        print("---------")
        preprocessing_result=pp.preprocess_and_OCR(upload_files,save_file_name_base) 
        ocr_result = preprocessing_result[0]
        # print(ocr_result)　harada
        boke = preprocessing_result[1]

        #OCR結果から必要な情報を抽出する
        print('preprocessing and OCR DONE, parsing result...', (dt.datetime.now()-start).total_seconds(),save_file_name_base) #DEBUG PRINT
        print("---------")
        basic_result, basic_result_confidence, within_expiration_date = bi.basic_info(ocr_result)
        med_result, med_result_confidence = mi.text_processing_med(ocr_result["med"],prescription_sheet_num=len(upload_files))

        #QRコードの生成開始をしていることを出力する
        print('parsing DONE, making QR...', (dt.datetime.now()-start).total_seconds(),save_file_name_base) #DEBUG PRINT
        
        return boke, basic_result, basic_result_confidence, med_result, med_result_confidence, within_expiration_date

    def main_flow_makeQR(basic_result, med_result,save_file_name_base,send_mail,usr_name,start):
        '''文字パース結果をQRコード化するためのmain処理を定義'''

        qr_result,med_result_len, basic_result, med_result=mq.make_qrcode(basic_result, med_result, save_file_name_base)
        path = qr_result[0] + "?" + str(time.time())
        mojibake = qr_result[1]

        #ユーザがメール送付を希望する場合はそれを行う
        if send_mail:

            #A4のcanvasに処方箋撮影画像, QRコードを貼ってpdf化する
            mq.process_QRimg_for_print(save_file_name_base)

            #上記pdfをメールにて送付する
            global gmail_obj
            try: ##PATCH JUST IN CASE
                mq.send_img_attatched_mail(save_file_name_base,usr_name,to=to_addr,gmail=gmail_obj)
            except Exception as e:
                print('mail could not be sent',e.args)
                try:
                    gmail_obj = mq.load_gmail_obj()
                    mq.send_img_attatched_mail(save_file_name_base,usr_name,to=to_addr,gmail=gmail_obj)
                    print('mail obj reloaded and mail successfully sent')
                except Exception as e:
                    warn('mail sending failed')

        print('QR created and mail sent.', (dt.datetime.now()-start).total_seconds(),save_file_name_base) #DEBUG PRINT
        return med_result_len, path, mojibake, basic_result, med_result

    ##MAINの処理フロー##
    if request.method == 'POST':

        #処理開始をコンソール上に宣言
        start = dt.datetime.now() #DEBUG PRINT  

        tz_jst = dt.timezone(dt.timedelta(hours=9))
        start_aware = dt.datetime.now(tz_jst)
        start_time_dt = start_aware.strftime('%Y-%m-%d-%H-%M-%S-%f')
        save_file_name_base = usr_name+'_'+start_time_dt
        global file_name_for_log
        file_name_for_log = save_file_name_base

        print(START_KEY_STRING,save_file_name_base) ##FOR LOGGING

        #dir構造が十分かをcheck
        assert_dir_struct()

        #読み取り結果完了initialize
        reading_DONE = False

        #avoid_ERRORをonにしている場合は, try~except文でmain処理を囲む
        if avoid_ERROR:
            try:
                boke, basic_result, basic_result_confidence, med_result, med_result_confidence, within_expiration_date = main_flow_toParse(save_file_name_base,start=start)
                reading_DONE = True
            except Exception as e:
                boke, basic_result, basic_result_confidence, med_result, med_result_confidence, within_expiration_date = False, None, None, None, None, True
                print('main function failed','args:',e.args)
            med_result_len, path, mojibake, basic_result, med_result = main_flow_makeQR(basic_result, med_result,save_file_name_base,send_mail=send_mail,usr_name=usr_name,start=start)            

        #avoid_ERRORをoffの場合は、シンプルに処理を実行
        else:
            boke, basic_result, basic_result_confidence, med_result, med_result_confidence, within_expiration_date = main_flow_toParse(save_file_name_base,start=start)
            med_result_len, path, mojibake, basic_result, med_result = main_flow_makeQR(basic_result, med_result,save_file_name_base,send_mail=send_mail,usr_name=usr_name,start=start)
            reading_DONE = True


        #出力画面にて表示する文字列・その特徴を生成する -> TO TOMOKI pass
        basic_result_confidence = create_msg.get_basic_confidence(basic_result_confidence)
        med_result_confidence = create_msg.get_med_confidence(med_result_confidence)
        msg_robot_top = create_msg.robot_statement(reading_DONE,boke,basic_result_confidence,med_result_confidence, within_expiration_date)

        print('============================')
        print('basic_result',basic_result)
        print('============================')
        print('basic_result_confidence',basic_result_confidence)
        print('============================')
        print('med_result',med_result)
        print('============================')
        print('med_result_confidence',med_result_confidence)
        print('============================')
        print('ROBOT:',msg_robot_top)
        print('============================') ##DEBUG PRINTS

        #処方箋の生の画像が存在するdirのlistを生成 ... 保存したタイミングでdirをreturnさせたほうが本来は良いので, 追々リファクタ
        l_path_input_image = []
        file_dir = './uploads/prescription_images'
        for i in range(len(request.files.getlist('img[]'))):
            file_name = save_file_name_base+'_'+str(i)+'.jpeg'
            l_path_input_image.append(os.path.join(file_dir,file_name))
        path_input_image_len = len(request.files.getlist('img[]'))

        print(END_KEY_STRING,save_file_name_base) ##FOR LOGGING
        print(path_input_image_len)

        return render_template("qrcode_main.html",boke=boke,path_input_image=l_path_input_image,path_input_image_len=path_input_image_len,basic_result=basic_result,med_result=med_result,med_result_len=med_result_len,path=path,mojibake=mojibake,msg_robot_top=msg_robot_top)
        

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.errorhandler(405)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404
                
            

## おまじない
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
