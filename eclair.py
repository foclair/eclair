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
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtWidgets import QFileDialog, QCheckBox, QRadioButton, QButtonGroup, QTabWidget, QMainWindow #, QLineEdit
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase
from PyQt5.QtCore import Qt
from qgis.utils import iface
from qgis.core import QgsVectorLayer, QgsProject, QgsDataSourceUri, QgsCoordinateReferenceSystem
import time

import os
import sys
import subprocess
import site
import ast
from pathlib import Path


ETK_BINPATH = os.path.expanduser("~/.local/bin")
os.environ["PATH"] += f":{ETK_BINPATH}"
sys.path += [f"/home/{os.environ['USER']}/.local/lib/python3.9/site-packages"]


from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
       
class Eclair(QWidget):
    def __init__(self, iface):
        super(Eclair, self).__init__()
        self.iface = iface
        self.setWindowTitle("ECLAIR")
        self.dock_widget = None  # Initialize the dock widget        

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
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        # Create a main widget for the dock widget
        self.main_widget = QWidget(self)
        self.setWidget(self.main_widget)
        # Set the minimum height for the dock widget
        self.setMinimumHeight(200) 
        # Set the layout for the main widget
        layout = QVBoxLayout(self.main_widget)
        self.tab_widget = QTabWidget(self.main_widget)
        layout.addWidget(self.tab_widget)

        # To automatically update database changes in visualized layer
        self.setup_watcher()
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
        self.tab_widget.addTab(self.tab_edit, "Edit")
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

        btn_action_existing_database = QPushButton("Choose existing database to edit", self.tab_db)
        layout_db.addWidget(btn_action_existing_database)
        btn_action_existing_database.clicked.connect(self.load_existing_database_dialog)

        btn_action_new_database = QPushButton("Create and connect to new database", self.tab_db)
        layout_db.addWidget(btn_action_new_database)
        btn_action_new_database.clicked.connect(self.create_new_database_dialog)

        # Import
        layout_import = QVBoxLayout()
        layout_import.setAlignment(Qt.AlignTop)
        self.tab_import.setLayout(layout_import)
        label = QLabel("Import data to your database (*.xlsx):", self.tab_import)
        layout_import.addWidget(label)

        btn_action_import_pointsourceactivities = QPushButton("Import data from spreadsheet", self.tab_import)
        layout_import.addWidget(btn_action_import_pointsourceactivities)
        btn_action_import_pointsourceactivities.clicked.connect(self.import_pointsources)

        btn_action_validate_pointsourceactivities = QPushButton("Validate spreadsheet without importing", self.tab_import)
        layout_import.addWidget(btn_action_validate_pointsourceactivities)
        btn_action_validate_pointsourceactivities.clicked.connect(self.validate_pointsources)

        # Edit
        layout_edit = QVBoxLayout()
        layout_edit.setAlignment(Qt.AlignTop)
        self.tab_edit.setLayout(layout_edit)
        label = QLabel("Functions for editing previously imported data.", self.tab_edit)
        layout_edit.addWidget(label)
        btn_action_edit = QPushButton(" Edit imported data ", self.tab_edit)
        btn_action_edit.setFont(italic_font)
        layout_edit.addWidget(btn_action_edit)

        # Export
        layout_export = QVBoxLayout()
        layout_export.setAlignment(Qt.AlignTop)
        self.tab_export.setLayout(layout_export)
        label = QLabel("Functions for exporting previously imported data.", self.tab_export)
        layout_export.addWidget(label)
        btn_action_export_all = QPushButton(" Export all imported data ", self.tab_export)
        btn_action_export_all.setFont(italic_font)
        layout_export.addWidget(btn_action_export_all)
        btn_action_export = QPushButton(" Export only pointsources, areasources or road sources ", self.tab_export)
        btn_action_export.setFont(italic_font)
        layout_export.addWidget(btn_action_export)

        # Calculate emissions
        layout_calculate = QVBoxLayout()
        layout_calculate.setAlignment(Qt.AlignTop)
        self.tab_calculate.setLayout(layout_calculate)
        label = QLabel("Functions for calculating previously imported data.", self.tab_calculate)
        layout_calculate.addWidget(label)

        btn_action_create_table = QPushButton(" Create table all pointsources and areasources, combining direct emissions and activities ", self.tab_calculate)
        layout_calculate.addWidget(btn_action_create_table)
        btn_action_create_table.clicked.connect(self.create_emission_table_dialog)

        btn_action_aggregate = QPushButton(" Aggregate emissions per sector ", self.tab_calculate)
        layout_calculate.addWidget(btn_action_aggregate)
        btn_action_aggregate.clicked.connect(self.aggregate_emissions_dialog)

        btn_action_raster = QPushButton(" Calculate raster of emissions ", self.tab_calculate)
        btn_action_raster.setFont(italic_font)
        layout_calculate.addWidget(btn_action_raster)

        # Visualize emissions
        layout_visualize = QVBoxLayout()
        layout_visualize.setAlignment(Qt.AlignTop)
        self.tab_visualize.setLayout(layout_visualize)
        label = QLabel("Functions for visualizing previously imported data.", self.tab_visualize)
        layout_visualize.addWidget(label)
        btn_action_visualize_point = QPushButton(" Load layers to canvas ", self.tab_visualize)
        layout_visualize.addWidget(btn_action_visualize_point)
        btn_action_visualize_point.clicked.connect(self.load_data)
        # btn_action_visualize_area = QPushButton(" Visualize areasources ", self.tab_visualize)
        # layout_visualize.addWidget(btn_action_visualize_area)
        # btn_action_visualize_area.clicked.connect(self.load_areasource_canvas)
        # Set the tab widget as the central widget
        # self.setCentralWidget(self.tab_widget)

    def update_db_label(self):
        db_path = os.environ.get("ETK_DATABASE_PATH", "Database not set yet.")
        self.db_label.setText(f"Eclair is currently connected to database:\n {db_path}")

    def load_existing_database_dialog(self):
        db_path, _ = QFileDialog.getOpenFileName(self.tab_db, "Open SQLite database", "", "Database (*.sqlite)")
        if db_path == '':
            # user cancelled
            message_box('Warning','No file chosen, database not configured.')
        else:
            os.environ["ETK_DATABASE_PATH"] = db_path
            self.update_db_label()
            message_box('Load database',f"Database succesfully chosen database {db_path}.")

    def create_new_database_dialog(self):
        db_path, _ = QFileDialog.getSaveFileName(None, "Create new SQLite database", "", "Database (*.sqlite)")
        if (db_path == '') or (db_path.split('.')[-1] !='sqlite'):
            # user cancelled
            message_box('Warning','No *.sqlite file chosen, database not created.')
        else:
            from etk.tools.utils import CalledProcessError, create_from_template
            try:
                # TODO should make sure that template database is migrated before
                # creating new from template!
                proc = create_from_template(db_path)
                os.environ["ETK_DATABASE_PATH"] = db_path
                self.update_db_label()
                message_box('Created database',f"Successfully created database {db_path}")
            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")    
                message_box('Import error',f"Error: {error}")
    
    def import_pointsources(self):
        self.dry_run = False
        self.import_pointsourceactivities_dialog()

    def validate_pointsources(self):
        self.dry_run = True
        self.import_pointsourceactivities_dialog()

    def import_pointsourceactivities_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open pointsourceactivities file", "", "Spreadsheet files (*.xlsx)")
        if file_path: #if file_path not empty string (user did not click cancel)
            from openpyxl import load_workbook
            workbook = load_workbook(filename=file_path, data_only=True)
            # workbook.worksheets  compare to SHEET_NAMES
            from etk.edb.const import SHEET_NAMES
            valid_sheets = [sheet.title for sheet in workbook.worksheets if sheet.title in SHEET_NAMES]
            
            checkboxDialog = CheckboxDialog(self,valid_sheets, self.dry_run)
            result = checkboxDialog.exec_()  # Show the dialog as a modal dialog
            if result == QDialog.Accepted:
                sheets = checkboxDialog.sheet_names
            else:
                if self.dry_run:
                    message_box('Validation progress','validating all valid sheets '+str(valid_sheets))
                else:
                    message_box('Importing progress','importing all valid sheets '+str(valid_sheets))
                sheets = SHEET_NAMES
            
            from etk.tools.utils import CalledProcessError, run_import
            try:
                (stdout, stderr) = run_import(file_path, str(sheets), dry_run=self.dry_run)
                if self.dry_run:
                    tableDialog = TableDialog(self,'Validation status','Validated file with pointsourceactivities successfully ',stdout.decode("utf-8"))
                    tableDialog.exec_() 
                else:
                    tableDialog = TableDialog(self,'Import status','Imported pointsourceactivities successfully ',stdout.decode("utf-8"))
                    tableDialog.exec_()  
            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")
                if "Database unspecified does not exist, first run 'etk create' or 'etk migrate'" in error:
                    message_box('Error',f"Error: a target database is not specified yet,"
                    +" choose an existing or create a new database first.")
                else:
                    import_error = error.split('ImportError:')[-1]
                    message_box('Import error',f"Error: {import_error}")
        else:
            # user cancelled
            message_box('Import error','No file chosen, no data imported.')

    def create_emission_table_dialog(self):
        #TODO catch exception if database does not have any emissions imported yet
        from etk.tools.utils import CalledProcessError, run_update_emission_tables
        db_path = os.environ.get("ETK_DATABASE_PATH", "Database not set yet.")
        try:
            (stdout, stderr) = run_update_emission_tables(db_path)
            message_box('Created emission table',"Successfully created emission table")
        except CalledProcessError as e:
            error = e.stderr.decode("utf-8")
            message_box('Import error',f"Error: {error}")

    def aggregate_emissions_dialog(self):
        #TODO catch exception if table not created yet, or create table on the fly in that case?
        from etk.tools.utils import CalledProcessError, run_aggregate_emissions
        filename, _ = QFileDialog.getSaveFileName(None, "Choose filename for aggregated emissions table", "", "(*.csv)")
        if (filename == '') or (filename.split('.')[-1] !='csv'):
            # user cancelled
            message_box('Warning','No *.csv file chosen, aggregated table not created.')
        else:
            try:
                #TODO give user choice which codeset to aggregate from;
                #  how to know which exist?
                (stdout, stderr) = run_aggregate_emissions(filename,codeset='code_set1')
                message_box('Aggregate emissions',"Successfully aggregated emissions.")
            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")
                message_box('Import error',f"Error: {error}")

    def setup_watcher(self):
        # Set up the watchdog observer
        self.event_handler = self.FileChangeHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path='.', recursive=False)
        self.observer.start()

    def load_pointsource_canvas(self):
        self.source_type = 'point'
        self.load_data()

    def load_areasource_canvas(self):
        self.source_type = 'area'
        self.load_data()

    def load_data(self):
        # Get the path to the SQLite database file
        self.db_path = os.environ.get("ETK_DATABASE_PATH", "Database not set yet.")
        if self.db_path == "Database not set yet.":
            message_box('Warning','Cannot load layer, database not chosen yet.')
            return 
        self.load_all_sources()
        message_box('Progress',f"Data loaded from {self.db_path}")
    
    def load_all_sources(self):
        self.tables = ['edb_pointsource','edb_areasource']
        db_name = os.path.basename(self.db_path).split('.')[0]
        # Create a group layer
        self.group = QgsProject.instance().layerTreeRoot().addGroup(db_name)
        self.display_names = {'edb_pointsource':'PointSource','edb_areasource':'AreaSource'}
        for self.table in self.tables:
            self.display_name = self.display_names[self.table]
            self.load_layer()
    
    def load_layer(self):
        # Connect to the database
        uri = QgsDataSourceUri()
        uri.setDatabase(self.db_path)
        schema = ''
        geom_column = 'geom'
        uri.setDataSource(schema, self.table, geom_column)
        self.layer = QgsVectorLayer(uri.uri(), self.display_name, 'spatialite')
        crs = QgsCoordinateReferenceSystem('EPSG:4326')
        self.layer.setCrs(crs)
        self.group.addLayer(self.layer)

    class FileChangeHandler(FileSystemEventHandler):
        def __init__(self, file_handler):
            self.file_handler = file_handler
            self.last_modified_times = {}
        def on_any_event(self, event):
            if event.is_directory:
                return
            elif event.event_type == 'modified' and event.src_path == self.file_handler.db_path:
                # Check which tables have been modified and reload only those
                for table in self.file_handler.tables:
                    table_path = f"{self.file_handler.db_path}.{table}"
                    last_modified_time = self.last_modified_times.get(table, None)
                    # Get the current modification time
                    current_modified_time = QDateTime().currentDateTime().toMSecsSinceEpoch()
                    if last_modified_time is None or current_modified_time > last_modified_time:
                        # the new point shows up, but the message box does not, why not?
                        message_box("NOTE","Reloading {table} due to changes in {event.src_path}")
                        self.file_handler.table = table
                        self.file_handler.display_name = self.file_handler.display_names[table]
                        self.file_handler.load_layer()
                        self.last_modified_times[table] = current_modified_time


