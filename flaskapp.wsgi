import os
import sys

# Make flaskapp.py importable no matter which directory Apache starts in.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flaskapp import app as application  # mod_wsgi looks for "application"
