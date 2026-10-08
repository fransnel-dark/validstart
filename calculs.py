# -*- coding: utf-8 -*-
"""
calculs.py - Moteur de calcul financier de ValidStart
=====================================================
Projet de fin d'annee - Licence 1 Big Data - DIT Dakar

Ce module contient toute la logique financiere de l'application.
Il est volontairement separe de la couche web (app.py) pour respecter
le principe de separation des responsabilites : la logique metier ne
depend ni de Flask, ni de la base de donnees, ni de l'interface.

Auteurs : [Votre nom] & [Nom du binome]
"""

# Coefficients de montee en charge sur 6 mois.
# Hypothese : une nouvelle activite ne tourne pas a plein regime
# des le premier mois. La clientele se construit progressivement.
COEFFICIENTS_CROISSANCE = [0.50, 0.70, 0.85, 1.00, 1.10, 1.20]

# Nombre de mois de charges fixes que le capital doit pouvoir absorber
# avant que l'activite ne devienne autonome (regle de prudence courante).
MOIS_DE_TRESORERIE = 3


def _arrondir(valeur):
    """Arrondit a l'entier le plus proche. Les FCFA n'ont pas de centimes."""
    return int(round(valeur))


def calculer_viabilite(
    prix_unitaire,
    quantite_mensuelle,
    cout_variable_unitaire,
    couts_fixes_mensuels,
    capital_disponible,
    stock_initial=0,
):
    """
    Analyse complete de la viabilite financiere d'un projet.

    Tous les montants sont exprimes en FCFA, sauf quantite_mensuelle
    qui est un nombre d'unites.

    Parametres
    ----------
    prix_unitaire : float
        Prix de vente d'une unite au client final.
    quantite_mensuelle : int
        Nombre d'unites ecoulees par mois (estimation prudente).
    cout_variable_unitaire : float
        Cout d'acquisition / production d'une unite (achat + import + transport).
    couts_fixes_mensuels : float
        Charges qui tombent chaque mois quelle que soit l'activite
        (loyer, abonnements, salaires fixes...).
    capital_disponible : float
        Tresorerie dont dispose l'entrepreneur au lancement.
    stock_initial : float, optionnel
        Valeur du premier stock a constituer avant la premiere vente.

    Retourne
    --------
    dict
        Dictionnaire de tous les indicateurs calcules, du verdict et
        du message d'accompagnement. En cas d'entree invalide, renvoie
        un dictionnaire contenant la cle "erreur".
    """

    # --- Garde-fous sur les entrees ---------------------------------------
    if quantite_mensuelle <= 0:
        return {"erreur": "La quantite mensuelle doit etre superieure a zero."}

    # 1. Chiffre d'affaires mensuel (regime de croisiere)
    ca_mensuel = prix_unitaire * quantite_mensuelle

    if ca_mensuel <= 0:
        return {"erreur": "Le chiffre d'affaires ne peut pas etre nul."}

    # 2. Cout variable total mensuel
    cout_variable_total = cout_variable_unitaire * quantite_mensuelle

    # 3. Marge brute (ce qui reste apres les couts directs)
    marge_brute = ca_mensuel - cout_variable_total
    taux_marge = (marge_brute / ca_mensuel) * 100

    # 4. Resultat net mensuel (apres les charges fixes)
    resultat_net = marge_brute - couts_fixes_mensuels

    # 5. Point mort : chiffre d'affaires a atteindre pour couvrir
    #    les charges fixes. Si la marge est nulle ou negative, il n'existe pas.
    if marge_brute <= 0:
        point_mort = None
    else:
        taux_marge_ratio = marge_brute / ca_mensuel
        point_mort = couts_fixes_mensuels / taux_marge_ratio

    # 6. Capital necessaire : de quoi tenir MOIS_DE_TRESORERIE mois
    #    de charges fixes, plus la constitution du stock de depart.
    capital_necessaire = (couts_fixes_mensuels * MOIS_DE_TRESORERIE) + stock_initial
    manque_capital = max(0, capital_necessaire - capital_disponible)

    # 7. Projection sur 6 mois avec montee en charge progressive
    projection = []
    for index, coefficient in enumerate(COEFFICIENTS_CROISSANCE):
        ca_mois = ca_mensuel * coefficient
        cout_var_mois = cout_variable_total * coefficient
        marge_nette_mois = ca_mois - cout_var_mois - couts_fixes_mensuels
        projection.append({
            "mois": index + 1,
            "ca": _arrondir(ca_mois),
            "marge_nette": _arrondir(marge_nette_mois),
        })

    # 8. Cumul de tresorerie : on part du capital disponible et on suit
    #    son evolution mois par mois. Permet de detecter une rupture de
    #    tresorerie meme quand l'activite est rentable a terme.
    tresorerie = capital_disponible - stock_initial
    cumul_tresorerie = []
    tresorerie_min = tresorerie
    for point in projection:
        tresorerie += point["marge_nette"]
        tresorerie_min = min(tresorerie_min, tresorerie)
        cumul_tresorerie.append({
            "mois": point["mois"],
            "solde": _arrondir(tresorerie),
        })

    # 9. Verdict automatique - 5 cas distincts
    verdict, message = _determiner_verdict(
        marge_brute=marge_brute,
        resultat_net=resultat_net,
        capital_disponible=capital_disponible,
        capital_necessaire=capital_necessaire,
        tresorerie_min=tresorerie_min,
    )

    # 10. Assemblage du resultat final
    return {
        "ca_mensuel": _arrondir(ca_mensuel),
        "cout_variable_total": _arrondir(cout_variable_total),
        "marge_brute": _arrondir(marge_brute),
        "taux_marge": round(taux_marge, 1),
        "couts_fixes": _arrondir(couts_fixes_mensuels),
        "resultat_net": _arrondir(resultat_net),
        "point_mort": _arrondir(point_mort) if point_mort is not None else None,
        "capital_necessaire": _arrondir(capital_necessaire),
        "capital_disponible": _arrondir(capital_disponible),
        "manque_capital": _arrondir(manque_capital),
        "tresorerie_min": _arrondir(tresorerie_min),
        "projection_6mois": projection,
        "cumul_tresorerie": cumul_tresorerie,
        "verdict": verdict,
        "message": message,
    }


