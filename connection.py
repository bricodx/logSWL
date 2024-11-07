import sqlite3
import logging

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

class DatabaseManager:
    def __init__(self, db_name):
        """Initialise la connexion à la base de données."""
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        logging.debug(f"Connexion à {db_name} réussie.")

    def fetch_data(self, lecture_sql):
        """Récupère des données de la table."""
        try:
            self.cursor.execute(lecture_sql)
            rows = self.cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            logging.debug(f"Erreur lors de la récupération des données : {e}")
            return None

    def fetch_one_data(self, lecture_sql, data):
        """Récupère des données de la table."""
        try:
            if data == ("",):
                self.cursor.execute(lecture_sql)
            else:
                self.cursor.execute(lecture_sql, data)
            rows = self.cursor.fetchone()
            return rows
        except sqlite3.Error as e:
            logging.debug(f"Erreur lors de la récupération des données : {e}")
            return None

    def exec_data(self, exec_sql, data):
        """Insère des données dans la table."""
        try:
            self.cursor.execute(exec_sql, data)
            self.conn.commit()
            return True  # réussite
        except sqlite3.Error as e:
            return False  # echec


    def close(self):
        """Ferme la connexion à la base de données."""
        self.conn.close()
        logging.debug("Connexion fermée.")


db = DatabaseManager("base.db")