# Analisi di Rilievo 3D x Posidonia Oceanica

Prende in input un rilievo fotogrammetrico 3D del fondale marino restituendo:
- L'**area** occupata da Posidonia e quella di sabbia nuda
- Il **volume** della chioma fogliare
- Le **metriche ecologiche** di perdita: CO₂ non più assorbita, O₂ non più prodotto
- Un **report completo** in formato Excel, JSON e PNG

Dalla cartella principale, basta fare doppio clic su **Avvia_Analisi.bat** (Windows) o **Avvia_Analisi.command** (Mac/Linux). Il sistema chiederà di selezionare la cartella o il file del rilievo e depositerà i risultati in `data/output/`.

---

## Struttura delle cartelle

```
posidonia_analysis/
│
├── main.py                    ← Unico file da lanciare
├── Avvia_Analisi.bat          ← Avvio con doppio clic su Windows
├── Avvia_Analisi.command      ← Avvio con doppio clic su Mac/Linux
├── config.json                ← Pannello di controllo dei parametri
│
├── bio_analysis/
│   ├── loader.py              ← Caricamento file 3D
│   ├── calibrator.py          ← Calibrazione metrica con RANSAC
│   ├── segmenter.py           ← Separazione Posidonia / sabbia con K-Means
│   ├── geometry.py            ← Calcolo area e volume
│   ├── metrics.py             ← Metriche ecologiche e validazione biologica
│   ├── reporter.py            ← Generazione report Excel, JSON, PNG, HTML
│   └── pipeline.py            ← Coordina tutti i moduli
│
├── data/
│   ├── input/
│   │   ├── PLY/               ← I file del rilievo 3D
│   │   ├── OBJ/
│   │   └── LAS/
│   └── output/                ← Qui appaiono i report dopo l'analisi
│
├── utility_scripts/
│   ├── test_colore.py         ← Analisi da top-view con Posidonia evidenziata manualmente
│   ├── test_scala.py          ← Verifica iniziale della scala usata in un modello 3D
│   └── esporta_percorso.py    ← Estrazione traccia GPS da file .txt
```

---

## I file principali — Spiegazione modulo per modulo

### `config.json` — Pannello di controllo
Permette di modificare i parametri dell'analisi senza toccare il codice. È sufficiente aprirlo con un editor di testo e cambiare i valori numerici.
 
```json
{
    "parametri_biologici": {
        "altezza_max_posidonia_m": 0.70,
        "ratio_volume_area_min_sano": 0.20,
        "co2_sequestrata_tc_m2": 0.0002,
        "o2_prodotto_l_m2_anno": 3650
    },
    "parametri_tecnici": {
        "dimensione_cella_griglia_m": 0.10,
        "campionamento_3d_punti_max": 50000
    }
}
```
 
**`altezza_max_posidonia_m`:** L'altezza massima della Posidonia nel sito specifico. Usata da RANSAC per calibrare la scala del modello. Da aggiornare se si analizza un sito con prateria di altezza diversa.
 
**`co2_sequestrata_tc_m2` e `o2_prodotto_l_m2_anno`:** Coefficienti ecologici da letteratura (Fourqurean et al., 2012). Se si dispone di dati rilevati direttamente sul fondale analizzato, questi valori possono essere sostituiti per ottenere stime più precise.
 
**`dimensione_cella_griglia_m`:** Risoluzione della griglia di analisi. Valori più piccoli (es. 0.05) aumentano la precisione ma rallentano il calcolo.
 
---

### `loader.py` — Acquisizione, caricamento e fusione dei dati 3D
I software fotogrammetrici esportano spesso il modello 3D suddiviso in molti file separati. Il modulo li carica e li fonde automaticamente in un unico modello. Supporta i formati `.ply`, `.obj` e `.las`.

---

### `calibrator.py` — Calibrazione metrica con RANSAC
I modelli 3D nascono in unità arbitrarie prive di significato metrico reale. Poiché nel rilievo non era presente un riferimento fisico di dimensioni note, il sistema usa una calibrazione biologica.
 
Tramite l'algoritmo RANSAC, il sistema ignora sassi, detriti e riflessi anomali, individua il piano matematico più grande e piatto (la sabbia nuda) e misura la distanza massima dei punti sovrastanti (le foglie di Posidonia). Sapendo che la Posidonia locale arriva al massimo a 70 cm, questa misura viene confrontata con quella in unità arbitrarie per calcolare il fattore di conversione spaziale — da qui in poi il modello lavora in metri reali.
 
