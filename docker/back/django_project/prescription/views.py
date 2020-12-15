import datetime as dt
import time
import traceback
import os
import uuid
from warnings import warn
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from .models import Prescription, PrescriptionImage, QRImage, OCRError
from .utils import get_image_path_from_prescription
from .const import QR_image_base_url
from config.const import TEMPORARY_DIR
from service.ocr.algo import basic_info as bi
from service.ocr.algo import create_msg
from service.ocr.algo import make_qr as mq
from service.ocr.algo import med_info as mi
from service.ocr.algo import preprocessing_and_OCR as pp
from django.conf import settings

# server立ち上げ時にgmail_objをglobal変数として取得する
try:
    gmail_obj = mq.load_gmail_obj()
except Exception as e:
    print('mail not loaded initially', e.args)


class OCRProcess:

    def __init__(self, images, prescription):
        self.prescription = prescription
        self.user_name = prescription.uploaded_by.email
        self.avoid_ERROR = settings.AVOID_ERROR
        self.upload_images = images
        self.save_file_name_base = self.get_save_file_name()
        self.result = self.exec_ocr()

    def get_save_file_name(self):
        tz_jst = dt.timezone(dt.timedelta(hours=9))
        start_aware = dt.datetime.now(tz_jst)
        start_time_dt = start_aware.strftime('%Y-%m-%d-%H-%M-%S-%f')
        save_file_name_base = self.user_name + '_' + str(uuid.uuid4()) + "_" + start_time_dt
        return save_file_name_base
        
    def exec_ocr(self):
        boke, basic_result, basic_result_confidence, med_result, med_result_confidence, within_expiration_date, reading_DONE = self.try_main_flow_toParse()
        med_result_len, path, mojibake, basic_result, med_result, csv_result = self.main_flow_makeQR(basic_result, med_result)

        # 出力画面にて表示する文字列・その特徴を生成する -> TO TOMOKI pass
        basic_result_confidence = create_msg.get_basic_confidence(basic_result_confidence)
        med_result_confidence = create_msg.get_med_confidence(med_result_confidence)
        msg_robot_top = create_msg.robot_statement(reading_DONE, boke, basic_result_confidence, med_result_confidence, within_expiration_date)

        # print('============================')
        # print('basic_result', basic_result)
        # print('============================')
        # print('basic_result_confidence', basic_result_confidence)
        # print('============================')
        # print('med_result', med_result)
        # print('============================')
        # print('med_result_confidence', med_result_confidence)
        # print('============================')
        # print('ROBOT:', msg_robot_top)
        # print('============================')

        return {
            "boke": boke,
            "basic_result": basic_result,
            "med_result": med_result,
            "csv_result": csv_result,
            "med_result_len": med_result_len,
            "path": path,
            "mojibake": mojibake,
            "msg_robot_top": msg_robot_top,
            "ocr_result": self.ocr_result if hasattr(self, 'ocr_result') else None
        }

    def try_main_flow_toParse(self):
        reading_DONE = True
        try:
            parse_result_array = self.main_flow_toParse()
        except Exception as e:
            parse_result_array = False, None, None, None, None, True
            reading_DONE = False
            print('main function failed', 'args:', e.args)
            if not self.avoid_ERROR:
                print(traceback.format_exc())
                raise e
        return (*parse_result_array, reading_DONE)

    def main_flow_toParse(self):
        '''文字パース完了までの実行し切りたいmain処理を定義'''

        # フロントから送られてきた画像ファイルを前処理し、OCRする
        ocr_result, boke, *_ = pp.preprocess_and_OCR(self.upload_images, self.save_file_name_base)
        self.ocr_result = ocr_result

        # OCR結果から必要な情報を抽出する
        basic_result, basic_result_confidence, within_expiration_date = bi.basic_info(ocr_result)
        med_result, med_result_confidence = mi.text_processing_med(ocr_result["med"], prescription_sheet_num=len(self.upload_images))
        
        return boke, basic_result, basic_result_confidence, med_result, med_result_confidence, within_expiration_date
    
    def main_flow_makeQR(self, basic_result, med_result):
        '''文字パース結果をQRコード化するためのmain処理を定義'''
        out_dir = os.path.join(QR_image_base_url, get_image_path_from_prescription(self.prescription))
        qr_result, med_result_len, basic_result, med_result, csv_result = mq.make_qrcode(
            basic_result, med_result, self.save_file_name_base, out_dir=os.path.join(TEMPORARY_DIR, out_dir))
        path = qr_result[0] + "?" + str(time.time())
        mojibake = qr_result[1]
        
        return med_result_len, path, mojibake, basic_result, med_result, csv_result


