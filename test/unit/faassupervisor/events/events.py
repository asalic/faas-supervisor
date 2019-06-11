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
"""Unit tests for the faassupervisor.events module and classes."""

import sys
import io
import os
import unittest
from unittest import mock
import faassupervisor.events as events
from faassupervisor.events.s3 import S3Event
from faassupervisor.events.minio import MinioEvent
from faassupervisor.events.onedata import OnedataEvent
from faassupervisor.events.unknown import UnknownEvent
from faassupervisor.events.apigateway import ApiGatewayEvent
from faassupervisor.exceptions import UnknowStorageEventWarning

# pylint: disable=missing-docstring
# pylint: disable=no-self-use

minio_event = {"Key": "images/nature-wallpaper-229.jpg",
               "Records": [{"s3": {"object": {"key": "nature-wallpaper-229.jpg"},
                                   "bucket": {"name": "images",
                                              "arn": "arn:aws:s3:::images"}},
                                   "eventSource": "minio:s3"}]}

onedata_event = {"Key": "/my-onedata-space/files/file.txt",
                 "Records": [{"objectKey": "file.txt",
                              "eventSource": "OneTrigger"}]}

s3_event = {'Records': [{'awsRegion': 'us-east-1',
                         'eventSource': 'aws:s3',
                         's3': {'bucket': {'arn': 'arn:aws:s3:::darknet-bucket',
                                           'name': 'darknet-bucket'},
                                           'object': {'key': 'darknet-s3/input/dog.jpg'}}}]}

unknow_event = {'Records': [{'eventSource': 'narnia'}]}

api_gateway_event_wo_json = {'body': 'aXQgd29ya3Mh',
                             'headers': {'Content-Type': 'application/octet-stream'},
                             'httpMethod': 'POST',
                             'isBase64Encoded': False,
                             'queryStringParameters': None}

api_gateway_event_w_json = {'body': s3_event,
                            'headers': {'Content-Type': 'application/json'},
                            'httpMethod': 'POST',
                            'isBase64Encoded': False,
                            'queryStringParameters': {'q1':'v1', 'q2':'v2'}}


class ModuleTest(unittest.TestCase):

    def test_is_api_gateway_event_true(self):
        self.assertTrue(events._is_api_gateway_event({'httpMethod': 'POST'}))

    def test_is_api_gateway_event_false(self):
        self.assertFalse(events._is_api_gateway_event({}))

    def test_is_storage_event_true(self):
        self.assertTrue(events._is_storage_event(s3_event))

    def test_is_storage_event_false(self):
        self.assertFalse(events._is_storage_event({}))

    def test_parse_storage_event_s3(self):
        result = events._parse_storage_event(s3_event)
        self.assertIsInstance(result, S3Event)

    def test_parse_storage_event_minio(self):
        result = events._parse_storage_event(minio_event)
        self.assertIsInstance(result, MinioEvent)

    def test_parse_storage_event_onedata(self):
        result = events._parse_storage_event(onedata_event)
        self.assertIsInstance(result, OnedataEvent)

    def test_parse_storage_event_unknown(self):
        self.assertRaises(UnknowStorageEventWarning, events._parse_storage_event(unknow_event))

    def test_parse_event_unknown(self):
        result = events.parse_event(unknow_event)
        self.assertIsInstance(result, UnknownEvent)

    def test_parse_event_apigateway_wo_json_body(self):
        result = events.parse_event(api_gateway_event_wo_json)
        self.assertIsInstance(result, ApiGatewayEvent)

    def test_parse_event_apigateway_w_json_body(self):
        result = events.parse_event(api_gateway_event_w_json)
        self.assertIsInstance(result, S3Event)

    def test_parse_event_storage(self):
        result = events.parse_event(s3_event)
        self.assertIsInstance(result, S3Event)


