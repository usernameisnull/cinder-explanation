# from oslo_service import wsgi
from oslo_messaging import get_transport
from oslo_messaging import get_rpc_server

class instance_deco(object):
    def __init__(object, *args, **kwargs):
        print 'in instance_deco.__init__', args, kwargs

    def xx(self):
        print "in instance_deco.xx"

    def __call__(self, f):
        f()
        print 'in instance_deco.__call__', f.__name__


def decofate_with_args(*args, **kwargs):
    print 'in decofate_with_args, args: %s, kwargs: %s ' % (args, kwargs)
    return instance_deco()


class decorat_(object):
    def __init__(self, func):
        self._func = func
        print 'func: %s' % func.__name__

    def __call__(self, *args, **kwargs):
        print 'before invoke %s' % self._func.__name__
        print args, kwargs
        return self._func(*args, **kwargs)


# @decofate_with_args(1, 2, 3, a=4, b=5)
# def test():
#     print 'hello, world!'

def action(name):
    """Mark a function as an action.

    The given name will be taken as the action key in the body.

    This is also overloaded to allow extensions to provide
    non-extending definitions of create and delete operations.
    """

    def decorator(func):
        func.wsgi_action = name
        return func

    return decorator


@action('new_attribute')
def hello_world():
    print "hello, world"


# hello_world()
print hello_world.wsgi_action

from routes import Mapper

map = Mapper()
a = object()
print a
map.resource('message', 'messages', controller=a)
result1 = map.match('/messages')
print result1
