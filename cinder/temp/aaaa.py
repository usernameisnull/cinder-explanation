from oslo_config import cfg
CONF=cfg.CONF

global_opts = [ cfg.StrOpt('auth_strategy',
           default='keystone',
           choices=['noauth', 'keystone', 'deprecated'],
           help='The strategy to use for auth. Supports noauth, keystone, '
                'and deprecated.')]

CONF.register_opts(global_opts)
print CONF.auth_strategy.split()[:-1]