def show_help(self):
    """Display application help to the user."""
    help_url = 'https://git.smhi.se/foclair/minimal-eclair/-/blob/develop/README.md'
    QDesktopServices.openUrl(QUrl(help_url))


def message_box(title,text):
    # For this example, let's display the file contents in a message box.
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
        else:
            label = QLabel("Choose sheets to import:")
        layout.addWidget(label)

        # Create checkboxes for each element in the list
        self.checkboxes = {}
        for label in self.box_labels:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)  # Set initial state
            layout.addWidget(checkbox)
            self.checkboxes[label] = checkbox

        # Set the layout for the dialog
        self.setLayout(layout)

        if self.dry_run:
            btn_action_import_sheets = QPushButton("Validate sheets")
        else:
            btn_action_import_sheets = QPushButton("Import sheets")
        layout.addWidget(btn_action_import_sheets)
        btn_action_import_sheets.clicked.connect(self.import_sheets_dialog)

    def import_sheets_dialog(self):
        # Store the state of the checkboxes
        self.sheet_names = [label for label in self.box_labels if self.checkboxes[label].isChecked()]
        # close the checkbox dialog
        self.accept()


class TableDialog(QDialog):
    def __init__(self,plugin, title=None, text=None, stdout=None):
        super().__init__()
        self.title = title
        self.plugin = plugin
        self.text = text
        self.stdout = stdout
        self.initUI()

    def initUI(self):
        # convert stdout to tuple 
        stdout = ast.literal_eval(self.stdout)
        (table_dict, return_message) = stdout

        # TODO: do not know whether timevar is updated or created, 
        # skipping from progress tabel for now
        if 'timevar' in table_dict:
            table_dict.pop('timevar')
        nr_rows = len(table_dict.keys())
        self.setWindowTitle(self.title)

        layout = QVBoxLayout()
        label = QLabel(self.text)
        layout.addWidget(label)

        tableWidget = QTableWidget(self)
        tableWidget.setRowCount(nr_rows)
        tableWidget.setColumnCount(2)

        for row, key in enumerate(sorted(table_dict.keys())):
            item = QTableWidgetItem(str(table_dict[key]['created']))
            tableWidget.setItem(row, 0, item)
            item = QTableWidgetItem(str(table_dict[key]['updated']))
            tableWidget.setItem(row, 1, item)

        # Set headers for the table, TO DO adapt for validation
        if self.plugin.dry_run:
            tableWidget.setHorizontalHeaderLabels(['to be created', 'to be updated'])
            tableWidget.setVerticalHeaderLabels(sorted(table_dict.keys()))
        else:
            tableWidget.setHorizontalHeaderLabels(['created', 'updated'])
            tableWidget.setVerticalHeaderLabels(sorted(table_dict.keys()))

        # Resize the columns to fit the content
        tableWidget.resizeColumnsToContents()
        layout.addWidget(tableWidget)

        label = QLabel(return_message)
        layout.addWidget(label)

        # Set the layout for the dialog
        self.setLayout(layout)

