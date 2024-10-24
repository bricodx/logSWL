import sqlite3
import logging

# Configuration du logger
logging.basicConfig(level=logging.INFO)  # Changez en logging.INFO ou  logging.DEBUG

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