# MES Printing Server

The MES Printing Server provides GUI for Monash engineering students to submit and monitor 3D model printing jobs.
Printing jobs are executed by calling Octo APIs to 3D printers in the lab, and real time printing data is
synchronized to the OPCUA server, which is the central control of the lab.

MES works with other systems (matrix, storage...) to provide automated printing services:

* students submit printing jobs
* jobs are picked and executed
* finished plates are picked by robots to storage
* students get notified and come to the lab
* models are picked from storage to students

## Architecture

The printing server runs several printer workers.
Each worker maintains a connection to one octoprint server and call octoprint APIs when needed.
Responses of APIs are pushed to the OPCUA server.

## Build

We use [poetry](https://python-poetry.org/) to manage dependencies. Please
first [install poetry](https://python-poetry.org/docs/#installation).

Then, use poetry to install dependencies:

```shell
poetry install
```

## Configuration

Before running the printing server, you need to tell the server about dependencies:

* URL of the database
* URL of the OPCUA server
* path to store uploaded GCode files

You can set environment variables before running the server.

```shell
EXPORT DATABASE_URL='postgresql+asyncpg://username:password@localhost:5432/mes_printing'
EXPORT OPCUA_SERVER_URL='opc.tcp://127.0.0.1:4840'
EXPORT UPLOAD_PATH='/var/lib/mes/gcode-files'
```

Or you can use one env file and set an environment variable of the file path.
See [the example env file](./.env.example)

```shell
EXPORT ENV_FILE='.env'
```

## Mocking

If you use `mock` as URL for an octoprint or OPCUA server,
the program will mock one instead of establishing a connection.

If you don't want to set up a database, you can use `sqlite+aiosqlite:///`
as the database URL, the program will use an in-memory SQLite.

## Run

Run the printer server:

```shell
export ENV_FILE='.env.local'
uvicorn app.main:app
```

## Test

```shell
poetry run pytest tests/
```

## Contribute

TODO: pre-commit hook

Make sure you format files with `black` before submitting a PR.

```shell
poetry run black .
```

## Resources

* [pytest](https://docs.pytest.org/en/7.4.x/)
    * [How to invoke pytest](https://docs.pytest.org/en/7.1.x/how-to/usage.html)
    * [How to use fixtures](https://docs.pytest.org/en/7.4.x/how-to/fixtures.html)
* [SQLAlchemy](https://www.sqlalchemy.org/)
    * [ORM Quick Start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
    * [Writing SELECT statements for ORM Mapped Classes](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html)
    * [asyncio extension](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#synopsis-orm)
    * [state management](https://docs.sqlalchemy.org/en/20/orm/session_state_management.html)
