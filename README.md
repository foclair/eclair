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
### Windows installation
The OSGeo4W installer helps to install the PROJ, GDAL, and GEOS libraries required by ECLAIR. First, download the  [OSGeo4W installer](https://trac.osgeo.org/osgeo4w/), and run it. Select Express Web-GIS Install and click next. In the ‘Select Packages’ list, ensure that GDAL is selected. If any other packages are enabled by default, they are not required by ECLAIR and may be unchecked safely. After clicking next and accepting the license agreements, the packages will be automatically downloaded and installed, after which you may exit the installer.

Next, open the OSGeo4W shell and run 
```
pip install -i https://test.pypi.org/simple/ rastafari==0.2.2
```
Instructions for installing etk will follow once publicly available. For now it can only be downloaded by SMHI employees, by also running in OSGeo4W shell:
```
git clone https://<resource-number>:<Personal-Access-Token>@git.smhi.se/foclair/etk.git
cd etk
pip install .
```
where resource number is for example a002469 and personal access token can be generated on https://git.smhi.se/. Now Eclair can either be installed from zip (easier for user not involved in development), or by creating a symbolic link as described below. 

## Development

Best through plugin-reloader. Create a symlink to this directory at the location where QGIS finds plugins. For Windows eg
```
mklink /D C:\Users\eefva\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\minimal-eclair C:\Users\eefva\Projects\minimal-eclair 
mklink /D C:\OSGeo4W\apps\qgis\plugins\minimal-eclair %UserProfile%\Projects\minimal-eclair
```
Not 100% which one worked, have to retry upon new installation.