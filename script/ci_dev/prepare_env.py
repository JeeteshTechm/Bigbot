"""This script help you to create environment for you according requirement txt."""

import os
import platform
import json
import subprocess

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "conf.json")
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OS_TYPE = platform.system()

def read_json():
    with open(CONFIG_FILE, "r") as jsonFile:
        data = json.load(jsonFile)
    return data

def get_venv():
    venv = read_json()["paths"]["venv"][OS_TYPE]
    which_python = read_json()["which_python"][OS_TYPE]
    if OS_TYPE == 'Windows':
        venv_python = os.path.join(venv, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv, "bin", "python.exe")
    return venv, venv_python, which_python

def pip_install(package=None, file_path=None):
    def arg(): return [package] if package else ['-r', file_path]
    return subprocess.call(["pip", "install", *arg()])

def create_virtualenv():
    venv, venv_python, which_python = get_venv()
    pip_install(package="virtualenv==16.7.6")

    if not os.path.exists(venv_python):
        print("Environment is creating...")
        subprocess.call([which_python, "-m", "virtualenv", venv])
    else:
        print(f"Environment already exist: {venv_python} \n Checking for updates.")

def install_requirements():
    requirements_path = os.path.join(PROJECT_ROOT, "requirements.txt")
    project_res = pip_install(file_path=requirements_path)

    return project_res

def main():
    venv, _, which_python = get_venv()
    subprocess.call([which_python, "--version"])
    create_virtualenv()

    if OS_TYPE == 'Linux':
        python_path = os.path.join(venv, "bin")
        seperator = ":"
    else:
        python_path = os.path.join(venv, "Scripts")
        seperator = ";"
    
    os.environ["PATH"] = f"{python_path}{seperator}" + os.environ["PATH"]

    project_result = install_requirements()
    exit(project_result)

if __name__ == "__main__":
    main()