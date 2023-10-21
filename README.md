# peewee-tidb

TiDB dialect for peewee.

## Installation

### Install from PyPI

```bash
pip install peewee-tidb
```

### Install from source

```bash
pip install git+https://github.com/wd0517/peewee-tidb.git@main
```

## Usage

```python
from peewee import *
from peewee_tidb import TidbDatabase

db = TiDBDatabase(
    'peewee',
    host='127.0.0.1',
    port=4000,
    user='root',
    password=''
)
```

### Using `AUTO_RANDOM`

[`AUTO_RANDOM`](https://docs.pingcap.com/tidb/stable/auto-random) is a feature in TiDB that generates unique IDs for a table automatically. It is similar to `AUTO_INCREMENT`, but it can avoid write hotspot in a single storage node caused by TiDB assigning consecutive IDs. It also have some restrictions, please refer to the [documentation](https://docs.pingcap.com/tidb/stable/auto-random#restrictions).

```python
from peewee_tidb import BigAutoRandomField

class MyModel(BaseModel):
    id = BigAutoRandomField(shard_bits=6, range=54, primary_key=True)
```

> **Note**
>
> `AUTO_RANDOM` is supported after TiDB v3.1.0, and only support define with `range` after v6.5.0, so `range` will be ignored if TiDB version is lower than v6.5.0.

### Using `AUTO_ID_CACHE`

[`AUTO_ID_CACHE`](https://docs.pingcap.com/tidb/stable/auto-increment#auto_id_cache) allow users to set the cache size for allocating the auto-increment ID, as you may know, TiDB guarantees that AUTO_INCREMENT values are monotonic (always increasing) on a per-server basis, but its value may appear to jump dramatically if an INSERT operation is performed against another TiDB Server, This is caused by the fact that each server has its own cache which is controlled by `AUTO_ID_CACHE`. But from TiDB v6.4.0, it introduces a centralized auto-increment ID allocating service, you can enable [*MySQL compatibility mode*](https://docs.pingcap.com/tidb/stable/auto-increment#mysql-compatibility-mode) by set `AUTO_ID_CACHE` to `1` when creating a table without losing performance.

To use `AUTO_ID_CACHE` in peewee, you can set `table_settings` in `Meta` class.

```python
class MyModel(BaseModel):
    name = CharField(max_length=32, unique=True)

    class Meta:
        table_settings = "auto_id_cache=1;"
```

### Some Known Issues

- TiDB before v6.6.0 does not support FOREIGN KEY constraints([#18209](https://github.com/pingcap/tidb/issues/18209)).
- TiDB before v6.2.0 does not support SAVEPOINT([#6840](https://github.com/pingcap/tidb/issues/6840)).
