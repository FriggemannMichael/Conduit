# Conduit

## Backend development

[!Catution] backend uses Django 1.10.5, which only runs on Python 3.6. Python 3.6 is
end-of-life since December 2021, so it is not installed locally. Development
runs in a dev container instead (`backend/Dockerfile.dev`, Python 3.6 + uv),
which uses the same base image as the production image.

Build the dev image:

    docker build -f backend/Dockerfile.dev -t conduit-backend-dev backend

Run the tests:

    docker run --rm -v "${PWD}\backend:/app" conduit-backend-dev

Run the linter:

    uvx ruff check --no-cache backend
