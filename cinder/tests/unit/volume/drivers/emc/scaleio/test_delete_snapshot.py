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
from cinder.tests.unit.fake_snapshot import fake_snapshot_obj
from cinder.tests.unit.volume.drivers.emc import scaleio
from cinder.tests.unit.volume.drivers.emc.scaleio import mocks


class TestDeleteSnapShot(scaleio.TestScaleIODriver):
    """Test cases for ``ScaleIODriver.delete_snapshot()``"""
    STORAGE_POOL_ID = six.text_type('1')
    STORAGE_POOL_NAME = 'SP1'

    PROT_DOMAIN_ID = six.text_type('1')
    PROT_DOMAIN_NAME = 'PD1'
    VOLUME_NOT_FOUND_ERROR = 3

    def setUp(self):
        """Setup a test case environment.

        Creates fake volume and snapshot objects and sets up the required
        API responses.
        """
        super(TestDeleteSnapShot, self).setUp()
        ctx = context.RequestContext('fake', 'fake', auth_token=True)

        self.snapshot = fake_snapshot_obj(ctx)
        self.snapshot_name_2x_enc = urllib.quote(
            urllib.quote(
                self.driver.id_to_base64(self.snapshot.id)
            )
        )

        self.HTTPS_MOCK_RESPONSES = {
            self.RESPONSE_MODE.Valid: {
                'types/Volume/instances/getByName::' +
                self.snapshot_name_2x_enc: self.snapshot.id,
                'instances/Volume::{}/action/removeMappedSdc'.format(
                    self.snapshot.id
                ): self.snapshot.id,
                'instances/Volume::{}/action/removeVolume'.format(
                    self.snapshot.id
                ): self.snapshot.id,
            },
            self.RESPONSE_MODE.BadStatus: {
                'types/Volume/instances/getByName::' +
                self.snapshot_name_2x_enc: self.BAD_STATUS_RESPONSE,
            },
            self.RESPONSE_MODE.Invalid: {
                'types/Volume/instances/getByName::' +
                self.snapshot_name_2x_enc: mocks.MockHTTPSResponse(
                    {
                        'errorCode': self.VOLUME_NOT_FOUND_ERROR,
                        'message': 'Test Delete Invalid Snapshot',
                    }, 400
                ),
            },
        }

    def test_bad_login(self):
        self.set_https_response_mode(self.RESPONSE_MODE.BadStatus)
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.delete_snapshot, self.snapshot)

    def test_delete_invalid_snapshot_force_delete(self):
        self.driver.configuration.set_override('sio_force_delete',
                                               override=True)
        self.set_https_response_mode(self.RESPONSE_MODE.Invalid)
        self.driver.delete_snapshot(self.snapshot)

    def test_delete_invalid_snapshot(self):
        self.set_https_response_mode(self.RESPONSE_MODE.Invalid)
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.delete_snapshot, self.snapshot)

    def test_delete_snapshot(self):
        """Setting the unmap volume before delete flag for tests """
        self.driver.configuration.set_override(
            'sio_unmap_volume_before_deletion',
            override=True)
        self.set_https_response_mode(self.RESPONSE_MODE.Valid)
        self.driver.delete_snapshot(self.snapshot)
