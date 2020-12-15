from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.storage import FileSystemStorage
from config.const import TEMPORARY_DIR
import os
import tempfile


class TemporaryStorage(FileSystemStorage):
    temporary_base_url = TEMPORARY_DIR

    def __init__(self):
        super().__init__(location=os.path.join(settings.BASE_DIR, self.temporary_base_url))

    def save(self, *args, **kwargs):
        save_path = super().save(*args, **kwargs)
        return os.path.join(self.temporary_base_url, save_path)


class StaticStorage(S3Boto3Storage):

    """uploads to 'mybucket/static/', serves from 'cloudfront.net/static/'"""
    location = settings.STATICFILES_LOCATION
    file_overwrite = True
    secure_urls = False
    access_key = settings.AWS_ACCESS_KEY_ID
    secret_key = settings.AWS_SECRET_ACCESS_KEY

    def __init__(self, *args, **kwargs):
        kwargs['custom_domain'] = "127.0.0.1:9000/prescription"
        super(StaticStorage, self).__init__(*args, **kwargs)


class MediaStorage(S3Boto3Storage):
    
    """uploads to 'mybucket/media/', serves from 'cloudfront.net/media/'"""
    location = settings.MEDIAFILES_LOCATION
    file_overwrite = False
    secure_urls = False

    def __init__(self, *args, **kwargs):
        kwargs['custom_domain'] = "127.0.0.1:9000/prescription"
        super(MediaStorage, self).__init__(*args, **kwargs)

    # 追記 for image-kit
    def _save_content(self, obj, content, parameters):
        """
        We create a clone of the content file as when this is passed to boto3 it wrongly closes
        the file upon upload where as the storage backend expects it to still be open
        """
        '''https://github.com/matthewwithanm/django-imagekit/issues/391'''
        # Seek our content back to the start
        content.seek(0, os.SEEK_SET)

        # Create a temporary file that will write to disk after a specified size
        content_autoclose = tempfile.SpooledTemporaryFile()

        # Write our original content into our copy that will be closed by boto3
        content_autoclose.write(content.read())

        # Upload the object which will auto close the content_autoclose instance
        # super(CustomS3Boto3Storage, self)._save_content(obj, content_autoclose, parameters)
        super()._save_content(obj, content_autoclose, parameters)
        
        # Cleanup if this is fixed upstream our duplicate should always close
        if not content_autoclose.closed:
            content_autoclose.close()