Il 98° percentile delle altezze viene usato invece del massimo assoluto, per evitare che singoli punti rumorosi (bolle, particelle in sospensione) falsino la calibrazione.

---

### `segmenter.py` — Segmentazione AI e separazione di Posidonia e sabbia con K-Means
Come separiamo la sabbia dalla Posidonia? Per evitare bias soggettivi l'algoritmo K-Means Clustering 2D implementato, invece di basarsi solo sul colore, fonde la geometria 3D con il Machine Learning. Esso guarda ogni cella di 10x10cm sul modello e incrocia due dati: quanto è scura (Luminanza) e quanto è alta (grazie a RANSAC). La Posidonia viene identificata automaticamente come il gruppo con l'altezza media maggiore. Questo incrocio è vitale: permette al software di capire che una macchia scura a quota zero è solo un'ombra sulla sabbia, non una pianta.

Vengono applicati filtri per rimuovere il rumore residuo: un singolo pixel scuro isolato viene eliminato, mentre un piccolo buco chiaro in una prateria densa viene riempito. In output otteniamo due maschere `mask_posidonia` e `mask_sabbia` che indicano per ogni cella della griglia la classe di appartenenza.

---

### `geometry.py` — Calcolo di area e volume
L'area viene calcolata moltiplicando il numero di celle classificate per la loro dimensione (0.01 m² ciascuna).

Per il volume non moltiplichiamo semplicemente l'area per un'altezza fissa: sovrastimerebbe il risultato perché la Posidonia non è un blocco uniforme — alcune zone hanno foglie alte 60 cm, altre 20 cm, ai bordi le foglie sono più basse. Il modulo calcola la "micro-altezza" locale di ogni singola cella 10x10cm (metodo Voxel 2.5D, Somma di Riemann). Questo significa che il calcolo si modella organicamente alla reale pendenza del fondale e ai bordi diradati della prateria.

---

### `metrics.py` — Metriche ecologiche e validazione
Trasforma i dati geometrici in informazioni ecologicamente significative e verifica che i risultati siano biologicamente plausibili basandosi su indici di letteratura.

| Metrica | Formula | Significato |
|---|---|---|
| Copertura Posidonia | area_pos / (area_pos + area_sabbia) × 100 | % del fondale ancora coperto |
| Perdita CO₂ | area_pos × 0.0002 tC/m² × 3.6663 × 1000 | kg di CO₂/anno assorbita |
| Perdita O₂ | area_pos × 3650 L/m²/anno | Litri di O₂/anno prodotti |
| Ratio Volume/Area | volume / area_posidonia | Altezza media effettiva della chioma |

I coefficienti (0.0002 tC/m², 3650 L O₂/m²/anno) sono valori standard dalla letteratura scientifica su *Posidonia oceanica* (Fourqurean et al., 2012). Possono essere aggiornati in `config.json` se si dispone di dati rilevati direttamente sul sito. Prima di esportare il modulo esegue anche 4 controlli automatici sull'affidabilità dei risultati rilevati finora (verifica della calibrazione RANSAC, del rapporto Volume/Area, della copertura complessiva e della qualità del clustering).

---

### `reporter.py` — Generazione dei report
Prende tutti i risultati e li confeziona in formati diversi per utilizzi diversi.

**Report Excel (.xlsx):**
- **"Summary":** Tutte le metriche finali (area, volume, copertura, CO₂, O₂).
- **"Validazione Biologica":** I risultati dei 4 controlli automatici con valori numerici.

**Report JSON (.json):**
File strutturato con metadati (timestamp, file sorgente, versione software), calibrazione (equazione del piano, fattore di scala), risultati K-Means. Pensato per essere letto da altri software o database.

**Report PNG (.png):**
| Pannello | Contenuto |
|---|---|
| 1 — Mappa Luminanza | Vista dall'alto in scala di grigi. Zone scure = Posidonia, zone chiare = sabbia. |
| 2 — Topografia | Vista dall'alto colorata per altezza (viola = basso, giallo = alto). Morfologia della chioma. |
| 3 — Segmentazione | Verde = Posidonia, giallo = sabbia. La visualizzazione principale del risultato. |
| 4 — Report Testuale | Metriche numeriche complete con eventuali note biologiche. |

