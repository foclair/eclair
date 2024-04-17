# Eclair - Emission CompiLation for AIR quality

*Eclair* is a QGIS plugin, which uses the python module *etk* to structure emission data and store emissions together with geographic information in a database. 

### Windows installation
The OSGeo4W installer helps to install the PROJ, GDAL, and GEOS libraries required by ECLAIR.

#### OSGeo4W installation instructions 
First, download the  [OSGeo4W installer](https://trac.osgeo.org/osgeo4w/), and run it. Select Express Web-GIS Install and click next. In the ‘Select Packages’ list, ensure that GDAL is selected. If any other packages are enabled by default, they are not required by ECLAIR and may be unchecked safely. After clicking next and accepting the license agreements, the packages will be automatically downloaded and installed, after which you may exit the installer.

#### Install etk and Eclair
Once OSGeo4W is installed, open the OSGeo4W shell and run 
```
pip install -i https://test.pypi.org/simple/ rastafari==0.2.2
```
Instructions for installing etk will follow once publicly available. For now, both etk and eclair are located in
```
/data/proj9/A-konsult/Västra_Balkan_luftmiljö_2022_2270_10.3/06_Underlag/ECLAIR_Beta_16april
```
Copy this directory to a suitable location, and use the command `cd` to go to etk in the OSGeo4W shell, for example:
```
cd C:\Users\<your_home>\Desktop\etk
```
The OSGeo4W shell should now state that you are located in the right directory, for example `C:\Users\<your_home>\Desktop\etk>`.
Install etk by:
```
pip install .
```
If etk is successfully installed, the last line of output should state `Successfully installed (....) etk-0.0.1.dev0 (...)`, where other Python packages used by etk are stated both before and after etk.

Somehow, it could be that OSGeo4W does not copy the sql files in etk. Check this by going to the location where you have installed OSGeo4W, if it is not in C:\):
```
cd C:\OSGeo4W\apps\Python39\Lib\site-packages\etk\emissions
dir
```
If there are no sql files, copy them manually
```
copy <your_path>\ECLAIR_Beta_16april\etk\src\etk\emissions\*.sql .
```
**TODO** this will be fixed automatically in future release. 


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
Eclair has several sheets, each of which are described below. 
For all sheets, the functions of buttons that are in *italic* are not yet implemented. 
Eclair often opens windows to report on the processing status. These windows have to be closed before being able to continue using the QGIS interface.

Currently, point- and areasources are implemented in etk, and gridsources are added very soon. 
Sources can either have direct emissions, where the emission of each substance is known for a source.
If the amount of emissions is not known, but the activity of the source is known (for example the energy demand for heating), an activity rate and emission factors can be imported to specify emissions.

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

Each source should have a unique combination of source_name and facility_id. The same facility_id cannot be used for different facility names. If you import a source which has a name and facility_id that already exist in the database, this source will not be **duplicated** but its parameters will be **updated**.

Direct emissions for a substance are specified by create a column 'subst:PM10', where PM10 is taken as an example. The implemented substances are: 

| abbreviation | name substance |
| :-- | :-- |
| As | Arsenic |
| BC | Black Carbon |
| BaP | Benzo\[a\]pyrene |
| Cd | Cadmium |
| Cr | Chromium |
| Cu | Copper |
| C6H6 | Benzene |
| CH4 | Methane |
| CO | Carbon monoxide |
| CO2 | Carbon dioxide |
| Dioxin | Dioxin |
| HC | Hydrocarbons |
| HCB | Hexachlorobenzene |
| HFC | Hydrofluorocarbons |
| Hg | Mercury |
| N2O | Nitrous oxide |
| NH3 | Ammonia |
| Ni | Nickel |
| NMHC | Non-methane hydrocarbons |
| NMVOC | Non-methane volatile organic compound |
| NOx | Nitrogen oxides as NO2 |
| NO2 | Nitrogen dioxide |
| NO | Nitrogen monooxide |
| O3 | Ozone |
| PAH4 | Sum of 4 polycyclic aromatic hydrocarbons |
| Pb | Lead |
| PFC | Perfluorocarbons |
| PM10 | Particulate matter < 10 micrometers in diameter |
| PM25 | Particulate matter < 2.5 micrometers in diameter |
| PM10resusp | Resuspended particles < 10 micrometers in diameter |
| PM25resusp | Resuspended particles < 2.5 micrometers in diameter |
| PN | Particle Number |
| Se | Selenium |
| PCB | Polychlorinated biphenyls |
| SF6 | Sulfur Hexafluoride |
| SO2 | Sulphur dioxide |
| SOx | Sulphur oxides as SO2 |
| TSP | Total Suspended Particles |
| Zn | Zinc |



Indirect emissions, specified by an activity, activity rate and emission factors, are added by a column act:activity_name (see templates for example).

**TODO** timevar should be optional for areasources as well

#### Edit
**TODO**
Currently, values can only be edited by loading layers interactively, and then for example moving the point or corners of a polygon using QGIS functionality. Parameter values can also be changed by right clicking on the interactively loaded layer, choose Open Attribute Table, Toggle Editing, and changing a number in the table. 

The currently easiest way to change emissions is to change the input file and import it again. If changes were made to the emissions through the QGIS functionality after emissions were imported, it is possible to first export all emissions (see export window), then change in the exported table, and import the adapted table. 

Removing points or areas is currently not possible. The most straightforward way to do this is to export all emissions, remove the points or polygons that should be removed, and create a **new** database where the new input file is imported. Just importing an input file where some sources are removed to an existing database will **not** remove those sources.

#### Export
Exports all data currently stored in the database to a file which has the correct format to be imported into an emission inventory.

#### Analyse
Aggregate (sum) emissions per sector and store as a csv file (**TODO** codeset cannot be chosen by user yet, taking codeset 1 as default).

Calculate raster of emissions and store as netcdf file. See instructions in QGIS window. 

#### Load layers
Layers can be loaded interactively, to always reflect the current state of the database which Eclair is connected to, or as a 'snapshot' of the state of the database when the 'Visualize all current sources' button is clicked. This latter button will add the date and time of creation of the layers to the layer name. Changes in the 'snapshot' layer will **not** be reflected in the database. However, the benifit of such a snapshot layer is that it will link the static information about sources (chimney_height etc) with both direct and indirect emissions of the sources. This is not (yet?) possible when visualizing layers interactively. Use the 'Identify Features' (often with shortcut ctrl+shift+i) to study the emissions. Note that the identify features tool only works on the layer which is currently selected in the Layers panel.


## Development

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

Development is best done through plugin-reloader. Create a symlink to this directory at the location where QGIS finds plugins. For Windows eg
```
mklink /D C:\Users\eefva\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\minimal-eclair C:\Users\eefva\Projects\minimal-eclair 
mklink /D C:\OSGeo4W\apps\qgis\plugins\minimal-eclair %UserProfile%\Projects\minimal-eclair
```
Not 100% which one worked, have to retry upon new installation.