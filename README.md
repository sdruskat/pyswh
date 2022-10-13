<!--
SPDX-FileCopyrightText: 2022 Stephan Druskat <pyswh@sdruskat.net>

SPDX-License-Identifier: CC-BY-4.0
-->

# *pyswh* - a Python wrapper library for the Software Heritage API

*pyswh* aims to wrap interactions with the [Software Heritage REST API](https://archive.softwareheritage.org/api/1/) into a comfortable Python API.

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=sdruskat_pyswh&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=sdruskat_pyswh)
[![Docs build](https://readthedocs.org/projects/pyswh/badge/?version=latest)](https://pyswh.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/sdruskat/pyswh/branch/develop/graph/badge.svg?token=8IDQ3BXC4M)](https://codecov.io/gh/sdruskat/pyswh)
[![REUSE status](https://api.reuse.software/badge/github.com/sdruskat/pyswh)](https://api.reuse.software/info/github.com/sdruskat/pyswh)

## Getting started

Install `pyswh` via pip:

```bash
pip install pyswh
```

Include `pyswh` in your project by adding a respective dependency to your project, e.g.,

```bash
# requirements.txt
pyswh==0.1.0
```

```toml
# Poetry pyproject.toml
[tool.poetry.dependencies]
pyswh = "^0.1.0"
```

You can now use `pyswh`:

```python
from pyswh import swh
from pyswh import errors as swh_errors

try:
    swh.save('https://github.com/sdruskat/pyswh', False, 'SWH-API-AUTH-TOKEN')
except swh_errors.SwhSaveError as sse:
    raise sse
```

Refer to the [complete documentation](https://pyswh.readthedocs.io/en/latest/) to learn more about using `pyswh`.

## Set up for development

**Requirements:** Python >= 3.10.0.

1. Install [Poetry](https://python-poetry.org).

2. Clone the repository:

```bash
git clone git@github.com:sdruskat/pyswh.git
```

3. Create a virtual environment in `.venv`:
```bash
python3.10 -m venv .venv 
```

4. Activate the Poetry shell and install project:

```bash
poetry shell
poetry install
```

## Testing

`pyswh` uses `pytest` for testing. To run all tests, do:

```bash
poetry shell
poetry run pytest test/
```

## Building documentation locally

Initialize the Poetry virtual environment with `poetry shell`, go into the `docs/` folder and run `make html`.

## Licensing

See [`LICENSE.md`](LICENSE.md)