# Metaserver

[![Test](https://github.com/stfwn/savage-metaserver/actions/workflows/test.yml/badge.svg)](https://github.com/stfwn/savage-metaserver/actions/workflows/test.yml)
[![Lint](https://github.com/stfwn/savage-metaserver/actions/workflows/black.yml/badge.svg)](https://github.com/stfwn/savage-metaserver/actions/workflows/black.yml)

## Installation

Install the dependencies in a virtual env:

1. Prepare the env: `python -m venv env`
2. Activate it for you current shell session: `source env/bin/activate`
3. Install modules: `pip install -r requirements.txt`


## Development

1. Activate the virtual env (`source env/bin/activate`)
2. Set `export DEV=true` for verbose SQL logs.
3. Optionally set your `DATABASE_URL` environment variable to the back-end of
   your choosing. Otherwise (and during tests) it's in-memory SQLite.
4. Write tests using the test client in `tests/` and run them with `pytest`. No
   need for throwaway cURL stuff and we end up with some tests too!
5. Implement things in `metaserver/`.
6. GOTO 4.

## Deployment

1. Activate the virtual env (`source env/bin/activate`)
2. Set the `DATABASE_URL` environment variable to a persistent database of your
   choosing. If it's unset the database is in-memory SQLite (gone when the
   process exists).
3. Set the AWS credentials in the environment variables:

   ```bash
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    AWS_DEFAULT_REGION=eu-central-1
   ```

4. Run `make serve` while in the virtual env (`source env/bin/activate`).

## FAQ

### What is the user registeration/login/user proof token flow?

```mermaid

flowchart TD
   s(("User starts the game"))
   p["Game uses credentials to request\nuser proof from metaserver"]
   l["Game shows login screen"]
   r["Game shows registration screen"]
   register["Game registers user with metaserver\nMetaserver sends email confirmation\nGame shows email token entry screen"]
   s -->|Username & password are saved locally| p
   s -->|Username & password are not saved locally| l
   l -->|User does not have an account| r
   l -->|User enters valid auth| p
   p -->|Auth is valid| browser["Game stores user credentials on disk\nGame stores user proof in memory\nUser browses servers"]
   p -->|Auth is invalid| l
   r -->|User enters valid username, display name and password| register
   r -->|User enters invalid data\nMetaserver reports errors to game\nGame reports errors to user| r
   register -->|User enters valid email token| p
   browser -->|User joins server| proof["Game provides user proof to game server"]
   proof -->|User proof is invalid| l
   proof -->|User proof is valid| play(("User plays game"))
   l -->|User enters invalid auth\nMetaserver reports errors to game\nGame reports errors to user| l
```

### I can haz REST spec?

Yes. Follow the installation steps, run the server with `make serve` and visit
`127.0.0.1:8000/docs`. You can even get an `openapi.json` file from
`http://127.0.0.1:8000/openapi.json` and automatically generate a client from
it.
