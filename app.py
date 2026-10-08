# -*- coding: utf-8 -*-
"""
app.py - Serveur web Flask de ValidStart
========================================
Projet de fin d'annee - Licence 1 Big Data - DIT Dakar

Role de ce fichier :
  - Servir les pages web (formulaire + rapport)
  - Recevoir les donnees du formulaire et appeler le moteur de calcul
  - Persister chaque simulation dans une base SQLite
  - Declencher la generation des graphiques R (ggplot2)
  - Exposer les donnees en JSON pour les graphiques JavaScript

Lancement :  python app.py
Puis ouvrir :  http://127.0.0.1:5000
"""

import os
import csv
import json
import sqlite3
import subprocess

from flask import (
    Flask, render_template, request,
    jsonify, redirect, url_for
)

from calculs import calculer_viabilite, recommander_financeurs

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
CHARTS_DIR = os.path.join(BASE_DIR, "static", "charts")

# Chemin vers Rscript. Adaptez la version si necessaire.
# Sous Windows : "C:/Program Files/R/R-4.5.2/bin/Rscript.exe"
# Sous Linux/Mac : "Rscript" suffit s'il est dans le PATH.
RSCRIPT_PATH = os.environ.get(
    "RSCRIPT_PATH",
    "C:/Program Files/R/R-4.5.2/bin/Rscript.exe"
)


