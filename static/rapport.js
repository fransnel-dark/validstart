/* =========================================================================
   ValidStart - rapport.js
   Animations et graphiques interactifs de la page de rapport.
   Utilise Chart.js (charge via CDN dans rapport.html).
     1. Compteurs animes sur les chiffres cles
     2. Deux jauges circulaires (taux de marge, couverture capital)
     3. Graphique principal a onglets (CA / marge / tresorerie)
   ========================================================================= */

(function () {
    "use strict";

    var DATA = window.VALIDSTART_DATA;
    var CAP = window.VALIDSTART_CAPITAL;

    var ENCRE = "#0E1A2B";
    var EMERAUDE = "#0FB57E";
    var EMERAUDE_CL = "#16d695";
    var ROUGE = "#E5484D";
    var AMBRE = "#F5A623";
    var GRIS = "#9AA6B4";
    var GRILLE = "#EDF1F5";

    function fcfa(v) { return Math.round(v).toLocaleString("fr-FR"); }

    // -- 1. Compteurs animes -----------------------------------------------
    function animerCompteurs() {
        document.querySelectorAll(".val-compteur").forEach(function (el) {
            var cible = parseFloat(el.dataset.val) || 0;
            var depart = 0;
            var duree = 1100;
            var t0 = null;
            var negatif = cible < 0;
            var abs = Math.abs(cible);

            function pas(ts) {
                if (!t0) t0 = ts;
                var p = Math.min((ts - t0) / duree, 1);
                // easing out-cubic
                var e = 1 - Math.pow(1 - p, 3);
                var courant = Math.round(abs * e);
                el.textContent = (negatif ? "-" : "") + fcfa(courant);
                if (p < 1) requestAnimationFrame(pas);
            }
            requestAnimationFrame(pas);
        });
    }

    // -- 2. Jauges circulaires ---------------------------------------------
    function jauge(canvasId, pourcent, couleur, libelle) {
        var ctx = document.getElementById(canvasId);
        if (!ctx) return;
        var p = Math.max(0, Math.min(pourcent, 100));

        new Chart(ctx, {
            type: "doughnut",
            data: {
                datasets: [{
                    data: [p, 100 - p],
                    backgroundColor: [couleur, GRILLE],
                    borderWidth: 0,
                    circumference: 360,
                    cutout: "78%"
                }]
            },
            options: {
                responsive: false,
                animation: { animateRotate: true, duration: 1200 },
                plugins: { tooltip: { enabled: false }, legend: { display: false } }
            },
            plugins: [{
                id: "centre",
                afterDraw: function (chart) {
                    var c = chart.ctx;
                    var x = chart.width / 2;
                    var y = chart.height / 2;
                    c.save();
                    c.textAlign = "center";
                    c.textBaseline = "middle";
                    c.fillStyle = ENCRE;
                    c.font = "700 30px Sora, sans-serif";
                    c.fillText(Math.round(p) + "%", x, y - 4);
                    c.fillStyle = GRIS;
                    c.font = "500 11px Outfit, sans-serif";
                    c.fillText(libelle, x, y + 20);
                    c.restore();
                }
            }]
        });
    }

    function initJauges() {
        // Jauge 1 : taux de marge (couleur selon seuils)
        var tm = CAP.taux_marge;
        var coulMarge = tm >= 30 ? EMERAUDE : tm >= 10 ? AMBRE : ROUGE;
        jauge("jauge-marge", tm, coulMarge, "marge");

        // Jauge 2 : couverture du capital (plafonnee a 100% pour l'affichage)
        var couverture = CAP.necessaire > 0
            ? (CAP.disponible / CAP.necessaire) * 100
            : 100;
        var coulCap = couverture >= 100 ? EMERAUDE : couverture >= 60 ? AMBRE : ROUGE;
        jauge("jauge-capital", couverture, coulCap, "couvert");
    }

    // -- 3. Graphique principal a onglets ----------------------------------
    var chartPrincipal = null;

    var VUES = {
        ca: {
            label: "Chiffre d'affaires (FCFA)",
            valeurs: DATA.projection.map(function (p) { return p.ca; }),
            couleur: EMERAUDE,
            type: "line"
        },
        marge: {
            label: "Marge nette (FCFA)",
            valeurs: DATA.projection.map(function (p) { return p.marge_nette; }),
            couleur: AMBRE,
            type: "bar"
        },
        treso: {
            label: "Tresorerie cumulee (FCFA)",
            valeurs: DATA.tresorerie.map(function (t) { return t.solde; }),
            couleur: ENCRE,
            type: "line"
        }
    };

    var LABELS = DATA.projection.map(function (p) { return "Mois " + p.mois; });

    function hexAlpha(hex, a) {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return "rgba(" + r + "," + g + "," + b + "," + a + ")";
    }

    function dessiner(vueKey) {
        var v = VUES[vueKey];
        var ctx = document.getElementById("chart-principal");
        if (chartPrincipal) chartPrincipal.destroy();

        // Couleur des barres selon le signe (pour la vue marge)
        var bgBar = v.valeurs.map(function (val) {
            return val >= 0 ? hexAlpha(EMERAUDE, .85) : hexAlpha(ROUGE, .85);
        });

        chartPrincipal = new Chart(ctx, {
            type: v.type,
            data: {
                labels: LABELS,
                datasets: [{
                    label: v.label,
                    data: v.valeurs,
                    borderColor: v.couleur,
                    backgroundColor: v.type === "bar" ? bgBar : hexAlpha(v.couleur, .12),
                    borderWidth: v.type === "bar" ? 0 : 3,
                    fill: v.type === "line",
                    tension: .4,
                    pointBackgroundColor: "#fff",
                    pointBorderColor: v.couleur,
                    pointBorderWidth: 2.5,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    borderRadius: v.type === "bar" ? 8 : 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 800, easing: "easeOutQuart" },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: ENCRE,
                        padding: 12,
                        titleFont: { family: "Sora", size: 13 },
                        bodyFont: { family: "Outfit", size: 13 },
                        callbacks: {
                            label: function (c) { return fcfa(c.parsed.y) + " FCFA"; }
                        }
                    }
                },
                scales: {
                    y: {
                        grid: { color: GRILLE },
                        ticks: {
                            color: GRIS,
                            font: { family: "Outfit", size: 11 },
                            callback: function (val) {
                                if (Math.abs(val) >= 1000)
                                    return (val / 1000) + "k";
                                return val;
                            }
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: GRIS, font: { family: "Outfit", size: 12 } }
                    }
                }
            }
        });
    }

    function initOnglets() {
        var onglets = document.querySelectorAll(".onglet");
        onglets.forEach(function (o) {
            o.addEventListener("click", function () {
                onglets.forEach(function (x) { x.classList.remove("actif"); });
                o.classList.add("actif");
                dessiner(o.dataset.vue);
            });
        });
    }

    // -- Lancement ----------------------------------------------------------
    document.addEventListener("DOMContentLoaded", function () {
        animerCompteurs();
        initJauges();
        dessiner("ca");
        initOnglets();
    });

})();
