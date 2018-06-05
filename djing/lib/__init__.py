import socket
import struct
from functools import wraps
from hashlib import sha256
from datetime import timedelta
from collections import Iterator


def ip2int(addr):
    try:
        return struct.unpack("!I", socket.inet_aton(addr))[0]
    except:
        return 0


def int2ip(addr):
    try:
        return socket.inet_ntoa(struct.pack("!I", addr))
    except:
        return ''


def safe_float(fl):
    try:
        return 0.0 if fl is None or fl == '' else float(fl)
    except ValueError:
        return 0.0


def safe_int(i):
    try:
        return 0 if i is None or i == '' else int(i)
    except ValueError:
        return 0


# Предназначен для Django CHOICES чтоб можно было передавать классы вместо просто описания поля,
# классы передавать для того чтоб по значению кода из базы понять какой класс нужно взять для нужной функциональности.
# Например по коду в базе вам нужно определять как считать тариф абонента, что реализовано в возвращаемом классе.
class MyChoicesAdapter(Iterator):
    chs = tuple()
    current_index = 0
    _max_index = 0

    # На вход принимает кортеж кортежей, вложенный из 2х элементов: кода и класса, как: TARIFF_CHOICES
    def __init__(self, choices):
        self._max_index = len(choices)
        self.chs = choices

    def __next__(self):
        if self.current_index >= self._max_index:
            raise StopIteration
        else:
            e = self.chs
            ci = self.current_index
            res = e[ci][0], e[ci][1].description()
            self.current_index += 1
            return res


# Russian localized timedelta
class RuTimedelta(timedelta):
    def __new__(cls, tm):
        if isinstance(tm, timedelta):
            return timedelta.__new__(
                cls,
                days=tm.days,
                seconds=tm.seconds,
                microseconds=tm.microseconds
            )

    def __str__(self):
        # hours, remainder = divmod(self.seconds, 3600)
        # minutes, seconds = divmod(remainder, 60)
        # text_date = "%d:%d" % (
        #    hours,
        #    minutes
        # )
        if self.days > 1:
            ru_days = 'дней'
            if 5 > self.days > 1:
                ru_days = 'дня'
            elif self.days == 1:
                ru_days = 'день'
            # text_date = '%d %s %s' % (self.days, ru_days, text_date)
            text_date = '%d %s' % (self.days, ru_days)
        else:
            text_date = ''
        return text_date


class MultipleException(Exception):
    def __init__(self, err_list):
        if not isinstance(err_list, (list, tuple)):
            raise TypeError
        self.err_list = err_list


class LogicError(Exception):
    pass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


#
# Function for hash auth
#

def calc_hash(data):
    if type(data) is str:
        result_data = data.encode('utf-8')
    else:
        result_data = bytes(data)
    return sha256(result_data).hexdigest()


def check_sign(get_list, sign):
    hashed = '_'.join(get_list)
    my_sign = calc_hash(hashed)
    return sign == my_sign

#
# only one process for function
#


class ProcessLocked(OSError):
    pass


def process_lock(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        s = None
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            # Create an abstract socket, by prefixing it with null.
            s.bind('\0postconnect_djing_lock_func_%s' % fn.__name__)
            return fn(*args, **kwargs)
        except socket.error:
            raise ProcessLocked
        finally:
            if s is not None:
                s.close()
    return wrapped
