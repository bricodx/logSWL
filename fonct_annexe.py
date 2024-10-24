from pathlib import Path
import logging
import os
import connection
from adif_file import adi
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import QLocale, QCoreApplication
from PyQt5.QtGui import QPixmap
from datetime import datetime,timezone

# Configuration du logger
logging.basicConfig(level=logging.INFO)  # Changez en logging.INFO ou  logging.DEBUG

def format_locator(locator):
    qth = f"{locator[:2].upper()}{locator[2:4]}{locator[4:].lower()}"
    return qth

def format_callsign(callsign):
    callsign = callsign.upper()
    return callsign

def ouvrir_dans_explorateur(url):
    # Ouvre le chemin dans le gestionnaire de fichiers
    chemin = url
    if os.path.isfile(chemin):
        # Ouvre le dossier contenant le fichier et sélectionne le fichier
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.dirname(chemin)))
    else:
        # Ouvre le dossier
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(chemin))

def export_adi():
    '''new_qso = {
        'HEADER': { 'CALL': 'F5ABC', # ... d'autres champs d'en-tête },
        'RECORDS': [
            {
                'CALL': 'DL2ABC', 'QSO_DATE': '20231225', 'TIME_ON': '1820' # ... d'autres champs d'un enregistrement
             }
            # ... d'autres enregistrements
        ]
    }'''
    fichier_adif = f"{datetime.now(timezone.utc).strftime("%Y%m%d%Y%H%M")}.adi"
    sql = '''SELECT MAX(idstation), date_changement, mycall, mygrid, qthname FROM mastation'''
    ma_station = connection.db.fetch_one_data(sql, ("",))
    # Exécuter la requête SQL pour obtenir les enregistrements
    sql = '''SELECT * FROM qso WHERE export = 0'''
    liste_all = connection.db.fetch_data(sql)
    nbre_export = 0
    if liste_all:
        # Créer une liste de dictionnaires pour chaque enregistrement
        records = []
        for row in liste_all:
            record = {
                'STATION_CALLSIGN': ma_station[2],
                'MY_GRIDSQUARE': ma_station[3],
                'SWL': 'Y',
                'CALL': row[3],
                'QSO_DATE': row[5],
                'TIME_ON': row[6],
                'BAND': row[8],
                'FREQ': str(float(row[9])/1000),
                'MODE': row[10],
                'RST_SENT': row[11],
                'QSLMSG': row[13]
                # ... ajouter d'autres champs si nécessaire
            }
            nbre_export += 1
            records.append(record)

        sql = '''SELECT MAX(idstation), date_changement, mycall, mygrid, qthname FROM mastation'''
        ma_station = connection.db.fetch_one_data(sql, ("",))
        # Créer le dictionnaire dict_export avec les variables header et records
        header = {
            'ADIF_VER': '3.1.4',
            'PROGRAMID': 'logSWL via PyADIF-File',
            'PROGRAMVERSION': '1.0'
            # ... autres champs d'en-tête
        }

        dict_export = {
            'HEADER': header,
            'RECORDS': records
        }
        adi.dump(f"{fichier_adif}", dict_export, 'Adif export from logSWL', False)
        sql_update = "UPDATE qso set export = ? WHERE export = 0"
        if connection.db.exec_data(sql_update, (1,)):
            # Si la modification a réussi, lance une autre action
            logging.debug("mise à jour export OK")
        else :
            # Si la modification a échouée, affiche une erreur
            logging.debug("problème mise à jour export")
    else :
        logging.debug("Aucune ligne à exporter")

    if nbre_export > 0:
        # Créer une instance de QMessageBox
        message_box = QtWidgets.QMessageBox()
        message_box.setWindowTitle("Succès")
        message_box.setIcon(QtWidgets.QMessageBox.Information)

        # Créer une QLabel avec le lien
        chemin_html = f'<a href="file://{os.path.abspath(fichier_adif)}">{os.path.abspath(fichier_adif)}</a>'
        label = QtWidgets.QLabel(
            f"Vous venez d'exporter {nbre_export} QSO<br>Le fichier est disponible ici :<br>{chemin_html}")
        label.setTextFormat(QtCore.Qt.RichText)
        label.setAlignment(QtCore.Qt.AlignCenter)  # Centrer la QLabel
        label.setOpenExternalLinks(False)  # Empêche l'ouverture automatique des liens
        label.linkActivated.connect(lambda: ouvrir_dans_explorateur(os.path.abspath(fichier_adif)))  # Connecte l'événement de clic

        # Ajouter la QLabel à la QMessageBox
        message_box.layout().addWidget(label, 0, 1)
        message_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        # Afficher la boîte de dialogue
        message_box.exec_()
    else :
        QtWidgets.QMessageBox.information(None, "Succès", f"Aucun QSO a exporter")


def test_presence_fichier(file_path):
    if os.path.exists(file_path):
        return file_path
    else:
        return None


def appliquer_validateur_float(champ, decimales=4):
    """
    Configure et applique un QDoubleValidator pour accepter des flottants
    avec un séparateur décimal point (.) et un séparateur de milliers virgule (,).

    :param champ: Le champ QLineEdit sur lequel appliquer le validateur.
    :param decimales: Le nombre de décimales autorisé (par défaut 4).
    """
    # Crée un validateur pour les flottants avec la configuration souhaitée
    validator = QDoubleValidator()
    validator.setNotation(QDoubleValidator.StandardNotation)
    validator.setDecimals(decimales)

    # Définit la locale anglaise pour avoir un point comme séparateur décimal
    validator.setLocale(QLocale(QLocale.English))

    # Applique le validateur au champ QLineEdit spécifié
    champ.setValidator(validator)


def show_message( msg_type, title_key, text_key):
    title = QCoreApplication.translate("Messages", title_key)
    text = QCoreApplication.translate("Messages", text_key)

    if msg_type == "info":
        QtWidgets.QMessageBox.information(None, title, text)
    elif msg_type == "warning":
        QtWidgets.QMessageBox.warning(None, title, text)