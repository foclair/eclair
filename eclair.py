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



from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

# from .etk.src.etk.edb.importers import import_pointsources

# import django

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
        QMessageBox.information(None, 'Eclair', 'Click OK to get started')
        dialog = EclairDialog()
        dialog.exec_()


       
class EclairDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECLAIR")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add other UI elements here (e.g., QLabel, QLineEdit, etc.)
        label = QLabel("Start importing files to your database below:")
        layout.addWidget(label)

        # Add the QPushButton to the layout
        btn_action_import_pointsource = QPushButton("Dummy: Import pointsource")
        layout.addWidget(btn_action_import_pointsource)
        # Connect the button click event to a function in your plugin's code
        btn_action_import_pointsource.clicked.connect(self.import_pointsource_dialog)

        # Add the QPushButton to the layout
        btn_action_import_django = QPushButton("Under construction: actual Import pointsource")
        layout.addWidget(btn_action_import_django)
        btn_action_import_django.clicked.connect(self.import_django_dialog)

        # connect the help button to our method
        # do this with inspiration from plugin builder tool, has .ui file, will we need that?
        # self.dialog.button_box.helpRequested.connect(self.show_help)



    def import_pointsource_dialog(self):
        # This function will be called when the button is clicked.
        # This is a dummy function just to show how file system can be accessed.
        file_path, _ = QFileDialog.getOpenFileName(None, "Open pointsource file", "", "Spreadsheet file (*.xlsx) or comma-separated (*.csv)")
        if file_path:
            ps = str(file_path) #import_pointsources(file_path)
            display_ps_import_progress(ps)
    
    
    def import_django_dialog(self):
        # This is a start to the actual import pointsource function
        # currently cannot do initial migrate from QGIS, due to SQLite and SPatiaLite
        # versions, see https://code.djangoproject.com/ticket/32935
        
        # Determine the path to the virtual environment
        venv_path = os.path.join(os.path.dirname(__file__), '.venv')
        site.addsitedir(os.path.join(venv_path, "lib", "python3.9", "site-packages"))

        import django
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "etk.settings")
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

        # from django.core.management import execute_from_command_line
        # execute_from_command_line(sys.argv)
        from django.core.management import call_command
        call_command('showmigrations')


        from etk.edb.importers import import_pointsources

        file_path, _ = QFileDialog.getOpenFileName(None, "Open pointsource file", "", "Spreadsheet file (*.xlsx) or comma-separated (*.csv)")
        if file_path:
            ps = import_pointsources(file_path)
            display_ps_import_progress(ps)



        # from io import StringIO
        # output = StringIO()
        # # Redirect sys.stdout to the captured_output
        # sys.stdout = output
        # django.db.connection.cursor().execute("SELECT InitSpatialMetaData(1)")
        # output_string = output.getvalue()
        # output.close()
        # display_ps_import_progress(output_string)

        # to try from terminal, in python run
        # import django
        # import os
        # import sys
        # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "etk.settings")
        # from django.core.management import execute_from_command_line
        # execute_from_command_line(sys.argv)
        # from etk.edb.importers import import_pointsources
        # import_pointsources('/home/a002469/Projects/etk/tests/edb/data/pointsources.csv')
    
    def show_help(self):
        """Display application help to the user."""
        help_url = 'https://git.smhi.se/foclair/minimal-eclair/-/blob/develop/README.md'
        QDesktopServices.openUrl(QUrl(help_url))


def display_ps_import_progress(ps_progress):
    # For this example, let's display the file contents in a message box.
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Pointsource import progress")
    msg_box.setText(ps_progress)
    msg_box.exec_()










