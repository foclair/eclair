# Eclair - Emission CompiLation for AIR quality

*Eclair* is a QGIS plugin, which uses the python module *etk* to structure emission data and store emissions together with geographic information in a database. 

### Windows installation
The OSGeo4W installer helps to install the PROJ, GDAL, and GEOS libraries required by ECLAIR. Therefore, even if you have QGIS installed already, to make sure Eclair works, follow the installation instructions below.

#### OSGeo4W installation instructions 
First, download the  [OSGeo4W installer](https://trac.osgeo.org/osgeo4w/), and run it. Select Express Web-GIS Install and click next. In the "Choose a download Site" dialog, add the url https://download.osgeo.org/osgeo4w/v2/snapshots/20230428-030718/ as User URL, and select the last download site which was added to the upper list by entering this url. This will ensure that an older version of OSGeo4W is installed, which has a GDAL version that is compatible with the version of Django used by etk. In the ‘Select Packages’ list, ensure that GDAL is selected. If any other packages are enabled by default, they are not required by ECLAIR and may be unchecked safely. After clicking next and accepting the license agreements, the packages will be automatically downloaded and installed, after which you may exit the installer.

#### Install Eclair
Eclair can either be installed from zip (easier for user not involved in development), or by creating a symbolic link as described in the section 'Development' below (only recommended for developers). To install from zip, open QGIS, go to Plugins > Manage and Install Plugins.. > Install from ZIP. If you get a 'Security warning', click Yes to continue.
Now Eclair is installed, and a button with 'Eclair!' should have appeared in QGIS. Clicking this button should open a panel below the 'layers' panel, on the left of the user interface.

### Using Eclair
Eclair has several panels, each of which are described below. 
Eclair often opens windows to report on the processing status. These windows have to be closed before being able to continue using the QGIS interface.

Sources can either have direct emissions, where the emission of each substance is known for a source.
If the amount of emissions is not known, but the activity of the source is known (for example the energy demand for heating), an activity rate and emission factors can be imported to estimate emissions.

#### DB Settings
Here you choose which database to edit. Every time the plugin is started, a database has to be chosen or created.
If you receive an error message stating "ModuleNotFoundError: No module named 'etk'", make sure that you opened the version of QGIS connected to your OSGeo4W installation (as QGIS could be installed twice, once as stand-alone and once as part of OSGeo4W through the installation guidelines above). The executable of the program connected to OSGeo4W can be found in `OSGeo4W/bin/qgis-ltr-bin`. Always use this version of QGIS when working with Eclair. 

When creating a new database, a coordinate reference system needs to be chosen. **TODO more info here, explain what it is used for**

#### Import emissions

Eclair can import four types of sources:
- point sources,
- area sources,
- grid sources,
- road sources.

Template files that show what structure import files should have are located in; 

[https://github.com/foclair/etk/tree/develop/tests/edb/data](https://github.com/foclair/etk/tree/develop/tests/edb/data)

The import files are Excel files which can have a number of sheets. 
Codesets (such as GNFR, NFR and SNAP) and their activity codes (such as 1.A.3.b) are set in sheets
"CodeSet" and "ActivityCode". These apply to all source types.
The parameters used for point, area and grid sources are set by sheets "EmissionFactor", 
"Timevar", "PointSource", "AreaSource" and "GridSource".
The parameters used to estimate emissions from traffic are set by the sheets
"VehicleFuel", "Fleet", "CongestionProfile", "FlowTimevar", "ColdstartTimevar",
"RoadAttribute", "TrafficSituation", "VehicleEmissionFactor" and "RoadSource".

It is recommended to first validate your file, before importing it. 
Validating your input file means that Eclair will try to import it, but keeping track of all errors if the import file misses data.
If you try to directly import an input file that has an incorrect format, you will only get the first error in the file, and the import routine will be aborted. However, if you are sure that your input file has the correct format, you can import it directly without validation. 
For both import and validation, you can choose which sheets of the file you want to process. 

If you want to import activities or activity codes for sources, these activities or activity codes have to either be defined in a previous import, or in the same file. It is not possible to import sources which specify rates for activities that are not defined yet. Activity codes have to be unique; one code cannot be used for multiple codesets.

Almost all columns in the import template are required, but point sources have a few optional columns: `timevar`, `chimney_height`, `outer_diameter` (of chimney), `inner_diameter`, `gas_speed`, `gas_temperature[K]`, `house_width` and `house_height`. These physical parameters have to be specified in SI units (m, m/s and K). 

Each point and area source needs to have a unique combination of `source_name` and `facility_id`. The same `facility_id` cannot be used for different `facility_name`s. If you import a point or area source which has a `source_name` and `facility_id` that already exist in the database, this source will not be **duplicated** but its parameters will be **updated**. Grid sources have a unique `source_name`; importing a file with a grid source name that already exists in the database will update the source, not duplicate it. Road sources on the other hand are **not** updated; importing the same import file twice will lead to duplicated road segments in the database. 

Direct emissions for a substance are specified by create a column `subst:PM10`, where the substance 'PM10' is taken as an example. The unit of direct emissions is set by `emission_unit`. The substances implemented in Eclair are: 

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

Indirect emissions, specified by an activity, activity rate and emission factors, are added by a column `act:activity_name` (see templates for example).
For grid sources, the columns `subst:` and `act:` can either contain a number, which will then scale the raster values such that the total direct emission or activity rate for the entire raster is equal to this number, or the word `sum` such that the raster values remain unscaled. 

#### Export emissions
Exports all data currently stored in the database to an Excel file which has the correct format to be imported into an emission inventory. Grid and road sources are also automatically exported to Tif and Geopackage files in the same directory as the database, consistent with the file path in the Excel file.

#### Analyse emissions
The output file names chosen for 
Aggregate (sum) emissions per activity code in the chosen codeset and store as an Excel file. Sources which do not have an activity code assigned will be summed separately from the other sources with defined activity code. Direct emissions (defined with `subst:??`) and indirect emissions (defined by activity rates and emission factors) are aggregated together.

Calculate raster of emissions and store as NetCDF file. A dialog will pop up where the user can choose the extent, coordinate system and resolution of the output raster. A begin and end date can also be specified to create NetCDF files with one band for every hour in the specified time range.

#### Load layers
Layers can be loaded dynamically, to always reflect the current state of the database which Eclair is connected to, or as a static 'snapshot' of the state of the database. The static visualisation will add the date and time of creation of the layers to the layer name. Changes in the 'snapshot' layer will **not** be reflected in the database. However, the benifit of such a snapshot layer is that it links both direct and indirect emissions to the sources. This is not possible when visualizing layers dynamically. The dynamical layers only show source related parameters such as `source_name` and `chimney_height`. Use the 'Identify Features' functionality in QGIS (most QGIS users can use the shortcut ctrl+shift+i) to study the emissions. Note that the identify features tool only works on the layer which is currently selected in the Layers panel.

Grid sources can only be loaded as static layers, not dynamically.


#### Edit imported emissions
Values can only edited by loading layers dynamically, and then moving a point or corners of a polygon or road using QGIS functionality. Source parameters such as `chimney_height` can be changed by right clicking on the dynamically loaded layer, choose 'Open Attribute Table', 'Toggle Editing', and change a number in the table. 

The currently easiest way to change emissions is to change the input file and update sources by importing it again (for area, point and grid sources). If changes were made to the sources through the QGIS functionality after emissions were imported, it is possible to first export all emissions as they are in the databse (using Eclairs 'Export' panel), then change in the exported file, and import the adapted file again. To edit parameters related to road sources, the most straightforward way is to export all sources to Excel, create a new database, adept the exported Excel file and import it to the new database.

Removing sources using QGIS functionality to edit layers is currently not possible. The most straightforward way to do this is to export all emissions, remove the points or polygons that should be removed, and create a **new** database where the new input file is imported. Just importing a file where some sources are removed to an existing database will **not** remove those sources, it will only update the sources in the file and leaving all other sources in the database unchanged.


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
mklink /D C:\OSGeo4W\apps\qgis\plugins\eclair %UserProfile%\eclair
```
