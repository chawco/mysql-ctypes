from ctypes import pointer, create_string_buffer, string_at

from MySQLdb import cursors, libmysql, converters
from MySQLdb.constants import error_codes


class Connection(object):
    MYSQL_ERROR_MAP = {
        error_codes.PARSE_ERROR: "ProgrammingError",
        error_codes.NO_SUCH_TABLE: "ProgrammingError",

        error_codes.ROW_IS_REFERENCED_2: "IntegrityError",
    }

    from MySQLdb.exceptions import (Warning, Error, InterfaceError,
        DatabaseError, OperationalError, IntegrityError, InternalError,
        ProgrammingError, NotSupportedError)

    def __init__(self, host=None, user=None, db=None, port=0, client_flag=0,
        charset=None, encoders=None, decoders=None, use_unicode=True):

        self._db = libmysql.c.mysql_init(None)
        res = libmysql.c.mysql_real_connect(self._db, host, user, None, db, port, None, client_flag)
        if not res:
            self._exception()

        if encoders is None:
            encoders = converters.DEFAULT_ENCODERS
        if decoders is None:
            decoders = converters.DEFAULT_DECODERS
        self.encoders = encoders
        self.decoders = decoders

        self.autocommit(False)
        if charset is not None:
            res = libmysql.c.mysql_set_character_set(self._db, charset)
            if res:
                self._exception()

    def __del__(self):
        if not self.closed:
            self.close()

    def _check_closed(self):
        if self.closed:
            raise self.InterfaceError("connection already closed")

    def _has_error(self):
        return libmysql.c.mysql_errno(self._db) != 0

    def _exception(self):
        err = libmysql.c.mysql_errno(self._db)
        if not err:
            err_cls = self.InterfaceError
        else:
            if err in self.MYSQL_ERROR_MAP:
                err_cls = getattr(self, self.MYSQL_ERROR_MAP[err])
            elif err < 1000:
                err_cls = self.InternalError
            else:
                err_cls = self.OperationalError
        raise err_cls(err, libmysql.c.mysql_error(self._db))

    @property
    def closed(self):
        return self._db is None

    def close(self):
        self._check_closed()
        libmysql.c.mysql_close(self._db)
        self._db = None

    def autocommit(self, flag):
        self._check_closed()
        res = libmysql.c.mysql_autocommit(self._db, chr(flag))
        if ord(res):
            self._exception()

    def commit(self):
        self._check_closed()
        res = libmysql.c.mysql_commit(self._db, "COMMIT")
        if ord(res):
            self._exception()

    def rollback(self):
        self._check_closed()
        res = libmysql.c.mysql_rollback(self._db)
        if ord(res):
            self._exception()

    def cursor(self, cursor_class=None, encoders=None, decoders=None):
        if cursor_class is None:
            cursor_class = cursors.Cursor
        if encoders is None:
            encoders = self.encoders[:]
        if decoders is None:
            decoders = self.decoders[:]
        return cursor_class(self, encoders=encoders, decoders=decoders)

    def string_literal(self, obj):
        self._check_closed()
        obj = str(obj)
        buf = create_string_buffer(len(obj) * 2)
        length = libmysql.c.mysql_real_escape_string(self._db, buf, obj, len(obj))
        return "'%s'" % string_at(buf, length)

    def character_set_name(self):
        self._check_closed()
        return libmysql.c.mysql_character_set_name(self._db)

    def get_server_info(self):
        self._check_closed()
        return libmysql.c.mysql_get_server_info(self._db)

def connect(*args, **kwargs):
    return Connection(*args, **kwargs)