# ---------------------------------------------------------------------------
# Base de donnees
# ---------------------------------------------------------------------------
def get_db():
    """Ouvre une connexion SQLite avec acces aux colonnes par nom."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cree les tables et insere les financeurs reels si absentes."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS simulation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_creation TEXT DEFAULT (datetime('now','localtime')),
            nom_projet TEXT NOT NULL,
            secteur TEXT NOT NULL,
            ville TEXT DEFAULT 'Dakar',
            capital_disponible REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS resultats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id INTEGER,
            ca_mensuel REAL,
            marge_brute REAL,
            taux_marge REAL,
            resultat_net REAL,
            point_mort REAL,
            capital_necessaire REAL,
            manque_capital REAL,
            verdict TEXT,
            projection TEXT,
            FOREIGN KEY (simulation_id) REFERENCES simulation(id)
        );

        CREATE TABLE IF NOT EXISTS financeurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            type TEXT NOT NULL,
            montant_min REAL,
            montant_max REAL,
            conditions TEXT,
            lien TEXT
        );
        """
    )

    # Insertion des financeurs reels (idempotent : on vide puis on remplit)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM financeurs")
    if cur.fetchone()[0] == 0:
        financeurs = [
            ("DER/FJ", "Etat - jeunes & femmes", 100000, 50000000,
             "Moins de 40 ans, projet structure",
             "https://der.sn"),
            ("CTIC Dakar", "Incubateur tech", 0, 0,
             "Startup technologique innovante",
             "https://cticdakar.com"),
            ("Dakar Network Angels", "Business angels", 500000, 10000000,
             "Prototype ou preuve de concept existante",
             "https://dakarnetworkangels.com"),
            ("FONSIS", "Fonds souverain", 5000000, 500000000,
             "Secteur strategique, fort potentiel",
             "https://fonsis.org"),
            ("PSEJ", "Programme entrepreneuriat jeunes", 50000, 5000000,
             "Jeune porteur de projet, toutes regions",
             "https://psej.net"),
        ]
        cur.executemany(
            """INSERT INTO financeurs
               (nom, type, montant_min, montant_max, conditions, lien)
               VALUES (?, ?, ?, ?, ?, ?)""",
            financeurs,
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Generation des graphiques R
# ---------------------------------------------------------------------------
def generer_graphiques_r(projection):
    """
    Ecrit la projection dans un CSV puis appelle le script R.
    Renvoie True si les deux PNG ont bien ete produits, False sinon.
    """
    os.makedirs(CHARTS_DIR, exist_ok=True)
    csv_path = os.path.join(CHARTS_DIR, "projection.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["mois", "ca", "marge_nette"])
        writer.writeheader()
        writer.writerows(projection)

    script_r = os.path.join(BASE_DIR, "graphiques.R")
    try:
        result = subprocess.run(
            [RSCRIPT_PATH, script_r, csv_path, CHARTS_DIR],
            timeout=60, check=True, capture_output=True, text=True
        )
        print("[R] stdout:", result.stdout)
        if result.stderr:
            print("[R] stderr:", result.stderr)
        return True
    except FileNotFoundError:
        print("[R] Rscript introuvable. Verifiez RSCRIPT_PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print("[R] Erreur d'execution:", e.stderr)
        return False
    except Exception as e:
        print("[R] Erreur inattendue:", e)
        return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Page d'accueil : le formulaire de saisie."""
    return render_template("index.html")


@app.route("/calculer", methods=["POST"])
def calculer():
    """Traite le formulaire, calcule, persiste, et affiche le rapport."""
    try:
        # Lecture et conversion des champs
        nom_projet = request.form.get("nom_projet", "Projet sans nom")
        secteur = request.form.get("secteur", "autre")
        ville = request.form.get("ville", "Dakar")
        prix_unitaire = float(request.form.get("prix_unitaire", 0))
        quantite = int(request.form.get("quantite_mensuelle", 0))
        cout_variable = float(request.form.get("cout_variable", 0))
        couts_fixes = float(request.form.get("couts_fixes", 0))
        capital = float(request.form.get("capital_disponible", 0))
        stock_initial = float(request.form.get("stock_initial", 0) or 0)

        # Calcul
        resultats = calculer_viabilite(
            prix_unitaire=prix_unitaire,
            quantite_mensuelle=quantite,
            cout_variable_unitaire=cout_variable,
            couts_fixes_mensuels=couts_fixes,
            capital_disponible=capital,
            stock_initial=stock_initial,
        )

        if "erreur" in resultats:
            return render_template("index.html", erreur=resultats["erreur"])

        # Persistance
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO simulation
               (nom_projet, secteur, ville, capital_disponible)
               VALUES (?, ?, ?, ?)""",
            (nom_projet, secteur, ville, capital),
        )
        simulation_id = cur.lastrowid
        cur.execute(
            """INSERT INTO resultats
               (simulation_id, ca_mensuel, marge_brute, taux_marge,
                resultat_net, point_mort, capital_necessaire,
                manque_capital, verdict, projection)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                simulation_id,
                resultats["ca_mensuel"], resultats["marge_brute"],
                resultats["taux_marge"], resultats["resultat_net"],
                resultats["point_mort"], resultats["capital_necessaire"],
                resultats["manque_capital"], resultats["verdict"],
                json.dumps(resultats["projection_6mois"]),
            ),
        )
        conn.commit()

        # Financeurs adaptes
        financeurs = recommander_financeurs(
            resultats["capital_necessaire"], secteur, conn
        )
        conn.close()

        # Graphiques R (best-effort : l'app fonctionne meme si R echoue)
        graphiques_ok = generer_graphiques_r(resultats["projection_6mois"])

        return render_template(
            "rapport.html",
            nom_projet=nom_projet,
            secteur=secteur,
            ville=ville,
            resultats=resultats,
            financeurs=financeurs,
            graphiques_ok=graphiques_ok,
            # JSON injecte pour les graphiques JavaScript cote client
            donnees_json=json.dumps({
                "projection": resultats["projection_6mois"],
                "tresorerie": resultats["cumul_tresorerie"],
                "taux_marge": resultats["taux_marge"],
                "point_mort": resultats["point_mort"],
                "ca_mensuel": resultats["ca_mensuel"],
            }),
        )

    except (ValueError, TypeError) as e:
        return render_template(
            "index.html",
            erreur="Verifiez vos saisies : tous les champs chiffres "
                   "doivent contenir des nombres valides."
        )


@app.route("/historique")
def historique():
    """Affiche les dernieres simulations enregistrees."""
    conn = get_db()
    lignes = conn.execute(
        """SELECT s.nom_projet, s.secteur, s.ville, s.date_creation,
                  r.ca_mensuel, r.verdict
           FROM simulation s
           JOIN resultats r ON r.simulation_id = s.id
           ORDER BY s.id DESC
           LIMIT 20"""
    ).fetchall()
    conn.close()
    return render_template("historique.html", lignes=lignes)


@app.route("/api/stats")
def api_stats():
    """
    Petit endpoint JSON : repartition des verdicts sur l'ensemble
    des simulations. Utilise pour un graphique JS sur l'historique.
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT verdict, COUNT(*) as n FROM resultats GROUP BY verdict"
    ).fetchall()
    conn.close()
    return jsonify({r["verdict"]: r["n"] for r in rows})


# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("ValidStart demarre sur http://127.0.0.1:5000")
    app.run(debug=True)
