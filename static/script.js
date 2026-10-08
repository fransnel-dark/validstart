/* =========================================================================
   ValidStart - script.js
   Interactions cote client :
     1. Apercu financier en temps reel pendant la saisie
     2. Validation avant envoi (prix < cout, quantite nulle)
     3. Indicateur de chargement sur le bouton
   Aucune dependance externe : JavaScript pur.
   ========================================================================= */

(function () {
    "use strict";

    // -- Utilitaires --------------------------------------------------------
    function fcfa(valeur) {
        return Math.round(valeur).toLocaleString("fr-FR") + " F";
    }
    function lire(id) {
        var el = document.getElementById(id);
        return el ? parseFloat(el.value) || 0 : 0;
    }

    // -- 1. Apercu temps reel ----------------------------------------------
    var champsSurveilles = [
        "prix_unitaire", "quantite_mensuelle",
        "cout_variable", "couts_fixes"
    ];

    function majApercu() {
        var prix     = lire("prix_unitaire");
        var quantite = lire("quantite_mensuelle");
        var cout     = lire("cout_variable");
        var fixes    = lire("couts_fixes");

        var ca         = prix * quantite;
        var margeBrute = ca - (cout * quantite);
        var taux       = ca > 0 ? (margeBrute / ca) * 100 : 0;
        var net        = margeBrute - fixes;

        var apercu = document.getElementById("apercu");
        if (ca <= 0) { apercu.hidden = true; return; }
        apercu.hidden = false;

        document.getElementById("ap-ca").textContent    = fcfa(ca);
        document.getElementById("ap-marge").textContent = fcfa(margeBrute);
        document.getElementById("ap-taux").textContent  = taux.toFixed(1) + " %";
        document.getElementById("ap-net").textContent   = fcfa(net);

        // Couleurs selon les valeurs
        colorier("ap-marge", margeBrute >= 0);
        colorier("ap-net", net >= 0);
        var tauxEl = document.getElementById("ap-taux");
        tauxEl.style.color = taux >= 30 ? "#16d695"
                           : taux >= 10 ? "#F5A623" : "#E5484D";
    }

    function colorier(id, positif) {
        document.getElementById(id).style.color =
            positif ? "#16d695" : "#E5484D";
    }

    champsSurveilles.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener("input", majApercu);
    });

    // -- 2 & 3. Validation + chargement ------------------------------------
    var form = document.getElementById("form-validstart");
    if (form) {
        form.addEventListener("submit", function (e) {
            var prix     = lire("prix_unitaire");
            var cout     = lire("cout_variable");
            var quantite = lire("quantite_mensuelle");

            if (quantite <= 0) {
                e.preventDefault();
                toast("La quantite vendue par mois doit etre superieure a 0.");
                return;
            }
            if (prix <= cout) {
                e.preventDefault();
                toast("Ton prix de vente (" + fcfa(prix) + ") est inferieur ou " +
                      "egal a ton cout d'achat (" + fcfa(cout) + "). " +
                      "La marge serait negative.");
                return;
            }

            // Tout est bon : etat de chargement
            var btn = document.getElementById("btn-go");
            btn.classList.add("loading");
            btn.querySelector(".btn-txt").textContent = "Analyse en cours";
            btn.querySelector(".btn-arrow").textContent = "\u27F3";
        });
    }

    // -- Toast d'alerte -----------------------------------------------------
    function toast(message) {
        var ancien = document.querySelector(".toast");
        if (ancien) ancien.remove();

        var el = document.createElement("div");
        el.className = "toast";
        el.innerHTML = "<span>" + message + "</span>";

        var fermer = document.createElement("button");
        fermer.textContent = "\u2715";
        fermer.onclick = function () { el.remove(); };
        el.appendChild(fermer);

        document.body.appendChild(el);
        requestAnimationFrame(function () { el.classList.add("show"); });
        setTimeout(function () {
            el.classList.remove("show");
            setTimeout(function () { el.remove(); }, 300);
        }, 5000);
    }

})();
