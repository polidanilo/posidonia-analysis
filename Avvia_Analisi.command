#!/bin/bash

# =====================================================================
# ISTRUZIONI PER UTENTI MAC/LINUX (da fare solo la primissima volta)
# =====================================================================
# Se facendo doppio clic questo file non si avvia in automatico,
# significa che non ha ancora i permessi di esecuzione.
# Per sbloccarlo per sempre, segui questi 4 step:
#
# 1. Apri l'app "Terminale"
# 2. Scrivi: chmod +x  (IMPORTANTE: lascia uno spazio dopo la x!)
# 3. Trascina l'icona di questo file dentro la finestra del Terminale 
#    (così scriverà il percorso da solo)
# 4. Premi Invio
#
# Fatto! Da ora in poi ti basterà fare un normale doppio clic su 
# questo file per avviare il software.
# =====================================================================

echo "========================================="
echo "Avvio Posidonia Analysis in corso..."
echo "========================================="

# Naviga nella cartella dove si trova questo script
cd "$(dirname "$0")"

# Attiva l'ambiente virtuale (Nota: su Mac/Linux il percorso è diverso da Windows)
source .venv/bin/activate

# Lancia il programma
python3 main.py

echo "Premi Invio per chiudere questa finestra..."
read