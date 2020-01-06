# SchedPresentationTool

This python script uses the SCHED API to:

- Download any files uploaded to a session in Sched.com
- Upload these files to the relevant S3 buckets.

## Usage

### Step 1 - Fork/clone this repo

```
git clone https://github.com/kylekirkby/SchedPresentationTool.git
```

### Step 2 - Add API key to secrets.py

To use this script you will need to create a `secrets.py` file and add your API key from Sched.com (which can be found [here](https://event_name.sched.com/editor/exports/api))

```python3
SCHED_API_KEY="abcdefghijklmnopqrstuvwxyz"
```

### Step3 - Setup your python3 virtualenv

Setup a python3 virtualenv and then install the required python modules using the `requirements.txt` file.

If you haven't already install `virtualenv` then do so with the following.

```bash
sudo pip3 install virtualenv
```

Setup the virtualenv in project folder:

```
$ virtualenv -p python3 venv/
$ source venv/bin/activate
```

Once you've setup the virtualenv tool you can then install the python modules required with the following:

```
$ pip install -r requirements.txt
```
