from waitress import serve   #import the serve function of waitress
from Dash_app import server       #import the "server" part of the Dash app from my main script, which is named app.py

serve(server)                #use waitress as server