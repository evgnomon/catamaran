# Getting started

```bash
poetry install
poetry run poe check
pip install -e . # for ansible to find the collection
```

# Release a new version

```
poetry version patch
# Set the same version in ansible_collections/evgnomon/catamaran/galaxy.yml
```

