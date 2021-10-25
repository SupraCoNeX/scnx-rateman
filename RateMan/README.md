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

Change directory to RateMan and install dependencies from requirements.txt:
```console
(.venv) foo@bar scnx-rateman:~$ cd RateMan; pip install -r requirements.txt
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

## Telegram Bot for Notification

### How to configure rateman with your telegram bot?

The token of your telegram bot should be added to the `keys.json` file which is inside the `docs` directory. The json file consists of two parameters: "bot_token" and "chat_ids". 

```json
{
    "bot_token": "Your telegram bot token",
    "chat_ids": ["Chat ids"] 
}
```

As the values suggest, replace `Your telegram bot token` with your telegram bot's token and `Chat ids` with chat ids. The **"chat_ids"** is a list of chat ids in string literal.

For multiple chat ids, the **"chat_ids"** could look like:

```json
{
    "bot_token": "bot_token",
    "chat_ids": ["id1", "id2", "id3"] 
}
```

### What notifications does the telegram bot send?

The telegram bot, for each experiment, sends two notification, one at the start and one at the end, to the chat ids listed in `docs/keys.json`. The current structure of the notification are:

**Start Notification**

~~~
/mnt/foo/Experiments/bar:

Experiment Started at 2021-10-07 17:23:44.282566
Time duration: 100.0 seconds
AP List: /mnt/foo/ap_lists/ap_list_sample.csv
~~~


**End Notification**

~~~
/mnt/foo/Experiments/bar:

Experiment Finished at 2021-10-07 17:25:24.592052
Data for the AP List, /mnt/foo/ap_lists/ap_list_sample.csv, has been successfully collected for 100.0 seconds!
~~~

The filepath, at the top of each notification, is where the experiment data and figures will be saved. The notification also shows the duration of the experiment along with the file used for list of access points. In case an experiment didn't run for the specified time duration, the bot will send an error notification.

**Error Notification**

~~~
/mnt/foo/Experiments/bar:

Experiment Finished at 2021-10-07 17:25:24.592052
Error: RateMan stopped before the specified time duration of 100.0!
RateMan was fetching data from /mnt/foo/ap_lists/ap_list_sample.csv

~~~

### How to enable notifications?

Please specify the `--notify` flag when running an experiment to enable notifications from your telegram bot.