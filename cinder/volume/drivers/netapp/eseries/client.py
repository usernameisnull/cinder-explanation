# Copyright (c) 2014 NetApp, Inc
# Copyright (c) 2014 Navneet Singh
# Copyright (c) 2015 Alex Meade
# Copyright (c) 2015 Rushil Chugh
# Copyright (c) 2015 Yogesh Kshirsagar
#  All Rights Reserved.
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
"""
Client classes for web services.
"""

import copy
import json
import uuid

from oslo_log import log as logging
from oslo_utils import importutils
import six
from six.moves import urllib

from cinder import exception
from cinder.i18n import _
import cinder.utils as cinder_utils
from cinder.volume.drivers.netapp.eseries import utils

netapp_lib = importutils.try_import('netapp_lib')
if netapp_lib:
    from netapp_lib.api.rest import rest as netapp_restclient


LOG = logging.getLogger(__name__)


class RestClient(object):
    """REST client specific to e-series storage service."""

    def __init__(self, scheme, host, port, service_path, username,
                 password, **kwargs):

        kwargs = kwargs or {}
        self.client = netapp_restclient.WebserviceClient(scheme, host, port,
                                                         service_path,
                                                         username, password,
                                                         **kwargs)
        self._system_id = kwargs.get('system_id')
        self._content_type = kwargs.get('content_type') or 'json'

    def set_system_id(self, system_id):
        """Set the storage system id."""
        self._system_id = system_id

    def get_system_id(self):
        """Get the storage system id."""
        return getattr(self, '_system_id', None)

    def _get_resource_url(self, path, use_system=True, **kwargs):
        """Creates end point url for rest service."""
        kwargs = kwargs or {}
        if use_system:
            if not self._system_id:
                raise exception.NotFound(_('Storage system id not set.'))
            kwargs['system-id'] = self._system_id
        path = path.format(**kwargs)
        if not self.client._endpoint.endswith('/'):
            self.client._endpoint = '%s/' % self.client._endpoint
        return urllib.parse.urljoin(self.client._endpoint, path.lstrip('/'))

    def _invoke(self, method, path, data=None, use_system=True,
                timeout=None, verify=False, **kwargs):
        """Invokes end point for resource on path."""
        url = self._get_resource_url(path, use_system, **kwargs)
        if self._content_type == 'json':
            headers = {'Accept': 'application/json',
                       'Content-Type': 'application/json'}
            if cinder_utils.TRACE_API:
                self._log_http_request(method, url, headers, data)
            data = json.dumps(data) if data else None
            res = self.client.invoke_service(method, url, data=data,
                                             headers=headers,
                                             timeout=timeout, verify=verify)
            res_dict = res.json() if res.text else None

            if cinder_utils.TRACE_API:
                self._log_http_response(res.status_code, dict(res.headers),
                                        res_dict)

            self._eval_response(res)
            return res_dict
        else:
            raise exception.NetAppDriverException(
                _("Content type not supported."))

    def _to_pretty_dict_string(self, data):
        """Convert specified dict to pretty printed string."""
        return json.dumps(data, sort_keys=True,
                          indent=2, separators=(',', ': '))

    def _log_http_request(self, verb, url, headers, body):
        scrubbed_body = copy.deepcopy(body)
        if scrubbed_body:
            if 'password' in scrubbed_body:
                scrubbed_body['password'] = "****"
            if 'storedPassword' in scrubbed_body:
                scrubbed_body['storedPassword'] = "****"

        params = {'verb': verb, 'path': url,
                  'body': self._to_pretty_dict_string(scrubbed_body) or "",
                  'headers': self._to_pretty_dict_string(headers)}
        LOG.debug("Invoking ESeries Rest API, Request:\n"
                  "HTTP Verb: %(verb)s\n"
                  "URL Path: %(path)s\n"
                  "HTTP Headers:\n"
                  "%(headers)s\n"
                  "Body:\n"
                  "%(body)s\n", (params))

    def _log_http_response(self, status, headers, body):
        params = {'status': status,
                  'body': self._to_pretty_dict_string(body) or "",
                  'headers': self._to_pretty_dict_string(headers)}
        LOG.debug("ESeries Rest API, Response:\n"
                  "HTTP Status Code: %(status)s\n"
                  "HTTP Headers:\n"
                  "%(headers)s\n"
                  "Body:\n"
                  "%(body)s\n", (params))

    def _eval_response(self, response):
        """Evaluates response before passing result to invoker."""
        status_code = int(response.status_code)
        # codes >= 300 are not ok and to be treated as errors
        if status_code >= 300:
            # Response code 422 returns error code and message
            if status_code == 422:
                msg = _("Response error - %s.") % response.text
            else:
                msg = _("Response error code - %s.") % status_code
            raise exception.NetAppDriverException(msg)

    def create_volume(self, pool, label, size, unit='gb', seg_size=0):
        """Creates volume on array."""
        path = "/storage-systems/{system-id}/volumes"
        data = {'poolId': pool, 'name': label, 'sizeUnit': unit,
                'size': int(size), 'segSize': seg_size}
        return self._invoke('POST', path, data)

    def delete_volume(self, object_id):
        """Deletes given volume from array."""
        path = "/storage-systems/{system-id}/volumes/{object-id}"
        return self._invoke('DELETE', path, **{'object-id': object_id})

    def list_volumes(self):
        """Lists all volumes in storage array."""
        path = "/storage-systems/{system-id}/volumes"
        return self._invoke('GET', path)

    def list_volume(self, object_id):
        """List given volume from array."""
        path = "/storage-systems/{system-id}/volumes/{object-id}"
        return self._invoke('GET', path, **{'object-id': object_id})

    def update_volume(self, object_id, label):
        """Renames given volume in array."""
        path = "/storage-systems/{system-id}/volumes/{object-id}"
        data = {'name': label}
        return self._invoke('POST', path, data, **{'object-id': object_id})

    def get_volume_mappings(self):
        """Creates volume mapping on array."""
        path = "/storage-systems/{system-id}/volume-mappings"
        return self._invoke('GET', path)

    def get_volume_mappings_for_volume(self, volume):
        """Gets all host mappings for given volume from array."""
        mappings = self.get_volume_mappings() or []
        host_maps = filter(lambda x: x.get('volumeRef') == volume['volumeRef'],
                           mappings)
        return host_maps

    def get_volume_mappings_for_host(self, host_ref):
        """Gets all volume mappings for given host from array."""
        mappings = self.get_volume_mappings() or []
        host_maps = filter(lambda x: x.get('mapRef') == host_ref, mappings)
        return host_maps

    def get_volume_mappings_for_host_group(self, hg_ref):
        """Gets all volume mappings for given host group from array."""
        mappings = self.get_volume_mappings() or []
        hg_maps = filter(lambda x: x.get('mapRef') == hg_ref, mappings)
        return hg_maps

    def create_volume_mapping(self, object_id, target_id, lun):
        """Creates volume mapping on array."""
        path = "/storage-systems/{system-id}/volume-mappings"
        data = {'mappableObjectId': object_id, 'targetId': target_id,
                'lun': lun}
        return self._invoke('POST', path, data)

    def delete_volume_mapping(self, map_object_id):
        """Deletes given volume mapping from array."""
        path = "/storage-systems/{system-id}/volume-mappings/{object-id}"
        return self._invoke('DELETE', path, **{'object-id': map_object_id})

    def move_volume_mapping_via_symbol(self, map_ref, to_ref, lun_id):
        """Moves a map from one host/host_group object to another."""

        path = "/storage-systems/{system-id}/symbol/moveLUNMapping"
        data = {'lunMappingRef': map_ref,
                'lun': int(lun_id),
                'mapRef': to_ref}
        return_code = self._invoke('POST', path, data)
        if return_code == 'ok':
            return {'lun': lun_id}
        msg = _("Failed to move LUN mapping.  Return code: %s") % return_code
        raise exception.NetAppDriverException(msg)

    def list_hardware_inventory(self):
        """Lists objects in the hardware inventory."""
        path = "/storage-systems/{system-id}/hardware-inventory"
        return self._invoke('GET', path)

    def list_target_wwpns(self):
        """Lists the world-wide port names of the target."""
        inventory = self.list_hardware_inventory()
        fc_ports = inventory.get("fibrePorts", [])
        wwpns = [port['portName'] for port in fc_ports]
        return wwpns

    def create_host_group(self, label):
        """Creates a host group on the array."""
        path = "/storage-systems/{system-id}/host-groups"
        data = {'name': label}
        return self._invoke('POST', path, data)

    def get_host_group(self, host_group_ref):
        """Gets a single host group from the array."""
        path = "/storage-systems/{system-id}/host-groups/{object-id}"
        try:
            return self._invoke('GET', path, **{'object-id': host_group_ref})
        except exception.NetAppDriverException:
            raise exception.NotFound(_("Host group with ref %s not found") %
                                     host_group_ref)

    def get_host_group_by_name(self, name):
        """Gets a single host group by name from the array."""
        host_groups = self.list_host_groups()
        matching = [host_group for host_group in host_groups
                    if host_group['label'] == name]
        if len(matching):
            return matching[0]
        raise exception.NotFound(_("Host group with name %s not found") % name)

    def list_host_groups(self):
        """Lists host groups on the array."""
        path = "/storage-systems/{system-id}/host-groups"
        return self._invoke('GET', path)

    def list_hosts(self):
        """Lists host objects in the system."""
        path = "/storage-systems/{system-id}/hosts"
        return self._invoke('GET', path)

    def create_host(self, label, host_type, ports=None, group_id=None):
        """Creates host on array."""
        path = "/storage-systems/{system-id}/hosts"
        data = {'name': label, 'hostType': host_type}
        data.setdefault('groupId', group_id if group_id else None)
        data.setdefault('ports', ports if ports else None)
        return self._invoke('POST', path, data)

    def create_host_with_ports(self, label, host_type, port_ids,
                               port_type='iscsi', group_id=None):
        """Creates host on array with given port information."""
        if port_type == 'fc':
            port_ids = [six.text_type(wwpn).replace(':', '')
                        for wwpn in port_ids]
        ports = []
        for port_id in port_ids:
            port_label = utils.convert_uuid_to_es_fmt(uuid.uuid4())
            port = {'type': port_type, 'port': port_id, 'label': port_label}
            ports.append(port)
        return self.create_host(label, host_type, ports, group_id)

    def update_host(self, host_ref, data):
        """Updates host type for a given host."""
        path = "/storage-systems/{system-id}/hosts/{object-id}"
        return self._invoke('POST', path, data, **{'object-id': host_ref})

    def get_host(self, host_ref):
        """Gets a single host from the array."""
        path = "/storage-systems/{system-id}/hosts/{object-id}"
        return self._invoke('GET', path, **{'object-id': host_ref})

    def update_host_type(self, host_ref, host_type):
        """Updates host type for a given host."""
        data = {'hostType': host_type}
        return self.update_host(host_ref, data)

    def set_host_group_for_host(self, host_ref, host_group_ref=utils.NULL_REF):
        """Sets or clears which host group a host is in."""
        data = {'groupId': host_group_ref}
        self.update_host(host_ref, data)

    def list_host_types(self):
        """Lists host types in storage system."""
        path = "/storage-systems/{system-id}/host-types"
        return self._invoke('GET', path)

    def list_snapshot_groups(self):
        """Lists snapshot groups."""
        path = "/storage-systems/{system-id}/snapshot-groups"
        return self._invoke('GET', path)

    def create_snapshot_group(self, label, object_id, storage_pool_id,
                              repo_percent=99, warn_thres=99, auto_del_limit=0,
                              full_policy='failbasewrites'):
        """Creates snapshot group on array."""
        path = "/storage-systems/{system-id}/snapshot-groups"
        data = {'baseMappableObjectId': object_id, 'name': label,
                'storagePoolId': storage_pool_id,
                'repositoryPercentage': repo_percent,
                'warningThreshold': warn_thres,
                'autoDeleteLimit': auto_del_limit, 'fullPolicy': full_policy}
        return self._invoke('POST', path, data)

    def delete_snapshot_group(self, object_id):
        """Deletes given snapshot group from array."""
        path = "/storage-systems/{system-id}/snapshot-groups/{object-id}"
        return self._invoke('DELETE', path, **{'object-id': object_id})

    def create_snapshot_image(self, group_id):
        """Creates snapshot image in snapshot group."""
        path = "/storage-systems/{system-id}/snapshot-images"
        data = {'groupId': group_id}
        return self._invoke('POST', path, data)

    def delete_snapshot_image(self, object_id):
        """Deletes given snapshot image in snapshot group."""
        path = "/storage-systems/{system-id}/snapshot-images/{object-id}"
        return self._invoke('DELETE', path, **{'object-id': object_id})

    def list_snapshot_images(self):
        """Lists snapshot images."""
        path = "/storage-systems/{system-id}/snapshot-images"
        return self._invoke('GET', path)

    def create_snapshot_volume(self, image_id, label, base_object_id,
                               storage_pool_id,
                               repo_percent=99, full_thres=99,
                               view_mode='readOnly'):
        """Creates snapshot volume."""
        path = "/storage-systems/{system-id}/snapshot-volumes"
        data = {'snapshotImageId': image_id, 'fullThreshold': full_thres,
                'storagePoolId': storage_pool_id,
                'name': label, 'viewMode': view_mode,
                'repositoryPercentage': repo_percent,
                'baseMappableObjectId': base_object_id,
                'repositoryPoolId': storage_pool_id}
        return self._invoke('POST', path, data)

    def delete_snapshot_volume(self, object_id):
        """Deletes given snapshot volume."""
        path = "/storage-systems/{system-id}/snapshot-volumes/{object-id}"
        return self._invoke('DELETE', path, **{'object-id': object_id})

    def list_storage_pools(self):
        """Lists storage pools in the array."""
        path = "/storage-systems/{system-id}/storage-pools"
        return self._invoke('GET', path)

    def get_storage_pool(self, volume_group_ref):
        """Get storage pool information from the array."""
        path = "/storage-systems/{system-id}/storage-pools/{object-id}"
        return self._invoke('GET', path, **{'object-id': volume_group_ref})

    def list_drives(self):
        """Lists drives in the array."""
        path = "/storage-systems/{system-id}/drives"
        return self._invoke('GET', path)

    def list_storage_systems(self):
        """Lists managed storage systems registered with web service."""
        path = "/storage-systems"
        return self._invoke('GET', path, use_system=False)

    def list_storage_system(self):
        """List current storage system registered with web service."""
        path = "/storage-systems/{system-id}"
        return self._invoke('GET', path)

    def register_storage_system(self, controller_addresses, password=None,
                                wwn=None):
        """Registers storage system with web service."""
        path = "/storage-systems"
        data = {'controllerAddresses': controller_addresses}
        data.setdefault('wwn', wwn if wwn else None)
        data.setdefault('password', password if password else None)
        return self._invoke('POST', path, data, use_system=False)

    def update_stored_system_password(self, password):
        """Update array password stored on web service."""
        path = "/storage-systems/{system-id}"
        data = {'storedPassword': password}
        return self._invoke('POST', path, data)

    def create_volume_copy_job(self, src_id, tgt_id, priority='priority4',
                               tgt_wrt_protected='true'):
        """Creates a volume copy job."""
        path = "/storage-systems/{system-id}/volume-copy-jobs"
        data = {'sourceId': src_id, 'targetId': tgt_id,
                'copyPriority': priority,
                'targetWriteProtected': tgt_wrt_protected}
        return self._invoke('POST', path, data)

    def control_volume_copy_job(self, obj_id, control='start'):
        """Controls a volume copy job."""
        path = ("/storage-systems/{system-id}/volume-copy-jobs-control"
                "/{object-id}?control={String}")
        return self._invoke('PUT', path, **{'object-id': obj_id,
                                            'String': control})

    def list_vol_copy_job(self, object_id):
        """List volume copy job."""
        path = "/storage-systems/{system-id}/volume-copy-jobs/{object-id}"
        return self._invoke('GET', path, **{'object-id': object_id})

    def delete_vol_copy_job(self, object_id):
        """Delete volume copy job."""
        path = "/storage-systems/{system-id}/volume-copy-jobs/{object-id}"
        return self._invoke('DELETE', path, **{'object-id': object_id})
