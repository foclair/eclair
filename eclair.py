"""
/***************************************************************************
 eclair
                                 A QGIS plugin
 This plugin compiles emission data for air quality. Data can be imported, edited and exported.
                              -------------------
        begin                : 2023-03-16
        git sha              : $Format:%H$
        copyright            : (C) 2023 by SMHI FO Luft
        email                : eef.vandongen@smhi.se
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""



from PyQt5.QtWidgets import QApplication, QAction, QWidget, QDockWidget, QTableWidget, QTableWidgetItem
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QComboBox
from PyQt5.QtWidgets import QFileDialog, QCheckBox, QRadioButton, QButtonGroup, QTabWidget, QMainWindow, QLineEdit
from PyQt5.QtCore import pyqtSlot

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QDoubleValidator
from PyQt5.QtCore import Qt
from qgis.utils import iface
from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsDataSourceUri,
    QgsCoordinateReferenceSystem,
    QgsRasterLayer,
    QgsProviderRegistry,
    QgsCoordinateTransform,
    QgsVectorLayerJoinInfo,
    QgsMessageLog,
    QgsLayerTreeLayer,
    Qgis, QgsApplication, QgsTask,
    QgsSingleBandGrayRenderer,
    QgsRasterBandStats
)
from qgis.gui import QgsProjectionSelectionDialog
import time

import os
import glob
import sys
import subprocess
import site
from math import ceil, floor
import ast
import re
from pathlib import Path
import datetime
import json
from tempfile import NamedTemporaryFile, gettempdir
from osgeo import gdal

import sqlite3
import rasterio

import processing
from concurrent.futures import ThreadPoolExecutor, as_completed

if os.name != "nt":
    CETK_BINPATH = os.path.expanduser("~/.local/bin")
    os.environ["PATH"] += f":{CETK_BINPATH}"
    sys.path += [f"/home/{os.environ['USER']}/.local/lib/python3.9/site-packages"]
else:
    OSGEO4W = r"C:\OSGeo4W"
    assert os.path.isdir(OSGEO4W), "Directory does not exist: " + OSGEO4W
    os.environ['OSGEO4W_ROOT'] = OSGEO4W
    os.environ['GDAL_DATA'] = OSGEO4W + r"\share\gdal"
    os.environ['PROJ_LIB'] = OSGEO4W + r"\share\proj"
    os.environ['PATH'] = OSGEO4W + r"\bin;" + os.environ['PATH']


try: 
    from cetk.edb.const import SHEET_NAMES
except:
    if QMessageBox.question(None, "Eclair dependencies not installed",
              "Do you want to install missing python modules? \r\n"
              "QGIS will be non-responsive for a while.",
               QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
        try:
            subprocess.check_call(["python", "-m", "pip", "install","cetk", "--user"])
            from cetk.edb.const import SHEET_NAMES
            QMessageBox.information(None, "Packages successfully installed",
                                    "To make all parts of the plugin work it is recommended to restart your QGIS-session.")
        except Exception as e:
            error = e.stderr.decode("utf-8")    
            QgsMessageLog.logMessage(error, level=Qgis.Warning)
            QMessageBox.information(None, "An error occurred",
                                    "Eclair couldn't install Python packages!\n"
                                    "See 'General' tab in 'Log Messages' panel for details.\n")
    else:
        QMessageBox.information(None,
                                "Information", "Packages not installed. Eclair will not function unless cetk is installed manually, see https://github.com/foclair/cetk for installation instructions.")




from cetk.tools.utils import (
    CalledProcessError, 
    create_from_template, 
    get_template_db,
    set_settings_srid,
    run_import,
    run_export,
    run_update_emission_tables,
    run_aggregate_emissions, 
    run_rasterize_emissions,
    run_get_settings
)
from cetk.db import run_migrate
        
class Eclair(QWidget):
    def __init__(self, iface):
        super(Eclair, self).__init__()
        self.iface = iface
        self.setWindowTitle("ECLAIR")
        self.dock_widget = None  

    def initGui(self):
        self.action = QAction('Eclair!', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
    
    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        # Show the widget when the plugin is triggered
        self.show_dock_panel()
    
    def show_dock_panel(self):
        # Create or show the dock widget
        if self.dock_widget is None:
            self.dock_widget = EclairDock(self.iface.mainWindow())
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)
        self.dock_widget.show()


class EclairDock(QDockWidget):
    def __init__(self, parent):
        super().__init__("ECLAIR", parent)

        # Check if template db exists, if not create by migrate
        if not os.path.exists(get_template_db()):
            os.makedirs(os.path.dirname(get_template_db()), exist_ok=True)
            run_migrate()


        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        # Create a main widget for the dock widget
        self.main_widget = QWidget(self)
        self.setWidget(self.main_widget)
        self.setMinimumHeight(200) 
        layout = QVBoxLayout(self.main_widget)
        self.tab_widget = QTabWidget(self.main_widget)
        layout.addWidget(self.tab_widget)

        default_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        italic_font = default_font
        italic_font.setItalic(True)
        # Create tabs
        self.tab_db = QWidget()
        self.tab_import = QWidget()
        self.tab_edit = QWidget()
        self.tab_export = QWidget()
        self.tab_calculate = QWidget()
        self.tab_visualize = QWidget()
        # Add tabs to the tab widget
        self.tab_widget.addTab(self.tab_db, "DB Settings")
        self.tab_widget.addTab(self.tab_import, "Import")
        # self.tab_widget.addTab(self.tab_edit, "Edit")
        self.tab_widget.addTab(self.tab_export, "Export")
        self.tab_widget.addTab(self.tab_calculate, "Analyse")
        self.tab_widget.addTab(self.tab_visualize, "Load Layers")

        # Database
        layout_db = QVBoxLayout()
        layout_db.setAlignment(Qt.AlignTop)
        self.tab_db.setLayout(layout_db)
        self.db_label = QLabel(self)
        self.update_db_label()
        layout_db.addWidget(self.db_label)

        btn_action_existing_database = QPushButton("Connect to existing database", self.tab_db)
        layout_db.addWidget(btn_action_existing_database)
        btn_action_existing_database.clicked.connect(self.load_existing_database_dialog)

        btn_action_new_database = QPushButton("Create and connect to new database", self.tab_db)
        layout_db.addWidget(btn_action_new_database)
        btn_action_new_database.clicked.connect(self.create_new_database_dialog)

        #TODO
        # btn_action_edit_db_settings = QPushButton("Edit database settings", self.tab_db)
        # btn_action_edit_db_settings.setFont(italic_font)
        # layout_db.addWidget(btn_action_edit_db_settings)
        # btn_action_edit_db_settings.clicked.connect(self.edit_db_settings)

        # Import
        layout_import = QVBoxLayout()
        layout_import.setAlignment(Qt.AlignTop)
        self.tab_import.setLayout(layout_import)
        label = QLabel("Import data from Excel to your database:", self.tab_import)
        layout_import.addWidget(label)

        btn_action_validate_sources = QPushButton("Validate data (before importing)", self.tab_import)
        layout_import.addWidget(btn_action_validate_sources)
        btn_action_validate_sources.clicked.connect(self.validate_sources)

        btn_action_import_sources = QPushButton("Import data", self.tab_import)
        layout_import.addWidget(btn_action_import_sources)
        btn_action_import_sources.clicked.connect(self.import_sources)

        #TODO
        # Edit
        # layout_edit = QVBoxLayout()
        # layout_edit.setAlignment(Qt.AlignTop)
        # self.tab_edit.setLayout(layout_edit)
        # label = QLabel("Edit or remove data.", self.tab_edit)
        # layout_edit.addWidget(label)
        # btn_action_edit = QPushButton(" Edit data", self.tab_edit)
        # btn_action_edit.setFont(italic_font)
        # layout_edit.addWidget(btn_action_edit)

        # Export
        layout_export = QVBoxLayout()
        layout_export.setAlignment(Qt.AlignTop)
        self.tab_export.setLayout(layout_export)
        label = QLabel("Export database to Excel", self.tab_export)
        layout_export.addWidget(label)
        btn_action_export_all = QPushButton(" Export all data", self.tab_export)
        layout_export.addWidget(btn_action_export_all)
        btn_action_export_all.clicked.connect(self.export_dialog)

        #TODO
        # btn_action_export = QPushButton(" Export only pointsources", self.tab_export)
        # btn_action_export.setFont(italic_font)
        # layout_export.addWidget(btn_action_export)

        # Calculate emissions
        layout_calculate = QVBoxLayout()
        layout_calculate.setAlignment(Qt.AlignTop)
        self.tab_calculate.setLayout(layout_calculate)
        label = QLabel("Create a Excel file with aggregated emissions per sector.", self.tab_calculate)
        layout_calculate.addWidget(label)

        btn_action_aggregate = QPushButton("Aggregate emissions", self.tab_calculate)
        layout_calculate.addWidget(btn_action_aggregate)
        btn_action_aggregate.clicked.connect(self.aggregate_emissions_dialog)

        label = QLabel("Create NetCDF files with rasterized emissions for all substances.", self.tab_calculate)
        layout_calculate.addWidget(label)
        btn_action_raster = QPushButton(" Calculate rasters of emissions", self.tab_calculate)
        layout_calculate.addWidget(btn_action_raster)
        btn_action_raster.clicked.connect(self.rasterize_emissions_dialog)

        # Visualize emissions
        layout_visualize = QVBoxLayout()
        layout_visualize.setAlignment(Qt.AlignTop)
        self.tab_visualize.setLayout(layout_visualize)

        label = QLabel("Load source geometries without emissions (dynamic)", self.tab_visualize)
        layout_visualize.addWidget(label)

        dynamic_sources_layout = QHBoxLayout()
        btn_action_visualize_point = QPushButton("Points", self.tab_visualize)
        dynamic_sources_layout.addWidget(btn_action_visualize_point)
        btn_action_visualize_point.clicked.connect(self.load_pointsource_canvas)
        btn_action_visualize_area = QPushButton("Areas", self.tab_visualize)
        dynamic_sources_layout.addWidget(btn_action_visualize_area)
        btn_action_visualize_area.clicked.connect(self.load_areasource_canvas)
        btn_action_visualize_road = QPushButton("Roads", self.tab_visualize)
        dynamic_sources_layout.addWidget(btn_action_visualize_road)
        btn_action_visualize_road.clicked.connect(self.load_roadsource_canvas)
        layout_visualize.addLayout(dynamic_sources_layout)
        
        label = QLabel("Load source geometries with emissions (static)\n"
        "Layers have to be re-loaded each time the inventory is updated.", self.tab_visualize)
        layout_visualize.addWidget(label)
        
        static_sources_layout = QHBoxLayout()
        btn_action_visualize_join_point = QPushButton("Points", self.tab_visualize)
        static_sources_layout.addWidget(btn_action_visualize_join_point)
        btn_action_visualize_join_point.clicked.connect(self.load_joined_pointsource_canvas)
        btn_action_visualize_join_area = QPushButton("Areas", self.tab_visualize)
        static_sources_layout.addWidget(btn_action_visualize_join_area)
        btn_action_visualize_join_area.clicked.connect(self.load_joined_areasource_canvas)
        btn_action_visualize_join_road = QPushButton("Roads", self.tab_visualize)
        static_sources_layout.addWidget(btn_action_visualize_join_road)
        btn_action_visualize_join_road.clicked.connect(self.load_joined_roadsource_canvas)
        btn_action_visualize_join_grid = QPushButton("Grids", self.tab_visualize)
        static_sources_layout.addWidget(btn_action_visualize_join_grid)
        btn_action_visualize_join_grid.clicked.connect(self.load_joined_gridsource_canvas)
        layout_visualize.addLayout(static_sources_layout)

    def update_db_label(self):
        db_path = os.environ.get("CETK_DATABASE_PATH", "Database not set yet.")
        self.db_label.setText(f"Eclair is currently connected to database:\n {os.path.basename(db_path)}")
        self.db_label.setToolTip(str(db_path))

    def load_existing_database_dialog(self):
        db_path, _ = QFileDialog.getOpenFileName(self.tab_db, "Open SQLite database", "", "Database (*.gpkg)")
        if db_path == '':
            # user cancelled
            message_box('Warning','No file chosen, database not configured.')
        else:
            os.environ["CETK_DATABASE_PATH"] = db_path
            self.update_db_label()
            message_box('Load database',f"Database succesfully chosen database {db_path}.")

    def create_new_database_dialog(self):
        db_path, _ = QFileDialog.getSaveFileName(None, "Create new SQLite database", "", "Database (*.gpkg)")
        if (db_path == ''): 
            # user cancelled
            message_box('Warning','No *.gpkg file chosen, database not created.')
        else:
            try:
                epsg = self.show_srid_dialog()
                proc = create_from_template(db_path)
                os.environ["CETK_DATABASE_PATH"] = db_path
                if epsg is not None:
                    set_settings_srid(epsg)
                self.update_db_label()
                message_box('Created database',f"Successfully created database {db_path} with coordinate system {epsg}")
            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")    
                message_box('Create database error',f"Error: {error}")

    def edit_db_settings(self):
        # TODO, create command in cetk.tools.utils that fixes this
        pass
    
    def import_sources(self):
        self.dry_run = False
        self.import_sources_dialog()

    def validate_sources(self):
        self.dry_run = True
        self.import_sources_dialog()

    def import_sources_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open spreadsheet with point- and/or areasource data file", "", "Spreadsheet files (*.xlsx)")
        if file_path: #if file_path not empty string (user did not click cancel)
            from openpyxl import load_workbook
            workbook = load_workbook(filename=file_path, data_only=True, read_only=True)
            # workbook.worksheets  compare to SHEET_NAMES
            valid_sheets = [sheet.title for sheet in workbook.worksheets if sheet.title in SHEET_NAMES]
            workbook.close()
            
            checkboxDialog = CheckboxDialog(self,valid_sheets, self.dry_run)
            result = checkboxDialog.exec_()  # Show the dialog as a modal dialog
            if result == QDialog.Accepted:
                sheets = checkboxDialog.sheet_names
            else:
                if self.dry_run:
                    message_box('Validation progress','Dialog closed, validation cancelled. Restart data validation and click Validate sheets button instead if validation is desired.')
                    return
                else:
                    message_box('Import progress','Dialog closed, data import cancelled. Restart data import and click Import sheets button instead if data import is desired.')
                    return
                sheets = SHEET_NAMES
            
            # from qgis.PyQt.QtCore import pyqtRemoveInputHook
            # pyqtRemoveInputHook()
            if self.dry_run:
                description = "Eclair data validation"
            else:
                description = "Eclair data import"
            self.importtask = RunImportTask(description,file_path,sheets)
            QgsApplication.taskManager().addTask(self.importtask)
        else:
            # user cancelled
            message_box('Import error','No file chosen, no data imported.')



    def export_dialog(self):
        filename, _ = QFileDialog.getSaveFileName(None, "Choose filename for exported emissions", "", "(*.xlsx)")
        if (filename == ''):
            # user cancelled
            message_box('Warning','No *.xlsx file chosen, emissions not exported.')
        else:
            if filename and not filename.endswith('.xlsx'):
                filename += '.xlsx'
            self.task = RunBackgroundTask(
                description="Export data",
                function=run_export,
                parent=self,
                filename=filename
            )
            QgsApplication.taskManager().addTask(self.task)
    

    def create_emission_table(self):
        #TODO catch exception if database does not have any emissions imported yet       
        db_path = os.environ.get("CETK_DATABASE_PATH", "Database not set yet.")
        self.task = RunBackgroundTask(
                description="Prepare emissions for static visualisation",
                function=run_update_emission_tables,
                parent=self,
                db_path=db_path,
                sourcetypes=self.source_type
        )
        QgsApplication.taskManager().addTask(self.task)


    def aggregate_emissions_dialog(self):
        filename, _ = QFileDialog.getSaveFileName(None, "Choose filename for aggregated emissions table", "", "(*.xlsx)")
        if (filename == ''):
            # user cancelled
            message_box('Warning','No file chosen, aggregated table not created.')
        else:
            if filename and not filename.endswith('.xlsx'):
                filename += '.xlsx'
            try:
                self.db_path = os.environ.get("CETK_DATABASE_PATH", "Database not set yet.")
                # Load codesets table
                connection = sqlite3.connect(self.db_path)
                cursor = connection.cursor()
                cursor.execute("SELECT slug FROM codesets LIMIT 3")
                codesets = [row[0] for row in cursor.fetchall()]
                connection.close()
                if len(codesets) > 0:
                    codesetDialog = ChooseCodesetDialog(self,filename,codesets)
                    codesetDialog.exec_()
                else:
                    # aggregating all substances when no codeset defined
                    self.task = RunBackgroundTask(
                        description="Aggregate emissions",
                        function=run_aggregate_emissions,
                        parent=self,
                        filename=filename
                    )
                    QgsApplication.taskManager().addTask(self.task)
            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")
                message_box('Aggregation error',f"Error: {error}")
    
    def rasterize_emissions_dialog(self):
        self.outputpath = QFileDialog.getExistingDirectory(None, "Choose output directory for raster NetCDF files")
        if (self.outputpath == ''):
            # user cancelled
            message_box('Rasterize error','No directory chosen, raster files not created.')
        else:
            # Get a list of files in the directory
            files_in_directory = os.listdir(self.outputpath)
            # Filter the list to include only NetCDF files
            netcdf_files = [file for file in files_in_directory if file.endswith(".nc")]
            if netcdf_files:
                message_box("Rasterize","NetCDF files already exist in provided output directory.\n" 
                + "New rasters will be named after the substances in the emission inventory "
                + "(for example PM10.nc). Files cannot be overwritten, so if such files already exist, "
                + "create a new output directory.")
                self.outputpath = QFileDialog.getExistingDirectory(None, "Choose output directory for raster NetCDF files, where no emissions rasters exist yet.")
            try:
                rasterDialog = RasterizeDialog(self)
                result = rasterDialog.exec_()  # Show the dialog as a modal dialog
                if result != QDialog.Accepted:
                    # user cancelled
                    message_box('Rasterize error',"No extent, srid and resolution defined, rasterization cancelled.")
                    return
                self.load_canvas = rasterDialog.load_to_canvas
                if self.load_canvas:
                    self.time_threshold = time.time()
                if rasterDialog.date[0] != '':
                    begin = datetime.datetime.strptime(rasterDialog.date[0], "%Y-%m-%d")
                    end = datetime.datetime.strptime(rasterDialog.date[1], "%Y-%m-%d")
                    self.task = RunBackgroundTask(
                        description="Rasterize emissions",
                        function=run_rasterize_emissions,
                        parent=self,
                        outputpath=self.outputpath,
                        cellsize=rasterDialog.cell_size, 
                        extent=rasterDialog.extent, 
                        srid=rasterDialog.raster_srid,
                        begin=begin,
                        end=end
                    )
                    
                else: 
                    self.task = RunBackgroundTask(
                        description="Rasterize emissions",
                        function=run_rasterize_emissions,
                        parent=self,
                        outputpath=self.outputpath, 
                        cellsize=rasterDialog.cell_size, 
                        extent=rasterDialog.extent, 
                        srid=rasterDialog.raster_srid
                    )
                
                QgsApplication.taskManager().addTask(self.task)

            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")
                message_box('Rasterize error',f"Error: {error}")
    

    def load_joined_pointsource_canvas(self):
        self.source_type = 'point'
        self.create_emission_table()


    def load_joined_areasource_canvas(self):
        self.source_type = 'area'
        self.create_emission_table()

    def load_joined_roadsource_canvas(self):
        self.source_type = 'road'
        self.create_emission_table()


    def load_joined_gridsource_canvas(self):
        try:
            self.db_path = os.environ.get("CETK_DATABASE_PATH", None)
            if self.db_path is None:
                message_box('Load GridSource error','Database not set yet, connect to '
                + ' an existing database or create a new one.')
                return
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            cursor.execute("SELECT id, name FROM edb_gridsource")
            result = cursor.fetchall()
            if len(result) > 0:
                timestamp = datetime.datetime.now().strftime("%m-%d-%Y_%H:%M")
                source_id, source_name = zip(*[(x[0], x[1]) for x in result])
                cursor.execute("SELECT source_id, raster FROM edb_gridsourcesubstance")
                result = cursor.fetchall()
                if len(result) > 0:
                    gss_source_id, gridsourcesubstance_rasters = zip(*[(x[0], x[1]) for x in result])
                else:
                    gss_source_id, gridsourcesubstance_rasters = [], []
                cursor.execute("SELECT source_id, raster FROM edb_gridsourceactivity")
                result = cursor.fetchall()
                if len(result) > 0:
                    gsa_source_id, gridsourceactivity_rasters = zip(*[(x[0], x[1]) for x in result])
                else:
                    gsa_source_id, gridsourceactivity_rasters = [], []
                connection.close()
                dbname = os.path.basename(self.db_path).split('.')[0]
                output_path = os.path.join(gettempdir(),dbname)
                if not os.path.exists(output_path):
                    os.mkdir(output_path)
                self.load_canvas = True
                self.time_threshold = time.time()
                for id, name in zip(source_id, source_name):
                    positions = [i for i, x in enumerate(gss_source_id) if x == id]
                    gss_rasters = [gridsourcesubstance_rasters[i] for i in positions]
                    positions = [i for i, x in enumerate(gsa_source_id) if x == id]
                    gsa_rasters = [gridsourceactivity_rasters[i] for i in positions]
                    unique_rasters = set(gss_rasters + gsa_rasters)
                    extent=[]
                    cellsize=[]
                    srid=[]
                    for raster in unique_rasters:
                        raster_layer = QgsRasterLayer(f'GPKG:{self.db_path}:raster_{raster}',raster)
                        raster_extent = (
                            raster_layer.dataProvider().extent().xMinimum(),
                            raster_layer.dataProvider().extent().yMinimum(),
                            raster_layer.dataProvider().extent().xMaximum(),
                            raster_layer.dataProvider().extent().yMaximum()
                        )
                        extent.append(raster_extent)
                        cellsize.append((raster_extent[2]-raster_extent[0])/raster_layer.dataProvider().xSize())
                        srid.append(raster_layer.crs().postgisSrid())
                    srid=set(srid)
                    if len(srid) != 1:
                        message_box('Load layers error',f"Cannot load grids with undefined or multiple srid for gridsource {name}")
                    else:
                        srid = srid.pop()
                    min_cellsize = min(cellsize)
                    result_extent = (
                        min(t[0] for t in extent), 
                        min(t[1] for t in extent), 
                        max(t[2] for t in extent), 
                        max(t[3] for t in extent)
                    )
                    self.outputpath = os.path.join(gettempdir(),dbname+'-'+name+'-'+timestamp)
                    if not os.path.exists(self.outputpath):
                        os.mkdir(self.outputpath)
                    else:
                        old_rasters = os.listdir(self.outputpath)
                        for file in old_rasters:
                            os.remove(os.path.join(self.outputpath,file))
                    # simultaneously running background tasks cannot have the same 
                    # variable name (eg self.task)
                    # message_box("rasterize task",f"cell size {min_cellsize}, extent {extent}, srid {srid}, grid_ids {id}")
                    setattr(self, f'task_{name}', RunBackgroundTask(
                        description=f"Rasterize emissions {name}",
                        function=run_rasterize_emissions,
                        parent=self,
                        outputpath=self.outputpath, 
                        cellsize=min_cellsize, 
                        extent=result_extent, 
                        srid=srid,
                        grid_ids=id
                    ))
                    QgsApplication.taskManager().addTask(getattr(self,f'task_{name}'))
            else:
                message_box("Load layers info","No gridsources exist in database.")
        except CalledProcessError as e:
            error = e.stderr.decode("utf-8")
            message_box('Load layers error',f"Error: {error}")

    def load_joined_sources_canvas(self):
        for self.source_type in ['point', 'area','road']:
            self.create_emission_table()


    def load_pointsource_canvas(self):
        self.source_type = 'point'
        self.load_interactive()

    def load_areasource_canvas(self):
        self.source_type = 'area'
        self.load_interactive()

    def load_gridsource_canvas(self):
        self.source_type = 'grid'
        self.load_interactive()

    def load_roadsource_canvas(self):
        self.source_type = 'road'
        self.load_interactive()

    def load_join(self):
        self.db_path = os.environ.get("CETK_DATABASE_PATH", "Database not set yet.")
        if self.db_path == "Database not set yet.":
            message_box('Warning','Cannot load layer, database not chosen yet.')
            return 
        db_name = os.path.basename(self.db_path).split('.')[0]
        timestamp = datetime.datetime.now().strftime("%m-%d-%Y_%H:%M")
        if self.source_type == 'point':
            table = 'edb_pointsource'
            join_table = 'pointsource_emissions'
            display_name = db_name + '-PointSource' + timestamp
        elif self.source_type == 'area':
            table = 'edb_areasource'
            join_table = 'areasource_emissions'
            display_name = db_name + '-AreaSource' + timestamp
        elif self.source_type == 'grid':
            table = 'edb_gridsource'
            join_table = 'gridsource_emissions'
            display_name = db_name + '-GridSource' + timestamp
        elif self.source_type == 'road':
            table = 'edb_roadsource'
            join_table = 'roadsource_emissions'
            display_name = db_name + '-RoadSource' + timestamp
        else:
            message_box('Warning', f"Cannot load layer, sourcetype {source_type} unknown.")

        # Create parameters for join by doing join through processing toolbox,
        # and using the lower button 'Advanced' > 'Copy as Python Command'
        parameters = { 'DISCARD_NONMATCHING' : False, 
        'FIELD' : 'id', # id in table for join
        'FIELDS_TO_COPY' : [], 
        'FIELD_2' : 'source_id', # id in join_table for join
        'INPUT' : f"spatialite://dbname=\'{self.db_path}\' table={table} (geom)", 
        'INPUT_2' : f"spatialite://dbname=\'{self.db_path}\' table={join_table}", 
        'METHOD' : 1, 
        'OUTPUT' : 'TEMPORARY_OUTPUT',
        'PREFIX' : '' }
        tmp_join = processing.run('qgis:joinattributestable',parameters)['OUTPUT']

        if self.source_type in ["area", "point"]:
            parameters_codeset_join = {'INPUT':tmp_join, 
            'FIELD':'activitycode1_id',
            'INPUT_2':f"spatialite://dbname=\'{self.db_path}\' table=edb_activitycode",
            'FIELD_2':'id',
            'FIELDS_TO_COPY':['code','label'],
            'METHOD':1,
            'DISCARD_NONMATCHING':False,
            'PREFIX':'codeset1_',
            'OUTPUT':'TEMPORARY_OUTPUT'}
            ac1_join = processing.run('qgis:joinattributestable',parameters_codeset_join)['OUTPUT']
            
            parameters_codeset_join['INPUT'] = ac1_join
            parameters_codeset_join['PREFIX'] = 'codeset2_'
            parameters_codeset_join['FIELD'] = 'activitycode2_id'
            ac2_join = processing.run('qgis:joinattributestable',parameters_codeset_join)['OUTPUT']

            parameters_codeset_join['INPUT'] = ac2_join
            parameters_codeset_join['PREFIX'] = 'codeset3_'
            parameters_codeset_join['FIELD'] = 'activitycode3_id'
            self.layer = processing.run('qgis:joinattributestable',parameters_codeset_join)['OUTPUT']
        else:
            self.layer = tmp_join
        self.layer.setName(display_name)
        QgsProject.instance().addMapLayer(self.layer)


    def load_interactive(self):
        self.db_path = os.environ.get("CETK_DATABASE_PATH", "Database not set yet.")
        if self.db_path == "Database not set yet.":
            message_box('Warning','Cannot load layer, database not chosen yet.')
            return 
        db_name = os.path.basename(self.db_path).split('.')[0]
        # Connect to the database
        uri = QgsDataSourceUri()
        uri.setDatabase(self.db_path)
        schema = ''
        if self.source_type =='point':
            table = 'edb_pointsource'
            display_name = db_name + '-PointSource'
        elif self.source_type == 'area':
            table = 'edb_areasource'
            display_name = db_name + '-AreaSource'
        elif self.source_type == 'grid':
            table = 'edb_gridsource'
            display_name = db_name + '-GridSource' 
        elif self.source_type == 'road':
            table = 'edb_roadsource'
            join_table = 'roadsource_emissions'
            display_name = db_name + '-RoadSource'
        else:
            message_box('Warning',f"Cannot load layer, sourcetype {source_type} unknown.")
        geom_column = 'geom'
        uri.setDataSource(schema, table, geom_column)
        self.layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')
        crs = QgsCoordinateReferenceSystem('EPSG:4326')
        self.layer.setCrs(crs)
        QgsProject.instance().addMapLayer(self.layer)
        
    def show_srid_dialog(self):
        crs_dialog = QgsProjectionSelectionDialog()
        crs_dialog.setWindowTitle("Select default coordinate system for your database")
        if crs_dialog.exec_():
            crs = crs_dialog.crs()
            epsg_code = crs.authid().split(":")[-1]
            return epsg_code
        else:
            return None

        

def show_help(self):
    """Display application help to the user."""
    help_url = 'https://git.smhi.se/foclair/minimal-eclair/-/blob/develop/README.md'
    QDesktopServices.openUrl(QUrl(help_url))


def message_box(title,text):
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.exec_()

class CheckboxDialog(QDialog):
    def __init__(self, parent=None, box_labels=None, dry_run=False):
        super().__init__(parent)
        self.box_labels = box_labels
        self.dry_run = dry_run
        self.initUI()

    def initUI(self):
        # Create a layout for the dialog
        layout = QVBoxLayout()
        if self.dry_run:
            label = QLabel("Choose sheets to validate:")
            self.setWindowTitle("Validate import file")
        else:
            label = QLabel("Choose sheets to import:")
            self.setWindowTitle("Import data")
        layout.addWidget(label)

        # Create checkboxes for each element in box_labels
        self.checkboxes = {}
        for label in self.box_labels:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)  
            layout.addWidget(checkbox)
            self.checkboxes[label] = checkbox

        self.setLayout(layout)

        if self.dry_run:
            btn_action_import_sheets = QPushButton("Validate sheets")
        else:
            btn_action_import_sheets = QPushButton("Import sheets")
        layout.addWidget(btn_action_import_sheets)
        btn_action_import_sheets.clicked.connect(self.import_sheets_dialog)

    def import_sheets_dialog(self):
        # Store the state of the checkboxes and close dialog
        self.sheet_names = [label for label in self.box_labels if self.checkboxes[label].isChecked()]
        self.accept()

class RasterizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        settings = run_get_settings()
        
        # Create a layout for the dialog
        self.setWindowTitle("Define rasterize settings")
        layout = QVBoxLayout()
        label = QLabel("Define srid, extent and resolution of output raster."
        +" Current (rounded) canvas extent and srid are pre-filled but can be adapted.\n"
        +"Raster extent and resolution have to be provided in meters, not degrees (a raster with EPSG 4326 is not possible).")
        layout.addWidget(label)

        srid_label = QLabel("Enter a coordinate system (EPSG, 4-5 integers):")
        layout.addWidget(srid_label)
        self.srid_input = QLineEdit(self)
        self.srid_input.setInputMask("99999")  # Max 5 integers
        self.srid_input.setMaximumWidth(150)
        # Initialize with current canvas CRS
        canvas_crs = iface.mapCanvas().mapSettings().destinationCrs()
        canvas_epsg = int(canvas_crs.authid().split(':')[-1])
        default_epsg = settings.srid
        if canvas_epsg != 4326:
            self.srid_input.setText(str(canvas_epsg))
        else:
            self.srid_input.setText(str(default_epsg))
        layout.addWidget(self.srid_input)

        # TODO would be nice to have option 'smallest extent to cover all sources'
        extent_label = QLabel("Enter x and y coordinates for lower left (x1, y1) and upper right (x2, y2) corners of output extent:")
        layout.addWidget(extent_label)
        extent_layout = QHBoxLayout()
        self.extent_input = {}
        self.extent_labels = ["x1:", "y1:", "x2:" ,"y2:"]
        current_extent = iface.mapCanvas().extent()
        if canvas_epsg == 4326:
            # convert from degrees to default_epsg, raster coordinates have to be metric
            target_crs = QgsCoordinateReferenceSystem(default_epsg)
            transform = QgsCoordinateTransform(canvas_crs, target_crs, QgsProject.instance())
            current_extent = transform.transform(current_extent)

        current_corners = {"x1:":floor(current_extent.xMinimum()/1000)*1000,
            "y1:":floor(current_extent.yMinimum()/1000)*1000, 
            "x2:":ceil(current_extent.xMaximum()/1000)*1000,
            "y2:":ceil(current_extent.yMaximum()/1000)*1000}

        for label_text in self.extent_labels:
            label = QLabel(label_text)
            extent_layout.addWidget(label)
            line_edit = QLineEdit(self)
            line_edit.setValidator(QDoubleValidator())   
            line_edit.setText(str(current_corners[label_text]))
            extent_layout.addWidget(line_edit)
            self.extent_input[label_text] = line_edit
        layout.addLayout(extent_layout)


        resolution_label = QLabel("Enter the desired resolution of the output extent, in meters:")
        layout.addWidget(resolution_label)
        resolution_layout = QHBoxLayout()
        self.resolution_input = {}
        self.resolution_labels = ["resolution [m]"]
        for label_text in self.resolution_labels:
            label = QLabel(label_text)
            resolution_layout.addWidget(label)
            line_edit = QLineEdit(self)
            line_edit.setValidator(QDoubleValidator())   # Set input mask for floats
            line_edit.setText(str(1000)) # initialize to 1km res
            resolution_layout.addWidget(line_edit)
            self.resolution_input[label_text] = line_edit
        layout.addLayout(resolution_layout)

        date_label = QLabel("If one raster per hour is desired, enter begin and end date for rasters (optional).")
        # TODO cetk now always assumes timezone UTC, could make it user-defined.
        layout.addWidget(date_label)
        date_layout = QHBoxLayout()
        self.date_input = {}
        self.date_labels = ["begin [yyyy-mm-dd]", "end [yyyy-mm-dd]"]
        for label_text in self.date_labels:
            label = QLabel(label_text)
            date_layout.addWidget(label)
            line_edit = QLineEdit(self) 
            date_layout.addWidget(line_edit)
            self.date_input[label_text] = line_edit
        layout.addLayout(date_layout)

        # Create checkbox
        self.checkbox = QCheckBox("Load rasters to canvas after creation.")
        self.checkbox.setChecked(True)  # Set initial state
        layout.addWidget(self.checkbox)
        self.setLayout(layout)

        # TODO let unit be user defined?
        btn_action_run_rasterizer = QPushButton("Create rasters")
        layout.addWidget(btn_action_run_rasterizer)
        btn_action_run_rasterizer.clicked.connect(self.run_rasterizer)

    def run_rasterizer(self):
        self.raster_srid = int(self.srid_input.text())
        if self.raster_srid < 1024 or self.raster_srid > 32767:
            message_box("Rasterize error", "EPSG codes defining coordinate systems should be between 1024 and 32767.")
            return
        self.extent = [float(self.extent_input[label].text()) for label in self.extent_labels]
        if self.extent[2] <= self.extent[0] or self.extent[3] <= self.extent[1]:
            message_box("Rasterize error", "Unvalid extent, x2 should be larger than x1 and y2 larger than y1.")
            return
        resolution = [float(self.resolution_input[label].text()) for label in self.resolution_labels]
        if resolution[0] <= 0:
            message_box("Rasterize error", "Unvalid resolution, should be a number larger than 0.")
            return        
        self.cell_size = resolution[0]
        self.date = [self.date_input[label].text() for label in self.date_labels]
        if self.date[0] != '':
            try:
                begin = datetime.datetime.strptime(self.date[0], "%Y-%m-%d")
            except ValueError:
                message_box("Rasterize error", "Incorrect begin date. For example, 1 february 2022 has the format: 2022-02-01")
                return
            if self.date[1] != '':
                try:
                    end = datetime.datetime.strptime(self.date[1], "%Y-%m-%d")
                except ValueError:
                    message_box("Rasterize error", "Incorrect end date. For example, 1 february 2022 has the format: 2022-02-01")
                    return
                if begin > end:
                    message_box("Rasterize error", "End date has to be after begin date.")
                    return
            else:
                message_box("Rasterize error", "If begin date is specified, end date has to be specified too.")
                return
        elif self.date[1] != '':
            message_box("Rasterize error", "If end date is specified, begin date has to be specified too.")
            return
        # below is now organised in cetk adjust extent    
        # self.nx = ceil((self.extent[2] - self.extent[0]) / resolution[0]) # always at least cover provided extent
        # self.ny = ceil((self.extent[3] - self.extent[1]) / resolution[1]) # then nx, ny cannot be 0 either.
        # convert extent to format for cetk --rasterize command "x1,y1,x2,y2"
        # self.extent = str(self.extent[0])+","+str(self.extent[1])+","+str(self.extent[0]+self.nx*resolution[0])+","+str(self.extent[1]+self.ny*resolution[1])
        # message_box("info",self.extent)
        # Store the state of the checkbox
        
        self.load_to_canvas = self.checkbox.isChecked()
        self.accept()

class ChooseCodesetDialog(QDialog):
    def __init__(self,plugin, filename, codesets=None):
        super().__init__()
        self.filename = filename
        self.codesets = codesets
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Emission aggregation")
        layout = QVBoxLayout()
        label = QLabel("Choose the codeset for which emissions should be aggregated.")
        layout.addWidget(label)
        label = QLabel(str(self.codesets))
        layout.addWidget(label)

        layout_buttons = QHBoxLayout()
        for codeset_i in self.codesets:
            btn_action = QPushButton(codeset_i)
            layout.addWidget(btn_action)
            btn_action.clicked.connect(lambda checked, cs=codeset_i: self.run_aggregation(cs))
        self.setLayout(layout)

    @pyqtSlot()
    def run_aggregation(self,codeset):
        self.accept()
        try:
            message_box('Aggregate emissions',"Emission aggregation for codeset "+str(codeset)+" starts after clicking OK.\n")      
            self.task = RunBackgroundTask(
                description="Aggregate emissions",
                function=run_aggregate_emissions,
                parent=self,
                filename=self.filename,
                codeset=codeset
            )
            QgsApplication.taskManager().addTask(self.task)
        except CalledProcessError as e:
            error = e.stderr.decode("utf-8")
            message_box('Aggregation error',f"Error: {error}")




class TableDialog(QDialog):
    def __init__(self,plugin, title=None, text=None, stdout=None):
        super().__init__()
        self.title = title
        self.plugin = plugin
        self.text = text
        self.stdout = stdout
        self.initUI()

    def initUI(self):


        self.setWindowTitle(self.title)
        layout = QVBoxLayout()
        label = QLabel(self.text)
        layout.addWidget(label)

        if type(self.stdout) == dict:
            table_dict = self.stdout

            # TODO: do not know whether timevar is updated or created, 
            # skipping from progress tabel for now
            if 'timevar' in table_dict:
                table_dict.pop('timevar')
            nr_rows = len(table_dict.keys())
            tableWidget = QTableWidget(self)
            tableWidget.setRowCount(nr_rows)
            tableWidget.setColumnCount(2)

            for row, key in enumerate(sorted(table_dict.keys())):
                item = QTableWidgetItem(str(table_dict[key]['created']))
                tableWidget.setItem(row, 0, item)
                item = QTableWidgetItem(str(table_dict[key]['updated']))
                tableWidget.setItem(row, 1, item)

            # Set headers for the table
            if self.plugin.dry_run:
                tableWidget.setHorizontalHeaderLabels(['to be created', 'to be updated'])
                tableWidget.setVerticalHeaderLabels(sorted(table_dict.keys()))
            else:
                tableWidget.setHorizontalHeaderLabels(['created', 'updated'])
                tableWidget.setVerticalHeaderLabels(sorted(table_dict.keys()))

            # Resize the columns to fit the content
            tableWidget.resizeColumnsToContents()
            tableWidget.resizeRowsToContents()
            tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            # tableWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            margins = layout.contentsMargins()
            max_row_label_width = 0
            for i in range(tableWidget.verticalHeader().count()):
                row_label_width = tableWidget.verticalHeader().sectionSize(i)
                max_row_label_width = max(max_row_label_width, row_label_width)
            tablewidth = (margins.left() + margins.right() + tableWidget.frameWidth() * 2 +
            max_row_label_width + tableWidget.horizontalHeader().length() + 10)
            tableWidget.setFixedWidth(tablewidth*4)
            tableWidget.setFixedHeight(margins.top() + margins.bottom() +
            tableWidget.verticalHeader().length()  + tableWidget.horizontalHeader().width())
            layout.addWidget(tableWidget)
        else:
            label = QLabel(self.stdout)
            layout.addWidget(label)

        self.setLayout(layout)
        self.adjustSize()


def load_rasters_to_canvas(directory_path, time_threshold):
    # Get a list of files in the directory
    files_in_directory = os.listdir(directory_path)
    # Filter the list to include only files modified after the time threshold
    modified_rasters = [
        file for file in files_in_directory 
        if (os.path.getmtime(os.path.join(directory_path, file)) > time_threshold)
        and file.endswith(".nc")
    ]
    # Check if there are any modified files
    if modified_rasters:
        project = QgsProject.instance()
        group_name = Path(directory_path).name
        root = project.layerTreeRoot()
        grp = root.addGroup(group_name)
        
        for raster_file in modified_rasters:
            # Construct the full path to the raster file
            full_path = os.path.join(directory_path, raster_file)
            # Create a raster layer
            raster_layer = QgsRasterLayer(full_path, raster_file, "gdal")
            # statistics band 1
            provider = raster_layer.dataProvider()
            stats = provider.bandStatistics(1, QgsRasterBandStats.All)
            # only visualize non-zero rasters:
            if stats.sum > 0:
                # Add the raster layer to the project
                project.addMapLayer(raster_layer, False)
                grp.insertChildNode(1, QgsLayerTreeLayer(raster_layer))



MESSAGE_CATEGORY = "Eclair info"

class RunImportTask(QgsTask):
    def __init__(self, description, file_path, sheets, dry_run=False):
        super().__init__(description, QgsTask.CanCancel)
        self.file_path = file_path
        self.sheets = sheets
        if "validation" in self.description():
            self.dry_run = True
        else:
            self.dry_run = False
        self.exception = None

    def check_process_ready(self):
        if self.proc:
            return self.proc.poll() is not None
        return False

    def run(self):
        """Implement heavy lifting.
        Periodically test for isCanceled() to gracefully abort.
        Raising exceptions here will crash QGIS, raise them in self.finished instead.
        """
        QgsMessageLog.logMessage('Started import task', MESSAGE_CATEGORY, Qgis.Info)
        try:
            self.backup_path, self.proc = run_import(self.file_path, self.sheets, dry_run=self.dry_run)
            for i in range(3600):
                # Check if the file size is greater than zero
                if self.check_process_ready(): 
                    return True
                else:
                    if self.isCanceled():
                        if self.dry_run:
                            self.exception = "Validation cancelled by user"
                        else:
                            self.exception = "Import cancelled by user"
                        self.cancel()
                        return False
                    time.sleep(1)
                    # set progress 1 % per second first 50 seconds
                    # second half progress estimation based on max 20min 
                    if i < 51:
                        self.setProgress(i)
                    else:
                        self.setProgress(50+i/1150.*50.)
            self.exception = "Failed to import file within one hour, decrease file size"
        except Exception as e:
            self.exception =  e
            return False
        return True
        

    def finished(self, result):
        """
        This function is automatically called when the task has
        completed (successfully or not). Result is the return value from self.run
        """
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed\n'.format(name=self.description()),
                MESSAGE_CATEGORY, Qgis.Success)
                    
            output_path = os.path.dirname(os.environ.get("CETK_DATABASE_PATH"))
            stdout_files = glob.glob(os.path.join(gettempdir(), 'cetk_import_*_stdout.log'))
            stderr_files = glob.glob(os.path.join(gettempdir(), 'cetk_import_*_stderr.log'))
            
            # Read the latest stderr file
            stderr_files.sort(key=lambda f: int(f.split('_')[-2]))
            if stderr_files:
                latest_stderr_file = stderr_files[-1]
                with open(latest_stderr_file, 'r') as f:
                    self.stderr_content = f.read()
            else:
                self.stderr_content = None

            validation_msgs = []
            updates = []

            def handle_line(l):
                error = False
                if l.startswith("VALIDATION"):
                    validation_msgs.append(l.split("VALIDATION:")[1].strip())
                elif l.startswith("ERROR"):
                    validation_msgs.append(l)
                else:
                    error = True
                    QgsMessageLog.logMessage(l, level=Qgis.Info)
                return error
            
            error = False
            # from qgis.PyQt.QtCore import pyqtRemoveInputHook;pyqtRemoveInputHook();breakpoint()
            if  'successfully' in self.stderr_content:
                if self.dry_run:
                    changes = eval(self.stderr_content.split('\n')[-2].split("validated")[1].strip())
                else:
                    changes = eval(self.stderr_content.split('\n')[-2].split("imported")[1].strip())
            elif 'Traceback' in self.stderr_content:
                traceback = self.stderr_content
                error = True
            else:
                for l in self.stderr_content.split('\n'):
                    error = handle_line(l)
                if error:
                    traceback = self.stderr_content


            if self.backup_path is not None:
                self.backup_path.unlink()

            if self.dry_run:
                if error:
                    # from qgis.PyQt.QtCore import pyqtRemoveInputHook;pyqtRemoveInputHook();breakpoint()
                    tableDialog = TableDialog(
                        self,'Validation status',
                        "Did not validate full file. \n "
                        "Error occurred that could not be handled by validation \n"
                        "Try to correct spreadsheet using error information below: \n ",
                        os.linesep.join(traceback.split('\n'))
                    )
                elif len(validation_msgs) > 0:
                    # len_errors = len(validation_msgs) - 1 
                    tableDialog = TableDialog(
                        self,'Validation status',
                        "Validated file successfully. \n "
                        "Found errors, correct spreadsheet using error information "
                        "given below before importing data: \n",
                        os.linesep.join(validation_msgs)
                    )
                else:
                    tableDialog = TableDialog(
                        self,'Validation status',
                        "Validated file successfully. \n"
                        "No changes to database yet, but number of features to be "
                        "created or updated if file would be imported are summarized in table.",
                        changes
                    )
                tableDialog.exec_() 
            else:
                if error:
                    tableDialog = TableDialog(
                        self,'Import status',
                        "Did not import file successfully. \n "
                        "Error occurred that could not be handled by Eclair. \n"
                        "First validate the file, correct spreadsheet using error information  \n"
                        "given below untill reaching a successful validation before importing data: \n",
                        os.linesep.join(traceback.split('\n'))
                    )
                if len(validation_msgs) > 0:
                    tableDialog = TableDialog(
                        self,'Import status',
                        "Did not import file successfully. \n "
                        "Import stopped at error. First validate the file, correct spreadsheet using error information "
                        "given below untill reaching a successful validation before importing data: \n",
                        os.linesep.join(validation_msgs)
                    )
                else:
                    tableDialog = TableDialog(
                        self, 'Import status',
                        'Imported data successfully. \n'
                        ' Number of features created or updated summarized in table.',
                        changes 
                    )
                tableDialog.exec_()  
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without '\
                    'exception (probably the task was manually '\
                    'canceled by the user)'.format(
                        name=self.description()),
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                if type(self.exception) == str:
                    error = self.exception
                else:
                    error = self.exception.stderr.decode("utf-8")
                if "Database unspecified does not exist, first run 'cetk create' or 'cetk migrate'" in error:
                    message_box('Error',f"Error: a target database is not specified yet,"
                    +" choose an existing or create a new database first.")
                else:
                    import_error = error.split('ImportError:')[-1]
                    if self.dry_run:
                        message_box('Validation error',f"Error: {import_error}")
                    else:
                        message_box('Import error',f"Error: {import_error}")


    def cancel(self):
        QgsMessageLog.logMessage(
            f"Task {self.description()} was canceled",
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()




class RunBackgroundTask(QgsTask):
    def __init__(self, description, function, parent, *args, **kwargs):
        super().__init__(description, QgsTask.CanCancel)
        self.function = function
        self.parent = parent
        self.args = args
        self.kwargs = kwargs
        self.exception = None
        self.proc = None

    def check_process_ready(self):
        if self.proc:
            return self.proc.poll() is not None
        return False

    def run(self):
        """Implement heavy lifting.
        Periodically test for isCanceled() to gracefully abort.
        Raising exceptions here will crash QGIS, raise them in self.finished instead.
        """
        QgsMessageLog.logMessage(f"Started task {self.description()}", MESSAGE_CATEGORY, Qgis.Info)
        try:
            self.proc = self.function(*self.args, **self.kwargs)
            for i in range(3600):
                # Check if the process is ready
                if self.check_process_ready(): 
                    return True
                else:
                    if self.isCanceled():
                        self.cancel()
                        return False
                    time.sleep(1)
                    if i < 51:
                        self.setProgress(i)
                    else:
                        self.setProgress(50+i/1150.*50.)
            self.exception = f"Failed to complete {self.description()} within one hour."
        except Exception as e:
            self.exception =  e
            return False
        return True

    def finished(self, result):
        """
        This function is automatically called when the task has
        completed (successfully or not). Result is the return value from self.run
        """
        if result:
            QgsMessageLog.logMessage(
                f"Task {self.description()} completed",
                MESSAGE_CATEGORY, Qgis.Success)
            if "Rasterize emissions" in self.description():
                if self.parent.load_canvas:
                    load_rasters_to_canvas(self.kwargs["outputpath"], self.parent.time_threshold)
            elif self.description() == "Prepare emissions for static visualisation":
                self.parent.load_join()
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    f"Task {self.description()} not successful but without "\
                    'exception (probably the task was manually '\
                    'canceled by the user)',
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                if isinstance(self.exception, str):
                    error = self.exception
                else:
                    error = str(self.exception)
                message_box('Eclair error', f"Error: {error}")

    def cancel(self):
        QgsMessageLog.logMessage(
            f"Task {self.description()} was canceled",
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()
