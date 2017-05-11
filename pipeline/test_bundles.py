# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import json
import pytest
from javaproperties import Properties
from uuid import uuid4

from testframework import sdc_models

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Test pipeline (simple generator -> trash)
@pytest.fixture(scope='module')
def pipeline(sdc_executor):
    builder = sdc_executor.get_pipeline_builder()

    generator = builder.add_stage(label='Dev Data Generator')
    trash = builder.add_stage(label='Trash')

    generator >> trash
    pipeline = builder.build(title='Simply the simplest pipeline')

    sdc_executor.add_pipeline(pipeline)
    yield pipeline


# Ensure that we can get bundle generators from the REST interface.
def test_generators_list(sdc_executor):
    generators = sdc_executor.get_bundle_generators()

    assert len(generators) >= 3
    assert generators['PipelineContentGenerator'] is not None
    assert generators['SdcInfoContentGenerator'] is not None
    assert generators['LogContentGenerator'] is not None
    assert generators['PythonLanguage'] is None

# Validate general ability to create new bundle
def test_generate_new_bundle(sdc_executor):
    bundle = sdc_executor.get_bundle()

    # The manifest is created last and contains all the generators
    with bundle.open('generators.properties') as zip_file:
        p = Properties()
        p.load(zip_file)

        assert p.get('com.streamsets.datacollector.bundles.content.PipelineContentGenerator') is not None
        assert p.get('com.streamsets.datacollector.bundles.content.LogContentGenerator') is not None
        assert p.get('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator') is not None
        assert p.get('universe.milky_way.solar_system.earth.europe.czech_republic.working_government') is None

# Pipeline generator
def test_validate_pipeline_generator(pipeline, sdc_executor):
    bundle = sdc_executor.get_bundle(['PipelineContentGenerator'])

    # Manifest must contain the generator
    with bundle.open('generators.properties') as zip_file:
        p = Properties()
        p.load(zip_file)
        assert p.get('com.streamsets.datacollector.bundles.content.PipelineContentGenerator') is not None
        assert p.get('com.streamsets.datacollector.bundles.content.LogContentGenerator') is None
        assert p.get('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator') is None

    # We should have pipeline in the bundle that we should be able to easily import to the SDC again
    with bundle.open('com.streamsets.datacollector.bundles.content.PipelineContentGenerator/{}/pipeline.json'.format(pipeline.id)) as raw:
        bundle_json = json.loads(raw.read().decode())
        bundle_pipeline = sdc_models.Pipeline(pipeline=bundle_json)
        # We need to "reset" the name, otherwise import will fail
        bundle_pipeline.id = str(uuid4())
        sdc_executor.add_pipeline(bundle_pipeline)

    # History have a known structure as the pipeline have not run yet
    with bundle.open('com.streamsets.datacollector.bundles.content.PipelineContentGenerator/{}/history.json'.format(pipeline.id)) as raw:
        bundle_json = json.loads(raw.read().decode())
        bundle_history = sdc_models.History(bundle_json)
        assert len(bundle_history) == 1

        entry = bundle_history.latest
        assert entry['user'] == 'admin'

    # Validate existence of some other files
    assert 'com.streamsets.datacollector.bundles.content.PipelineContentGenerator/{}/info.json'.format(pipeline.id) in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.PipelineContentGenerator/{}/offset.json'.format(pipeline.id) in bundle.namelist()


# Log generator
def test_validate_log_generator(sdc_executor):
    bundle = sdc_executor.get_bundle(['LogContentGenerator'])

    # Manifest must contain the generator
    with bundle.open('generators.properties') as zip_file:
        p = Properties()
        p.load(zip_file)
        assert p.get('com.streamsets.datacollector.bundles.content.LogContentGenerator') is not None
        assert p.get('com.streamsets.datacollector.bundles.content.PipelineContentGenerator') is None
        assert p.get('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator') is None

    # Main log
    with bundle.open('com.streamsets.datacollector.bundles.content.LogContentGenerator//sdc.log') as raw:
        log = raw.read().decode()

        assert "Main - Build info" in log
        assert "Main - Runtime info" in log
        assert "Main - Starting" in log


    # We're fine with just validating that gc log is indeed there
    assert 'com.streamsets.datacollector.bundles.content.LogContentGenerator//gc.log' in bundle.namelist()

# SDC Info generator
def test_validate_sdcinfo_generator(sdc_executor):
    bundle = sdc_executor.get_bundle(['SdcInfoContentGenerator'])

    for name in bundle.namelist():
        print(name)

    # Manifest must contain the generator
    with bundle.open('generators.properties') as zip_file:
        p = Properties()
        p.load(zip_file)
        assert p.get('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator') is not None
        assert p.get('com.streamsets.datacollector.bundles.content.LogContentGenerator') is None
        assert p.get('com.streamsets.datacollector.bundles.content.PipelineContentGenerator') is None

    with bundle.open('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/properties/build.properties') as raw:
        p = Properties()
        p.load(raw)
        assert p.get('version') is not None

    with bundle.open('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/properties/system.properties') as raw:
        p = Properties()
        p.load(raw)
        assert p.get('os.name') is not None
        assert p.get('java.vm.version') is not None
        assert p.get('sdc.hostname') is not None

    with bundle.open('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/conf/sdc.properties') as raw:
        p = Properties()
        p.load(raw)
        assert p.get('https.keystore.password') is not None


    # We're fine with just validating existence of some other files
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/dir_listing/conf.txt' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/dir_listing/resource.txt' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/dir_listing/data.txt' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/dir_listing/log.txt' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/dir_listing/lib_extra.txt' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/dir_listing/stagelibs.txt' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/conf/sdc-log4j.properties' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/conf/dpm.properties' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/conf/ldap-login.conf' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/conf/sdc-security.policy' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/libexec/sdc-env.sh' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/libexec/sdcd-env.sh' in bundle.namelist()
    assert 'com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/runtime/threads.txt' in bundle.namelist()

# Redaction
def test_validate_redaction(sdc_executor):
    bundle = sdc_executor.get_bundle()

    # Redaction in files
    with bundle.open('com.streamsets.datacollector.bundles.content.SdcInfoContentGenerator/conf/sdc.properties') as raw:
        p = Properties()
        p.load(raw)
        assert p.get('https.keystore.password') == 'REDACTED'


