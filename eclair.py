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
from PyQt5.QtWidgets import QAction, QMessageBox
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
import os
from PyQt5.QtWidgets import QFileDialog


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
        btn_action = QPushButton("Choose file")
        layout.addWidget(btn_action)

        # Connect the button click event to a function in your plugin's code
        btn_action.clicked.connect(self.open_file_dialog)

    def open_file_dialog(self):
        # This function will be called when the button is clicked.
        # You can define the desired action here.
        file_path, _ = QFileDialog.getOpenFileName(None, "Open External File", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'r') as file:
                file_contents = file.read()
                display_file_contents(file_contents)

def display_file_contents(contents):
    # For this example, let's display the file contents in a message box.
    msg_box = QMessageBox()
    msg_box.setWindowTitle("File Contents")
    msg_box.setText(contents)
    msg_box.exec_()





