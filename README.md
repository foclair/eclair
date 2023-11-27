# Eclair

Build on QGIS minimalist plugin.
In order to use, may have to create your own venv, install all requirements and etk (which is not yet included in requirements.txt).

If experience problems with template database, run following in QGIS Python console to find where template database is located:

```
import os
DATABASE_DIR = Path(
    os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "eclair"
    )
)
```