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

# from .etk.src.etk.edb.importers import import_pointsources

# import django

import os
import sys
import subprocess
import site




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



    def import_pointsource_dialog(self):
        # This function will be called when the button is clicked.
        # You can define the desired action here.
        file_path, _ = QFileDialog.getOpenFileName(None, "Open pointsource file", "", "Spreadsheet file (*.xlsx) or comma-separated (*.csv)")
        if file_path:
            ps = str(file_path) #import_pointsources(file_path)
            display_ps_import_progress(ps)
    
    
    def import_django_dialog(self):
        # This function will be called when the button is clicked.
        # Determine the path to the virtual environment
        venv_path = os.path.join(os.path.dirname(__file__), '.venv')
        site.addsitedir(os.path.join(venv_path, "lib", "python3.9", "site-packages"))

        import django
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "etk.settings")
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)
        from etk.edb.importers import import_pointsources

        msg_box = QMessageBox()
        msg_box.setWindowTitle("Test, not actually importing django yet")
        msg_box.setText("test")
        msg_box.exec_()

def display_ps_import_progress(ps_progress):
    # For this example, let's display the file contents in a message box.
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Pointsource import progress")
    msg_box.setText(ps_progress)
    msg_box.exec_()








