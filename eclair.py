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
from PyQt5.QtWidgets import QFileDialog, QCheckBox, QRadioButton, QButtonGroup
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import Qt

import os
import sys
import subprocess
import site
from pathlib import Path


ETK_BINPATH = os.path.expanduser("~/.local/bin")
os.environ["PATH"] += f":{ETK_BINPATH}"
sys.path += [f"/home/{os.environ['USER']}/.local/lib/python3.9/site-packages"]

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
        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel("Initialize database:")
        layout.addWidget(label)

        btn_action_existing_database = QPushButton("Choose existing database to edit")
        layout.addWidget(btn_action_existing_database)
        btn_action_existing_database.clicked.connect(self.load_existing_database_dialog)

        btn_action_new_database = QPushButton("Create and connect to new database")
        layout.addWidget(btn_action_new_database)
        btn_action_new_database.clicked.connect(self.create_new_database_dialog)

        label = QLabel("Import data to your database (*.xlsx and *.csv):")
        layout.addWidget(label)

        btn_action_import_pointsourceactivities = QPushButton("Import data from spreadsheet")
        layout.addWidget(btn_action_import_pointsourceactivities)
        btn_action_import_pointsourceactivities.clicked.connect(self.import_pointsourceactivities_dialog)


    def load_existing_database_dialog(self):
            db_path, _ = QFileDialog.getOpenFileName(None, "Open SQLite database", "", "Database (*.sqlite)")
            if db_path == '':
                # user cancelled
                message_box('Warning','No file chosen, database not configured.')
            else:
                os.environ["ETK_DATABASE_PATH"] = db_path
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
                message_box('Created database',f"Successfully created database {db_path}")
            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")    
                message_box('Import error',f"Error: {error}")

    def import_pointsourceactivities_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open pointsourceactivities file", "", "Spreadsheet files (*.xlsx);; Comma-separated files (*.csv)")
        #TODO let user specify unit
        if file_path: #if file_path not empty string (user did not click cancel)
            from openpyxl import load_workbook
            workbook = load_workbook(filename=file_path, data_only=True)
            # workbook.worksheets  compare to SHEET_NAMES
            from etk.edb.const import SHEET_NAMES
            valid_sheets = [sheet.title for sheet in workbook.worksheets if sheet.title in SHEET_NAMES]
            
            checkboxDialog = CheckboxDialog(self,valid_sheets)
            result = checkboxDialog.exec_()  # Show the dialog as a modal dialog
            if result == QDialog.Accepted:
                sheets = checkboxDialog.sheet_names
            else:
                message_box('Importing progress','importing all valid sheets '+str(valid_sheets))
                sheets = SHEET_NAMES

            if "PointSource" in sheets:
                # need to specify unit for PointSourceSubstance
                unitDialog = UnitDialog(self,options=["ton/year","g/s"])
                result = unitDialog.exec_()  # Show the dialog as a modal dialog
                if result == QDialog.Accepted:
                    unit = unitDialog.unit
                else:
                    message_box('Importing progress','Importing pointsources with default unit ton/year.')
                    unit = "ton/year"
            else:
                unit=None
            
            from etk.tools.utils import CalledProcessError, run_import
            try:
                # specify db_path here?
                (stdout, stderr) = run_import(file_path, str(sheets), unit=unit)
                message_box('Import status','Imported pointsourceactivities successfully '+stdout.decode("utf-8"))
            except CalledProcessError as e:
                error = e.stderr.decode("utf-8")
                if "Database unspecified does not exist, first run 'etk create' or 'etk migrate'" in error:
                    message_box('Error',f"Error: a target database is not specified yet,"
                    +" choose an existing or create a new database first.")
                else:
                    #  (Exit Code {e.returncode})
                    import_error = error.split('ImportError:')[-1]
                    message_box('Import error',f"Error: {import_error}")
        else:
            # user cancelled
            message_box('Import error','No file chosen, no data imported.')
    

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
        # close the checkbox dialog
        self.accept()

class UnitDialog(QDialog):
    # commonly called RadioButtonDialog, change if used for more cases
    def __init__(self, parent=None, options=None):
        super().__init__(parent)
        self.options = options
        self.selected_option = None

        self.initUI()

    def initUI(self):
        # Create radio buttons for each option in the list
        self.radio_buttons = []
        self.button_group = QButtonGroup()

        for option in self.options:
            radio_button = QRadioButton(option)
            self.radio_buttons.append(radio_button)
            self.button_group.addButton(radio_button)

        # Create a button to save and close the dialog
        saveButton = QPushButton('Save and Close')
        saveButton.clicked.connect(self.saveAndClose)

        # Create a layout for the dialog
        layout = QVBoxLayout()
        
        # Add radio buttons and the save button to the layout
        for radio_button in self.radio_buttons:
            layout.addWidget(radio_button)
        layout.addWidget(saveButton)

        # Set the layout for the dialog
        self.setLayout(layout)

    def saveAndClose(self):
        # Determine the selected option
        for radio_button in self.radio_buttons:
            if radio_button.isChecked():
                self.unit = radio_button.text()
                break

        # Close the dialog
        self.accept()
