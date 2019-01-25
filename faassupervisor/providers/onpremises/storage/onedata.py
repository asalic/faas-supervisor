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

import os, base64
import requests
import faassupervisor.utils as utils
from faassupervisor.interfaces.dataprovider import DataProviderInterface

class Onedata(DataProviderInterface):

    CDMI_PATH = '/cdmi'

    def __init__(self, event, output_folder):
        self.event = event
        self.os_tmp_folder = os.path.dirname(output_folder)
        self.output_folder = output_folder
        # Onedata settings
        self.onedata_access_token = os.environ.get('ONEDATA_ACCESS_TOKEN')
        self.oneprovider_host = os.environ.get('ONEPROVIDER_HOST')
        self.headers = {
            'X-CDMI-Specification-Version': '1.1.1',
            'X-Auth-Token': self.onedata_access_token
        }

    @classmethod    
    def is_onedata_event(cls, event):
        if utils.is_key_and_value_in_dictionary('data', event) \
        and utils.is_key_and_value_in_dictionary('body', event['data']) \
        and utils.is_key_and_value_in_dictionary('eventSource', event['data']['body']):
            event_source = event['data']['body']['eventSource']
            return event_source == 'OneTrigger'
        return False

    def download_input(self):
        '''Downloads the file from the Onedata space and returns the path were the download is placed'''
        file_path = self.event['data']['body']['path']
        file_name = self.event['data']['body']['file']
        url = 'https://{0}{1}{2}'.format(self.oneprovider_host, self.CDMI_PATH, file_path)
        print("Downloading item from '{0}' with key '{1}'".format(file_path, file_name))
        req = requests.get(url, headers=self.headers)
        if req.status_code == 200:
            response = req.json()
            file_download_path = "{0}/{1}".format(self.os_tmp_folder, file_name) 
            utils.create_folder(self.os_tmp_folder)
            encoded_content = response['value']
            print(file_name)
            with open(file_download_path, 'wb') as f:
                f.write(base64.b64decode(encoded_content))
            print("Successful download of file '{0}' from Oneprovider '{1}' in path '{2}'".format(file_name, file_path, file_download_path))
            return file_download_path
        else:
            print("Download failed!")
            return None

    def upload_output(self):
        pass

    def upload_file(self, file_name):
        pass