# Contributing Guide

## Fork

[Fork this repo](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo)
under your
account, [clone](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#cloning-your-forked-repository)
to your local machine and configure Git account.

```shell
git config user.name "John Doe"
git config user.email "johndoe@example.com"
```

## Install pre-commit hooks

[Pre-commit hooks](https://pre-commit.com/) such as linter and formatter will run automatically before commiting.

```shell
pre-commit install
```

## Code

Open a new [branch](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging) and finish your
feature/bugfix.

Also add test cases to demonstrate your update is bug free.
Please check [Pytest](https://docs.pytest.org/en/8.1.x/), [pytest-asyncio](https://pypi.org/project/pytest-asyncio/)
and existing test cases under `tests/` folder.

## Unit Test

Make sure all tests are passed before pushing to remote.

```shell
poetry run pytest
```

## Linting

Make sure code passes all static type checking.

```shell
poetry run mypy src/
```

## Submit a PR

[Commit](https://git-scm.com/docs/git-commit) your update and [push](https://git-scm.com/docs/git-push) to your remote
repo.
Then [create a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)
from your new branch to main branch of the upstream repo.
Please also include a brief introduction of your update in your PR.
