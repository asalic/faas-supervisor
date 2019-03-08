# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from faassupervisor.storage.storage import DefaultStorageProvider
import boto3
import faassupervisor.logger as logger
import faassupervisor.utils as utils

class Minio(DefaultStorageProvider):

    @utils.lazy_property
    def client(self):
        client = boto3.client('s3', endpoint_url='http://minio-service.minio:9000',
                              aws_access_key_id=self.auth.get('USER'),
                              aws_secret_access_key=self.auth.get('PASS'))
        return client

    def __init__(self, **kwargs):
        self.auth = kwargs['Auth']
        # This is the output bucket in case of OUTPUT storage
        self.storage_path = kwargs['Path']

    def download_input(self, event, input_dir_path):
        '''Downloads the file from the minio bucket'''
        file_download_path = utils.join_paths(input_dir_path, event.file_name) 
        logger.info("Downloading item from bucket '{0}' with key '{1}'".format(event.bucket_name, event.file_name))
        with open(file_download_path, 'wb') as data:
            self.client.download_fileobj(event.bucket_name, event.file_name, data)
        logger.info("Successful download of file '{0}' from bucket '{1}' in path '{2}'".format(event.file_name,
                                                                                               event.bucket_name,
                                                                                               file_download_path))
        return file_download_path
    
    def upload_output(self, output_dir_path):
        output_files = utils.get_all_files_in_directory(output_dir_path)
        logger.info("Found the following files to upload: {0}".format(output_files))
        for file_path in output_files:
            file_key = file_path.replace("{0}/".format(output_dir_path), "")
            self.upload_file(file_path, file_key)
    
    def upload_file(self, file_path, file_key):
        logger.info("Uploading file '{0}' to bucket '{1}'".format(file_key, self.storage_path))
        with open(file_path, 'rb') as data:
            self.client.upload_fileobj(data, self.storage_path, file_key)