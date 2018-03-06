# grabbit
Get grabby with file trees

## Overview

Grabbit is a lightweight Python 3 package for simple queries over filenames within a project. It's geared towards projects or applications with highly structured filenames that allow useful queries to be performed without having to inspect the file metadata or contents.

## Status
* [![Build Status](https://travis-ci.org/grabbles/grabbit.svg?branch=master)](https://travis-ci.org/grabbles/grabbit)
* [![Coverage Status](https://coveralls.io/repos/github/grabbles/grabbit/badge.svg?branch=master)](https://coveralls.io/github/grabbles/grabbit?branch=master)

## Installation

```
$ pip install grabbit
```

Or, if you like to (a) do things the hard way or (b) live on the bleeding edge:

```
$ git clone https://github.com/grabbles/grabbit
$ cd grabbit
$ python setup.py develop
```

## Quickstart

Suppose we've already defined (or otherwise obtained) a grabbit JSON configuration file that looks [like this](https://github.com/grabbles/grabbit/blob/master/grabbit/tests/specs/test.json). And suppose we also have some kind of many-filed project that needs managing. Maybe it looks like this:

```
├── dataset_description.json
├── participants.tsv
├── sub-01
│   ├── ses-1
│   │   ├── anat
│   │   │   ├── sub-01_ses-1_T1map.nii.gz
│   │   │   └── sub-01_ses-1_T1w.nii.gz
│   │   ├── fmap
│   │   │   ├── sub-01_ses-1_run-1_magnitude1.nii.gz
│   │   │   ├── sub-01_ses-1_run-1_magnitude2.nii.gz
│   │   │   ├── sub-01_ses-1_run-1_phasediff.json
│   │   │   ├── sub-01_ses-1_run-1_phasediff.nii.gz
│   │   │   ├── sub-01_ses-1_run-2_magnitude1.nii.gz
│   │   │   ├── sub-01_ses-1_run-2_magnitude2.nii.gz
│   │   │   ├── sub-01_ses-1_run-2_phasediff.json
│   │   │   └── sub-01_ses-1_run-2_phasediff.nii.gz
│   │   ├── func
│   │   │   ├── sub-01_ses-1_task-rest_acq-fullbrain_run-1_bold.nii.gz
│   │   │   ├── sub-01_ses-1_task-rest_acq-fullbrain_run-1_physio.tsv.gz
│   │   │   ├── sub-01_ses-1_task-rest_acq-fullbrain_run-2_bold.nii.gz
│   │   │   ├── sub-01_ses-1_task-rest_acq-fullbrain_run-2_physio.tsv.gz
│   │   │   ├── sub-01_ses-1_task-rest_acq-prefrontal_bold.nii.gz
│   │   │   └── sub-01_ses-1_task-rest_acq-prefrontal_physio.tsv.gz
│   │   └── sub-01_ses-1_scans.tsv
│   ├── ses-2
│   │   ├── fmap
│   │   │   ├── sub-01_ses-2_run-1_magnitude1.nii.gz
│   │   │   ├── sub-01_ses-2_run-1_magnitude2.nii.gz
│   │   │   ├── sub-01_ses-2_run-1_phasediff.json
│   │   │   ├── sub-01_ses-2_run-1_phasediff.nii.gz
│   │   │   ├── sub-01_ses-2_run-2_magnitude1.nii.gz
│   │   │   ├── sub-01_ses-2_run-2_magnitude2.nii.gz
│   │   │   ├── sub-01_ses-2_run-2_phasediff.json
│   │   │   └── sub-01_ses-2_run-2_phasediff.nii.gz
```

We can initialize a grabbit Layout object like so:

```python
from grabbit import Layout
config_file = 'my_config.json'
project_root = '/my_project' 
layout = Layout(project_root, config_file)
```

The `Layout` instance is a lightweight container for all of the files in the project directory. It automatically detects any entities found in the file paths, and allows us to perform simple but relatively powerful queries over the file tree. The entities are defined in a JSON configuration file (or explicitly added via add_entity() calls). For example, we might have "subject", "session", "run", and "type" entities defined as follows:

```json
entities = [
    {
      "name": "subject",
      "pattern": "(sub-\\d+)",
      "directory": "{{root}}/{subject}",
    },
    {
      "name": "session",
      "pattern": "(ses-\\d)",
      "directory": "{{root}}/{subject}/{session}",
    },
    {
      "name": "run",
      "pattern": "(run-\\d+)"
    },
    {
      "name": "type",
      "pattern": ".*_(.*?)\\."
    }
]
```

In each case, the "name" key defines the name of the entity, and the "pattern" key defines the search path within each file. These are the only two mandatory keys. Notice that we use regex groups to define the unique ID to capture for each entity. This allows us to match files to entities, but keep only part of the match as the unique identifier (e.g., if we wanted to detect 'sub-05' as a subject, but keep only '05' as the subject ID, we could use the pattern "sub-(\\d+)").

For entities where each instance is associated with a directory (e.g., each subject's data is contained in a single directory), we can also specify the full directory path. Notice that we can refer to other entities within the path--e.g., "{{root}}/{subject}/{session}" will substitute unique subject and session IDs when they are detected ({{root}} is a magic constant that is always replaced with the root directory of the project specified at Layout initialization).

### Getting unique values and counts
Once we've initialized a `Layout`, we can do simple things like counting and listing all unique values of a given entity:

```python
>>> layout.unique('subject')
['sub-09', 'sub-05', 'sub-08', 'sub-01', 'sub-02', 'sub-06', 'sub-04', 'sub-03', 'sub-07', 'sub-10']

>>> layout.count('run')
2
```

### Querying and filtering
Counting is kind of trivial; everyone can count! More usefully, we can run simple logical queries, returning the results in a variety of formats:

```python
>>> files = layout.get(subject='sub-0[12]', run=1, extensions='.nii.gz')
>>> files[0]
File(filename='sub-02/ses-1/fmap/sub-02_ses-1_run-1_magnitude1.nii.gz', subject='sub-02', run='run-1', session='ses-1', type='magnitude1')

>>> [f.path for f in files]
['sub-02/ses-2/fmap/sub-02_ses-2_run-1_phasediff.nii.gz',
 'sub-01/ses-2/func/sub-01_ses-2_task-rest_acq-fullbrain_run-1_bold.nii.gz',
 'sub-02/ses-1/fmap/sub-02_ses-1_run-1_phasediff.nii.gz',
 ...,
 ]
```
In the above snippet, we retrieve all files with subject id 1 or 2 and run id 1 (notice that any entity defined in the config file can be used a filtering argument), and with a file extension of .nii.gz. The returned result is a list of named tuples, one per file, allowing direct access to the defined entities as attributes.

Some other examples of get() requests:

```python
>>> # Return all unique 'session' directories
>>> layout.get(target='session', return_type='dir')
['sub-08/ses-1',
 'sub-06/ses-2',
 'sub-01/ses-2',
 ...
 ]

>>> # Return a list of unique file types available for subject 1
>>> layout.get(target='type', return_type='id', subject=1)
['T1map', 'magnitude2', 'magnitude1', 'scans', 'bold', 'phasediff', 'T1w', 'physio']
```

For convenience, it's also possible to create getters for all entities when initializing the Layout, by passing dynamic_getters=True:

```python
>>> layout = Layout(project_root, dynamic_getters=True)
>>> # Now we can call, e.g., get_subjects()
>>> layout.get_subjects()
['sub-09', 'sub-05', 'sub-08', 'sub-01', 'sub-02', 'sub-06', 'sub-04', 'sub-03', 'sub-07', 'sub-10']
```

Internally, the get_{entity}() methods are simply a partial function of the main get() method that sets target={entity}. So you can still pass all of the other arguments (e.g., to filter subjects by any of the other entities or return subject directories rather than unique IDs by specifying return_type='dir').

By default, `.get()` calls will return either absolute or relative paths, with behavior dictated by the project root passed in when the `Layout` was created (i.e., if an absolute project root was provided, returned paths will also be absolute, and similarly for relative project roots). You can force the `Layout` to always return absolute paths by setting `Layout(absolute_paths=True)`.

### For everything else, there's pandas
If you want to run more complex queries, grabbit provides an easy way to return the full project tree (or a subset of it) as a pandas DataFrame:

```python
# Return all session 1 files as a pandas DF
>>> layout.as_data_frame(session=1)
```

Each row is a single file, and each defined entity is automatically mapped to a column in the DataFrame.
