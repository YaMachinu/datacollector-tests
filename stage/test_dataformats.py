# Copyright 2018 StreamSets Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

logger = logging.getLogger(__name__)

#
# Text base file format parsing via Data Parser processor
#


def create_text_pipeline(sdc_builder, data_format, content):
    builder = sdc_builder.get_pipeline_builder()

    origin = builder.add_stage('Dev Raw Data Source')
    origin.data_format = 'TEXT'
    origin.raw_data = content

    parser = builder.add_stage('Data Parser')

    parser.field_to_parse = '/text'
    parser.target_field = '/'
    parser.data_format = data_format

    trash = builder.add_stage('Trash')

    origin >> parser >> trash

    return builder.build('Parse {}'.format(data_format))


def test_parse_json(sdc_builder, sdc_executor):
    """Validate parsing of JSON content via the Data Parser processor."""
    pipeline = create_text_pipeline(sdc_builder, 'JSON', '{"key" : "value"}')

    sdc_executor.add_pipeline(pipeline)
    snapshot = sdc_executor.capture_snapshot(pipeline, start_pipeline=True).snapshot
    sdc_executor.stop_pipeline(pipeline)

    assert len(snapshot['DataParser_01'].output) == 1
    assert snapshot['DataParser_01'].output[0].get_field_data('/key') == 'value'


def test_parse_delimited(sdc_builder, sdc_executor):
    """Validate parsing of delimited content via the Data Parser processor."""
    pipeline = create_text_pipeline(sdc_builder, 'DELIMITED', '1,2,3')

    sdc_executor.add_pipeline(pipeline)
    snapshot = sdc_executor.capture_snapshot(pipeline, start_pipeline=True).snapshot
    sdc_executor.stop_pipeline(pipeline)

    assert len(snapshot['DataParser_01'].output) == 1
    assert snapshot['DataParser_01'].output[0].get_field_data('[0]') == '1'
    assert snapshot['DataParser_01'].output[0].get_field_data('[1]') == '2'
    assert snapshot['DataParser_01'].output[0].get_field_data('[2]') == '3'


def test_parse_log(sdc_builder, sdc_executor):
    """Validate parsing of log content via the Data Parser processor."""
    pipeline = create_text_pipeline(sdc_builder, 'LOG', '127.0.0.1 ss h [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326')

    sdc_executor.add_pipeline(pipeline)
    snapshot = sdc_executor.capture_snapshot(pipeline, start_pipeline=True).snapshot
    sdc_executor.stop_pipeline(pipeline)

    assert len(snapshot['DataParser_01'].output) == 1
    assert snapshot['DataParser_01'].output[0].get_field_data('/request') == '/apache_pb.gif'
    assert snapshot['DataParser_01'].output[0].get_field_data('/clientip') == '127.0.0.1'


def test_parse_syslog(sdc_builder, sdc_executor):
    """Validate parsing of syslog content via the Data Parser processor."""
    pipeline = create_text_pipeline(sdc_builder, 'SYSLOG', "<34>Oct 11 22:14:15 mymachine su: 'su root' failed for lonvick on /dev/pts/")

    sdc_executor.add_pipeline(pipeline)
    snapshot = sdc_executor.capture_snapshot(pipeline, start_pipeline=True).snapshot
    sdc_executor.stop_pipeline(pipeline)

    assert len(snapshot['DataParser_01'].output) == 1
    assert snapshot['DataParser_01'].output[0].get_field_data('/severity') == 2
    assert snapshot['DataParser_01'].output[0].get_field_data('/host') == 'mymachine'


def test_parse_xml(sdc_builder, sdc_executor):
    """Validate parsing of xml content via the Data Parser processor."""
    pipeline = create_text_pipeline(sdc_builder, 'XML', "<root><key>value</key></root>")

    sdc_executor.add_pipeline(pipeline)
    snapshot = sdc_executor.capture_snapshot(pipeline, start_pipeline=True).snapshot
    sdc_executor.stop_pipeline(pipeline)

    assert len(snapshot['DataParser_01'].output) == 1
    assert snapshot['DataParser_01'].output[0].get_field_data('/key[0]/value') == 'value'