class ApiGatewayEventTest(unittest.TestCase):

    def test_set_event_params(self):
        api = ApiGatewayEvent(api_gateway_event_w_json)
        self.assertEqual(api.body, s3_event)
        api = ApiGatewayEvent(api_gateway_event_wo_json)
        self.assertEqual(api.body, 'aXQgd29ya3Mh')

    def test_has_json_body(self):
        api = ApiGatewayEvent(api_gateway_event_w_json)
        self.assertTrue(api.has_json_body())
        api = ApiGatewayEvent(api_gateway_event_wo_json)
        self.assertFalse(api.has_json_body())

    def test_is_request_with_parameters(self):
        api = ApiGatewayEvent(api_gateway_event_w_json)
        self.assertTrue(api._is_request_with_parameters())
        api = ApiGatewayEvent(api_gateway_event_wo_json)
        self.assertFalse(api._is_request_with_parameters())

    def test_save_request_parameters(self):
        with mock.patch.dict('os.environ', {}, clear=True):
            ApiGatewayEvent(api_gateway_event_w_json)
            self.assertEqual(os.environ, {"CONT_VAR_q1":"v1", "CONT_VAR_q2":"v2"})

    @mock.patch('faassupervisor.utils.FileUtils.create_file_with_content')
    @mock.patch('faassupervisor.utils.SysUtils.join_paths')
    def test_save_event_json(self, mock_join, mock_create):
        mock_join.return_value = '/tmp/test/file'
        api = ApiGatewayEvent(api_gateway_event_w_json)
        result = api.save_event('/tmp/test')
        self.assertEqual(result, '/tmp/test/file')
        mock_create.assert_called_once_with('/tmp/test/file', s3_event)

    @mock.patch('faassupervisor.utils.FileUtils.create_file_with_content')
    @mock.patch('faassupervisor.utils.SysUtils.join_paths')
    def test_save_event_binary(self, mock_join, mock_create):
        mock_join.return_value = '/tmp/test/file'
        api = ApiGatewayEvent(api_gateway_event_wo_json)
        result = api.save_event('/tmp/test')
        self.assertEqual(result, '/tmp/test/file')
        mock_create.assert_called_once_with('/tmp/test/file', b'it works!', mode='wb')


class MinioEventTest(unittest.TestCase):

    def test_minio_event_creation(self):
        event = MinioEvent(minio_event)
        self.assertEqual(event.object_key, "images/nature-wallpaper-229.jpg")
        self.assertEqual(event.bucket_arn, "arn:aws:s3:::images")
        self.assertEqual(event.bucket_name, "images")
        self.assertEqual(event.file_name, "nature-wallpaper-229.jpg")
        self.assertEqual(event.get_type(), "MINIO")


class OnedataEventTest(unittest.TestCase):

    def test_onedata_event_creation(self):
        event = OnedataEvent(onedata_event)
        self.assertEqual(event.object_key, "/my-onedata-space/files/file.txt")
        self.assertEqual(event.file_name, "file.txt")
        self.assertEqual(event.get_type(), "ONEDATA")


class S3EventTest(unittest.TestCase):

    def test_s3_event_creation(self):
        event = S3Event(s3_event)
        self.assertEqual(event.object_key, "darknet-s3/input/dog.jpg")
        self.assertEqual(event.bucket_arn, "arn:aws:s3:::darknet-bucket")
        self.assertEqual(event.bucket_name, "darknet-bucket")
        self.assertEqual(event.file_name, "dog.jpg")
        self.assertEqual(event.get_type(), "S3")


class UnknownEventTest(unittest.TestCase):

    def test_set_event_params(self):
        event = UnknownEvent(unknow_event)
        self.assertEqual(event.get_type(), "UNKNOWN")

    def test_set_event_params_empty(self):
        event = UnknownEvent("")
        self.assertEqual(event.get_type(), "UNKNOWN")

    @mock.patch('faassupervisor.utils.FileUtils.create_file_with_content')
    @mock.patch('faassupervisor.utils.SysUtils.join_paths')
    def test_save_event(self, mock_join, mock_create):
        mock_join.return_value = '/tmp/test/file'
        event = UnknownEvent(unknow_event)
        event.save_event('/tmp/test')
        mock_join.assert_called_once_with('/tmp/test', 'event_file')
        mock_create.assert_called_once_with('/tmp/test/file', unknow_event)

