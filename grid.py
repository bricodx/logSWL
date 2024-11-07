import folium
import io
import connection
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView


def position_pin(gridsquare = 'JN18eu' ):
    gridsquare = gridsquare.upper()  # Toujours travailler en majuscule

    # Calcul des deux premiers caractères (grande zone)
    lon_base = (ord(gridsquare[0]) - ord('A')) * 20 - 180
    lat_base = (ord(gridsquare[1]) - ord('A')) * 10 - 90

    # Calcul avec les deux chiffres suivants (sous-zone)
    lon_offset = int(gridsquare[2]) * 2
    lat_offset = int(gridsquare[3]) * 1

    # Longitude et latitude initiales pour un gridsquare de 4 caractères
    lon = lon_base + lon_offset
    lat = lat_base + lat_offset

    # Si le gridsquare est à 6 caractères, ajouter le calcul pour les deux derniers caractères
    if len(gridsquare) == 6:
        lon_small_offset = (ord(gridsquare[4]) - ord('A')) * 5 / 60
        lat_small_offset = (ord(gridsquare[5]) - ord('A')) * 2.5 / 60

        lon += lon_small_offset
        lat += lat_small_offset

    return lat, lon



class Ui_mapDialog(object):
    def setupUi(self, mapDialog, mygrid = 'JN18eu',choixcarte=None):
        mapDialog.setObjectName("mapDialog")
        mapDialog.resize(1100, 720)
        self.mygrid = mygrid
        # Créer un layout vertical principal
        self.mainLayout = QtWidgets.QVBoxLayout(mapDialog)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # Créer un layout horizontal pour les boutons
        self.button_Layout = QtWidgets.QHBoxLayout()
        self.button_Layout.setContentsMargins(0, 0, 0, 0)
        self.button_Layout.setSpacing(5)


        # Obtenir les résultats de la requête SQL
        if choixcarte == "Mode":
            sql = "SELECT q.MODE, COUNT(*) AS count FROM qso AS q JOIN callsign AS c ON q.call = c.call WHERE c.gridsquare IS NOT NULL GROUP BY MODE"
        else:
            sql = "SELECT q.BAND, COUNT(*) AS count FROM qso AS q JOIN callsign AS c ON q.call = c.call WHERE c.gridsquare IS NOT NULL GROUP BY BAND"
        results = connection.db.fetch_data(sql)

        # Ajouter les boutons en fonction des résultats de la requête
        button_text = f"All"  # Texte du bouton incluant le nombre d'occurrences
        button = QtWidgets.QPushButton(button_text)
        self.button_Layout.addWidget(button)
        button.clicked.connect(lambda: self.on_button_click())

        # Ajouter les boutons en fonction des résultats de la requête
        for filtre, count in results:
            button_text = f"{filtre} ({count})"  # Texte du bouton incluant le nombre d'occurrences
            button = QtWidgets.QPushButton(button_text)
            self.button_Layout.addWidget(button)
            # Connecter chaque bouton avec une méthode personnalisée
            if choixcarte =="Mode":
                button.clicked.connect(lambda _, f=filtre: self.on_button_click(None, f))
            else:
                button.clicked.connect(lambda _, f=filtre: self.on_button_click(f, None))

        # Ajouter le button_band_Layout au layout principal
        self.mainLayout.addLayout(self.button_Layout)

        # Créer le composant QWebEngineView et un widget pour l'encapsuler
        self.web_view = QWebEngineView()

        # Charger la carte directement en HTML
        map_html = self.create_map()
        self.web_view.setHtml(map_html)

        # Ajouter le QWebEngineView directement dans le layout principal
        self.mainLayout.addWidget(self.web_view)

        self.retranslateUi(mapDialog)
        QtCore.QMetaObject.connectSlotsByName(mapDialog)

    def retranslateUi(self, mapDialog):
        _translate = QtCore.QCoreApplication.translate
        mapDialog.setWindowTitle(_translate("mapDialog", "Map des QSO"))

    def create_map(self, band=None, mode=None):
        zoom_level = 2
        ma_position = position_pin(self.mygrid) # récupération de la position de l'écouteur
        m = folium.Map(location=[ma_position[0], ma_position[1]], zoom_start=zoom_level, tiles='OpenStreetMap') # création de la carte centrée sur la position de l'écouteur
        folium.Marker([ma_position[0], ma_position[1]],tooltip="My QTH",icon=folium.Icon(color='red')).add_to(m) # placement sur la map d'un pin a la position de l'écouteur
        # requete pour toutes les BAND, ou juste celle sélectionnée
        if band is None and mode is None:
            sql = "SELECT SUBSTR(gridsquare, 1, 4) AS gridsquare_prefix, COUNT(*) AS count FROM callsign WHERE gridsquare IS NOT NULL GROUP BY gridsquare_prefix;"
        else:
            sql = "SELECT SUBSTR(c.gridsquare, 1, 4) AS gridsquare_prefix, COUNT(*) AS count FROM qso AS q JOIN callsign AS c ON q.call = c.call WHERE c.gridsquare IS NOT NULL"
            if band is not None:
                sql += f" AND q.BAND = '{band}'"
            if mode is not None:
                sql += f" AND q.MODE = '{mode}'"
            sql += " GROUP BY gridsquare_prefix;"
        liste_all = connection.db.fetch_data(sql)
        for row in liste_all:
            pos_pin = position_pin(row[0]) # calcul de la position du pin a placer sur la carte
            folium.Marker([pos_pin[0], pos_pin[1]], tooltip=f" {row[1]} qso").add_to(m) # ajout du pin

        # Enregistrer la carte dans un objet mémoire
        map_data = io.BytesIO()
        m.save(map_data, close_file=False)
        return map_data.getvalue().decode('utf-8')

    def on_button_click(self, band=None, mode=None):
        # personnalisez la carte selon la bande, ou rechargez simplement la carte par défaut
        if band is None and mode is None:
            map_html = self.create_map()
        else:
            map_html = self.create_map(band,mode)
        self.web_view.setHtml(map_html)



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mapDialog = QtWidgets.QDialog()
    ui = Ui_mapDialog()
    ui.setupUi(mapDialog)
    mapDialog.show()
    sys.exit(app.exec_())
