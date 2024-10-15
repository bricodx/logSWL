import folium
import io
import connection

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView

def GetLon(ONE, THREE, FIVE):
    StrStartLon = ''
    StrEndLon = ''

    Field = ((ord(ONE.lower()) - 97) * 20)
    Square = int(THREE) * 2
    SubSquareLow = (ord(FIVE.lower()) - 97) * (2 / 24)
    SubSquareHigh = SubSquareLow + (2 / 24)

    StrStartLon = str(Field + Square + SubSquareLow - 180)
    StrEndLon = str(Field + Square + SubSquareHigh - 180)

    return StrStartLon, StrEndLon


def GetLat(TWO, FOUR, SIX):
    StrStartLat = ''
    StrEndLat = ''

    Field = ((ord(TWO.lower()) - 97) * 10)
    Square = int(FOUR)
    SubSquareLow = (ord(SIX.lower()) - 97) * (1 / 24)
    SubSquareHigh = SubSquareLow + (1 / 24)

    StrStartLat = str(Field + Square + SubSquareLow - 90)
    StrEndLat = str(Field + Square + SubSquareHigh - 90)

    return StrStartLat, StrEndLat


def create_map():
    zoom_level = 2
    # Créer une carte centrée
    m = folium.Map(location=[51.509865, -0.118092], zoom_start=zoom_level, tiles='OpenStreetMap')

    sql = "SELECT SUBSTR(gridsquare, 1, 4) AS gridsquare_prefix, COUNT(*) AS count FROM callsign WHERE gridsquare IS NOT NULL GROUP BY gridsquare_prefix ORDER BY count DESC;"
    liste_all = connection.db.fetch_data(sql)
    for row in liste_all:
        gridsquare = row[0]
        # Extraire les champs et carrés
        lon_field = gridsquare[0].upper()
        lat_field = gridsquare[1].upper()
        lon_square = gridsquare[2]
        lat_square = gridsquare[3]

        # Conversion des champs en degrés
        lon = (ord(lon_field) - ord('A')) * 20 - 180
        lat = (ord(lat_field) - ord('A')) * 10 - 90

        # Conversion des carrés en degrés
        lon += int(lon_square) * 2
        lat += int(lat_square)

        # Calculer le centre du carré
        center_lon = lon + 1  # Ajouter 1 pour obtenir le centre en longitude (2/2)
        center_lat = lat + 0.5  # Ajouter 0.5 pour obtenir le centre en latitude (1/2)

        folium.Marker([center_lat, center_lon], tooltip=f"{row[1]} qso").add_to(m)

    # Enregistrer la carte dans un objet mémoire
    map_data = io.BytesIO()
    m.save(map_data, close_file=False)

    return map_data.getvalue().decode('utf-8')

class Ui_mapDialog(object):
    def setupUi(self, mapDialog):
        mapDialog.setObjectName("mapDialog")
        mapDialog.resize(1100, 720)
        self.verticalLayoutWidget = QtWidgets.QWidget(mapDialog)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(0, 0, 1100, 720))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.layout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setObjectName("layout")
        # Créer le composant QWebEngineView
        self.web_view = QWebEngineView()

        # Charger la carte directement en HTML
        map_html = create_map()
        self.web_view.setHtml(map_html)

        # Ajouter le composant au layout
        self.layout.addWidget(self.web_view)

        self.retranslateUi(mapDialog)
        QtCore.QMetaObject.connectSlotsByName(mapDialog)

    def retranslateUi(self, mapDialog):
        _translate = QtCore.QCoreApplication.translate
        mapDialog.setWindowTitle(_translate("mapDialog", "Map des QSO"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mapDialog = QtWidgets.QDialog()
    ui = Ui_mapDialog()
    ui.setupUi(mapDialog)
    mapDialog.show()
    sys.exit(app.exec_())
