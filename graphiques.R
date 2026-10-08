# -*- coding: utf-8 -*-
# ===========================================================================
# graphiques.R - Generation des visualisations ValidStart avec ggplot2
# ===========================================================================
# Projet de fin d'annee - Licence 1 Big Data - DIT Dakar
#
# Ce script est appele par app.py via subprocess. Il recoit deux arguments :
#   1. le chemin du fichier CSV contenant la projection
#   2. le dossier de sortie pour les images PNG
#
# Il produit trois graphiques :
#   - graphique_ca.png      : evolution du chiffre d'affaires
#   - graphique_marge.png   : marge nette mensuelle (barres)
#   - graphique_treso.png   : tresorerie cumulee
# ===========================================================================

# Installation silencieuse de ggplot2 si absent
if (!requireNamespace("ggplot2", quietly = TRUE)) {
  install.packages("ggplot2", repos = "https://cran.r-project.org")
}
suppressMessages(library(ggplot2))

# --- Lecture des arguments -------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
csv_path   <- args[1]
output_dir <- args[2]

donnees <- read.csv(csv_path, stringsAsFactors = FALSE)

# --- Palette de couleurs (coherente avec l'interface web) ------------------
VERT     <- "#0FB57E"
VERT_CLR <- "#7BE0B8"
ROUGE    <- "#E5484D"
ENCRE    <- "#0E1A2B"
GRIS     <- "#8B94A3"
GRILLE   <- "#EDF1F5"

# Theme commun a tous les graphiques pour un rendu homogene et soigne
theme_validstart <- theme_minimal(base_size = 13) +
  theme(
    plot.title    = element_text(face = "bold", size = 16, color = ENCRE,
                                 margin = margin(b = 2)),
    plot.subtitle = element_text(size = 10.5, color = GRIS,
                                 margin = margin(b = 14)),
    axis.title.y  = element_text(size = 10, color = GRIS,
                                 margin = margin(r = 8)),
    axis.text     = element_text(color = GRIS, size = 9.5),
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(color = GRILLE, linewidth = 0.5),
    plot.background  = element_rect(fill = "white", color = NA),
    plot.margin      = margin(22, 26, 18, 22)
  )

format_fcfa <- function(x) paste0(format(x, big.mark = " "), " F")

# ===========================================================================
# GRAPHIQUE 1 - Evolution du chiffre d'affaires
# ===========================================================================
g1 <- ggplot(donnees, aes(x = mois, y = ca)) +
  geom_area(fill = VERT, alpha = 0.12) +
  geom_line(color = VERT, linewidth = 1.6, lineend = "round") +
  geom_point(color = VERT, fill = "white", size = 4.2,
             shape = 21, stroke = 2) +
  geom_text(aes(label = format(ca, big.mark = " ")),
            vjust = -1.4, size = 3.2, color = ENCRE, fontface = "bold") +
  scale_x_continuous(breaks = 1:6, labels = paste("M", 1:6)) +
  scale_y_continuous(labels = format_fcfa,
                     expand = expansion(mult = c(0.05, 0.18))) +
  labs(title = "Evolution du chiffre d'affaires",
       subtitle = "Projection sur 6 mois avec montee en charge progressive",
       x = NULL, y = "CA mensuel") +
  theme_validstart

ggsave(file.path(output_dir, "graphique_ca.png"),
       g1, width = 8.2, height = 4.4, dpi = 150)
cat("OK graphique_ca.png\n")

# ===========================================================================
# GRAPHIQUE 2 - Marge nette mensuelle (barres colorees selon le signe)
# ===========================================================================
donnees$signe <- ifelse(donnees$marge_nette >= 0, "positif", "negatif")

g2 <- ggplot(donnees, aes(x = mois, y = marge_nette, fill = signe)) +
  geom_col(width = 0.62) +
  geom_hline(yintercept = 0, color = ENCRE, linewidth = 0.7) +
  geom_text(aes(label = format(marge_nette, big.mark = " "),
                vjust = ifelse(marge_nette >= 0, -0.6, 1.5)),
            size = 3.1, fontface = "bold", color = ENCRE) +
  scale_fill_manual(values = c("positif" = VERT, "negatif" = ROUGE)) +
  scale_x_continuous(breaks = 1:6, labels = paste("M", 1:6)) +
  scale_y_continuous(labels = format_fcfa,
                     expand = expansion(mult = c(0.15, 0.15))) +
  labs(title = "Marge nette mensuelle",
       subtitle = "Benefice apres deduction de toutes les charges",
       x = NULL, y = "Marge nette") +
  theme_validstart +
  theme(legend.position = "none")

ggsave(file.path(output_dir, "graphique_marge.png"),
       g2, width = 8.2, height = 4.4, dpi = 150)
cat("OK graphique_marge.png\n")

# ===========================================================================
# GRAPHIQUE 3 - Tresorerie cumulee (le solde du compte mois apres mois)
# ===========================================================================
# Reconstruit le cumul a partir de la marge nette (meme logique que Python)
donnees$cumul <- cumsum(donnees$marge_nette)
donnees$zone  <- ifelse(donnees$cumul >= 0, "positif", "negatif")

g3 <- ggplot(donnees, aes(x = mois, y = cumul)) +
  geom_hline(yintercept = 0, color = ROUGE, linewidth = 0.6,
             linetype = "dashed") +
  geom_line(color = ENCRE, linewidth = 1.4, lineend = "round") +
  geom_point(aes(color = zone), size = 4, shape = 19) +
  geom_text(aes(label = format(cumul, big.mark = " ")),
            vjust = -1.3, size = 3, color = ENCRE, fontface = "bold") +
  scale_color_manual(values = c("positif" = VERT, "negatif" = ROUGE)) +
  scale_x_continuous(breaks = 1:6, labels = paste("M", 1:6),
                     expand = expansion(mult = c(0.04, 0.10))) +
  scale_y_continuous(labels = format_fcfa,
                     expand = expansion(mult = c(0.12, 0.18))) +
  labs(title = "Tresorerie cumulee",
       subtitle = "Evolution du solde disponible au fil des mois",
       x = NULL, y = "Solde cumule") +
  theme_validstart +
  theme(legend.position = "none")

ggsave(file.path(output_dir, "graphique_treso.png"),
       g3, width = 8.2, height = 4.4, dpi = 150)
cat("OK graphique_treso.png\n")

cat("Tous les graphiques ont ete generes.\n")
