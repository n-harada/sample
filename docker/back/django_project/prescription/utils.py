import os
import uuid
from prescription.const import QR_image_base_url, Pescription_image_base_url


def get_QRImage_upload_to(image_object, filename):
    return os.path.join(
        QR_image_base_url,
        'original',
        get_image_path_from_prescription(image_object.prescription),
        str(uuid.uuid4()) + "_" + filename
    )


def get_A4_QRimage_upload_to(image_object, filename):
    return os.path.join(
        QR_image_base_url,
        'A4',
        get_image_path_from_prescription(image_object.prescription),
        str(uuid.uuid4()) + "_" + filename
    )


def get_PrescriptionImage_upload_to(image_object, filename):
    return os.path.join(
        Pescription_image_base_url,
        get_image_path_from_prescription(image_object.prescription),
        str(uuid.uuid4()) + "_" + filename)


def get_image_path_from_prescription(prescription):
    '''QRImage or PrescriptionImageからpath: {pharmacy.id}/{user.id}を作る関数'''
    pharmacy_id = str(prescription.pharmacy.id) if prescription.pharmacy else "None"
    upload_user_id = str(prescription.uploaded_by.id)
    return os.path.join(pharmacy_id, upload_user_id)


class OCRInvalidLabelError(Exception):
    pass
