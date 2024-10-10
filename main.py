from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import  QIcon, QPixmap
import sys
from fen_station import Ui_fen_station
from logswl import Ui_MainWindow
from apropos import Ui_Dialog
from fenqso import Ui_fen_qso
import connection
from datetime import datetime,timezone
import callsign
import fonct_annexe
import logging
import grid

# Configuration du logger
logging.basicConfig(level=logging.DEBUG)  # Changez en logging.INFO ou  logging.DEBUG

class ApplicationIHM:
    def __init__(self):
        super(ApplicationIHM, self).__init__()
        # Création de l'application
        self.app = QtWidgets.QApplication(sys.argv)
        self.actionqso = 0

        # All the bands listed in the ADIF specification.
        self.BANDS = ["", "2190m", "630m", "560m", "160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m",
                 "6m", "4m", "2m", "1.25m", "70cm", "33cm", "23cm", "13cm", "9cm", "6cm", "3cm", "1.25cm", "6mm", "4mm",
                 "2.5mm", "2mm", "1mm"]
        # The lower and upper frequency bounds (in MHz) for each band in BANDS.
        self.BANDS_RANGES = [(None, None), (136, 137), (472, 479), (501, 504), (1800, 2000), (3500, 4000),
                        (5102, 5406.5), (7000, 7300), (10000, 10150), (14000, 14350), (18068, 18168), (21000, 21450),
                        (24890, 24990), (28000, 29700), (50000, 54000), (70000, 71000), (144000, 148000), (222000, 225000),
                        (420000, 450000), (902000, 928000), (1240000, 1300000), (2300000, 2450000), (3300000, 3500000),
                        (5650000, 5925000), (10000000, 10500000), (24000000, 24250000), (47000000, 47200000),
                        (75500000, 81000000), (119980000, 120020000), (142000000, 149000000), (241000000, 250000000)]

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
        self.ui.actionMap_des_QSO.triggered.connect(self.open_map)
        # Connexion menu pour ouvrir la fenêtre "ma station"
        self.ui.actionMa_station.triggered.connect(self.open_station_dialog)
        # Connexion MOD pour ouvrir la fenêtre "qso"
        self.ui.bouton_nouveau.clicked.connect(lambda: self.open_qso_dialog(["new",0]))
        self.ui.bouton_modifier.clicked.connect(lambda: self.open_qso_dialog(["mod",0]))
        self.ui.bouton_supprimer.clicked.connect(lambda: self.open_qso_dialog(["sup",0]))
        # Connexion d'une nouvelle action pour ouvrir la fenêtre "À propos"
        self.ui.actionA_propos.triggered.connect(self.open_about_dialog)
        # Connecter le signal clicked à la méthode de sélection
        self.ui.tableView.clicked.connect(self.select_row)
        self.populate_table()
        # Affichage de la fenêtre principale
        self.mw.show()
        self.update_date_time()
        # Création et configuration du timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_date_time)  # Appelle update_date_time toutes les secondes
        self.timer.start(30000)  # Intervalle de 1000 ms (1 seconde)


    # Méthode pour remplir le QTableView
    def populate_table(self):
        largeur_des_colonnes = [60,90,100,70,90,80,100,70,70,90,70,70,70,180,30]
        entete_colonne = ["Id", "CALL", "DATE", "TIME_ON", "FREQ", "BAND", "MODE", "RST_SENT","LOCA","CALL_B", "RST_B","LOCB","TIME_OFF","COMMENT","img"]
        sql = '''SELECT * FROM qso ORDER BY "idqso" DESC'''
        liste_all = connection.db.fetch_data(sql)
        nbre_item = len(liste_all)
        # Crée un modèle pour la table
        model = QtGui.QStandardItemModel()

        # Ajouter des entêtes de colonnes (omettre les colonnes 2 et 4 par exemple)
        # Supposons que self.entete_colonne a été définie avec toutes les colonnes disponibles
        # Vous pouvez également créer une liste personnalisée d'entêtes pour les colonnes à afficher.
        colonnes_a_afficher = [0, 3, 5, 6, 9, 8, 10, 11,14, 4, 12,15, 7, 13]  # Indices des colonnes que vous voulez afficher

        # Ajouter des entêtes de colonnes
        model.setHorizontalHeaderLabels(entete_colonne)

        # Ajouter les données au modèle
        for row in liste_all:
            # Sélectionner uniquement les colonnes que vous souhaitez afficher
            filtered_row = [row[i] for i in colonnes_a_afficher]
            filtered_row.append(fonct_annexe.test_presence_fichier(f"sstv/{filtered_row[2]}{filtered_row[3]}.png"))  # Ajoute l'image à la fin de filtered_row
            filtered_row[3] = f"{filtered_row[3][:2]}:{filtered_row[3][2:]}"
            filtered_row[2] = f"{filtered_row[2][6:]}-{filtered_row[2][4:6]}-{filtered_row[2][:4]}"

            '''items = [QtGui.QStandardItem(str(field) if field is not None and field != "0" else "") for field in filtered_row]
            for item in items:
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)  # Rendre la cellule non modifiable
            model.appendRow(items)'''
            # Créer les items pour chaque cellule
            items = []
            for index,field in enumerate(filtered_row):
                item = QtGui.QStandardItem()
                if field and field != "0":
                    if isinstance(field, str) and (field.endswith(".png") or field.endswith(".jpg")):
                        # Charger l'image dans un QImage
                        image = QPixmap(field)  # Utilise le chemin pour créer un QImage
                        icon = QIcon("sstv/icon.png")  # Créer un QIcon à partir du QPixmap redimensionné
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

    def open_map(self):
        self.map_window = grid.MapWindow()
        self.map_window.show()


    # Méthode pour ouvrir la boîte de dialogue "À propos"
    def open_about_dialog(self):
        dialog = QtWidgets.QDialog()  # Crée un objet QDialog
        ui = Ui_Dialog()  # Instancie l'UI de la boîte de dialogue
        ui.setupUi(dialog)  # Configure l'UI
        # Créer un modèle pour le QListView
        model = QtGui.QStandardItemModel()  # Utiliser QStandardItemModel pour peupler le QListView
        # Peupler le modèle avec des données
        data = ["20/09/2024   Début du codage de cette application ", "06/10/2024   L'application est fonctionnel"]
        for item in data:
            model.appendRow(QtGui.QStandardItem(item))  # Ajouter chaque item au modèle
        # Assigner le modèle au QListView
        ui.listView.setModel(model)  # Assigner le modèle au QListView
        dialog.exec_()  # Affiche la boîte de dialogue de manière modale

    # Méthode pour ouvrir la fenetre de saisi des QSO
    def open_qso_dialog(self, typeqso):
        if not self.ui.affich_mycall.text() or not self.ui.affich_mygrid.text():
            QtWidgets.QMessageBox.warning(None, "Attention",
                               "N'oubliez pas de saisir votre indicatif et votre QTH")
            return
        if self.actionqso == 0 and typeqso[0] != "new":
            QtWidgets.QMessageBox.warning(None,"Attention",
                                          "Avant de supprimer ou modifier un QSO, il faut sélectionner une ligne")
            return
        ligne_selectionnee = self.actionqso
        self.actionqso = 0 # Réinitialiser la sélection
        self.ui.tableView.clearSelection() # Désélectionner les lignes dans le tableau
        self.qsodialog = QtWidgets.QDialog()  # Crée un objet QDialog
        self.ui2 = Ui_fen_qso()  # Instancie l'UI de la boîte de dialogue
        self.ui2.setupUi(self.qsodialog)  # Configure l'UI
        self.qsodialog.show()  # Affiche la boîte de dialogue de manière non modale
        if typeqso[0] == "new":
            self.ui2.label_titre.setText(" Nouveau QSO")
        elif typeqso[0] == "mod":
            self.ui2.label_titre.setText(" Modifier un QSO")
        elif typeqso[0] == "sup":
            self.ui2.label_titre.setText(" Supprimer un QSO")
        choixmode = ["AM","FM","SSB","CW","SSTV","DIGITALVOICE","RTTY", ]
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
            if connection.db.delete_ligne(sql, (ligne_selectionnee,)):
                # Si l'insertion a réussi, lance une autre action
                QtWidgets.QMessageBox.information(None, "Succès", "La ligne a été supprimée")
                # Après l'insertion dans la base
                self.populate_table()
                self.qsodialog.close()
            else:
                # Si la suppression a échouée, affiche une erreur
                QtWidgets.QMessageBox.warning(None, "Erreur", "La suppression a échoué")

        else:
            data = [self.ui.affich_mycall.text(), self.ui.affich_mygrid.text(), self.ui2.saisie_calla.text(), self.ui2.saisie_date.text(), self.ui2.saisie_timeon.text(), self.ui2.saisie_freq.text(), self.ui2.choix_mode.currentText(), self.ui2.saisie_rsta.text(), self.ui2.saisie_comment.text(), self.ui2.saisie_callb.text(), self.ui2.saisie_timeoff.text(), self.ui2.saisie_rstb.text()]
            data_obligatoire = [2,5,7]
            for index in data_obligatoire:
                if not data[index]:
                    QtWidgets.QMessageBox.warning(None,"Attention", f"Certains champs obligatoires sont vides")
                    return
            if not self.ui2.saisie_date.text().isdigit() or len(self.ui2.saisie_date.text()) > 8 or int(self.ui2.saisie_date.text()[:2]) > 31 or int(self.ui2.saisie_date.text()[2:4]) > 12:
                QtWidgets.QMessageBox.warning(None,"Attention", f"DATE n'est pas correct")
                return
            if len(self.ui2.saisie_freq.text()) > 20:
                QtWidgets.QMessageBox.warning(None, "Attention", f"FREQ est trop long")
                return
            if not self.ui2.saisie_rsta.text().isdigit() or len(self.ui2.saisie_rsta.text()) > 5:
                QtWidgets.QMessageBox.warning(None, "Attention", f"RST_SENT n'est pas correct")
                return
            band_qso = "None"
            for i, (min_freq, max_freq) in enumerate(self.BANDS_RANGES):
                if min_freq is not None and max_freq is not None:
                    if min_freq <= int(self.ui2.saisie_freq.text()) <= max_freq:
                        # Retourne le nom de la bande et sa plage
                        band_qso = self.BANDS[i]

            if typeqso == "new":
                sql = "INSERT INTO qso (STATION_CALLSIGN, MY_GRIDSQUARE, CALL, QSO_DATE, TIME_ON, BAND, FREQ, MODE, RST_SENT, COMMENT, CALL_B, TIME_OFF, RST_B, export) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)"
                # Les données à insérer
                data = (
                    fonct_annexe.format_callsign(self.ui.affich_mycall.text()),
                    self.ui.affich_mygrid.text(),
                    fonct_annexe.format_callsign(self.ui2.saisie_calla.text()),
                    f"{self.ui2.saisie_date.text()[4:]}{self.ui2.saisie_date.text()[2:4]}{self.ui2.saisie_date.text()[:2]}",
                    self.ui2.saisie_timeon.text(),
                    band_qso,
                    self.ui2.saisie_freq.text(),
                    self.ui2.choix_mode.currentText(),
                    self.ui2.saisie_rsta.text(),
                    self.ui2.saisie_comment.text(),
                    fonct_annexe.format_callsign(self.ui2.saisie_callb.text()),
                    self.ui2.saisie_timeoff.text(),
                    self.ui2.saisie_rstb.text()
                )
                # Appel à la fonction d'insertion
                if connection.db.insert_data(sql, data):
                    # Si l'insertion a réussi, lance une autre action
                    QtWidgets.QMessageBox.information(None, "Succès", "Le QSO a été enregistré avec succès")
                    # Après l'insertion dans la base
                    callsign.verif_callsign(fonct_annexe.format_callsign(self.ui2.saisie_calla.text()),)
                    if self.ui2.saisie_callb.text(): callsign.verif_callsign(fonct_annexe.format_callsign(self.ui2.saisie_callb.text()),)
                    self.populate_table()
                    self.qsodialog.close()
                    self.open_qso_dialog(["new", 0])
                else:
                    # Si l'insertion a échoué, affiche une erreur
                    QtWidgets.QMessageBox.warning(None, "Erreur", "L'enregistrement a échoué")

            elif typeqso == "mod":
                data = (
                    fonct_annexe.format_callsign(self.ui2.saisie_calla.text()),
                    f"{self.ui2.saisie_date.text()[4:]}{self.ui2.saisie_date.text()[2:4]}{self.ui2.saisie_date.text()[:2]}",
                    self.ui2.saisie_timeon.text(),
                    band_qso,
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
                if connection.db.modif_ligne(sql, data):
                    # Si la modification a réussi, lance une autre action
                    QtWidgets.QMessageBox.information(None, "Succès", "Le QSO a été modifié avec succès")
                    # Après l'insertion dans la base
                    callsign.verif_callsign(fonct_annexe.format_callsign(self.ui2.saisie_calla.text()),)
                    if self.ui2.saisie_callb.text(): callsign.verif_callsign(
                        fonct_annexe.format_callsign(self.ui2.saisie_callb.text()), )
                    self.populate_table()
                    self.qsodialog.close()
                else:
                    # Si la modification a échouée, affiche une erreur
                    QtWidgets.QMessageBox.warning(None, "Erreur", "La modification a échoué")

    #affichage fenetre configuration ma station
    def open_station_dialog(self):
        self.stationdialog = QtWidgets.QDialog()  # Crée un objet QDialog
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
        if connection.db.insert_data(sql, data):
            # Si la modification a réussi, lance une autre action
            QtWidgets.QMessageBox.information(None, "Succès", "La station a été modifié avec succès")
            # Après l'insertion dans la base
            self.ui.affich_mygrid.setText(data[2])
            self.ui.affich_mycall.setText(data[1])
            self.ui.affich_qthname.setText(data[3])
            self.stationdialog.close()
        else:
            # Si la modification a échouée, affiche une erreur
            QtWidgets.QMessageBox.warning(None, "Erreur", "La modification a échoué")


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
        if column != (model.columnCount() - 1):  # model.columnCount() retourne le nombre total de colonnes
            self.ui.tableView.selectRow(row)  # Sélectionner la ligne entière
            # Obtenir la valeur de la colonne 0 de la ligne sélectionnée
            model = self.ui.tableView.model()
            value = model.data(model.index(row, 0))  # Récupérer la valeur de la colonne 0
            self.actionqso = int(value)
        else:
            # Obtenir le chemin de l'image depuis le modèle
            print (model.data(model.index(row, 14)))
            file_path = model.data(model.index(row, 14), QtCore.Qt.UserRole)  # Changez l'index selon la colonne où le chemin est stocké
            if file_path:
                self.show_image(file_path)

        for i in range(model.columnCount()):
            print(f"Column {i}: {model.data(model.index(row, i))}")

    def show_image(self, file_path):
        # Créer un QDialog pour afficher l'image
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Image")

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



if __name__ == "__main__":
    # Création de l'application IHM
    application = ApplicationIHM()

    # Lancement de la boucle d'événements
    sys.exit(application.app.exec_())
