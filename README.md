# [galaxy-community-activities]()

[![Build and deploy](https://github.com/kostrykin/galaxy-community-activities/actions/workflows/build.yml/badge.svg)](https://github.com/kostrykin/galaxy-community-activities/actions/workflows/build.yml)

Tool which reports and summarizes activities within a Galaxy community.

Updates are scheduled weekly.

## Local setup

Steps to setup locally:
- `mamba env create -f environment.yml`
- `source activate galaxy-community-activities`
- `gem install jekyll`
- `ln -s $(which ruby) $CONDA_PREFIX/share/rubygems/bin/`

## Update the cache

Set your GitHub PAT as `GITHUB_TOKEN` or use `--api` to pass it via command line: 
```bash
python -m activities.cli --fetch
```

## Build the report from cache

```bash
python -m activities.cli --report
```
