# Copyright (C) 2012 - 2014 EMC Corporation.
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

from migrate import ForeignKeyConstraint
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import ForeignKey, MetaData, String, Table


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    # New table
    consistencygroups = Table(
        'consistencygroups', meta,
        Column('created_at', DateTime(timezone=False)),
        Column('updated_at', DateTime(timezone=False)),
        Column('deleted_at', DateTime(timezone=False)),
        Column('deleted', Boolean(create_constraint=True, name=None)),
        Column('id', String(36), primary_key=True, nullable=False),
        Column('user_id', String(length=255)),
        Column('project_id', String(length=255)),
        Column('host', String(length=255)),
        Column('availability_zone', String(length=255)),
        Column('name', String(length=255)),
        Column('description', String(length=255)),
        Column('volume_type_id', String(length=255)),
        Column('status', String(length=255)),
        mysql_engine='InnoDB',
        mysql_charset='utf8',
    )

    consistencygroups.create()

    # New table
    cgsnapshots = Table(
        'cgsnapshots', meta,
        Column('created_at', DateTime(timezone=False)),
        Column('updated_at', DateTime(timezone=False)),
        Column('deleted_at', DateTime(timezone=False)),
        Column('deleted', Boolean(create_constraint=True, name=None)),
        Column('id', String(36), primary_key=True, nullable=False),
        Column('consistencygroup_id', String(36),
               ForeignKey('consistencygroups.id'),
               nullable=False),
        Column('user_id', String(length=255)),
        Column('project_id', String(length=255)),
        Column('name', String(length=255)),
        Column('description', String(length=255)),
        Column('status', String(length=255)),
        mysql_engine='InnoDB',
        mysql_charset='utf8',
    )

    cgsnapshots.create()

    # Add column to volumes table
    volumes = Table('volumes', meta, autoload=True)
    consistencygroup_id = Column('consistencygroup_id', String(36),
                                 ForeignKey('consistencygroups.id'))
    volumes.create_column(consistencygroup_id)
    volumes.update().values(consistencygroup_id=None).execute()

    # Add column to snapshots table
    snapshots = Table('snapshots', meta, autoload=True)
    cgsnapshot_id = Column('cgsnapshot_id', String(36),
                           ForeignKey('cgsnapshots.id'))

    snapshots.create_column(cgsnapshot_id)
    snapshots.update().values(cgsnapshot_id=None).execute()


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    # Drop column from snapshots table
    if migrate_engine.name == 'mysql':
        # MySQL cannot drop column cgsnapshot_id until the foreign key
        # constraint is removed. So remove the foreign key first, and
        # then drop the column.
        table = Table('snapshots', meta, autoload=True)
        ref_table = Table('snapshots', meta, autoload=True)
        params = {'columns': [table.c['cgsnapshot_id']],
                  'refcolumns': [ref_table.c['id']],
                  'name': 'snapshots_ibfk_1'}

        fkey = ForeignKeyConstraint(**params)
        fkey.drop()

    snapshots = Table('snapshots', meta, autoload=True)
    cgsnapshot_id = snapshots.columns.cgsnapshot_id
    snapshots.drop_column(cgsnapshot_id)

    # Drop column from volumes table
    if migrate_engine.name == 'mysql':
        # MySQL cannot drop column consistencygroup_id until the foreign
        # key constraint is removed. So remove the foreign key first,
        # and then drop the column.
        table = Table('volumes', meta, autoload=True)
        ref_table = Table('volumes', meta, autoload=True)
        params = {'columns': [table.c['consistencygroup_id']],
                  'refcolumns': [ref_table.c['id']],
                  'name': 'volumes_ibfk_1'}

        fkey = ForeignKeyConstraint(**params)
        fkey.drop()

    volumes = Table('volumes', meta, autoload=True)
    consistencygroup_id = volumes.columns.consistencygroup_id
    volumes.drop_column(consistencygroup_id)

    # Drop table
    cgsnapshots = Table('cgsnapshots', meta, autoload=True)
    cgsnapshots.drop()

    # Drop table
    consistencygroups = Table('consistencygroups', meta, autoload=True)
    consistencygroups.drop()