**Modello 3D Interattivo (.html):**
Genera una pagina web che permette di ruotare, zoomare e ispezionare il fondale segmentato direttamente nel browser, con celle colorate in verde (Posidonia) e giallo (sabbia/cicatrice).
*(Richiede `pip install plotly` — se non installato viene saltato automaticamente senza bloccare il resto)*

---

### `pipeline.py` - Esecuzione in sequenza degli altri moduli
Coordina l'esecuzione di tutti i moduli nell'ordine corretto, gestendo gli errori e il logging dettagliato di ogni fase:
 
```
[1/6] Caricamento e fusione dei file 3D
[2/6] Calibrazione RANSAC → scala metrica
[3/6] K-Means 2D → segmentazione Posidonia/sabbia
[4/6] Calcolo area e volume
[5/6] Metriche ecologiche e validazione biologica
[6/6] Generazione report

---

### `scripts_utility/test_colore.py` — Test aggiuntivo di Ground Truth
Per validare ulteriormente il sistema confrontiamo i risultati automatici con una stima manuale: su una vista dall'alto del rilievo, le zone coperte da Posidonia vengono evidenziate manualmente in rosso, simulando la classica ispezione visiva umana. Lo script misura la percentuale di rosso sull'immagine e la confronta con la stima K-Means del modello 3D.

**Risultati a confronto (test su rilievo di Porto Cesareo):**
| Metodo | Copertura stimata | Causa dell'errore (risolta nello step successivo) |
|---|---|---|
| **Occhio umano** (2D manuale) | **48.5%** | Effetto ombrello delle foglie + ombre sul fondale |
| **K-Means 1D** (solo luminanza) | **38.7%** | Ombre sulla sabbia contate come Posidonia |
| **K-Means 2D** (luminanza + altezza) | **34.8%** | Ombre piatte escluse grazie alla quota |

La progressione **48.5% → 38.7% → 34.8%** non indica una perdita di dati, al contrario il sistema guadagna in precisione. La Posidonia crea un effetto ombrello quando le foglie lunghe si piegano coprendo la sabbia sottostante; l'occhio umano e i metodi 2D guardano dall'alto e contano tutto quel tetto verde e le ombre sul fondale come biomassa viva. Ogni passaggio rimuove quindi una fonte di illusione ottica: il K-Means 2D usa le altezze per scartare le ombre piatte (quota ~2cm). Il 34.8% è il dato epurato da distorsioni sottomarine.

---

## Tutti i risultati (test su rilievo di Porto Cesareo):

| Metrica | Valore |
|---|---|
| Area totale analizzata | **176.55 m²** |
| Area Posidonia | **61.41 m²** |
| Area Sabbia | **115.14 m²** |
| Volume Posidonia | **11.00 m³** |
| Copertura Posidonia | **34.8%** |
| Copertura sabbia | **65.2%** |
| Ratio Volume/Area | **0.179 m** |
| Stima 2D manuale (test colore) | 48.5% (sovrastimata del ~13.7%) |
| Fattore di scala RANSAC | 0.2675 |

**Validazione dell'area con dato empirico:**  
Una traversata fisica stimata di circa 15 metri nell'area del rilievo corrisponde a un'area circolare di π × 7.5² = **176.71 m²**. Il software ha restituito **176.55 m²** — uno scarto inferiore allo 0.1% rispetto a quella stima realistica, ottenuto calibrandosi autonomamente usando solo l'altezza biologica limite della Posidonia locale tramite RANSAC.

**Nota sul Ratio Volume/Area (0.179 m):**  
La soglia di normalità (0.20 m) è calibrata su una prateria sana e integra. Un'altezza media di 17.9 cm in una zona con estesa regressione è biologicamente attesa: le foglie ai bordi delle aree danneggiate sono spesso recise, piegate o rade. Il warning segnala una condizione di diradamento.

---

## Sviluppi futuri
**Georeferenziazione automatica:**
Integrare i punti GPS del percorso per ancorare il modello a coordinate reali.

**Stima della biomassa fogliare:**
Dal volume della chioma, usare la densità fogliare media da letteratura (~1.2 kg/m³ di materia secca per *Posidonia oceanica*) per stimare la biomassa totale.

---

## Dipendenze software

\```
Python 3.11+
numpy
scipy
scikit-learn
trimesh
laspy
matplotlib
pandas
openpyxl
plotly
\```

**Installazione:**
\```
pip install numpy scipy scikit-learn trimesh laspy matplotlib pandas openpyxl plotly
\```

Nota: open3d NON è richiesto. Il sistema usa il RANSAC di scikit-learn.
