# Python Imports
import sys
import json
import os
import datetime
from enum import Enum

# PySide6 Imports
from PySide6.QtWidgets import QApplication, QMainWindow, QStyle, QMessageBox
from PySide6.QtCore import Qt, QSettings, QFile, QTextStream, QStandardPaths, QPoint, QTimer, QUrl
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices

import Resources_rc
from UI_Components import Ui_MainWindow

from TrafficRecorder import TrafficRecorder

#Log Levels
class LogLevel(Enum):
    INFO = 0
    ERROR = 10
    DEBUG = 20
    
    @staticmethod
    def get(value):
        for level in LogLevel:
            if(value == level.value):
                return level
        return LogLevel.INFO


class MainWindow(QMainWindow, Ui_MainWindow):
    
    def __init__(self):
        super(MainWindow, self).__init__()
        #Load UI Components
        self.setupUi(self)
        
        #App Constants
        self.geometryToRestore = None
        self.repoUrl = QUrl("https://github.com/cwtravis/appscan-traffic-recorder-client")
        self.traffic_recorder = TrafficRecorder()
        
        #Read Version File From Resources
        version_file = QFile(":version.json")
        version_file.open(QFile.ReadOnly)
        text_stream = QTextStream(version_file)
        version_file_text = text_stream.readAll()
        self.version_dict = json.loads(version_file_text)
        self.app_name = self.version_dict["product_name"]
        self.version = self.version_dict["version"]
        self.description = self.version_dict["description"]
        self.author = self.version_dict["author"]
        self.author_email = self.version_dict["author_email"]
        self.project_name = self.app_name.title().replace(" ", "")
        self.setWindowTitle(f"{self.app_name} {self.version}")
        
        #Load Settings
        self.config_dir = QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
        if(not os.path.isdir(self.config_dir)):
            os.makedirs(self.config_dir)
        self.ini_path = os.path.join(self.config_dir, f"{self.project_name}.ini").replace("\\", "/")
        self.settings = QSettings(self.ini_path, QSettings.IniFormat)
        
        #Setup Proxy TableWidget
        self.proxyTable.setColumnCount(5)
        self.proxyTable.setHorizontalHeaderLabels(["Port", "Encrypted", "Stop", "Traffic", "Remove"])

        #Setup Button Signals
        # Button/Menu Signals Go Here
        self.closeButton.clicked.connect(self.closeButtonClicked)
        self.minimizeButton.clicked.connect(self.minimizedButtonClicked)
        self.maximizeButton.clicked.connect(self.maximizedButtonClicked)
        self.homeMenuButton.clicked.connect(self.showHomePane)
        self.logMenuButton.clicked.connect(self.showLogPane)
        self.aboutButton.clicked.connect(self.showAbout)
        self.githubButton.clicked.connect(self.showGithub)
        self.showErrorsCheckbox.stateChanged.connect(self.showErrorsClicked)
        self.showDebugCheckbox.stateChanged.connect(self.showDebugClicked)
        self.specifyPortRadioButton.toggled.connect(self.portRadioButtons)
        self.portRangeRadioButton.toggled.connect(self.portRadioButtons)
        self.randomPortRadioButton.toggled.connect(self.portRadioButtons)

        #Finally, Show the UI
        self.specifyPortRadioButton.setChecked(True)
        geometry = self.settings.value(f"{self.project_name}/geometry")
        window_state = self.settings.value(f"{self.project_name}/windowState")
        self.showErrors = self.settings.value(f"{self.project_name}/showErrors", "1") == "1"
        self.showDebug = self.settings.value(f"{self.project_name}/showDebug", "1") == "1"
        self.showErrorsCheckbox.setChecked(self.showErrors)
        self.showDebugCheckbox.setChecked(self.showDebug)
        if(geometry and window_state):
            self.restoreGeometry(geometry) 
            self.restoreState(window_state)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.show()
        self.log("AppScan Traffic Recorder Client started")
    
    def portRadioButtons(self):
        if self.specifyPortRadioButton.isChecked():
            self.topPortLabel.setText("Port Number:")
            self.bottomPortLabel.setVisible(False)
            self.bottomPortLineEdit.setVisible(False)
        elif self.portRangeRadioButton.isChecked():
            self.topPortLabel.setText("Lower Bound:")
            self.bottomPortLabel.setText("Upper Bound:")
            self.topPortLineEdit.setVisible(True)
            self.bottomPortLineEdit.setVisible(True)
            self.topPortLabel.setVisible(True)
            self.bottomPortLabel.setVisible(True)
        elif self.randomPortRadioButton.isChecked():
            self.topPortLabel.setText("Lower Bound:")
            self.bottomPortLabel.setText("Upper Bound:")
            self.topPortLineEdit.setVisible(True)
            self.bottomPortLineEdit.setVisible(True)
            self.topPortLabel.setVisible(True)
            self.bottomPortLabel.setVisible(True)

    def showAbout(self):
        repo = self.repoUrl.toString()
        text = f"AppScan Traffic Recorder Client\n\n{self.description}\n\nGitHub: {repo}\nAuthor: {self.author} <{self.author_email}>"
        mb = QMessageBox(QMessageBox.Icon.Information, "About", text)
        mb.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mb.exec()

    def showGithub(self):
        QDesktopServices.openUrl(self.repoUrl)

    def showHomePane(self):
        self.stackedWidget.setCurrentWidget(self.proxyWidget)

    def showLogPane(self):
        self.stackedWidget.setCurrentWidget(self.logWidget)

    def showErrorsClicked(self):
        self.showErrors = self.showErrorsCheckbox.isChecked()
        if self.showErrors:
            showError = "1"
        else:
            showError = "0"
        self.settings.setValue(f"{self.project_name}/showErrors", showError)
        self.settings.sync()

    def showDebugClicked(self):
        self.showDebug = self.showDebugCheckbox.isChecked()
        if self.showDebug:
            showDebugStr = "1"
        else:
            showDebugStr = "0"
        self.settings.setValue(f"{self.project_name}/showDebug", showDebugStr)
        self.settings.sync()

    def log(self, msg, level=LogLevel.INFO):
        print(msg)
        if not msg:
            return
        if level == LogLevel.ERROR:
            if not self.showErrors:
                return
            style = "color: #cc0000;"
        elif level == LogLevel.DEBUG:
            if not self.showDebug:
                return
            style = "color: #006600;"
        else:
            style = "color: #000000;"
        now = datetime.datetime.now()
        timestamp = now.strftime("%H:%M:%S")
        msg = f'<span style="{style}">{timestamp} - {msg}</span>'
        self.logBrowser.append(msg)

    def mousePressEvent(self, event):
        globalPos = event.globalPosition().toPoint()
        relativePos = event.position().toPoint()
        source = self.childAt(relativePos)
        if source == self.titleLabel:
            self.oldPos = globalPos

    def mouseMoveEvent(self, event):
        globalPos = event.globalPosition().toPoint()
        relativePos = event.position().toPoint()
        source = self.childAt(relativePos)
        if source == self.titleLabel:
            delta = QPoint(globalPos - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = globalPos

    def minimizedButtonClicked(self):
        self.setWindowState(Qt.WindowMinimized)

    def maximizedButtonClicked(self):
        if self.isMaximized():
            #Restore the non-maximized window geometry
            self.restoreGeometry(self.geometryToRestore)
        else:
            #Save window geometry before minimizing
            self.geometryToRestore = self.saveGeometry()
            self.setWindowState(Qt.WindowMaximized)

    def closeButtonClicked(self):
        self.close()

    # App is closing, cleanup
    def closeEvent(self, evt=None):
        # Remember the size and position of the GUI
        if(self.showErrors):
            showError = "1"
        else:
            showError = "0"
        if(self.showDebug):
            showDebug = "1"
        else:
            showDebug = "0"
        self.settings.setValue(f"{self.project_name}/geometry", self.saveGeometry())
        self.settings.setValue(f"{self.project_name}/windowState", self.saveState())
        self.settings.setValue(f"{self.project_name}/showErrors", showError)
        self.settings.setValue(f"{self.project_name}/showDebug", showDebug)
        self.settings.sync()
        evt.accept()

# Start the PySide6 App
if __name__ == "__main__":
    app = QApplication(sys.argv)
    version_file = QFile(":version.json")
    version_file.open(QFile.ReadOnly)
    text_stream = QTextStream(version_file)
    version_file_text = text_stream.readAll()
    version_dict = json.loads(version_file_text)
    org_name = version_dict["company_name"]
    app_name = version_dict["product_name"]
    version = version_dict["version"]
    app.setOrganizationName(org_name)
    app.setApplicationName(app_name)
    app.setApplicationVersion(version)
    window = MainWindow()
    sys.exit(app.exec())