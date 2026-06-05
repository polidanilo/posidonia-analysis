# Analisi di rilievo x Posidonia Oceanica

Prende in input un rilievo fotogrammetrico 3D del fondale marino (una **nuvola di punti** o una **mesh**) restituendo:

- L'**area** occupata da Posidonia e quella di sabbia nuda
- Il **volume** della chioma fogliare
- Le **metriche ecologiche** di perdita: CO₂ non più assorbita, O₂ non più prodotto
- Un **report completo** in formato Excel, JSON e PNG

Dalla cartella principale, basta lanciare: python main.py
Il sistema prenderà i dati del rilievo in data/input/PLY/ e depositerà i risultati in data/output/.

---

## Struttura delle cartelle

```
posidonia_analysis/
│
├── main.py                    ← Unico file da lanciare
│
├── bio_analysis/
│   ├── loader.py              ← Caricamento file 3D
│   ├── calibrator.py          ← Calibrazione metrica con RANSAC
│   ├── segmenter.py           ← Separazione Posidonia / Sabbia con K-Means
│   ├── geometry.py            ← Calcolo area e volume
│   ├── metrics.py             ← Metriche ecologiche e validazione biologica
│   ├── reporter.py            ← Generazione report Excel, JSON, PNG
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
│   ├── test_colore.py         ← Analisi su top-view con zone distinte e colorate manualmente
│   ├── test_scala.py          ← Verifica iniziale della scala usata in un modello 3D
│   └── esporta_percorso.py    ← Estrazione traccia GPS da file .txt
```

---

## I file principali — Spiegazione modulo per modulo

### `loader.py` — Acquisizione, caricamento e fusione dei dati 3D.
I software fotogrammetrici esportano spesso il modello 3D suddiviso in molti file separati. Il modulo li carica e li fonde automaticamente in un unico modello. Supporta i formati ply, obj e las.

---

### `calibrator.py` — Calibrazione metrica con RANSAC
I modelli 3D nascono in unità arbitrarie. Poiché sul fondale non avevamo un riferimento metrico fisico, usiamo una calibrazione biologica. Tramite l'algoritmo RANSAC, il sistema ignora sassi detriti e riflessi anomali, individua il piano matematico più grande e piatto della sabbia e cerca i punti più alti (le foglie di Posidonia). Sapendo che la Posidonia locale arriva al massimo a 70 cm, questa misura viene confrontata con l'altezza massima in unità arbitrarie (che se nel modello è ad esempio 0.003 unità, permette di calcolare un fattore di conversione spaziale come `0.70 / 0.003 = 233.3`) -> tutti i punti vengono moltiplicati per questo fattore -> da qui in poi il modello può pensare in metri reali.

---

### `segmenter.py` — Segmentazione AI e separazione di Posidonia e sabbia con K-Means
Come separiamo la sabbia dalla pianta? Per evitare bias soggettivi l''algoritmo K-Means Clustering 2D implementato guarda ogni cella di 10x10cm e incrocia due dati: quanto è scura (Luminanza) e quanto è alta (grazie a RANSAC). La Posidonia viene identificata automaticamente come il gruppo con l'altezza media maggiore. Questo incrocio è vitale: permette al software di capire che una macchia scura a quota zero è solo un'ombra sulla sabbia, non una pianta.

Vengono applicati filtri per rimuovere il rumore residuo: un singolo pixel scuro isolato viene eliminato, mentre un piccolo buco chiaro in una prateria densa viene riempito. In output otteniamo due maschere `mask_posidonia` e `mask_sabbia` che indicano per ogni cella della griglia la classe di appartenenza.

---

### `geometry.py` — Calcolo di area e volume
Non moltiplichiamo semplicemente l'area per un'altezza fissa: sovrastimeremmo il volume, perché la Posidonia non è un blocco di cemento piatto — alcune zone hanno foglie alte 60 cm, altre 20 cm, ai bordi le foglie sono più basse. Il modulo calcola la "micro-altezza" locale di ogni singola cella 10x10cm (Somma di Riemann o Voxel 2.5D). Questo significa che il calcolo si modella organicamente sulla reale pendenza del fondale e sui bordi diradati della prateria.

---

### `metrics.py` — Metriche ecologiche e validazione
Trasforma i dati geometrici in informazioni ecologicamente significative e verifica che i risultati siano biologicamente plausibili basandosi su indici di letteratura.

| Metrica | Formula | Significato |
|---|---|---|
| Copertura Posidonia | area_pos / (area_pos + area_sabbia) × 100 | % del fondale ancora coperto |
| Perdita CO₂ | area_sabbia × 0.0002 tC/m² × 3.6663 × 1000 | kg di CO₂/anno non più assorbita |
| Perdita O₂ | area_sabbia × 3650 L/m²/anno | Litri di O₂/anno non più prodotti |
| Ratio Volume/Area | volume / area_posidonia | Altezza media effettiva della chioma |

I coefficienti (0.0002 tC/m², 3650 L O₂/m²/anno) sono valori standard dalla letteratura scientifica su *Posidonia oceanica*. Prima di esportare esegue anche 4 controlli sull'affidabilità dei dati biologici rilevati finora (ad esempio check su altezza massima, rapporto volume/area).

---

### `reporter.py` — Generazione dei report
Prende tutti i risultati e li confeziona in formati diversi per utilizzi diversi.

