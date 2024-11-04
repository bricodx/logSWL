import connection
import fonct_annexe
import requests
import xml.etree.ElementTree as ET
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSettings
import logging


# Initialisation des paramètres pour mémoriser la configuration
settings = QSettings("bricodx_dev", "logSWL")

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


def verif_callsign(qrz = None):
    sql = "SELECT call FROM callsign WHERE call = (?)"
    result = connection.db.fetch_one_data(sql, (qrz,))
    # Vérification de la présence de 'qrz'
    if not result:
        sql = "INSERT INTO callsign (call , nom, ITU, DXCC, CQZONE, prefixe, gridsquare, LOTW, adresse1, zipcode, ville, pays, EQSL) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
        result_scrap = traitement_qrzcq(qrz)
        if traitement_qrzcq(qrz):
            data = (
                qrz, result_scrap[0], result_scrap[1], result_scrap[2], result_scrap[3], result_scrap[4],
                result_scrap[5],
                result_scrap[6], result_scrap[7], result_scrap[8], result_scrap[9], result_scrap[10], result_scrap[11])
            # execution de la requete préparée
            if connection.db.exec_data(sql, data):
                logger.info("call enregistré")
            else:
                logger.error("erreur bdd")

    else:
        logger.info("call déjà présent dans la base")


