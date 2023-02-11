# Python Imports
import sys
import json
import os
import datetime
from enum import Enum

# PySide6 Imports
from PySide6.QtWidgets import QApplication, QMainWindow, QStyle, QMessageBox, QTableWidgetItem, QPushButton, QHBoxLayout, QWidget, QToolButton, QLabel, QHeaderView
from PySide6.QtCore import Qt, QSettings, QFile, QTextStream, QStandardPaths, QPoint, QTimer, QUrl, QSize, Signal, QObject, QRunnable, QThreadPool
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices, QIntValidator, QMovie

import Resources_rc
from TrafficRecorder import TrafficRecorder
from UI_Components import Ui_MainWindow

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
            os.mkdir(self.config_dir)
        self.ini_path = os.path.join(self.config_dir, f"{self.project_name}.ini").replace("\\", "/")
        self.settings = QSettings(self.ini_path, QSettings.IniFormat)

        #Setup Proxy TableWidget
        headers = ["","Status", "Port", "Encrypted", "Stop", "Traffic", "Remove"]
        self.proxyTable.setColumnCount(len(["","Status", "Port", "Encrypted", "Stop", "Traffic", "Remove"]))
        self.proxyTable.setHorizontalHeaderLabels(headers)
        self.proxyTable.verticalHeader().hide()
        self.proxyTable.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
        self.proxyTable.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents)
        self.proxyTable.horizontalHeader().setStretchLastSection(True)

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
        self.startProxyButton.clicked.connect(self.startProxyButtonClicked)
        self.urlLineEdit.editingFinished.connect(self.validateServerURL)

        # Make sure the line edits only accept valid port numbers
        portNumberValidator = QIntValidator(0, 65535)
        self.topPortLineEdit.setValidator(portNumberValidator)
        self.bottomPortLineEdit.setValidator(portNumberValidator)

        # TrafficRecord Obj
        self.trafficRecorder = None

        ## ThreadPool
        self.threadpool = QThreadPool()

        #Setup Icons
        ## Green check #00cc66
        self.check_pixmap = QPixmap(":resources/img/icons/check-circle.svg").scaled(QSize(24,24))
        ## Red x  #ff6666
        self.x_pixmap = QPixmap(":resources/img/icons/x-circle.svg").scaled(QSize(24,24))
        ## Red StopSign  #ff6666
        self.stop_pixmap = QPixmap(":resources/img/icons/stop-circle.svg").scaled(QSize(20,20))
        ## Spinning Circle Loading GIF
        self.loading_gif = QMovie(":resources/img/icons/loading.gif")
        self.loading_gif.setScaledSize(QSize(24,24))
        ## Ripple GIF
        self.ripple_gif = QMovie(":resources/img/icons/ripple.gif")
        self.ripple_gif.setScaledSize(QSize(24,24))

        #Finally, Show the UI
        self.specifyPortRadioButton.setChecked(True)
        geometry = self.settings.value(f"{self.project_name}/geometry")
        window_state = self.settings.value(f"{self.project_name}/windowState")
        self.showErrors = self.settings.value(f"{self.project_name}/showErrors", "1") == "1"
        self.showDebug = self.settings.value(f"{self.project_name}/showDebug", "1") == "1"
        url = self.settings.value(f"{self.project_name}/serverUrl", "")
        self.showErrorsCheckbox.setChecked(self.showErrors)
        self.showDebugCheckbox.setChecked(self.showDebug)
        if(geometry and window_state):
            self.restoreGeometry(geometry) 
            self.restoreState(window_state)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.show()
        if len(url) > 0:
            self.urlLineEdit.setText(url)
            self.validateServerURL()
        self.log("AppScan Traffic Recorder Client started")
    
    def setServerValidateResult(self, result):
        self.loading_gif.stop()
        self.statusLabel.clear()
        self.urlLineEdit.setEnabled(True)
        self.urlStatusLabel.clear()
        if result:
            self.urlStatusLabel.setPixmap(self.check_pixmap)
            url = self.urlLineEdit.text()
            self.settings.setValue(f"{self.project_name}/serverUrl", url)
        else:
            self.urlStatusLabel.setPixmap(self.x_pixmap)
            self.settings.setValue(f"{self.project_name}/serverUrl", "")

    def validateServerURL(self):
        self.urlLineEdit.setEnabled(False)
        url = self.urlLineEdit.text()
        self.urlStatusLabel.setMovie(self.loading_gif)
        self.loading_gif.start()
        worker = TrafficRecorderRunner(url)
        worker.signals.log.connect(self.log)
        worker.signals.result.connect(self.setServerValidateResult)
        self.threadpool.start(worker)

    def startProxyButtonClicked(self):
        encrypted = self.encryptCheckBox.isChecked()
        topPort = self.topPortLineEdit.text()
        bottomPort = self.bottomPortLineEdit.text()
        url = self.urlLineEdit.text()

        if self.specifyPortRadioButton.isChecked():
            print(f"Specified Port {topPort} Encrypted {encrypted}")
            worker = TrafficRecorderRunner(url, TrafficRecorderRunner.Action.START)
            worker.signals.log.connect(self.log)
            worker.signals.httpResponse.connect(self.proxyStartCallback)
            self.threadpool.start(worker)
        elif self.portRangeRadioButton.isChecked():
            print(f"Port Range {topPort}-{bottomPort} Encrypted {encrypted}")
        elif self.randomPortRadioButton.isChecked():
            print(f"Random Port {topPort}-{bottomPort} Encrypted {encrypted}")
        else:
            return

    def proxyStartCallback(self, resultTuple):
        if resultTuple[0] >= 200 and resultTuple[0] < 300:
            port = resultTuple[1]["port"]
            encrypted = resultTuple[1]["encryptTraffic"]
            msg = resultTuple[1]["message"]
            self.statusMsg(msg, 7000)
            self.addProxyTableLine(port, encrypted)

    def stopProxyButtonClicked(self, port):
        self.log(f"Stop Button Clicked for Proxy Port {port}")
        url = self.urlLineEdit.text()
        worker = TrafficRecorderRunner(url, TrafficRecorderRunner.Action.STOP)
        worker.setTopPort(port)
        worker.signals.log.connect(self.log)
        worker.signals.httpResponse.connect(self.proxyStopCallback)
        self.threadpool.start(worker)

    def proxyStopCallback(self, resultTuple):
        msg = resultTuple[1]["message"]
        if resultTuple[0] >= 200 and resultTuple[0] < 300:
            port = resultTuple[1]["port"]
            for x in range(0, self.proxyTable.rowCount()):
                if self.proxyTable.item(x, 2).text() == port:
                    self.proxyTable.cellWidget(x, 0).clear()
                    self.proxyTable.cellWidget(x, 0).setPixmap(self.stop_pixmap)
                    self.proxyTable.cellWidget(x, 1).setText("Stopped")
                    break
        else:
            self.log(f"Problem stopping listener - status code {resultTuple[0]}")
            self.log(resultTuple[0])
        self.statusMsg(msg, 7000)

    def rowButtonClicked(self):
        sender = self.sender()
        row = sender.getRow()
        action = sender.getAction()
        port = sender.getPortNumber()
        if action == "stop":
            self.stopProxyButtonClicked(port)
        elif action == "traffic":
            for x in range(0, self.proxyTable.rowCount()):
                if self.proxyTable.item(x, 2).text() == port:
                    #Attempt to stop the proxy if its still Listening
                    if self.proxyTable.cellWidget(x, 1).text() == "Listening":
                        resp = QMessageBox.question(self, "Traffic Recorder", 
                            f"The proxy at port {port} is still listening. Would you like to to stop it?", 
                            QMessageBox.StandardButton.Yes, 
                            QMessageBox.StandardButton.No)
                        if resp == QMessageBox.StandardButton.Yes:
                            self.stopProxyButtonClicked(port)
                    
        elif action == "remove":
            for x in range(0, self.proxyTable.rowCount()):
                if self.proxyTable.item(x, 2).text() == port:
                    #Attempt to stop the proxy if its still Listening
                    if self.proxyTable.cellWidget(x, 1).text() == "Listening":
                        resp = QMessageBox.question(self, "Traffic Recorder", 
                            f"The proxy at port {port} is still listening. Would you like to to stop it?", 
                            QMessageBox.StandardButton.Yes, 
                            QMessageBox.StandardButton.No)
                        if resp == QMessageBox.StandardButton.Yes:
                            self.stopProxyButtonClicked(port)
                    self.proxyTable.removeRow(x)

    def addProxyTableLine(self, port, encrypted):
        newRowIndex = self.proxyTable.rowCount()
        stopBtn = ProxyTableButton(port, "stop", newRowIndex)
        stopBtn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        stopBtn.setText("Stop")
        stopBtn.clicked.connect(self.rowButtonClicked)
        trafficBtn = ProxyTableButton(port, "traffic", newRowIndex)
        trafficBtn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        trafficBtn.setText("Download")
        trafficBtn.clicked.connect(self.rowButtonClicked)
        removeBtn = ProxyTableButton(port, "remove", newRowIndex)
        removeBtn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        removeBtn.setText("Remove")
        removeBtn.clicked.connect(self.rowButtonClicked)
        gifLabel = QLabel()
        gifLabel.setMovie(self.ripple_gif)
        self.ripple_gif.start()
        statusTextLabel = QLabel("Listening")
        self.proxyTable.insertRow(newRowIndex)
        self.proxyTable.setCellWidget(newRowIndex, 0, gifLabel)
        self.proxyTable.setCellWidget(newRowIndex, 1, statusTextLabel)
        self.proxyTable.setItem(newRowIndex, 2, QTableWidgetItem(port))
        self.proxyTable.setItem(newRowIndex, 3, QTableWidgetItem(str(encrypted)))
        self.proxyTable.setCellWidget(newRowIndex, 4, stopBtn)
        self.proxyTable.setCellWidget(newRowIndex, 5, trafficBtn)
        self.proxyTable.setCellWidget(newRowIndex, 6, removeBtn)

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

    def statusMsg(self, msg, timeout=0):
        self.statusLabel.setText(msg)
        if timeout > 0:
            timer = QTimer.singleShot(timeout, lambda: self.statusLabel.setText(""))

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


