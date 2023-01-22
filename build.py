import os
import subprocess
import shutil
import sys
import json


VERSION_TEMPLATE = """{
    "version": "1.0",
    "ico": "./resources/img/<ICON>.png",
    "company_name": "<COMPANY_NAME>",
    "product_name": "<PROJECT_NAME>",
    "description": "<PROJECT_DESCRIPTION>"
}
"""

RESOURCES_TEMPLATE = """<!DOCTYPE RCC><RCC version="1.0">
<qresource>
    <file>version.json</file>
</qresource>
</RCC>
"""

UI_TEMPPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>634</width>
    <height>160</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>MainWindow</string>
  </property>
  <widget class="QWidget" name="centralwidget">
   <widget class="QLabel" name="label">
    <property name="geometry">
     <rect>
      <x>40</x>
      <y>20</y>
      <width>441</width>
      <height>16</height>
     </rect>
    </property>
    <property name="text">
     <string>UI Template - Replace this file with one from QT Designer</string>
    </property>
   </widget>
   <widget class="QLabel" name="label_2">
    <property name="geometry">
     <rect>
      <x>40</x>
      <y>60</y>
      <width>441</width>
      <height>41</height>
     </rect>
    </property>
    <property name="text">
     <string>Save the ui file to &lt;PROJECT_ROOT&gt;/resources/ui/</string>
    </property>
   </widget>
  </widget>
  <widget class="QMenuBar" name="menubar">
   <property name="geometry">
    <rect>
     <x>0</x>
     <y>0</y>
     <width>634</width>
     <height>22</height>
    </rect>
   </property>
  </widget>
  <widget class="QStatusBar" name="statusbar"/>
 </widget>
 <resources/>
 <connections/>
