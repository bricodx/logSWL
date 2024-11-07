from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer, QTranslator, QSettings, QCoreApplication
from PyQt5.QtGui import  QIcon, QPixmap
import sys
import callsign
from fen_station import Ui_fen_station
from logswl import Ui_MainWindow
from apropos import Ui_Dialog
from fenqso import Ui_fen_qso
from fen_connex import Ui_fen_connex
from callsign import Ui_fen_callsign
import connection
from datetime import datetime,timezone
import fonct_annexe
import logging
import grid

# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("app.log")
file_handler.setLevel(logging.DEBUG)  # Définir le niveau du fichier
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)  # Définir le niveau du terminal
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Fonction pour capturer les erreurs non prévues
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Ne pas consigner les interruptions clavier comme erreurs
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Une erreur non prévue s'est produite", exc_info=(exc_type, exc_value, exc_traceback))

# Assigner notre fonction au gestionnaire global d'exceptions
sys.excepthook = handle_exception

class ApplicationIHM:
    def __init__(self):
        super(ApplicationIHM, self).__init__()
        self.translator = QTranslator()  # Initialisation du traducteur

        # Création de l'application
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setWindowIcon(QtGui.QIcon("logo32x32.png"))
        self.actionqso = 0

        # Dictionnaire pour stocker les bandes et leurs plages de fréquences
        self.BANDS_DATA = {
            "": (None, None),
            "2190m": (136, 137),
            "630m": (472, 479),
            "560m": (501, 504),
            "160m": (1800, 2000),
            "80m": (3500, 4000),
            "60m": (5102, 5406.5),
            "40m": (7000, 7300),
            "30m": (10000, 10150),
            "20m": (14000, 14350),
            "17m": (18068, 18168),
            "15m": (21000, 21450),
            "12m": (24890, 24990),
            "10m": (28000, 29700),
            "6m": (50000, 54000),
            "4m": (70000, 71000),
            "2m": (144000, 148000),
            "1.25m": (222000, 225000),
            "70cm": (420000, 450000),
            "33cm": (902000, 928000),
            "23cm": (1240000, 1300000),
            "13cm": (2300000, 2450000),
            "9cm": (3300000, 3500000),
            "6cm": (5650000, 5925000),
            "3cm": (10000000, 10500000),
            "1.25cm": (24000000, 24250000),
            "6mm": (47000000, 47200000),
            "4mm": (75500000, 81000000),
            "2.5mm": (119980000, 120020000),
            "2mm": (142000000, 149000000),
            "1mm": (241000000, 250000000),
        }

        # Création de la fenêtre principale
        self.mw = QtWidgets.QMainWindow()
        # Configuration de l'interface utilisateur (UI)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.mw)
        sql = '''SELECT MAX(idstation), date_changement, mycall, mygrid, qthname FROM mastation'''
        self.ma_station = connection.db.fetch_one_data(sql, ("",))
        self.ui.affich_mygrid.setText(self.ma_station[3])
        self.ui.affich_mycall.setText(self.ma_station[2])
        self.ui.affich_qthname.setText(self.ma_station[4])
        self.ui.affich_mygrid.setReadOnly(True)
        self.ui.affich_mycall.setReadOnly(True)
        # Connexion des actions du menu Fichier
        self.ui.actionADIFeqsl.triggered.connect(fonct_annexe.export_adi)
        self.ui.actionQuitter.triggered.connect(self.app.quit)
        # Connexion des actions du menu Cartes
        self.ui.actiontricartes_mode.triggered.connect(lambda: self.open_map("Mode"))
        self.ui.actiontricartes_band.triggered.connect(lambda: self.open_map("Band"))
        # Connexion des actions du menu Configuration
        self.ui.actionMa_station.triggered.connect(self.open_station_dialog)
        self.ui.actionQRZCQ.triggered.connect(self.open_connex_dialog)
        # Connexion menu pour configuration langue
        self.ui.actionFrancais.triggered.connect(lambda: self.change_language("fr"))
        self.ui.actionAnglais.triggered.connect(lambda: self.change_language("en"))
        # Connexion MOD pour ouvrir la fenêtre "qso"
        self.ui.bouton_nouveau.clicked.connect(lambda: self.open_qso_dialog(["new",0]))
        self.ui.bouton_modifier.clicked.connect(lambda: self.open_qso_dialog(["mod",0]))
        self.ui.bouton_supprimer.clicked.connect(lambda: self.open_qso_dialog(["sup",0]))
        # Connexion d'une nouvelle action pour ouvrir la fenêtre "À propos"
        self.ui.actionA_propos.triggered.connect(self.open_about_dialog)
        # Connecter le signal clicked à la méthode de sélection
        self.ui.tableView.clicked.connect(self.select_row)
        # Connecter la fermeture de l'application à la sauvegarde des paramètres
        self.app.aboutToQuit.connect(self.save_settings)
        self.populate_table()
        # Affichage de la fenêtre principale
        self.mw.show()
        # Initialisation des paramètres pour mémoriser la configuration
        self.settings = QSettings("bricodx_dev", "logSWL")
        # Charger la langue précédente si elle existe
        self.chargement_settings()
        self.update_date_time()
        # Création et configuration du timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_date_time)  # Appelle update_date_time toutes les secondes
        self.timer.start(30000)  # Intervalle de 1000 ms (1 seconde)


    # Méthode pour remplir le QTableView
    def populate_table(self):
        largeur_des_colonnes = [60, 90, 100, 70, 90, 80, 100, 70, 70, 90, 70, 70, 70, 180, 30]
        entete_colonne = ["Id", "CALL", "DATE", "TIME_ON", "FREQ", "BAND", "MODE", "RST_SENT", "LOCA", "CALL_B",
                          "RST_B", "LOCB", "TIME_OFF", "COMMENT", "img"]

        icon = QIcon("sstv/icon.png")  # Créer un QIcon à partir du QPixmap redimensionné
        sql = '''SELECT * FROM qso ORDER BY "idqso" DESC'''
        liste_all = connection.db.fetch_data(sql)
        nbre_item = len(liste_all)
        # Crée un modèle pour la table
        model = QtGui.QStandardItemModel()

        # Ajouter des entêtes de colonnes (omettre les colonnes 2 et 4 par exemple)
        # Supposons que self.entete_colonne a été définie avec toutes les colonnes disponibles
        # Vous pouvez également créer une liste personnalisée d'entêtes pour les colonnes à afficher.
        colonnes_a_afficher = [0, 3, 5, 6, 9, 8, 10, 11, 14, 4, 12, 15, 7,
                               13]  # Indices des colonnes que vous voulez afficher

        # Ajouter des entêtes de colonnes
        model.setHorizontalHeaderLabels(entete_colonne)

        # Ajouter les données au modèle
        for row in liste_all:
            # Sélectionner uniquement les colonnes que vous souhaitez afficher
            filtered_row = [row[i] for i in colonnes_a_afficher]
            filtered_row.append(fonct_annexe.test_presence_fichier(
                f"sstv/{filtered_row[2]}{filtered_row[3]}.png"))  # Ajoute l'image à la fin de filtered_row
            filtered_row[3] = f"{filtered_row[3][:2]}:{filtered_row[3][2:]}"
            filtered_row[2] = f"{filtered_row[2][6:]}-{filtered_row[2][4:6]}-{filtered_row[2][:4]}"

            # Créer les items pour chaque cellule
            items = []
            for index, field in enumerate(filtered_row):
                item = QtGui.QStandardItem()
                if field and field != "0":
                    if isinstance(field, str) and (field.endswith(".png") or field.endswith(".jpg")):
                        # Charger l'image dans un QImage
                        image = QPixmap(field)  # Utilise le chemin pour créer un QImage

                        item.setIcon(icon)  # Assigner l'icône à l'élément
                        item.setData(field, QtCore.Qt.UserRole)  # Utiliser Qt.UserRole pour stocker le chemin
                    else:
                        item.setText(str(field))
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                items.append(item)
            model.appendRow(items)

        # Assigner le modèle à la table
        self.ui.tableView.setModel(model)
        for i in range(len(largeur_des_colonnes)):
            self.ui.tableView.setColumnWidth(i, largeur_des_colonnes[i])  # Largeur de la première colonne


    def append_to_table(self, new_row):
        model = self.ui.tableView.model()  # Récupérer le modèle actuel

        # Ajouter la nouvelle ligne
        items = [QtGui.QStandardItem(str(field) if field is not None and field != "0" else "") for field in new_row]
        for item in items:
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)  # Rendre la cellule non modifiable

        model.appendRow(items)

    def open_map(self, choixcarte=None):
        self.mapdialog = QtWidgets.QDialog()  # Crée un objet QDialog
        self.ui_map = grid.Ui_mapDialog()
        self.ui_map.setupUi(self.mapdialog, self.ma_station[3], choixcarte)  # Passez l'instance de dialog à setupUi
        self.mapdialog.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)  # suppression du bouton ? dans la barre de titre
        self.mapdialog.show()

    # Méthode pour ouvrir la boîte de dialogue "À propos"
    def open_about_dialog(self):
        dialog = QtWidgets.QDialog()  # Crée un objet QDialog
        ui = Ui_Dialog()  # Instancie l'UI de la boîte de dialogue
        ui.setupUi(dialog)  # Configure l'UI
        dialog.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint) # suppression du bouton ? dans la barre de titre
        dialog.exec_()  # Affiche la boîte de dialogue de manière modale

    # Méthode pour ouvrir la fenetre de saisi des QSO
    def open_qso_dialog(self, typeqso):
        if not self.ui.affich_mycall.text() or not self.ui.affich_mygrid.text():
            fonct_annexe.show_message("warning", "Attention", "N'oubliez pas de saisir votre indicatif et votre QTH")
            return
        if self.actionqso == 0 and typeqso[0] != "new":
            fonct_annexe.show_message("warning", "Attention", "Avant de supprimer ou modifier un QSO, il faut sélectionner une ligne")
            return
        ligne_selectionnee = self.actionqso
        self.actionqso = 0 # Réinitialiser la sélection
        self.ui.tableView.clearSelection() # Désélectionner les lignes dans le tableau
        self.qsodialog = QtWidgets.QDialog()  # Crée un objet QDialog
        self.qsodialog.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)  # suppression du bouton ? dans la barre de titre
        self.ui2 = Ui_fen_qso()  # Instancie l'UI de la boîte de dialogue
        self.ui2.setupUi(self.qsodialog)  # Configure l'UI
        self.qsodialog.show()  # Affiche la boîte de dialogue de manière non modale
        if typeqso[0] == "new":
            self.ui2.label_suppr.hide()
            self.ui2.label_modifier.hide()
            self.ui2.label_ajouter.show()
        elif typeqso[0] == "mod":
            self.ui2.label_ajouter.hide()
            self.ui2.label_suppr.hide()
            self.ui2.label_modifier.show()
        elif typeqso[0] == "sup":
            self.ui2.label_modifier.hide()
            self.ui2.label_ajouter.hide()
            self.ui2.label_suppr.show()
        choixmode = ["AM","FM","SSB","CW","SSTV","DIGITALVOICE"]
        self.ui2.choix_mode.addItems(choixmode)
        self.ui2.saisie_timeon.setText(self.now_utc.strftime("%H%M"))
        self.ui2.saisie_date.setText(self.now_utc.strftime("%d%m%Y")) # Format de la date et de l'heure
        self.ui2.bouton_enregister.clicked.connect(lambda: self.save_qso(typeqso[0], ligne_selectionnee)) #confirmation d'action
        self.ui2.bouton_annuler.clicked.connect(self.qsodialog.close)
        #masque de saisie
        fonct_annexe.appliquer_validateur_float(self.ui2.saisie_freq, decimales=4)
        self.ui2.saisie_freq.setPlaceholderText("1,234.5678")
        # Si ce n'est pas un nouveau QSO, charger les données existantes
        if typeqso[0] != "new":
            sql = '''SELECT * FROM qso WHERE "idqso" = (?)'''
            lignebdd = connection.db.fetch_one_data(sql, (ligne_selectionnee,))
            if lignebdd:
                champs_mapping = {
                    self.ui2.saisie_calla: lignebdd[3],
                    self.ui2.saisie_date: f"{lignebdd[5][6:]}{lignebdd[5][4:6]}{lignebdd[5][:4]}",  # Formater la date
                    self.ui2.saisie_timeon: lignebdd[6],
                    self.ui2.saisie_freq: lignebdd[9],
                    self.ui2.saisie_rsta: lignebdd[11],
                    self.ui2.saisie_callb: lignebdd[4],
                    self.ui2.saisie_rstb: lignebdd[12],
                    self.ui2.saisie_timeoff: lignebdd[7],
                    self.ui2.saisie_comment: lignebdd[13]
                }
                # Appliquer les valeurs aux widgets de l'UI
                for widget, valeur in champs_mapping.items():
                    if valeur is not None:  # S'assurer que la valeur n'est pas nulle
                        widget.setText(str(valeur))
                # Sélectionner l'élément correspondant dans le QComboBox (choix_mode)
                if lignebdd[10] in [self.ui2.choix_mode.itemText(i) for i in range(self.ui2.choix_mode.count())]:
                    self.ui2.choix_mode.setCurrentText(lignebdd[10])


    # Méthode pour enregistrer la saisie d'un nouveau QSO en BDD
    def save_qso(self, typeqso , ligne_selectionnee):
        if typeqso == "sup":
            sql = "DELETE FROM qso WHERE idqso = ?"
            # Appel à la fonction d'insertion
            if connection.db.exec_data(sql, (ligne_selectionnee,)):
                # Si l'insertion a réussi, lance une autre action
                fonct_annexe.show_message("info", "Succès", "La ligne a été supprimée")
                # Après l'insertion dans la base
                self.populate_table()
                self.qsodialog.close()
            else:
                # Si la suppression a échouée, affiche une erreur
                fonct_annexe.show_message("warning", "Erreur", "La suppression a échoué")

        else:
            data = [self.ui.affich_mycall.text(), self.ui.affich_mygrid.text(), self.ui2.saisie_calla.text(), self.ui2.saisie_date.text(), self.ui2.saisie_timeon.text(), self.ui2.saisie_freq.text(), self.ui2.choix_mode.currentText(), self.ui2.saisie_rsta.text(), self.ui2.saisie_comment.text(), self.ui2.saisie_callb.text(), self.ui2.saisie_timeoff.text(), self.ui2.saisie_rstb.text()]
            if not self.validate_qso_data(data):
                return  # Validation échouée, retournez sans continuer

            '''band_qso = "None"
                for i, (min_freq, max_freq) in enumerate(self.BANDS_RANGES):
                if min_freq is not None and max_freq is not None:
                    if min_freq <= int(self.ui2.saisie_freq.text()) <= max_freq:
                        # Retourne le nom de la bande et sa plage
                        band_qso = self.BANDS[i]'''
            # freq` est la fréquence saisie par l'utilisateur.
            freq = float(self.ui2.saisie_freq.text())
            # Initialisez une variable pour stocker le résultat
            band_qso = (None, (None, None))

            # Parcourez le dictionnaire pour trouver la bande correspondante
            for band, (min_freq, max_freq) in self.BANDS_DATA.items():
                if min_freq is not None and max_freq is not None:
                    if min_freq <= freq <= max_freq:
                        # Assignez le nom de la bande et sa plage à `band_qso`
                        band_qso = (band, (min_freq, max_freq))
                        break  # On peut arrêter la boucle une fois la bande trouvée
            # band_qso contient maintenant le nom de la bande et sa plage, ou None si rien n'a été trouvé

            if typeqso == "new":
                sql = "INSERT INTO qso (STATION_CALLSIGN, MY_GRIDSQUARE, CALL, QSO_DATE, TIME_ON, BAND, FREQ, MODE, RST_SENT, COMMENT, CALL_B, TIME_OFF, RST_B, export) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)"
                # Les données à insérer
                data = (
                    fonct_annexe.format_callsign(self.ui.affich_mycall.text()),
                    self.ui.affich_mygrid.text(),
                    fonct_annexe.format_callsign(self.ui2.saisie_calla.text()),
                    f"{self.ui2.saisie_date.text()[4:]}{self.ui2.saisie_date.text()[2:4]}{self.ui2.saisie_date.text()[:2]}",
                    self.ui2.saisie_timeon.text(),
                    band_qso[0],
                    self.ui2.saisie_freq.text(),
                    self.ui2.choix_mode.currentText(),
                    self.ui2.saisie_rsta.text(),
                    self.ui2.saisie_comment.text(),
                    fonct_annexe.format_callsign(self.ui2.saisie_callb.text()),
                    self.ui2.saisie_timeoff.text(),
                    self.ui2.saisie_rstb.text()
                )
                # Appel à la fonction d'insertion
                if connection.db.exec_data(sql, data):
                    # Si l'insertion a réussi, lance une autre action
                    fonct_annexe.show_message("info", "Succès", "Le QSO a été enregistré avec succès")
                    # Après l'insertion dans la base
                    callsign.verif_callsign(fonct_annexe.format_callsign(self.ui2.saisie_calla.text()))
                    if self.ui2.saisie_callb.text(): callsign.verif_callsign(fonct_annexe.format_callsign(self.ui2.saisie_callb.text()))
                    self.populate_table()
                    self.qsodialog.close()
                    self.open_qso_dialog(["new", 0])
                    if data:
                        self.ui2.saisie_freq.setText(data[6])
                        # Sélectionner l'élément correspondant dans le QComboBox (choix_mode)
                        self.ui2.choix_mode.setCurrentText(data[7])
                else:
                    # Si l'insertion a échoué, affiche une erreur
                    fonct_annexe.show_message("warning", "Erreur", "L'enregistrement a échoué")

            elif typeqso == "mod":
                data = (
                    fonct_annexe.format_callsign(self.ui2.saisie_calla.text()),
                    f"{self.ui2.saisie_date.text()[4:]}{self.ui2.saisie_date.text()[2:4]}{self.ui2.saisie_date.text()[:2]}",
                    self.ui2.saisie_timeon.text(),
                    band_qso[0],
                    self.ui2.saisie_freq.text(),
                    self.ui2.choix_mode.currentText(),
                    self.ui2.saisie_rsta.text(),
                    self.ui2.saisie_comment.text(),
                    fonct_annexe.format_callsign(self.ui2.saisie_callb.text()),
                    self.ui2.saisie_timeoff.text(),
                    self.ui2.saisie_rstb.text(),
                    ligne_selectionnee
                )
                sql = ("Update qso set CALL = ?, QSO_DATE = ?, TIME_ON = ?, BAND = ?, FREQ = ?, MODE = ?, RST_SENT = ?, COMMENT = ?, CALL_B = ?, TIME_OFF = ?, RST_B = ? where idqso = ?")
                # Appel à la fonction de modification
                if connection.db.exec_data(sql, data):
                    # Si la modification a réussi, lance une autre action
                    fonct_annexe.show_message("info", "Succès", "Le QSO a été modifié avec succès")
                    # Après l'insertion dans la base
                    callsign.verif_callsign(fonct_annexe.format_callsign(self.ui2.saisie_calla.text()))
                    if self.ui2.saisie_callb.text(): callsign.verif_callsign(
                        fonct_annexe.format_callsign(self.ui2.saisie_callb.text()))
                    self.populate_table()
                    self.qsodialog.close()
                else:
                    # Si la modification a échouée, affiche une erreur
                    fonct_annexe.show_message("warning", "Erreur", "La modification a échoué")

    # validation du formulaire QSO
    def validate_qso_data(self, data):
        """ Validate mandatory fields and formats for QSO data """

        # Check mandatory fields
        for index in [2, 5, 7]:
            if not data[index]:
                fonct_annexe.show_message("warning", "Attention", "Certains champs obligatoires sont vides")
                return False

        # Check date format
        if not data[3].isdigit() or len(data[3]) > 8 or int(data[3][:2]) > 31 or int(data[3][2:4]) > 12:
            fonct_annexe.show_message("warning", "Attention", "DATE n'est pas correct")
            return False

        # Check frequency length
        if len(data[5]) > 20:
            fonct_annexe.show_message("warning", "Attention", "FREQ est trop long")
            return False

        # Check RST_SENT format
        if not data[7].isdigit() or len(data[7]) > 5:
            fonct_annexe.show_message("warning", "Attention", "RST_SENT n'est pas correct")
            return False

        return True

    #ouverture fenetre callsign
    def open_callsign_dialog(self, qrz=None):
        self.callsigndialog = QtWidgets.QDialog()  # Crée un objet QDialog
        self.callsigndialog.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)  # suppression du bouton ? dans la barre de titre
        self.ui_callsign = Ui_fen_callsign()  # Instancie l'UI de la boîte de dialogue
        self.ui_callsign.setupUi(self.callsigndialog)  # Configure l'UI
        self.callsigndialog.show()  # Affiche la boîte de dialogue de manière non modale
        if qrz: # si on transmet le QRZ, c'est pour afficher le détail et le modifier
            sql_callsign='''SELECT * FROM callsign WHERE call = (?)'''
            result_callsign = connection.db.fetch_one_data(sql_callsign,(qrz,))
            if result_callsign:
                self.ui_callsign.saisie_call.setText(qrz)
                self.ui_callsign.saisie_nom.setText(result_callsign[2])
                self.ui_callsign.saisie_grid.setText(result_callsign[3])
                self.ui_callsign.saisie_adresse1.setText(result_callsign[4])
                self.ui_callsign.saisie_zip.setText(result_callsign[6])
                self.ui_callsign.saisie_ville.setText(result_callsign[7])
                self.ui_callsign.saisie_pays.setText(result_callsign[8])
                self.ui_callsign.saisie_dxcc.setText(result_callsign[10])
                self.ui_callsign.saisie_itu.setText(result_callsign[9])
                self.ui_callsign.saisie_cqzone.setText(result_callsign[11])
        if qrz:
            self.ui_callsign.bouton_enregister.clicked.connect(lambda: self.save_callsign("mod"))
        else:
            self.ui_callsign.bouton_enregister.clicked.connect(lambda: self.save_callsign("new"))

    #enregistrement des données du formulaire callsign
    def save_callsign(self, action = "new"):
        if self.ui_callsign.saisie_call.text():
            sql = "INSERT INTO callsign (nom, ITU, DXCC, CQZONE, gridsquare, adresse1, zipcode, ville, pays, call) VALUES (?,?,?,?,?,?,?,?,?,?)"
            data = [
                self.ui_callsign.saisie_nom.text(),
                self.ui_callsign.saisie_itu.text(),
                self.ui_callsign.saisie_dxcc.text(),
                self.ui_callsign.saisie_cqzone.text(),
                self.ui_callsign.saisie_grid.text(),
                self.ui_callsign.saisie_adresse1.text(),
                self.ui_callsign.saisie_zip.text(),
                self.ui_callsign.saisie_ville.text(),
                self.ui_callsign.saisie_pays.text(),
                self.ui_callsign.saisie_call.text()
            ]
            if action == "mod":
                sql = "UPDATE callsign SET nom = ? , ITU = ? , DXCC = ? , CQZONE = ? , gridsquare = ? , adresse1 = ?, zipcode = ?, ville = ?, pays = ? WHERE call = ?"
            if connection.db.exec_data(sql, data):
                fonct_annexe.show_message("info", "Succès", "Enregistrement confirmé")
                self.callsigndialog.close()
            else:
                fonct_annexe.show_message("warning", "Attention", "L'enregistrement a échoué")
        else:
            fonct_annexe.show_message("warning", "Attention", "Certains champs obligatoires sont vides")

    #affichage fenetre configuration ma station
    def open_station_dialog(self):
        self.stationdialog = QtWidgets.QDialog()  # Crée un objet QDialog
        self.stationdialog.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)  # suppression du bouton ? dans la barre de titre
        self.ui3 = Ui_fen_station()  # Instancie l'UI de la boîte de dialogue
        self.ui3.setupUi(self.stationdialog)  # Configure l'UI
        self.stationdialog.show()  # Affiche la boîte de dialogue de manière non modale
        self.ui3.saisie_qrz.setText(self.ma_station[2])
        self.ui3.saisie_mygrid.setText(self.ma_station[3])
        self.ui3.saisie_qthname.setText(self.ma_station[4])
        self.ui3.bouton_enregister.clicked.connect(self.save_config_station)  # confirmation d'action

    def save_config_station(self):
        data = (
            datetime.now(timezone.utc),
            fonct_annexe.format_callsign(self.ui3.saisie_qrz.text()),
            fonct_annexe.format_locator(self.ui3.saisie_mygrid.text()),
            self.ui3.saisie_qthname.text()
        )
        sql = "INSERT INTO mastation (date_changement, mycall, mygrid, qthname) values ( ?, ?, ?, ?)"
        # Appel à la fonction de modification
        if connection.db.exec_data(sql, data):
            # Si la modification a réussi, lance une autre action
            fonct_annexe.show_message("info", "Succès", "La station a été modifiée avec succès")
            # Après l'insertion dans la base
            self.ui.affich_mygrid.setText(data[2])
            self.ui.affich_mycall.setText(data[1])
            self.ui.affich_qthname.setText(data[3])
            self.stationdialog.close()
        else:
            # Si la modification a échouée, affiche une erreur
            fonct_annexe.show_message("warning", "Erreur", "La modification a échoué")

    # affichage fenetre configuration ma station
    def open_connex_dialog(self):
        self.connexdialog = QtWidgets.QDialog()  # Crée un objet QDialog
        self.connexdialog.setWindowFlags(
                QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)  # suppression du bouton ? dans la barre de titre
        self.ui4 = Ui_fen_connex()  # Instancie l'UI de la boîte de dialogue
        self.ui4.setupUi(self.connexdialog)  # Configure l'UI
        self.connexdialog.show()  # Affiche la boîte de dialogue de manière non modale
        self.ui4.saisie_login.setText(self.settings.value("login_qrzcq", "")) # "" par défaut si login_qrzcq est non configuré
        self.ui4.saisie_mdp.setText(self.settings.value("mdp_qrzcq", "")) # "" par défaut si mdp_qrzcq est non configuré
        self.ui4.saisie_apikey_json.setText(self.settings.value("apijson_qrzcq", ""))
        self.ui4.bouton_enregister.clicked.connect(self.save_config_connex)  # confirmation d'action
        self.ui4.bouton_raz.clicked.connect(self.raz_connex) #action RAZ de la connexion

    # enregistrement de la connexion à QRZCQ
    def save_config_connex(self):
        saisie_login =str(self.ui4.saisie_login.text())
        saisie_mdp = str(self.ui4.saisie_mdp.text())
        saisie_apijson = str(self.ui4.saisie_apikey_json.text())
        if saisie_login and saisie_mdp:
            # Enregistrer la langue sélectionnée dans les paramètres
            self.settings.setValue("login_qrzcq", saisie_login)
            self.settings.setValue("mdp_qrzcq", saisie_mdp)
            self.settings.setValue("apijson_qrzcq",saisie_apijson)
            fonct_annexe.show_message("info", "Succès", "Accès enregistré avec succès")
            self.connexdialog.close()
        else:
            fonct_annexe.show_message("warning", "Erreur", "Saisie incorrecte")

    # suppression de la connexion à QRZCQ
    def raz_connex(self):
        saisie_login = None
        saisie_mdp = None
        # Enregistrer la langue sélectionnée dans les paramètres
        self.settings.setValue("login_qrzcq", saisie_login)
        self.settings.setValue("mdp_qrzcq", saisie_mdp)
        fonct_annexe.show_message("info", "Succès", "Suppression de la connexion avec succès")
        self.connexdialog.close()


    # mise à jour de la date et de l'heure
    def update_date_time(self):
        # Obtenir la date et l'heure UTC
        self.now_utc = datetime.now(timezone.utc) # utcnow()
        formatted_time = self.now_utc.strftime("%H h %M")  # Format de la date et de l'heure
        formatted_date = self.now_utc.strftime("%d - %m - %Y")  # Format de la date et de l'heure
        # Mettre à jour le texte du QLabel
        self.ui.affich_hutc.setText(f"{formatted_time}")
        self.ui.affich_date.setText(f"{formatted_date}")


    def select_row(self, index):
        # Sélectionner toute la ligne de l'index cliqué
        row = index.row()  # Obtenir le numéro de la ligne
        column = index.column()
        model = self.ui.tableView.model() # Obtenir le modèle du tableau
        if column != (model.columnCount() - 1) and column != 1 and column != 9:  # model.columnCount() retourne le nombre total de colonnes
            self.ui.tableView.selectRow(row)  # Sélectionner la ligne entière
            # Obtenir la valeur de la colonne 0 de la ligne sélectionnée
            model = self.ui.tableView.model()
            value = model.data(model.index(row, 0))  # Récupérer la valeur de la colonne 0
            self.actionqso = int(value)
        else:
            if column == 1 or column == 9:
                # Obtenir le callsign de la selection
                callsign_select = model.data(model.index(row, column), QtCore.Qt.DisplayRole)  # Changez l'index selon la colonne où le chemin est stocké
                self.open_callsign_dialog(callsign_select)
            else:
                # Obtenir le chemin de l'image depuis le modèle
                file_path = model.data(model.index(row, 14), QtCore.Qt.UserRole)  # Changez l'index selon la colonne où le chemin est stocké
                if file_path:
                    self.show_image(file_path)

    def show_image(self, file_path):
        # Créer un QDialog pour afficher l'image
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Image")
        # Supprime le bouton d'aide et conserve uniquement le bouton de fermeture
        dialog.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowTitleHint)

        # Créer un QLabel pour afficher l'image
        label = QtWidgets.QLabel(dialog)
        pixmap = QtGui.QPixmap(file_path)
        label.setPixmap(pixmap.scaled(320, 256, QtCore.Qt.KeepAspectRatio))  # Ajuste la taille selon tes besoins

        # Disposition
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        dialog.setLayout(layout)

        # Afficher le dialogue
        dialog.exec_()


    def change_language(self, language_code):
        # Décharger le traducteur actuel
        self.app.removeTranslator(self.translator)
        # Charger le nouveau fichier de traduction
        if language_code == 'fr':
            self.translator.load("lang/lang_fr.qm")
        elif language_code == 'en':
            self.translator.load("lang/lang_en.qm")
        self.app.installTranslator(self.translator)
        # Mettre à jour l'interface principale
        self.ui.retranslateUi(self.mw)
        # Mettre à jour toutes les fenêtres/dialogues ouverts
        if hasattr(self, 'qsodialog') and self.qsodialog.isVisible():
            self.ui2.retranslateUi(self.qsodialog)
        # Refaire pour d'autres dialogues ou fenêtres
        if hasattr(self, 'stationdialog') and self.stationdialog.isVisible():
            self.ui3.retranslateUi(self.stationdialog) # pour fen_station
        # Refaire pour d'autres dialogues ou fenêtres
        if hasattr(self, 'mapdialog') and self.mapdialog.isVisible():
               self.ui_map.retranslateUi(self.mapdialog)  # pour fen_station
        # ... (répéter pour d'autres fenêtres ou dialogues ouverts)
        if hasattr(self, 'dialog') and self.dialog.isVisible():
            self.ui.retranslateUi(self.dialog) # pour la fenêtre "À propos"
        # Enregistrer la langue sélectionnée dans les paramètres
        self.settings.setValue("language", language_code)

    def load_language_settings(self):
        # Récupérer la langue enregistrée
        language_code = self.settings.value("language", "fr")  # "fr" par défaut si aucune langue n'est sauvegardée
        self.change_language(language_code)

    def chargement_settings(self):
        # chargement de la langue enregistrée
        self.load_language_settings()
        # Charger la position et la taille de la fenêtre principale
        geometry = self.settings.value("window/geometry")
        state = self.settings.value("window/state")
        if geometry:
            self.mw.restoreGeometry(geometry)
        if state:
            self.mw.restoreState(state)

    # Méthodes de sauvegarde et de chargement des paramètres de la fenêtre
    def save_settings(self):
        self.settings.setValue("window/geometry", self.mw.saveGeometry())
        self.settings.setValue("window/state", self.mw.saveState())



if __name__ == "__main__":
    # Création de l'application IHM
    application = ApplicationIHM()

    # Lancement de la boucle d'événements
    sys.exit(application.app.exec_())