class TrafficRecorderRunner(QRunnable):

    #Actions
    class Action(Enum):
        START = 0
        STOP = 10
        TRAFFIC = 20
        CERT = 30
        VERIFY = 40

    class Signals(QObject):
        log = Signal(str, LogLevel)
        result = Signal(bool)
        httpResponse = Signal(tuple)

    def __init__(self, url, action=Action.VERIFY):
        super(TrafficRecorderRunner, self).__init__()
        self.action = action
        self.url = url
        self.trafficRecorder = TrafficRecorder(url)
        self.signals = self.Signals()
        self.topPort = 0
        self.botPort = None
        self.encrypt = False

    def setTopPort(self, topPort):
        self.topPort = topPort

    def setBopPort(self, botPort):
        self.botPort = botPort

    def setEncrypt(self, encrypt):
        self.encrypt = encrypt

    def run(self):
        if self.action == self.Action.VERIFY:
            res = self.trafficRecorder.info()
            self.log(f"Validating Server URL {self.url}", LogLevel.DEBUG)
            self.log(f"Response HTTP Code:{res[0]}\n{res[1]}", LogLevel.DEBUG)
            self.signals.result.emit(res[0] == 200)
            return
        elif self.action == self.Action.START:
            res = self.trafficRecorder.start_proxy(self.topPort, self.botPort, self.encrypt)
            self.log(f"Starting Proxy {self.url}", LogLevel.DEBUG)
            self.log(f"Response HTTP Code:{res[0]}\n{res[1]}", LogLevel.DEBUG)
            self.signals.httpResponse.emit(res)
            return
        elif self.action == self.Action.STOP:
            res = self.trafficRecorder.stop_proxy(self.topPort)
            self.log(f"Stopping Proxy Port {self.topPort}", LogLevel.DEBUG)
            self.log(f"Response HTTP Code:{res[0]}\n{res[1]}", LogLevel.DEBUG)
            self.signals.httpResponse.emit(res)
            return
        elif self.action == self.Action.TRAFFIC:
            return
        elif self.action == self.Action.CERT:
            return

    def log(self, msg, level=LogLevel.INFO):
        self.signals.log.emit(msg, level)

class ProxyTableButton(QToolButton):
    def __init__(self, portNumber, action, row):
        super(ProxyTableButton, self).__init__()
        self.portNumber = portNumber
        self.action = action
        self.row = row
    
    def getPortNumber(self):
        return self.portNumber

    def getAction(self):
        return self.action

    def getRow(self):
        return self.row

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