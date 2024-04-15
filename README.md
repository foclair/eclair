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
Instructions for installing etk will follow once publicly available. For now, both etk and eclair are located in
```
/data/proj9/A-konsult/Västra_Balkan_luftmiljö_2022_2270_10.3/06_Underlag/ECLAIR_Beta_16april
```
Copy this directory to a suitable location, and go to etk in the OSGeo4W shell, for example:
```
cd C:\Users\<your_home>\Desktop\ECLAIR_Beta_16april\etk
pip install .
```
Somehow, it could be that OSGeo4W does not copy the sql files in etk. Check this as follows (make sure to change to your location of OSGeo4W, if it is not in C:\):
```
cd C:\OSGeo4W\apps\Python39\Lib\site-packages\etk\emissions
dir
```

Now create a folder in your home directory: **TODO** this should not be necessary, but the automatic creation of the folder does not work in Windows yet.
```
mkdir C:\Users\<your_home>\.config
mkdir C:\Users\<your_home>\.config\eclair
```
and create a template database, which includes the full database structure, but without any data:
```
etk migrate
```
You can check whether the database was created, by checking whether a file eclair.gpkg was created:
```
dir C:\Users\<your_home>\.config\eclair
```

Eclair can either be installed from zip (easier for user not involved in development), or by creating a symbolic link as described in the section 'Development' below (only recommended for developers). To install from zip, open QGIS, go to Plugins > Manage and Install Plugins.. > Install from ZIP. If you get a 'Security warning', click Yes to continue.
Now Eclair is installed, and a button with 'Eclair!' should have appeared in QGIS. Clicking this button should open a panel below the 'layers' panel, on the left of the user interface.

### Using Eclair
Eclair has several windows, each of which are described below. 
For all windows, the functions of buttons that are in *italic* are not yet implemented. 
Eclair often opens windows to report on the processing status. These windows have to be closed before being able to continue using the QGIS interface.

#### DB Settings
Here you choose which database to edit. Every time the plugin is started, a database has to be chosen or created.
When creating a new database, it is now **obligatory** to give a name ending in ".gpkg" (this will likely change in next update).
If you receive an error message stating "ModuleNotFoundError: No module named 'etk'", make sure that you opened the version of QGIS connected to your OSGeo4W installation (as QGIS could be installed twice, once as stand-alone and once as part of OSGeo4W). The executable of the program connected to OSGeo4W can be found in `OSGeo4W/bin/qgis-ltr-bin`. Always use this version of QGIS when working with Eclair. 
#### Import
Template files that show what structure import files should have are located in 
```
/data/proj9/A-konsult/Västra_Balkan_luftmiljö_2022_2270_10.3/06_Underlag/ETK_Templates
```
It is recommended to first validate your file, before importing it. 
Validating your input file means that Eclair will try to import it, but keeps track of all errors if the import file misses data.
If you try to directly import an input file that has missing data, you will only get 1 error for each missing cell in the file, and the import routine will be aborted. However, if you are sure that your input file has the correct format, you can import it directly without validation. 
For both import and validation, you can choose which sheets of the file you want to process. 
Note that if you want to import activities or activity codes for sources, these activities or activity codes have to either be defined in a previous import, or in the same file. It is not possible to import sources which specify rates for activities that are not defined yet.

Required columns for areasources are: facility_id, facility_name, source_name, geometry and timevar, where the geometry of the polygons is in WKT format (see template). Required columns for pointsources are: facility_id, facility_name, source_name, lat and lon. 
Optional columns for pointsources are: timevar, chimney_height, outer_diameter (of chimney), inner_diameter, gas_speed, gas_temperature[K], house_width and house_height. All physical parameters should be specified in SI units (m, m/s and K). 

Each source should have a unique combination of source_name and facility_id. The same facility_id cannot be used for different facility names.

Direct emissions for a substance are specified by create a column 'subst:PM10', where PM10 is taken as an example. The implemented substances are: 
    ("As", "As", "Arsenic"),
    ("BC", "BC", "Black Carbon"),
    ("BaP", "BaP", "Benzo[a]pyrene"),
    ("Cd", "Cd", "Cadmium"),
    ("Cr", "Cr", "Chromium"),
    ("Cu", "Cu", "Copper"),
    ("C6H6", "Benzene", "Benzene"),
    ("CH4", "Methane", "Methane"),
    ("CO", "CO", "Carbon monoxide"),
    ("CO2", "CO2", "Carbon dioxide"),
    (
        "Dioxin",
        "Dioxin",
        "Dioxin",
    ),
    ("HC", "Hydrocarbons", "Hydrocarbons"),
    ("HCB", "HCB", "Hexachlorobenzene"),
    ("HFC", "HFC", "Hydrofluorocarbons"),
    ("Hg", "Hg", "Mercury"),
    ("N2O", "N2O", "Nitrous oxide"),
    ("NH3", "NH3", "Ammonia"),
    ("Ni", "Ni", "Nickel"),
    ("NMHC", "NMHC", "Non-methane hydrocarbons"),
    ("NMVOC", "NMVOC", "Non-methane volatile organic compound"),
    ("NOx", "NOx", "Nitrogen oxides (as NO2)"),
    ("NO2", "NO2", "Nitrogen dioxide"),
    ("NO", "NO", "Nitrogen monooxide"),
    ("O3", "Ozone", "Ozone"),
    ("PAH4", "PAH4", "Sum of 4 polycyclic aromatic hydrocarbons"),
    ("Pb", "Pb", "Lead"),
    ("PFC", "PFC", "Perfluorocarbons"),
    ("PM10", "PM10", "Particulate matter < 10 micrometers in diameter"),
    ("PM25", "PM2.5", "Particulate matter < 2.5 micrometers in diameter"),
    ("PM10resusp", "PM10resusp", "Resuspended particles < 10 micrometers in diameter"),
    (
        "PM25resusp",
        "PM2.5resusp",
        "Resuspended particles < 2.5 micrometers in diameter",
    ),
    ("PN", "PN", "Particle Number"),
    ("Se", "Se", "Selenium"),
    ("PCB", "PCB", "Polychlorinated biphenyls"),
    ("SF6", "SF6", "Sulfur Hexafluoride"),
    ("SO2", "SO2", "Sulphur dioxide"),
    ("SOx", "SOx", "Sulphur oxides (as SO2)"),
    ("traffic_work", "traffic work", "Traffic work"),
    ("TSP", "TSP", "Total Suspended Particles"),
    ("Zn", "Zn", "Zinc"),

Indirect emissions, specified by an activity, activity rate and emission factors, are added by a column act:activity_name (see templates for example).

**TODO** timevar should be optional for areasources as well? format list of substances


## Development

Best through plugin-reloader. Create a symlink to this directory at the location where QGIS finds plugins. For Windows eg
```
mklink /D C:\Users\eefva\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\minimal-eclair C:\Users\eefva\Projects\minimal-eclair 
mklink /D C:\OSGeo4W\apps\qgis\plugins\minimal-eclair %UserProfile%\Projects\minimal-eclair
```
Not 100% which one worked, have to retry upon new installation.