import re
import warnings

from peewee import (
    MySQLDatabase,
    Node,
    NodeList,
    ensure_entity,
    fn,
    CommaNodeList,
    Field,
    SQL,
    Value,
    basestring,
    BigAutoField,
)
from playhouse.pool import PooledDatabase
from playhouse.db_url import register_database

__version__ = "0.1.1"
__all__ = (
    "TiDBDatabase",
    "PooledTiDBDatabase",
    "BigAutoRandomField",
    "register_tidb_to_peewee",
)


class BigAutoRandomField(BigAutoField):
    field_type = "BIGAUTO_RANDOM"

    def __init__(self, shard_bits=5, range=64, *args, **kwargs):
        self.shard_bits = shard_bits
        self.range = range
        super(BigAutoRandomField, self).__init__(*args, **kwargs)

    def get_modifiers(self):
        db = self.model._meta.database
        if db.server_version < (6, 3, 0):
            # TiDB < 6.3 doesn't support define AUTO_RANDOM with range
            return [self.shard_bits]
        else:
            return [self.shard_bits, self.range]


class TiDBDatabase(MySQLDatabase):
    field_types = {
        **MySQLDatabase.field_types,
        "BIGAUTO_RANDOM": "BIGINT AUTO_RANDOM",
    }

    def _set_server_version(self, conn):
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        self.server_version = self._extract_server_version(version)

    def _extract_server_version(self, version):
        version = version.lower()
        match_obj = re.search(r"tidb-v(\d+\.\d+\.\d+)", version)
        if match_obj is not None:
            return tuple(int(num) for num in match_obj.groups()[0].split("."))

        warnings.warn('Unable to determine TiDB version: "%s"' % version)
        return (0, 0, 0)

    def conflict_update(self, on_conflict, query):
        # Copy from MySQLDatabase.conflict_update.
        # Because MySQLDatabase.conflict determines the value function by
        # mysql's version, but TiDB only supports `fn.VALUES`
        if (
            on_conflict._where
            or on_conflict._conflict_target
            or on_conflict._conflict_constraint
        ):
            raise ValueError(
                "MySQL does not support the specification of "
                "where clauses or conflict targets for conflict "
                "resolution."
            )

        updates = []
        if on_conflict._preserve:
            for column in on_conflict._preserve:
                entity = ensure_entity(column)
                expression = NodeList(
                    (ensure_entity(column), SQL("="), fn.VALUES(entity))
                )
                updates.append(expression)

        if on_conflict._update:
            for k, v in on_conflict._update.items():
                if not isinstance(v, Node):
                    # Attempt to resolve string field-names to their respective
                    # field object, to apply data-type conversions.
                    if isinstance(k, basestring):
                        k = getattr(query.table, k)
                    if isinstance(k, Field):
                        v = k.to_value(v)
                    else:
                        v = Value(v, unpack=False)
                updates.append(NodeList((ensure_entity(k), SQL("="), v)))

        if updates:
            return NodeList((SQL("ON DUPLICATE KEY UPDATE"), CommaNodeList(updates)))


class PooledTiDBDatabase(PooledDatabase, TiDBDatabase):
    def _is_closed(self, conn):
        try:
            conn.ping(False)
        except:  # noqa: E722
            return True
        else:
            return False


def register_tidb_to_peewee():
    register_database(TiDBDatabase, "tidb")
    register_database(PooledTiDBDatabase, "tidb+pool")