def renouveler_cle_api():
    login = settings.value("login_qrzcq", "")
    mdp = settings.value("mdp_qrzcq", "")
    if login and mdp:
        api_url = f"https://ssl.qrzcq.com/xml?username={login}&password={mdp}&agent=Program"
        # Envoi de la requête GET
        try :
            response = requests.get(api_url, timeout=10)
            # Vérification de la réponse
            if response.status_code == 200:
                # Parser la réponse XML
                root = ET.fromstring(response.text)

                # Namespace à définir pour les balises
                namespace = {'qrz': 'http://qrzcq.com'}

                # Extraire la nouvelle clé
                key_element = root.find('.//qrz:Key', namespace)
                if key_element is not None:
                    nouvelle_cle = key_element.text
                    logger.info(f"Nouvelle clé API obtenue : {nouvelle_cle}")
                    settings.setValue("apixml_qrzcq", nouvelle_cle)
                else:
                    logger.error("Erreur : Impossible de trouver la nouvelle clé API.")
                    return None
            else:
                logger.error(f"Erreur lors du renouvellement de la clé API, code HTTP : {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            logger.error("Erreur : La demande a dépassé le délai d'attente.")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de connexion : {e}")
            return None
    else:
        logger.info("vous n'avez de login et mdp QRZCQ")
        return None


def traitement_qrzcq(qrz):
    while True:  # Boucle infinie pour relancer la fonction si nécessaire
        # Envoi de la requête GET
        api_qrzcq_key = settings.value("apixml_qrzcq","")
        api_url = f"https://ssl.qrzcq.com/xml?s={api_qrzcq_key}&callsign={qrz}&agent=Program"
        try:
            response = requests.get(api_url, timeout=10)
            # Vérification de la réponse
            if response.status_code == 200:
                    # Parser la réponse XML
                root = ET.fromstring(response.text)
                # Namespace à définir pour les balises
                namespace = {'qrz': 'http://qrzcq.com'}

                erreur_api = root.find('.//qrz:Error', namespace)
                if erreur_api is not None:
                    erreur_api = erreur_api.text
                    if erreur_api == "Session Timeout":
                        logger.info("Erreur : Session Timeout détectée.")
                        api_qrzcq_key = renouveler_cle_api()  # Renouvelle la clé API
                        if api_qrzcq_key is None:  # Si le renouvellement échoue, sort de la boucle
                            break
                        continue  # Relance le traitement avec la nouvelle clé
                    elif erreur_api == f"Not found: {qrz}":
                        logger.info(f"Erreur : aucun {qrz} sur QRZCQ")
                        break  # Quitte la boucle si c'est une autre erreur
                    else:
                        logger.info("Erreur : ", erreur_api)
                        break  # Quitte la boucle si c'est une autre erreur

                if root.find('qrz:Callsign/qrz:name', namespace) is not None:
                    nom_complet_sans_plus = root.find('qrz:Callsign/qrz:name', namespace).text
                else:
                    nom_complet_sans_plus = None
                if root.find('qrz:Callsign/qrz:address', namespace) is not None:
                    address = root.find('qrz:Callsign/qrz:address', namespace).text
                else:
                    address = None
                if root.find('qrz:Callsign/qrz:zip', namespace) is not None:
                    zipcode = root.find('qrz:Callsign/qrz:zip', namespace).text
                else:
                    zipcode = None
                if root.find('qrz:Callsign/qrz:city', namespace) is not None:
                    city = root.find('qrz:Callsign/qrz:city', namespace).text
                else:
                    city = None
                if root.find('qrz:Callsign/qrz:country', namespace) is not None:
                    country = root.find('qrz:Callsign/qrz:country', namespace).text
                else:
                    country = None
                if root.find('qrz:Callsign/qrz:locator', namespace) is not None:
                    grid = root.find('qrz:Callsign/qrz:locator', namespace).text
                else:
                    grid = None
                if root.find('qrz:Callsign/qrz:dxcc', namespace) is not None:
                    dxcc = root.find('qrz:Callsign/qrz:dxcc', namespace).text
                else:
                    dxcc = None
                if root.find('qrz:Callsign/qrz:itu', namespace) is not None:
                    itu_zone = root.find('qrz:Callsign/qrz:itu', namespace).text
                else:
                    itu_zone = None
                if root.find('qrz:Callsign/qrz:cq', namespace) is not None:
                    cq_zone = root.find('qrz:Callsign/qrz:cq', namespace).text
                else:
                    cq_zone = None
                if root.find('qrz:Callsign/qrz:lotw', namespace) is not None:
                    lotw = root.find('qrz:Callsign/qrz:lotw', namespace).text
                else:
                    lotw = 0
                if root.find('qrz:Callsign/qrz:prefix', namespace) is not None:
                    prefix = root.find('qrz:Callsign/qrz:prefix', namespace).text
                else:
                    prefix = None
                if root.find('qrz:Callsign/qrz:eqsl', namespace) is not None:
                     eqsl = root.find('qrz:Callsign/qrz:eqsl', namespace).text
                else:
                    eqsl = 0

                return nom_complet_sans_plus, itu_zone, dxcc, cq_zone, prefix, grid, lotw, address, zipcode, city, country, eqsl
            else:
                logger.error(f"Erreur de connexion, code HTTP : {response.status_code}")
                break  # Quitte la boucle pour d'autres erreurs de connexion

        except requests.exceptions.ConnectTimeout:
            logger.error("Erreur : La connexion a dépassé le délai d'attente.")
            break  # On peut également utiliser `continue` pour réessayer

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de connexion : {e}")
            break


class Ui_fen_callsign(object):
    def setupUi(self, fen_callsign):
        fen_callsign.setObjectName("fen_callsign")
        fen_callsign.resize(590, 503)
        self.frame_callsign = QtWidgets.QFrame(fen_callsign)
        self.frame_callsign.setGeometry(QtCore.QRect(0, 0, 581, 491))
        self.frame_callsign.setObjectName("frame_callsign")
        self.label_prenom = QtWidgets.QLabel(self.frame_callsign)
        self.label_prenom.setGeometry(QtCore.QRect(50, 70, 100, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_prenom.setFont(font)
        self.label_prenom.setAccessibleName("")
        self.label_prenom.setAccessibleDescription("")
        self.label_prenom.setTextFormat(QtCore.Qt.PlainText)
        self.label_prenom.setObjectName("label_prenom")
        self.label_titre = QtWidgets.QLabel(self.frame_callsign)
        self.label_titre.setGeometry(QtCore.QRect(0, 0, 580, 40))
        font = QtGui.QFont()
        font.setPointSize(22)
        self.label_titre.setFont(font)
        self.label_titre.setAccessibleName("")
        self.label_titre.setTextFormat(QtCore.Qt.PlainText)
        self.label_titre.setAlignment(QtCore.Qt.AlignCenter)
        self.label_titre.setObjectName("label_titre")
        self.bouton_enregister = QtWidgets.QPushButton(self.frame_callsign)
        self.bouton_enregister.setGeometry(QtCore.QRect(315, 440, 75, 30))
        self.bouton_enregister.setObjectName("bouton_enregister")
        self.bouton_annuler = QtWidgets.QPushButton(self.frame_callsign)
        self.bouton_annuler.setGeometry(QtCore.QRect(450, 440, 75, 30))
        self.bouton_annuler.setObjectName("bouton_annuler")
        self.saisie_call = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_call.setGeometry(QtCore.QRect(40, 90, 121, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_call.setFont(font)
        self.saisie_call.setInputMask("")
        self.saisie_call.setText("")
        self.saisie_call.setMaxLength(14)
        self.saisie_call.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_call.setObjectName("saisie_call")
        self.label_nom = QtWidgets.QLabel(self.frame_callsign)
        self.label_nom.setGeometry(QtCore.QRect(250, 70, 151, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_nom.setFont(font)
        self.label_nom.setAccessibleName("")
        self.label_nom.setAccessibleDescription("")
        self.label_nom.setTextFormat(QtCore.Qt.PlainText)
        self.label_nom.setObjectName("label_nom")
        self.saisie_nom = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_nom.setGeometry(QtCore.QRect(240, 90, 291, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_nom.setFont(font)
        self.saisie_nom.setInputMask("")
        self.saisie_nom.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_nom.setObjectName("saisie_nom")
        self.label_adresse1 = QtWidgets.QLabel(self.frame_callsign)
        self.label_adresse1.setGeometry(QtCore.QRect(50, 140, 151, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_adresse1.setFont(font)
        self.label_adresse1.setAccessibleName("")
        self.label_adresse1.setAccessibleDescription("")
        self.label_adresse1.setTextFormat(QtCore.Qt.PlainText)
        self.label_adresse1.setObjectName("label_adresse1")
        self.saisie_adresse1 = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_adresse1.setGeometry(QtCore.QRect(40, 160, 501, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_adresse1.setFont(font)
        self.saisie_adresse1.setInputMask("")
        self.saisie_adresse1.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_adresse1.setObjectName("saisie_adresse1")
        self.label_pays = QtWidgets.QLabel(self.frame_callsign)
        self.label_pays.setGeometry(QtCore.QRect(120, 280, 151, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_pays.setFont(font)
        self.label_pays.setAccessibleName("")
        self.label_pays.setAccessibleDescription("")
        self.label_pays.setTextFormat(QtCore.Qt.PlainText)
        self.label_pays.setObjectName("label_pays")
        self.saisie_pays = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_pays.setGeometry(QtCore.QRect(110, 300, 331, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_pays.setFont(font)
        self.saisie_pays.setInputMask("")
        self.saisie_pays.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_pays.setObjectName("saisie_pays")
        self.label_zip = QtWidgets.QLabel(self.frame_callsign)
        self.label_zip.setGeometry(QtCore.QRect(60, 210, 151, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_zip.setFont(font)
        self.label_zip.setAccessibleName("")
        self.label_zip.setAccessibleDescription("")
        self.label_zip.setTextFormat(QtCore.Qt.PlainText)
        self.label_zip.setObjectName("label_zip")
        self.saisie_zip = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_zip.setGeometry(QtCore.QRect(50, 230, 151, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_zip.setFont(font)
        self.saisie_zip.setInputMask("")
        self.saisie_zip.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_zip.setObjectName("saisie_zip")
        self.label_ville = QtWidgets.QLabel(self.frame_callsign)
        self.label_ville.setGeometry(QtCore.QRect(260, 210, 151, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_ville.setFont(font)
        self.label_ville.setAccessibleName("")
        self.label_ville.setAccessibleDescription("")
        self.label_ville.setTextFormat(QtCore.Qt.PlainText)
        self.label_ville.setObjectName("label_ville")
        self.saisie_ville = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_ville.setGeometry(QtCore.QRect(250, 230, 261, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_ville.setFont(font)
        self.saisie_ville.setInputMask("")
        self.saisie_ville.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_ville.setObjectName("saisie_ville")
        self.saisie_dxcc = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_dxcc.setGeometry(QtCore.QRect(20, 370, 101, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_dxcc.setFont(font)
        self.saisie_dxcc.setInputMask("9999")
        self.saisie_dxcc.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_dxcc.setObjectName("saisie_dxcc")
        self.label_dxcc = QtWidgets.QLabel(self.frame_callsign)
        self.label_dxcc.setGeometry(QtCore.QRect(30, 350, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_dxcc.setFont(font)
        self.label_dxcc.setAccessibleName("")
        self.label_dxcc.setAccessibleDescription("")
        self.label_dxcc.setTextFormat(QtCore.Qt.PlainText)
        self.label_dxcc.setObjectName("label_dxcc")
        self.label_grid = QtWidgets.QLabel(self.frame_callsign)
        self.label_grid.setGeometry(QtCore.QRect(420, 350, 201, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_grid.setFont(font)
        self.label_grid.setAccessibleName("")
        self.label_grid.setAccessibleDescription("")
        self.label_grid.setTextFormat(QtCore.Qt.PlainText)
        self.label_grid.setObjectName("label_mygrid")
        self.saisie_grid = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_grid.setGeometry(QtCore.QRect(410, 370, 141, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_grid.setFont(font)
        self.saisie_grid.setInputMask("AA99aa")
        self.saisie_grid.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_grid.setObjectName("saisie_grid")
        self.label_exemple = QtWidgets.QLabel(self.frame_callsign)
        self.label_exemple.setGeometry(QtCore.QRect(510, 350, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label_exemple.setFont(font)
        self.label_exemple.setObjectName("label_exemple")
        self.label_cqzone = QtWidgets.QLabel(self.frame_callsign)
        self.label_cqzone.setGeometry(QtCore.QRect(160, 350, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_cqzone.setFont(font)
        self.label_cqzone.setAccessibleName("")
        self.label_cqzone.setAccessibleDescription("")
        self.label_cqzone.setTextFormat(QtCore.Qt.PlainText)
        self.label_cqzone.setObjectName("label_cqzone")
        self.saisie_cqzone = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_cqzone.setGeometry(QtCore.QRect(150, 370, 101, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_cqzone.setFont(font)
        self.saisie_cqzone.setInputMask("999")
        self.saisie_cqzone.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_cqzone.setObjectName("saisie_cqzone")
        self.label_itu = QtWidgets.QLabel(self.frame_callsign)
        self.label_itu.setGeometry(QtCore.QRect(290, 350, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label_itu.setFont(font)
        self.label_itu.setAccessibleName("")
        self.label_itu.setAccessibleDescription("")
        self.label_itu.setTextFormat(QtCore.Qt.PlainText)
        self.label_itu.setObjectName("label_itu")
        self.saisie_itu = QtWidgets.QLineEdit(self.frame_callsign)
        self.saisie_itu.setGeometry(QtCore.QRect(280, 370, 101, 30))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.saisie_itu.setFont(font)
        self.saisie_itu.setInputMask("999")
        self.saisie_itu.setAlignment(QtCore.Qt.AlignCenter)
        self.saisie_itu.setObjectName("saisie_itu")

        self.retranslateUi(fen_callsign)
        self.bouton_annuler.clicked.connect(fen_callsign.close) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(fen_callsign)

    def retranslateUi(self, fen_callsign):
        _translate = QtCore.QCoreApplication.translate
        fen_callsign.setWindowTitle(_translate("fen_callsign", "Dialog"))
        self.label_prenom.setText(_translate("fen_callsign", "CALLSIGN"))
        self.label_titre.setText(_translate("fen_callsign", "Info CALLSIGN"))
        self.bouton_enregister.setText(_translate("fen_callsign", "Valider"))
        self.bouton_annuler.setText(_translate("fen_callsign", "Annuler"))
        self.label_nom.setText(_translate("fen_callsign", "NOM"))
        self.label_adresse1.setText(_translate("fen_callsign", "Adresse 1"))
        self.label_pays.setText(_translate("fen_callsign", "PAYS"))
        self.label_zip.setText(_translate("fen_callsign", "ZIP code"))
        self.label_ville.setText(_translate("fen_callsign", "VILLE"))
        self.label_dxcc.setText(_translate("fen_callsign", "DXCC"))
        self.label_grid.setText(_translate("fen_callsign", "LOCATOR"))
        self.label_exemple.setText(_translate("fen_callsign", "Ex: JN18eu"))
        self.label_cqzone.setText(_translate("fen_callsign", "CQ-zone"))
        self.label_itu.setText(_translate("fen_callsign", "ITU"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    fen_callsign = QtWidgets.QDialog()
    ui = Ui_fen_callsign()
    ui.setupUi(fen_callsign)
    fen_callsign.show()
    sys.exit(app.exec_())