class ResultView(TemplateView):
    template_name = "qrcode_main.html"

    def post(self, request):
        user = request.user
        images = request.FILES.getlist("img[]")

        # 処方箋レコード作成
        prescription = Prescription.objects.create(
            pharmacy=user.pharmacy,
            uploaded_by=request.user
        )
        result = OCRProcess(images, prescription).result

        # 処方箋アップデート
        prescription.ocr_result = result["ocr_result"]
        prescription.basic_result = result["basic_result"]
        prescription.med_result = result["med_result"]
        prescription.qr_csv = result["csv_result"]
        prescription.save()
        
        # QR画像レコード作成
        qr_image = QRImage.objects.create(
            prescription=prescription,
            image_data=result["path"].replace('media/', '').split("?")[0],
        )

        # 処方箋画像作成
        prescription_image_list = []
        for image in images:
            prescription_image = PrescriptionImage.objects.create(
                prescription=prescription,
                image_data=image,
            )
            prescription_image_list.append(prescription_image)

        # メール送信
        user.send_mail and self.send_mail(result.save_file_name_base) and QRImage.objects.filter(pk=qr_image.pk).update(sent_to_user=True)

        # context作成
        context = result
        context.update({
            "prescription_id": str(prescription.id)
        })

        med_result = result["med_result"]
        context.update({
            "med_result_list": [{
                "result": res,
                "count": index,
                "next_PR_number": med_result[index + 1]["RP番号"] if index != len(med_result) - 1 else None 
            } for index, res in enumerate(med_result)],
            "path_input_image_list": [prescription_image.image_data for prescription_image in prescription_image_list],
            "qr_path": qr_image.image_data
        })

        return render(
            request,
            self.template_name,
            context=context)

    def send_mail(self, save_file_name_base):
        user = self.request.user
        send_success = True

        # A4のcanvasに処方箋撮影画像, QRコードを貼ってpdf化する
        mq.process_QRimg_for_print(save_file_name_base)

        # 上記pdfをメールにて送付する
        global gmail_obj
        try:  # PATCH JUST IN CASE
            mq.send_img_attatched_mail(save_file_name_base, user.email, to=user.email, gmail=gmail_obj)
        except Exception as e:
            print('mail could not be sent', e.args)
            try:
                gmail_obj = mq.load_gmail_obj()
                mq.send_img_attatched_mail(save_file_name_base, user.email, to=user.email, gmail=gmail_obj)
                print('mail obj reloaded and mail successfully sent')
            except Exception as e:
                print(e)
                warn('mail sending failed')
                send_success = False
        return send_success


class IndexView(TemplateView):
    template_name = "multi_ok.html"
    
    def get(self, request):
        context = {}
        return render(request, self.template_name, context)


class ReportRedirectPageView(TemplateView):
    template_name = "multi_ok.html"

    def get(self, request, **kwargs):
        prescription = Prescription.objects.get(id=self.kwargs["prescription_id"])
        user = request.user
        label = self.kwargs['slug']
        OCRError.objects.create(
            prescription=prescription,
            label=label
        )
        print("create OCRError", prescription, label)
        return redirect('prescription:index')

class ReportPageView(TemplateView):
    template_name = "report.html"

    def get(self, request, **kwargs):
        context = {}
        return render(request, self.template_name, context)
