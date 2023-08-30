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



from PyQt5.QtWidgets import QAction, QWidget
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtWidgets import QFileDialog, QCheckBox
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import Qt

import os
import sys
import subprocess
import site
from pathlib import Path


# from etk, can re-use from there?
DEFAULT_SETTINGS = {
    "DEBUG": False,
    "INSTALLED_APPS": [
        "django.contrib.gis",
        "etk.edb.apps.EdbConfig",
        "rest_framework",
    ],
    "DATABASE_ROUTERS": ["dynamic_db_router.DynamicDbRouter"],
    "LANGUAGE_CODE": "en-us",
    "TIME_ZONE": "UTC",
    "USE_I18N": True,
    "USE_TZ": True,
}

class Eclair:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.action = QAction('Eclair!', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)


    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        # QMessageBox.information(None, 'Eclair', 'Click OK to get started')
        dialog = EclairDialog()
        dialog.exec_()        

       
class EclairDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECLAIR")
        self.init_ui()

    def init_ui(self):
        # Determine the path to the virtual environment
        venv_path = os.path.join(os.path.dirname(__file__), '.venv')
        site.addsitedir(os.path.join(venv_path, "lib", "python3.9", "site-packages"))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "etk.settings")
        

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel("Initialize database:")
        layout.addWidget(label)

        btn_action_existing_database = QPushButton("Choose existing database to edit")
        layout.addWidget(btn_action_existing_database)
        btn_action_existing_database.clicked.connect(self.load_existing_database_dialog)

        btn_action_new_database = QPushButton("Create and load new database")
        layout.addWidget(btn_action_new_database)
        btn_action_new_database.clicked.connect(self.create_new_database_dialog)

        label = QLabel("Import data to your database (*.xlsx and *.csv):")
        layout.addWidget(label)

        # btn_action_import_pointsource = QPushButton("Import pointsource")
        # layout.addWidget(btn_action_import_pointsource)
        # btn_action_import_pointsource.clicked.connect(self.import_pointsource_dialog)

        btn_action_import_pointsourceactivities = QPushButton("Import data from spreadsheet")
        layout.addWidget(btn_action_import_pointsourceactivities)
        btn_action_import_pointsourceactivities.clicked.connect(self.import_pointsourceactivities_dialog)


    def load_existing_database_dialog(self):
        from django.conf import settings
        import django
        if hasattr(settings, "configured") and not settings.configured:
            db_path, _ = QFileDialog.getOpenFileName(None, "Open SQLite database", "", "Database (*.sqlite)")
            if db_path == '':
                # user cancelled
                message_box('Warning','No file chosen, database not configured.')
            else:
                # TODO catch if empty string, when pushing cancel!! 
                db_name = db_path.split('/')[-1] #does this work for windows and linux?
                settings.configure(
                    **DEFAULT_SETTINGS,
                    DATABASES={
                    "default": {
                            "ENGINE": "django.contrib.gis.db.backends.spatialite",
                            "NAME": db_path,
                            "TEST": {"TEMPLATE": db_name},
                        },
                    }
                )
                django.setup()
                message_box('Progress database','Database succesfully loaded.')
        else:
            db_path = settings.DATABASES['default']['NAME']
            message_box('Warning','Eclair already configured to use '+str(db_path)+
                ', restart QGIS before choosing another database.'
            )

    def create_new_database_dialog(self):        
        # Determine the path to the virtual environment
        import django
        from django.conf import settings
        if hasattr(settings, "configured") and not settings.configured:
            db_path, _ = QFileDialog.getSaveFileName(None, "Create new SQLite database", "", "Database (*.sqlite)")
            if (db_path == '') or (db_path.split('.')[-1] !='sqlite'):
                # user cancelled
                message_box('Warning','No *.sqlite file chosen, database not created.')
            else:
                db_name = db_path.split('/')[-1] #does this work for windows and linux?
                settings.configure(
                    **DEFAULT_SETTINGS,
                    DATABASES={
                    "default": {
                            "ENGINE": "django.contrib.gis.db.backends.spatialite",
                            "NAME": db_path,
                            "TEST": {"TEMPLATE": db_name},
                        },
                    }
                )
                django.setup()
                #TODO add command to copy 'master/template' database, migrate doesnt work
                message_box('Progress database','Database succesfully created and loaded.')
        else:
            db_path = settings.DATABASES['default']['NAME']
            message_box('Warning','Eclair already configured to use '+str(db_path)+
                ', restart QGIS before choosing another database.'
            )
    
    
    def import_pointsource_dialog(self):
        import django
        from django.conf import settings
        if hasattr(settings, "configured") and not settings.configured:
            #alternative to setup, code mainly comes from etk, should be possible to re-use?
            default_config_home = os.path.expanduser("~/.config")
            config_home = Path(os.environ.get("XDG_CONFIG_HOME", default_config_home))
            default_db = os.path.join(default_config_home,'eclair','eclair.sqlite')
            db_path = os.environ.get("ETK_DATABASE_PATH", default_db)
            settings.configure(
                **DEFAULT_SETTINGS,
                DATABASES={
                "default": {
                        "ENGINE": "django.contrib.gis.db.backends.spatialite",
                        "NAME": db_path,
                        "TEST": {"TEMPLATE": "eclair.sqlite"},
                    },
                }
            )
            django.setup()
        
        def create_codesets():
            from etk.edb.models.source_models import CodeSet, Domain
            try:
                domain = Domain.objects.get(slug='domain-1')
            except etk.edb.models.source_models.Domain.DoesNotExist:
                extent = (
                    "MULTIPOLYGON ((("
                    "10.95 50.33, 24.16 50.33, 24.16 69.06, 10.95 69.06, 10.95 50.33"
                    ")))"
                )
                domain = Domain.objects.create(
                    name="Domain 1",
                    slug="domain-1",
                    srid=3006,
                    extent=extent,
                    timezone="Europe/Stockholm",
                )
            try:
                vertical_dist = domain.vertical_dists.get(name='vdist1')
            except etk.edb.models.source_models.VerticalDist.DoesNotExist: 
                vertical_dist = domain.vertical_dists.create(
                    name="vdist1", weights="[[5.0, 0.4], [10.0, 0.6]]"
                )

            try:
                CodeSet.objects.get(name="code set 1")
            except etk.edb.models.source_models.CodeSet.DoesNotExist:
                # similar to base_set in gadget
                cs1 = CodeSet.objects.create(name="code set 1", slug="code_set1", domain=domain)
                cs1.codes.create(code="1", label="Energy")
                cs1.codes.create(
                    code="1.1", label="Stationary combustion", vertical_dist=vertical_dist
                )
                cs1.codes.create(
                    code="1.2", label="Fugitive emissions", vertical_dist=vertical_dist
                )
                cs1.codes.create(code="1.3", label="Road traffic", vertical_dist=vertical_dist)
                cs1.save()
                cs2 = CodeSet.objects.create(name="code set 2", slug="code_set2", domain=domain)
                cs2.codes.create(code="A", label="Bla bla")
                cs2.save()


        from etk.edb.importers import import_pointsources
        import etk
        create_codesets()
        file_path, _ = QFileDialog.getOpenFileName(None, "Open pointsource file", "", "Spreadsheet files (*.xlsx);; Comma-separated files (*.csv)")
        #TODO let user specify unit
        if file_path: #if file_path not empty string (user did not click cancel)
            from openpyxl import load_workbook
            workbook = load_workbook(filename=file_path, data_only=True)
            from etk.edb.importers import SHEET_NAMES
            # workbook.worksheets  compare to SHEET_NAMES
            valid_sheets = [sheet.title for sheet in workbook.worksheets if sheet.title in SHEET_NAMES]
            checkboxDialog = CheckboxDialog(self,valid_sheets)
            checkboxDialog.exec_()  # Show the dialog as a modal dialog
            ps = import_pointsources(file_path, unit="ton/year")
            message_box('Import pointsources progress',str(ps))

    def import_pointsourceactivities_dialog(self):
        import django
        from django.conf import settings
        if hasattr(settings, "configured") and not settings.configured:
            #alternative to setup, code mainly comes from etk, should be possible to re-use?
            default_config_home = os.path.expanduser("~/.config")
            config_home = Path(os.environ.get("XDG_CONFIG_HOME", default_config_home))
            default_db = os.path.join(default_config_home,'eclair','eclair.sqlite')
            db_path = os.environ.get("ETK_DATABASE_PATH", default_db)
            settings.configure(
                **DEFAULT_SETTINGS,
                DATABASES={
                "default": {
                        "ENGINE": "django.contrib.gis.db.backends.spatialite",
                        "NAME": db_path,
                        "TEST": {"TEMPLATE": "eclair.sqlite"},
                    },
                }
            )
            django.setup()
        
        def create_codesets():
            from etk.edb.models.source_models import CodeSet, Domain
            try:
                domain = Domain.objects.get(slug='domain-1')
            except etk.edb.models.source_models.Domain.DoesNotExist:
                extent = (
                    "MULTIPOLYGON ((("
                    "10.95 50.33, 24.16 50.33, 24.16 69.06, 10.95 69.06, 10.95 50.33"
                    ")))"
                )
                domain = Domain.objects.create(
                    name="Domain 1",
                    slug="domain-1",
                    srid=3006,
                    extent=extent,
                    timezone="Europe/Stockholm",
                )
            try:
                vertical_dist = domain.vertical_dists.get(name='vdist1')
            except etk.edb.models.source_models.VerticalDist.DoesNotExist: 
                vertical_dist = domain.vertical_dists.create(
                    name="vdist1", weights="[[5.0, 0.4], [10.0, 0.6]]"
                )

            try:
                CodeSet.objects.get(name="code set 1")
            except etk.edb.models.source_models.CodeSet.DoesNotExist:
                # similar to base_set in gadget
                cs1 = CodeSet.objects.create(name="code set 1", slug="code_set1", domain=domain)
                cs1.codes.create(code="1", label="Energy")
                cs1.codes.create(
                    code="1.1", label="Stationary combustion", vertical_dist=vertical_dist
                )
                cs1.codes.create(
                    code="1.2", label="Fugitive emissions", vertical_dist=vertical_dist
                )
                cs1.codes.create(code="1.3", label="Road traffic", vertical_dist=vertical_dist)
                cs1.save()
                cs2 = CodeSet.objects.create(name="code set 2", slug="code_set2", domain=domain)
                cs2.codes.create(code="A", label="Bla bla")
                cs2.save()




        from etk.edb.importers import import_pointsourceactivities
        import etk
        create_codesets()
        file_path, _ = QFileDialog.getOpenFileName(None, "Open pointsourceactivities file", "", "Spreadsheet files (*.xlsx);; Comma-separated files (*.csv)")
        #TODO let user specify unit
        if file_path: #if file_path not empty string (user did not click cancel)
            from openpyxl import load_workbook
            workbook = load_workbook(filename=file_path, data_only=True)
            from etk.edb.importers import SHEET_NAMES
            # workbook.worksheets  compare to SHEET_NAMES
            valid_sheets = [sheet.title for sheet in workbook.worksheets if sheet.title in SHEET_NAMES]
            
            checkboxDialog = CheckboxDialog(self,valid_sheets)
            result = checkboxDialog.exec_()  # Show the dialog as a modal dialog
            if result == QDialog.Accepted:
                sheets = checkboxDialog.sheet_names
            else:
                message_box('Importing progress','importing all valid sheets '+str(valid_sheets))
                sheets = valid_sheets
            ps = import_pointsourceactivities(file_path,import_sheets=sheets)
            message_box('Import pointsourceactivities progress',str(ps))

    def showCheckboxDialog(self):
        checkboxDialog = CheckboxDialog(self,valid_sheets)
        checkboxDialog.connect(self.handleSheetNames)
        checkboxDialog.exec_()  # Show the dialog as a modal dialog
    
    def handleSheetNames(self, sheet_names):
        return sheet_names
    
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
    def __init__(self, parent=None, box_labels=None):
        super().__init__(parent)
        self.box_labels = box_labels
        self.initUI()

    def initUI(self):
        # Create a layout for the dialog
        layout = QVBoxLayout()

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

        btn_action_import_sheets = QPushButton("Import sheets")
        layout.addWidget(btn_action_import_sheets)
        btn_action_import_sheets.clicked.connect(self.import_sheets_dialog)

    def import_sheets_dialog(self):
        # Store the state of the checkboxes
        self.sheet_names = [label for label in self.box_labels if self.checkboxes[label].isChecked()]
        message_box('Import sheets progress','Under construction, checkbox states'+str(self.sheet_names))

        # close the checkbox dialog
        self.accept()







# leftover code from testing
# from io import StringIO
# output = StringIO()
# # Redirect sys.stdout to the captured_output
# sys.stdout = output
# django.db.connection.cursor().execute("SELECT InitSpatialMetaData(1)")
# output_string = output.getvalue()
# output.close()
# message_box(output_string)

# to try from terminal, in python run
# import django
# import os
# import sys
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "etk.settings")
# from django.core.management import execute_from_command_line
# execute_from_command_line(sys.argv)
# from etk.edb.importers import import_pointsources
# import_pointsources('/home/a002469/Projects/etk/tests/edb/data/pointsources.csv')

# from django.core.management import execute_from_command_line
# execute_from_command_line(sys.argv)
# from django.core.management import call_command
# call_command('showmigrations')