</ui>
"""

def make_dirs(path):
    try:
        if not os.path.exists(path):
            print(f"Creating path {path}")
            os.makedirs(path)
    except Exception as e:
        print("Error creating bin dir")
        print(e)


# Function to compile the provided ui_file to py
# and place it in destination_path
def installRequirements(requirements_file="requirements.txt"):
    # pip install -r requirements.txt
    ret = subprocess.run(["py", "-m", "pip", "install", "-r", "requirements.txt"], capture_output=True)
    if(ret.returncode != 0):
        print(f"\nError")
        print(ret.stderr.decode("utf-8"))
        return False
    output = ret.stdout.decode("utf-8")
    return True

# Function to find all files in dir_path 
# with extension (not recursive)
def getFilesWithExtension(dir_path,  extension):
    files = []
    for file in os.listdir(dir_path):
        if file.endswith(f".{extension}"):
            files.append(os.path.join(ui_path, file))
    return files
    
# Function to compile the provided ui_file to py
# and place it in destination_path
def compileUiFile(ui_file, destination_file):
    # uic -g python $ui_file >> destination_file
    ret = subprocess.run(["uic", "-g", "python", ui_file], capture_output=True)
    if(ret.returncode != 0):
        print(f"\nError Compiling {ui_file}")
        print(ret.stderr.decode("utf-8"))
        return False
    output = ret.stdout
    with open(destination_file, "ab") as py_file:
        py_file.write(output)
        py_file.write(b"\r\n\r\n")
    return True

# Function to compile the provided ui_file to py
# and place it in destination_path
def compileResources(resources_file, destination_file):
    if not os.path.exists(destination_file):
        #Create the destination file if it doesnt exist
        with open(destination_file, 'w') as fp:
            pass

    #rcc -g python -o Resources.py {PROJECT_NAME}.rc
    ret = subprocess.run(["rcc", "-g", "python", "-o", destination_file, resources_file], capture_output=True)
    stderr = ret.stderr.decode("utf-8")
    if(ret.returncode != 0):
        print(stderr)
        return False
    return True


target_env = "windows"
partial = False

if(len(sys.argv)>1):
    if(sys.argv[1] == "partial"):
        partial = True

print("Starting build script")
print("=============================================\n")
if not os.path.exists("version.json"):
    print("version.json file does not exist. Generating template")
    print("Complete this template before rerunning")
    with open("version.json", "w") as f:
        f.write(VERSION_TEMPLATE)
    sys.exit(1)
print("Reading Version File: version.json")
with open("version.json", "r") as version_file:
    version = json.load(version_file)
print(f"Company Name: {version['company_name']}")
print(f"Product Name: {version['product_name']}")
print(f"Version: {version['version']}")
print("=============================================\n")
TEST_BUILD = False
PROJECT_NAME = version['product_name'].title().replace(" ","")
OUTPUT_FILE = f"{PROJECT_NAME}.exe"
# Specify Paths and Files
cwd = os.getcwd()
ui_path = os.path.join(cwd, "resources", "ui")
destination_file = os.path.join(cwd, "UI_Components.py")
resource_file = os.path.join(cwd, f"{PROJECT_NAME}.qrc")


print("Installing Requirements via pip:")
with open("requirements.txt") as f:
    r = f.read()
    print(r)

if installRequirements():
    print("Packages installed successfully")
else:
    print("Error installing packages from requirements.txt")
    print("Try installing manually 'py -m pip install -r requirements.txt'")
    sys.exit(1)
print("=============================================\n")

print("Checking required directories:")
print("resources/ui")
print("resources/files")
print("resources/img")
print("bin")

# Make sure resources directories exist, create them if not
make_dirs("resources/ui")
make_dirs("resources/files")
make_dirs("resources/img")
make_dirs("bin")

print("=============================================\n")
print("Compiling All UI Files to Single Python File")
print(f"UI File Dir: {ui_path}")
print(f"Destination Python File: {destination_file}")

if(os.path.exists(destination_file)):
    print("Existing Destination File Found")
    destination_file_bak = destination_file + ".bak"
    print(f"Making Backup: {destination_file_bak}")
    try:
        shutil.copyfile(destination_file, destination_file_bak)
        print("\tFile Backup Success")
    except Exception as e:
        print("Error Making Backup File")
        print(e)
        print("Quitting...")
        sys.exit(1)
    print("Removing Old Destination File")
    os.remove(destination_file)
print("=============================================\n")

print("Compiling UI Files from ./resources/ui/")
ui_files = getFilesWithExtension(ui_path, "ui")
#If no ui files, create the blank one
if len(ui_files) == 0:
    with open("resources/ui/template.ui", "w") as f:
        f.write(UI_TEMPPLATE)
    ui_files = ["resources/ui/template.ui"]

for file in ui_files:
    print(f"> Compiling {file}...", end="")
    if(compileUiFile(file, destination_file)):
        print("Success")
    else:
        print("Failure")
        print("Error compiling UI File. Please fix and rerun.")
        sys.exit(1)

print("\nUI Files Compiled")
print("=============================================\n")
print("Compiling Resources")

#Create Resources.rc if it doesn't exist
if not os.path.exists("Resources.qrc"):
    print("Resources.qrc does not exist. Creating it")
    with open("Resources.qrc", "w") as f:
        f.write(RESOURCES_TEMPLATE)

resource_dest = "Resources_rc.py"
if(compileResources("Resources.qrc", resource_dest)):
    print(f"> File: Resources.qrc to {resource_dest}")
else:
    print(f"\nError Compiling {resource_file}")

print("=============================================\n")

if(partial):
    print("Partial Build Requested. Not Compiling Binary")
    print("=============================================\n")
    sys.exit(0)

print("Compiling Binary")

if(target_env == "windows"):
    show_cmd = "--windows-disable-console "
    if(TEST_BUILD):
        show_cmd = ""
    
    icon = f"--windows-icon-from-ico={version['ico']}"
    if not os.path.exists(version['ico']):
        icon = ""
    
    cmd = f"py -m nuitka --onefile --standalone" \
            f" --enable-plugin=pyside6 " \
            f"{icon}" \
            f" {show_cmd}" \
            f" -o bin/{OUTPUT_FILE}" \
            " MainWindow.py"
    
proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
for c in iter(lambda: proc.stdout.read(1), b''):
    sys.stdout.write(c.decode("utf-8"))
    
for c in iter(lambda: proc.stderr.read(1), b''):
    sys.stdout.write(c.decode("utf-8"))

proc.communicate()

print("\n=============================================")
if(proc.returncode == 0):
    print("Binary Compiled Successfully")
    print(f"./bin/{OUTPUT_FILE}")
else:
    print("Error Compiling Binary")
print("=============================================\n")