**Report Excel (.xlsx):**
- **Sheet "Summary":** Tabella con tutte le metriche finali (area, volume, copertura, CO₂, O₂).
- **Sheet "Grid Data":** Una riga per ogni cella 10×10 cm della griglia, con luminanza media, altezza e classificazione (Posidonia/Sabbia).
- **Sheet "Validation":** I risultati dei 4 controlli biologici con valori numerici.
- **Sheet "Cicatrice":** Focus sulle metriche della zona danneggiata (sabbia): area, CO₂ persa, O₂ perso, copertura residua.

**Report JSON (.json):**
File strutturato con metadati (timestamp, file sorgente, versione software), calibrazione (equazione del piano, fattore di scala), risultati K-Means. Pensato per essere letto da altri software o database.

**Report PNG (.png):**
| Pannello | Contenuto |
|---|---|
| 1 — Istogramma Luminanza | Distribuzione delle luminanze con i due centroidi K-Means e la soglia di separazione. Dimostra visivamente che i due gruppi sono separati. |
| 2 — Mappa Luminanza | Vista dall'alto del fondale in scala di grigi. Si vedono le zone scure (Posidonia) e chiare (sabbia). |
| 3 — Mappa Altezze | Vista dall'alto colorata per altezza: viola = basso, giallo = alto. Mostra la morfologia della chioma. |
| 4 — Mappa Segmentazione | Vista dall'alto con verde = Posidonia, rosso = sabbia. È la visualizzazione principale del risultato. |
| 5 — Report Testuale | Tutte le metriche numeriche in formato leggibile, con lista dei warning. |

**Modello 3D Interattivo (.html):**
Genera una pagina web che permette di ruotare, zoomare e ispezionare il fondale segmentato direttamente nel browser, con celle colorate in **verde** (Posidonia) e **oro** (sabbia/cicatrice).
*(Richiede `pip install plotly` — se non installato viene saltato automaticamente senza bloccare il resto)*

---

### `pipeline.py` - Esecuzione in sequenza degli altri moduli
Coordina l'esecuzione di tutti i moduli nell'ordine corretto, gestendo gli errori e il logging.

---

### `scripts_utility/test_colore.py` — Test aggiuntivo di Ground Truth
Per validare ulteriormente il sistema confrontiamo i risultati del software con quelli stimati analizzando una top-view del rilievo su cui le zone coperte da Posidonia sono state evidenziate in rosso manualmente, per simulare la classica ispezione visiva umana. Lo script misura la percentuale di rosso sull'immagine e la confronta con la stima K-Means del modello 3D.

**Risultati sulla copertura a confronto (rilievo di Porto Cesareo):**
| Metodo | Copertura stimata | Causa dell'errore (risolta nello step successivo) |
|---|---|---|
| **Occhio umano** (2D manuale) | **48.5%** | Effetto ombrello delle foglie sovrastanti + Ombre |
| **K-Means 1D** (solo luminanza) | **38.7%** | Ombre sulla sabbia contate come Posidonia |
| **K-Means 2D** (luminanza + altezza) | **34.8%** | Ombre piatte escluse grazie alla quota |

La progressione **48.5% → 38.7% → 34.8%** non indica che il sistema perde dati, al contrario esso guadagna in precisione. La Posidonia crea un effetto ombrello quando le foglie lunghe si piegano coprendo la sabbia sottostante; l'occhio umano e i metodi 2D guardano dall'alto e contano tutto quel tetto verde e le ombre sul fondale come biomassa viva. Ogni passaggio rimuove quindi una fonte di illusione ottica: il K-Means 2D usa le altezze per "guardare sotto" le foglie e scartare le ombre piatte (quota ~2cm). Il 34.8% è il dato epurato da distorsioni sottomarine.

---

## Tutti i risultati (rilievo di Porto Cesareo):

| Metrica | Valore |
|---|---|
| Area totale analizzata | **176.55 m²** |
| Area Posidonia | **61.41 m²** |
| Area Sabbia | **115.14 m²** |
| Volume Posidonia | **11.00 m³** |
| Copertura Posidonia | **34.8%** |
| Copertura sabbia | **65.2%** |
| Silhouette Score K-Means 2D | **0.5298** (buono, clustering affidabile) |
| Ratio Volume/Area | **0.179 m** ⚠️ segnala sofferenza/diradamento |
| Stima 2D manuale (test colore) | 48.5% (sovrastimata del ~13.7%) |
| Fattore di scala RANSAC | 0.2675 |

**Validazione dell'area con dato empirico:**  
Stimiamo che l'area del rilievo abbia avuto una traversata massima di circa 15 metri: un rilievo circolare con 15 metri di diametro corrisponde a un'area di π × 7.5² = **176.71 m²**. Il software ha restituito **176.55 m²** — uno scarto inferiore allo 0.1% rispetto a quella stima realistica, ottenuto calibrandosi autonomamente usando solo l'altezza biologica limite della Posidonia tramite RANSAC.

**Sul warning Ratio Volume/Area (0.179 m):**  
La soglia di normalità è impostata a 0.2 m pensando a una prateria sana. Questo rilievo analizza una zona di cicatrice da ancoraggio: è biologicamente atteso che le foglie ai bordi dello strappo siano recise, piegate o meno dense. Un'altezza media di 17.9 cm in una zona danneggiata evidenzia lo stato di sofferenza delle piante superstiti ai margini del cratere.

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