def _determiner_verdict(
    marge_brute,
    resultat_net,
    capital_disponible,
    capital_necessaire,
    tresorerie_min,
):
    """
    Determine le verdict de viabilite selon 5 cas mutuellement exclusifs.

    Logique, du plus grave au plus favorable :
      Cas 1 - Marge brute negative  -> NON VIABLE (modele casse)
      Cas 2 - Deficitaire + capital insuffisant -> RISQUE (double probleme)
      Cas 3 - Deficitaire mais capital suffisant -> RISQUE (a surveiller)
      Cas 4 - Rentable mais capital de demarrage insuffisant -> RISQUE
      Cas 5 - Rentable et capital suffisant -> VIABLE
    """
    # Cas 1 : le prix de vente ne couvre meme pas le cout d'achat
    if marge_brute <= 0:
        return "non_viable", (
            "Votre prix de vente ne couvre pas vos couts de production. "
            "Chaque vente vous fait perdre de l'argent. Il faut revoir le "
            "prix a la hausse ou negocier un cout d'achat plus bas."
        )

    # Cas 2 : activite deficitaire ET tresorerie insuffisante
    if resultat_net < 0 and capital_disponible < capital_necessaire:
        return "risque", (
            "Projet a haut risque : votre activite est deficitaire chaque "
            "mois et votre capital ne suffit pas a couvrir le demarrage. "
            "Un financement externe est indispensable avant de vous lancer."
        )

    # Cas 3 : deficitaire mais le capital peut absorber la periode creuse
    if resultat_net < 0:
        return "risque", (
            "Projet a surveiller : votre activite est deficitaire les "
            "premiers mois, mais votre capital peut absorber cette periode "
            "de demarrage. Visez le point mort rapidement."
        )

    # Cas 4 : rentable, mais pas assez de capital pour demarrer sereinement
    if capital_disponible < capital_necessaire or tresorerie_min < 0:
        manque = capital_necessaire - capital_disponible
        return "risque", (
            "Votre modele est rentable, mais votre capital de demarrage est "
            "juste : il manque environ {:,} FCFA pour lancer dans de bonnes "
            "conditions. Un petit financement securiserait le projet."
        ).format(_arrondir(max(0, manque)))

    # Cas 5 : tout est au vert
    return "viable", (
        "Projet viable ! Votre activite degage un benefice net et votre "
        "capital couvre le demarrage. Les indicateurs sont au vert pour "
        "vous lancer."
    )


def recommander_financeurs(capital_necessaire, secteur, db_connection):
    """
    Recommande les dispositifs de financement adaptes au besoin en capital.

    Interroge la table 'financeurs' de la base SQLite et renvoie ceux dont
    le plafond de financement couvre le besoin (ou les incubateurs, dont le
    montant est a 0 car ils apportent de l'accompagnement, pas du cash direct).

    Parametres
    ----------
    capital_necessaire : float
        Besoin en capital calcule pour le projet.
    secteur : str
        Secteur d'activite (reserve pour un filtrage futur plus fin).
    db_connection : sqlite3.Connection
        Connexion active a la base de donnees.

    Retourne
    --------
    list[dict]
        Liste des financeurs pertinents, classes par montant minimum croissant.
    """
    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT nom, type, montant_min, montant_max, conditions, lien
        FROM financeurs
        WHERE montant_max >= ? OR montant_max = 0
        ORDER BY montant_min ASC
        """,
        (capital_necessaire,),
    )

    financeurs = []
    for row in cursor.fetchall():
        financeurs.append({
            "nom": row[0],
            "type": row[1],
            "montant_min": row[2],
            "montant_max": row[3],
            "conditions": row[4],
            "lien": row[5],
        })
    return financeurs


# ---------------------------------------------------------------------------
# Bloc de test autonome : permet de verifier le moteur sans lancer le serveur.
# Lancer avec :  python calculs.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scenarios = {
        "NON VIABLE": dict(prix_unitaire=5000, quantite_mensuelle=20,
                           cout_variable_unitaire=8000, couts_fixes_mensuels=50000,
                           capital_disponible=200000),
        "RISQUE (capital insuffisant)": dict(prix_unitaire=25000, quantite_mensuelle=30,
                           cout_variable_unitaire=12000, couts_fixes_mensuels=80000,
                           capital_disponible=300000, stock_initial=120000),
        "RISQUE (deficitaire)": dict(prix_unitaire=15000, quantite_mensuelle=10,
                           cout_variable_unitaire=8000, couts_fixes_mensuels=100000,
                           capital_disponible=500000),
        "VIABLE": dict(prix_unitaire=30000, quantite_mensuelle=50,
                           cout_variable_unitaire=10000, couts_fixes_mensuels=80000,
                           capital_disponible=800000),
    }

    for nom, params in scenarios.items():
        res = calculer_viabilite(**params)
        print("=" * 55)
        print("SCENARIO ATTENDU :", nom)
        print("Verdict obtenu   :", res["verdict"].upper())
        print("CA mensuel       : {:,} FCFA".format(res["ca_mensuel"]))
        print("Resultat net     : {:,} FCFA".format(res["resultat_net"]))
        print("Tresorerie min   : {:,} FCFA".format(res["tresorerie_min"]))
        print("Message          :", res["message"])
    print("=" * 55)
