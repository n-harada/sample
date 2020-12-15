import os
import shutil

dict_errorname_dirname = {
    '':'all_images','no_error':'no_error',
    'patients name':'患者氏名miss','patients name kana':'患者氏名カナmiss',
    'birthday':'生年月日miss','hokensha number':'保険者番号miss','kigo-bangou':'記号番号miss',
    'hakkobi':'発行日miss','gender':'性別miss',
    'iryokikan':'医療機関miss','iyakuhin':'医薬品miss','yohoyoryo':'用法用量miss',
    'Could not read the QR':'QR読み込みmiss'}

def reshape_uploads_dir(ERROR_KEY='[error-report]',dict_errorname_dirname=dict_errorname_dirname):
    '''LOG_FILENAME内のエラー報告内容に応じ、uploads内の画像のdir構造を整理する関数'''

    #dir情報を取得・定義
    ROOT_DIR = os.path.join(os.getcwd().split('prescription')[0],'prescription')
    l_uploads_files = ['uploads/prescription_images','uploads/QR_images','uploads/QR_images_A4']

    #log fileの名前を取得
    os.chdir(os.path.join(ROOT_DIR,'uploads'))
    l_logs = [i for i in os.listdir() if i.split('.')[-1]=='log']
    tmp = sorted([int(i.rstrip('.log')) for i in l_logs])
    LOG_FILENAME = str(tmp[-1])+'.log'
    print('log file used was',LOG_FILENAME) ##DEBUG PRINT

    #log fileの読み込み
    fd = open(LOG_FILENAME, mode='r')
    error_log = fd.read().splitlines()
    fd.close()

    #error報告のあったfileとその内容のdictを作成
    dict_errors = {}
    for str_ in error_log:
        if ERROR_KEY in str_:
            err_name = str_.split(',')[1].strip()
            err_file = str_.split(',')[2].strip()
            dict_errors[err_file] = err_name

    #dict_errorの内容に応じ、画像のdir構造を変更
    for dir_now in l_uploads_files:
        
        #該当dirへ移動し、file nameを取得する
        base_dir = os.path.join(ROOT_DIR,dir_now)
        os.chdir(base_dir)
        l_files = [i for i in os.listdir() if os.path.isfile(os.path.join(base_dir,i))]
        
        for file_ in l_files:        
            #エラー文を取得する
            for file_name_base in dict_errors.keys():
                if file_name_base in file_:
                    err = dict_errors[file_name_base]
                    break
                else:
                    err = 'no_error'
                    
            #格納対象となるdirを定義する, error_name~dir_nameの対応を定義していない場合は, error_nameをそのままdir_nameに定義
            if err in dict_errorname_dirname.keys():
                dir_ = dict_errorname_dirname[err]
            else:
                dir_ = err
            
            #格納対象となるdirを作成する
            try:
                os.mkdir(os.path.join(base_dir,dir_))
            except FileExistsError:
                pass
            
            #格納対象となるdirへフォルダを保存する
            copy_dir = os.path.join(base_dir,file_)
            out_dir = os.path.join(base_dir,dir_,file_)
            shutil.copy2(copy_dir,out_dir)

            #最後に、該当画像をall_imagesへ移動する
            try:
                os.mkdir(os.path.join(base_dir,dict_errorname_dirname['']))
            except FileExistsError:
                pass
            final_dir = os.path.join(base_dir,dict_errorname_dirname[''])
            shutil.move(copy_dir,final_dir)

if __name__ == '__main__':
    reshape_uploads_dir()