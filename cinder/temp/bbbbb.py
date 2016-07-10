#!/usr/bin/env python
# encoding: utf-8
from oslo_config import cfg
import oslo_messaging as messaging
import logging
import eventlet

eventlet.monkey_patch()
logging.basicConfig()
log = logging.getLogger()
log.addHandler(logging.StreamHandler())
log.setLevel(logging.INFO)


class NotificationHandler(object):
    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        if publisher_id == 'testing':
            log.info('Handled')
            return messaging.NotificationResult.HANDLED


log.info('Configuring connection')
transport_url = 'rabbit://testing:test@127.0.0.1:5672/'
transport = messaging.get_transport(cfg.CONF, transport_url)

targets = [messaging.Target(topic='monitor')]
endpoints = [NotificationHandler()]

server = messaging.get_notification_listener(transport, targets, endpoints, allow_requeue=True, executor='eventlet')
log.info('Starting up server')
server.start()
log.info('Waiting for something')
server.wait()
