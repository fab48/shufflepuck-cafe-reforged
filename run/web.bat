@echo off
rem Lance le jeu en local : http://localhost:8731
rem Le dossier web est donne en chemin complet : peu importe d ou on lance.
start "" http://localhost:8731
python -m http.server 8731 --directory "%~dp0..\web"
