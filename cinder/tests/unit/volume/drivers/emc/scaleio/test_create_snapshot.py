# Copyright (c) 2013 - 2015 EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import urllib

import six

from cinder import context
from cinder import exception
from cinder.tests.unit import fake_snapshot
from cinder.tests.unit.volume.drivers.emc import scaleio
from cinder.tests.unit.volume.drivers.emc.scaleio import mocks


class TestCreateSnapShot(scaleio.TestScaleIODriver):
    """Test cases for ``ScaleIODriver.create_snapshot()``"""
    STORAGE_POOL_ID = six.text_type('1')
    STORAGE_POOL_NAME = 'SP1'

    PROT_DOMAIN_ID = six.text_type('1')
    PROT_DOMAIN_NAME = 'PD1'

    def setUp(self):
        """Setup a test case environment.

        Creates fake volume and snapshot objects and sets up the required
        API responses.
        """
        super(TestCreateSnapShot, self).setUp()
        ctx = context.RequestContext('fake', 'fake', auth_token=True)

        self.snapshot = fake_snapshot.fake_snapshot_obj(ctx)
        self.volume_name_2x_enc = urllib.quote(
            urllib.quote(self.driver.id_to_base64(self.snapshot.volume_id))
        )
        self.snapshot_name_2x_enc = urllib.quote(
            urllib.quote(self.driver.id_to_base64(self.snapshot.id))
        )

        self.HTTPS_MOCK_RESPONSES = {
            self.RESPONSE_MODE.Valid: {
                'types/Volume/instances/getByName::' +
                self.volume_name_2x_enc: '"{}"'.format(
                    self.snapshot.volume_id
                ),
                'instances/System/action/snapshotVolumes': self.snapshot.id,
                'types/Volume/instances/getByName::' +
                self.snapshot_name_2x_enc: self.snapshot.id,
            },
            self.RESPONSE_MODE.BadStatus: {
                'types/Volume/instances/getByName::' +
                self.volume_name_2x_enc: self.BAD_STATUS_RESPONSE,
                'types/Volume/instances/getByName::' +
                self.snapshot_name_2x_enc: mocks.MockHTTPSResponse(
                    {
                        'errorCode': 401,
                        'message': 'BadStatus Snapshot Test',
                    }, 401
                ),
            },
            self.RESPONSE_MODE.Invalid: {
                'types/Volume/instances/getByName::' +
                self.volume_name_2x_enc: None,
                'instances/System/action/snapshotVolumes':
                    mocks.MockHTTPSResponse(
                        {
                            'errorCode': 400,
                            'message': 'Invalid Volume Snapshot Test'
                        }, 400
                    ),
            },
        }

    def test_bad_login(self):
        self.set_https_response_mode(self.RESPONSE_MODE.BadStatus)
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_snapshot,
            self.snapshot
        )

    def test_invalid_volume(self):
        self.set_https_response_mode(self.RESPONSE_MODE.Invalid)
        self.assertRaises(
            exception.VolumeBackendAPIException,
            self.driver.create_snapshot,
            self.snapshot
        )

    def test_create_snapshot(self):
        self.set_https_response_mode(self.RESPONSE_MODE.Valid)
        self.driver.create_snapshot(self.snapshot)
