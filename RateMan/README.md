# Rate Manager

## Setup and Deployment
Clone the repository and create a virtual environment using `venv` module:

```bash
foo@bar scnx-rateman:~$ python3 -m venv .venv/
foo@bar scnx-rateman:~$ source .venv/bin/activate
```

Install/Update `pip` and `setuptools`:
```console
(.venv) foo@bar scnx-rateman:~$ python -m pip install -U pip setuptools
```

Install `rateman` package with the command:
```console
(.venv) foo@bar RateMan:~$ pip install -e .
```
---
>**NOTE:**
>
>The virtual environment can be deactivated using the `deactivate` command.
>```console
>(.venv) foo@bar scnx-py-minstrel:~$ deactivate
>```
---

