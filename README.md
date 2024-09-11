# Aurora

Aurora is an open source project to collect and register data.
It is focused mainly on performance and security.

## Local development instructions

Dependencies:
- *Mandatory*: A [Postgres](https://www.postgresql.org/) DB (default 'aurora' on port 5432,
  override with DATABASE_URL environment variable)
- *Mandatory*: [Redis](https://redis.io/)
- *Mandatory*: [pdm](https://pdm-project.org/en/latest/)
- *Optional*: [direnv](https://direnv.net/)

### Virtualenv

For a quick setup first install pdm and then follow
following steps:

```shell
# Create the virtual env in local .venv folder
pdm venv create

# Configure to use the local venv  
pdm use
```

If you are using direnv then create a .envrc file:

```shell
export PYTHONPATH="$PYTHONPATH:./src:./tests/extras"
eval $(pdm venv activate)
unset PS1
```

Hint: if you are using a .env file for your environment variables the first line of your .envrc should be:
```shell
dotenv
```


### Run the code 

```shell
  python manage.py runserver
````

## using docker-composer

For the first time you need to run in root project directory

```shell
./manage env --comment --defaults > .env
docker-compose build
docker-compose up
```

each next time

```shell
docker-compose up
```
