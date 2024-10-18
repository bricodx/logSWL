from PyQt5 import QtCore, QtGui, QtWidgets
import connection
import requests
from bs4 import BeautifulSoup

def verif_callsign(qrz):
    url = f"https://www.qrzcq.com/call/{qrz}"
    sql = "SELECT call FROM callsign WHERE call = (?)"
    result = connection.db.fetch_one_data(sql,(qrz,))
    # Vérification de la présence de 'qrz'
    if not result:
        sql = "INSERT INTO callsign (call , nom, ITU, DXCC, CQZONE, prefixe, gridsquare) VALUES (?,?,?,?,?,?,?)"
        # Envoi de la requête GET pour récupérer le contenu de la page
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # on cherche le nom et prénom
        info = soup.find("p", class_="haminfoaddress")
        if info:
            nom_complet = info.find("b").get_text(strip=True)
            if nom_complet.endswith("(+)"):
                nom_complet_sans_plus = nom_complet[:-3]  # Supprime les 3 derniers caractères
            else:
                nom_complet_sans_plus = nom_complet  # Garde le nom intact
            # Parcours des tableaux pour trouver la section qui contient "Call data"
            call_data = {}
            tables = soup.find_all('table')
            for table in tables:
                # Vérifie si le tableau contient "Call data"
                if 'Call data' in table.get_text():
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            label = cols[0].get_text(strip=True).replace(":", "")
                            value = cols[1].get_text(strip=True)
                            call_data[label] = value
                    break  # Quitte la boucle une fois le tableau "Call data" trouvé
            # Récupérer les données spécifiques pour la mise à jour SQL
            itu_zone = call_data.get("ITU Zone")
            dxcc = call_data.get("DXCC Zone")
            cq_zone = call_data.get("CQ Zone")
            prefix = call_data.get("Main prefix")
            grid =  call_data.get("Locator")
            data = (qrz, nom_complet_sans_plus, itu_zone, dxcc, cq_zone, prefix, grid)
        else:
            data = (qrz,None,None,None,None,None,None) # si le call n'est pas déjà dans la base, on l'enregistre même si l'on ne trouve aucune info
        # execution de la requete préparée
        if connection.db.insert_data(sql, data):
            print("call enregistré")
        else:
            print("erreur bdd")
    else:
        print("call déjà présent dans la base")
