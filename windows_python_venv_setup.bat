mkdir venv
python -m venv venv
"%CD%\venv\Scripts\activate.bat"&&pip install --upgrade pip&pip install --upgrade pip&&pip install -r requirements.txt&&"%CD%\venv\Scripts\deactivate.bat"
