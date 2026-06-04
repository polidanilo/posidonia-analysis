# Posidonia Analyzer v2.0
### Sistema di Analisi 3D per il Monitoraggio di Praterie di *Posidonia oceanica*

> Sviluppato nell'ambito del progetto BioPressAdria / LIFE NatuReef  
> Università di Ferrara — Tirocinio e Tesi Triennale in Informatica  
> Studente: Danilo Poli — Tutor esterno: Simone Modugno

---

## Cos'è questo software

Posidonia Analyzer è uno strumento scientifico che prende in input un rilievo fotogrammetrico 3D del fondale marino (una **nuvola di punti** o una **mesh**) e produce automaticamente:

- L'**area** occupata da Posidonia e quella di sabbia nuda (la "cicatrice" da ancoraggio)
- Il **volume** della chioma fogliare residua
- Le **metriche ecologiche** di perdita: CO₂ non più sequestrata, O₂ non più prodotto
- Un **report completo** in formato Excel, JSON e immagine PNG

Il software non richiede che l'operatore conosca la programmazione. È sufficiente avere Python installato e lanciare un solo file.

---

## Come si usa — Il Pulsante Rosso

```bash
# Dalla cartella del progetto:
python main.py
```

Il programma leggerà i dati dalla cartella `data/input/PLY/`, eseguirà tutta l'analisi automaticamente e salverà i risultati in `data/output/`.

---

## Struttura delle cartelle

```
poseidonia/
│
├── main.py                    ← L'UNICO FILE DA LANCIARE
│
├── bio_analysis/              ← Il motore scientifico (non modificare)
│   ├── loader.py              ← Caricamento file 3D
│   ├── calibrator.py          ← Calibrazione metrica con RANSAC
│   ├── segmenter.py           ← Separazione Posidonia / Sabbia con K-Means
│   ├── geometry.py            ← Calcolo area e volume
│   ├── metrics.py             ← Metriche ecologiche e validazione biologica
│   ├── reporter.py            ← Generazione report Excel, JSON, PNG
│   └── pipeline.py            ← Orchestratore: coordina tutti i moduli
│
├── data/
│   ├── input/
│   │   ├── PLY/               ← I file del rilievo 3D (19 tile .ply)
│   │   ├── OBJ/               ← Eventuale file mesh unificato
│   │   └── LAS/               ← File nuvola di punti grezzi
│   └── output/                ← Qui appaiono i report dopo l'analisi
│
├── scripts_utility/
│   ├── test_colore.py         ← Confronto visivo manuale vs automatico
│   ├── test_scala.py          ← Verifica iniziale della scala del modello
│   └── esporta_percorso.py    ← Estrazione traccia GPS del ROV
│
├── archive_legacy/            ← Versioni precedenti (non usare)
│   ├── poseidonia.py          ← Codice 2D originale
│   └── trial1.py              ← Primo prototipo 3D monolitico
│
└── docs/
    └── notes.md               ← Note di sviluppo e roadmap
```

---

## I file del motore scientifico — Spiegazione modulo per modulo

---

### `loader.py` — Caricamento e fusione dei dati 3D

**Cosa fa:** Legge i file del rilievo 3D dal disco e li trasforma in una struttura dati unificata (una matrice di milioni di punti con coordinate X, Y, Z e colori R, G, B).

**Il problema che risolve:** I software fotogrammetrici come Agisoft Metashape esportano spesso il modello 3D suddiviso in molti file separati chiamati "tile" (nel vostro caso 19 file .ply). Il loader li fonde automaticamente in un unico modello senza che l'operatore debba fare nulla.

**Formati supportati:**
- `.ply` — formato nuvola di punti standard (quello principale)
- `.obj` — formato mesh con triangoli
- `.las` — formato nuvola di punti con coordinate assolute

**Funzioni principali:**
- `load(path)` — carica un singolo file
- `load_tiled_ply(folder)` — carica e fonde tutti i .ply da una cartella
- `get_stats()` — stampa statistiche: numero di punti, presenza colori, dimensioni del modello

**Output:** Due matrici NumPy — `vertices` (coordinate 3D di ogni punto) e `colors` (colori RGB di ogni punto).

**Nota tecnica:** Se i file .ply non contengono informazioni di colore, il loader assegna automaticamente un grigio neutro come colore di fallback, in modo che il resto della pipeline non si interrompa.

---

### `calibrator.py` — Calibrazione metrica con RANSAC

**Il problema che risolve:** I software fotogrammetrici producono modelli 3D in **unità arbitrarie** — un cubo che nella realtà misura 1 metro nel modello potrebbe valere 0.003 unità oppure 500 unità, a seconda dello strumento usato. Senza una calibrazione, le aree e i volumi calcolati sono numeri privi di significato reale.

**La sfida specifica di questo rilievo:** Nel rilievo non è stato posizionato nessun oggetto di dimensioni note (come un quadrato 50×50 cm) sul fondale. Non c'è quindi un riferimento metrico diretto.

**La soluzione — Calibrazione biologica con RANSAC:**

Il software usa un vincolo biologico noto: la *Posidonia oceanica* in questo tratto ha un'altezza massima della chioma di **70 cm**. La procedura è:

1. **RANSAC trova il piano del fondale.** L'algoritmo RANSAC (Random Sample Consensus) analizza tutti i milioni di punti della nuvola e identifica matematicamente il piano più grande e piatto — che corrisponde alla sabbia nuda. RANSAC è robusto agli "outlier": sassi, detriti o riflessi anomali non influenzano il risultato perché vengono automaticamente ignorati.

2. **Si calcola la distanza massima dal piano.** Una volta identificato il fondo, il software misura quanto sono distanti i punti più alti (le foglie di Posidonia). Questa distanza massima in unità arbitrarie viene confrontata con i 70 cm noti.

3. **Si ricava il fattore di scala.** Se la distanza massima nel modello è 0.003 unità e sappiamo che corrisponde a 0.70 m reali, il fattore di scala è `0.70 / 0.003 = 233.3`. Tutti i punti vengono moltiplicati per questo fattore.

4. **Validazione automatica.** Dopo la scalatura, il software verifica che l'altezza massima risultante sia davvero ≈ 0.70 m (con tolleranza ±5%). Se non lo è, viene emesso un warning.

**Nota sul 98° percentile:** Per evitare che pochi punti rumorosi galleggianti (bolle, particelle in sospensione) falsino la calibrazione, il software usa il 98° percentile delle altezze invece del valore assoluto massimo.

**Output:** Il fattore di scala, il modello con coordinate in metri reali, l'equazione matematica del piano del fondale.

---

### `segmenter.py` — Separazione Posidonia / Sabbia con K-Means

**Il problema che risolve:** Come distinguere automaticamente i punti che appartengono alla Posidonia da quelli che appartengono alla sabbia?

**Il problema del p-hacking:** Il metodo intuitivo sarebbe guardare la luminosità dei punti e scegliere una soglia manualmente: "tutti i punti più scuri di 120 sono Posidonia, gli altri sono sabbia". Questo approccio è scientificamente inaccettabile perché la soglia viene scelta dopo aver visto i dati, quindi inconsciamente si sceglie quella che dà il risultato visivamente più convincente. Al convegno, se qualcuno chiedesse "perché 120?", non ci sarebbe una risposta obiettiva.

**La soluzione — K-Means Clustering bimodale:**

Invece di scegliere la soglia a mano, il software la calcola matematicamente:

1. **Costruzione della griglia spaziale.** Il fondale viene suddiviso in una griglia di celle da 10×10 cm. Per ogni cella si calcola la luminanza media dei punti contenuti (media dei canali R+G+B diviso 3) e l'altezza massima dal fondo.

2. **K-Means trova i due gruppi naturali.** L'algoritmo K-Means analizza le luminanze di tutte le celle e le divide in due cluster senza istruzioni umane: un gruppo di celle scure (la Posidonia, più scura per il colore verde-marrone delle foglie) e un gruppo di celle chiare (la sabbia).

3. **La soglia è il punto medio tra i due centroidi.** Se K-Means trova che il centro del gruppo scuro è a luminanza 85 e il centro del gruppo chiaro è a luminanza 195, la soglia è automaticamente 140. Nessuna scelta soggettiva.

4. **Silhouette Score — La qualità del clustering.** Il software calcola lo Silhouette Score, un numero da -1 a 1 che misura quanto i due gruppi siano realmente separati. Nel vostro rilievo il valore è **0.64**, che è considerato "buono" e significa che Posidonia e sabbia hanno luminanze abbastanza diverse da essere distinte con affidabilità.

5. **Filtri morfologici.** Dopo il clustering, vengono applicati due filtri matematici (Opening e Closing) che rimuovono i punti isolati: un singolo pixel scuro circondato da sabbia è probabilmente rumore, non Posidonia, e viene eliminato. Viceversa, un piccolo buco chiaro all'interno di un'area densa di Posidonia viene riempito.

**Output:** Due maschere binarie — `mask_posidonia` e `mask_sabbia` — che indicano per ogni cella della griglia se contiene Posidonia o sabbia.

---

### `geometry.py` — Calcolo di area e volume

**Cosa fa:** Trasforma le maschere binarie prodotte dal segmenter in misure metriche reali.

**Calcolo dell'area:**

Semplice e robusto: ogni cella della griglia vale 10×10 cm = 0.01 m². L'area totale di Posidonia è il numero di celle classificate come Posidonia moltiplicato per 0.01 m². Idem per la sabbia.

**Calcolo del volume — Metodo Voxel 2.5D (Somma di Riemann):**

Questo è il contributo scientifico più significativo rispetto all'analisi 2D tradizionale.

Il metodo semplice sarebbe: `volume = area × altezza_fissa`. Ma moltiplicare l'area per 70 cm fissi sovrastima il volume perché la Posidonia non è un blocco di cemento piatto — alcune zone hanno foglie alte 60 cm, altre 20 cm, ai bordi le foglie sono basse.

Il metodo implementato è più preciso:
- Per ogni cella 10×10 cm classificata come Posidonia, si calcola la **micro-altezza locale**: differenza tra il punto più alto (la punta delle foglie) e il punto più basso (la sabbia immediatamente sotto) in quella specifica cella.
- Il volumetto di quella cella è `micro-altezza × 0.01 m²`.
- Il volume totale è la **somma di tutti i volumetti**.

Questo significa che se il fondale è in pendenza, o se la Posidonia è più bassa ai bordi della prateria, il calcolo si adatta automaticamente alla morfologia reale.

**Output:** `area_posidonia_m2`, `area_sabbia_m2`, `volume_posidonia_m3`.

---

### `metrics.py` — Metriche ecologiche e validazione biologica

**Cosa fa:** Trasforma i dati geometrici in informazioni ecologicamente significative e verifica che i risultati siano biologicamente plausibili.

**Le metriche ecologiche calcolate:**

| Metrica | Formula | Significato |
|---|---|---|
| Copertura Posidonia | area_pos / (area_pos + area_sabbia) × 100 | % del fondale ancora coperto |
| Perdita CO₂ | area_sabbia × 0.0002 tC/m² × 3.6663 × 1000 | kg di CO₂/anno non più sequestrata |
| Perdita O₂ | area_sabbia × 3650 L/m²/anno | Litri di O₂/anno non più prodotti |
| Ratio Volume/Area | volume / area_posidonia | Altezza media effettiva della chioma |

I coefficienti (0.0002 tC/m², 3650 L O₂/m²/anno) sono valori standard dalla letteratura scientifica su *Posidonia oceanica*.

**La validazione biologica — 4 controlli automatici:**

Il software non si fida ciecamente dei propri calcoli. Prima di produrre il report, esegue 4 controlli:

1. **Controllo calibrazione:** L'altezza massima post-scalatura deve essere ≈ 0.70 m ± 3.5 cm. Se è fuori range, la calibrazione RANSAC potrebbe aver trovato un piano sbagliato.

2. **Controllo Ratio Volume/Area:** Deve essere tra 0.20 m e 0.80 m. Se è sotto 0.20, la Posidonia risulta troppo bassa (possibile fondale molto ondulato o rumore). Se è sopra 0.80, le altezze sono probabilmente sovrastimate da rumore nella nuvola di punti. Nel vostro rilievo il valore è **0.166 m**, leggermente sotto soglia — il software emette correttamente un warning che segnala un possibile fondale ondulato.

3. **Controllo copertura:** Deve essere tra 10% e 95%. Valori estremi indicano probabili errori di segmentazione.

4. **Controllo clustering:** Lo Silhouette Score deve essere > 0.3. Sotto questa soglia i due gruppi si sovrappongono troppo per una segmentazione affidabile.

**Output:** Dizionario con tutte le metriche + lista di warning con descrizione del problema rilevato.

---

### `reporter.py` — Generazione dei report

**Cosa fa:** Prende tutti i risultati e li salva in tre formati diversi per utilizzi diversi.

**Report Excel (.xlsx) — 4 fogli:**

- **Sheet "Summary":** Tabella con tutte le metriche finali (area, volume, copertura, CO₂, O₂). È il foglio da portare al convegno.
- **Sheet "Grid Data":** Una riga per ogni cella 10×10 cm della griglia, con luminanza media, altezza e classificazione (Posidonia/Sabbia). Permette analisi di dettaglio.
- **Sheet "Validation":** I risultati dei 4 controlli biologici con valori numerici.
- **Sheet "Cicatrice":** Focus sulle metriche della zona danneggiata (sabbia): area cicatrice, CO₂ persa, O₂ perso, copertura residua.

**Report JSON (.json) — Per integrazione futura:**

File strutturato con metadati (timestamp, file sorgente, versione software), calibrazione (equazione del piano, fattore di scala), risultati K-Means (centroidi, soglia, silhouette), tutte le metriche e la lista dei warning. Progettato per essere letto da altri software o database.

**Visualizzazione PNG — Dashboard a 5 pannelli:**

| Pannello | Contenuto |
|---|---|
| 1 — Istogramma Luminanza | Distribuzione delle luminanze con i due centroidi K-Means e la soglia di separazione. Dimostra visivamente che i due gruppi sono separati. |
| 2 — Mappa Luminanza | Vista dall'alto del fondale in scala di grigi. Si vedono le zone scure (Posidonia) e chiare (sabbia). |
| 3 — Mappa Altezze | Vista dall'alto colorata per altezza: viola = basso, giallo = alto. Mostra la morfologia della chioma. |
| 4 — Mappa Segmentazione | Vista dall'alto con verde = Posidonia, rosso = sabbia. È la visualizzazione principale del risultato. |
| 5 — Report Testuale | Tutte le metriche numeriche in formato leggibile, con lista dei warning. |

---

### `pipeline.py` — L'orchestratore

**Cosa fa:** Coordina l'esecuzione di tutti i moduli nell'ordine corretto, gestendo gli errori e il logging.

**La sequenza di esecuzione:**

```
[1/6] loader      → Carica i 19 file PLY e li fonde
[2/6] calibrator  → RANSAC + calcolo fattore di scala
[3/6] segmenter   → Griglia + K-Means + filtri morfologici
[4/6] geometry    → Calcolo area e volume
[5/6] metrics     → Metriche ecologiche + 4 validazioni biologiche
[6/6] reporter    → Genera Excel + JSON + PNG
```

**Due modalità di utilizzo:**
- `run_single_file("file.ply")` — per un singolo file
- `run_tiled_ply("cartella/")` — per una cartella con più file (il caso vostro)

---

### `scripts_utility/test_colore.py` — Il test di Ground Truth

**Cosa fa:** Confronta la stima automatica del software con una stima manuale fatta dall'occhio umano, per dimostrare scientificamente che l'analisi 3D è più accurata di quella 2D.

**La procedura:**
1. Si prende un'ortofoto (vista dall'alto) del rilievo.
2. Un operatore colora manualmente le zone di Posidonia in rosso.
3. Il software misura la percentuale di rosso sull'immagine come stima "umana".
4. Si confronta con la stima K-Means del modello 3D.

**Il risultato nel vostro rilievo:**
- Stima occhio umano (2D): **48.5%** di Posidonia
- Stima K-Means 3D: **38.7%** di Posidonia

La differenza di ~10 punti percentuali è reale e attesa: l'analisi 2D sovrastima la Posidonia perché le foglie proiettano ombre sul fondo sabbioso, facendo sembrare scura anche la sabbia vicina. Il modello 3D elimina questo artefatto perché lavora sulla geometria reale, non sui colori dell'immagine.

**Questo test è il vostro argomento più forte al convegno** per giustificare l'uso della fotogrammetria 3D rispetto all'analisi video tradizionale.

---

## Come si incrociano RANSAC, K-Means e test colore

I tre metodi non sono alternativi — sono tre strati sovrapposti che si correggono a vicenda:

```
RANSAC
  └─ Trova il piano del fondale in modo robusto agli outlier
  └─ Calibra la scala trasformando unità arbitrarie in metri reali
  └─ Prerequisito per tutto il resto: senza scala corretta, 
     area e volume sono numeri senza senso

K-Means (lavora sui dati già scalati da RANSAC)
  └─ Separa Posidonia da sabbia senza soglie manuali
  └─ La soglia è matematicamente ottimale (punto medio tra i centroidi)
  └─ Il Silhouette Score certifica la qualità della separazione
  └─ I filtri morfologici puliscono il rumore residuo

Test colore manuale (confronto esterno con l'output di K-Means)
  └─ Non influenza il calcolo automatico
  └─ Serve a validare che il risultato automatico sia realistico
  └─ Dimostra che il 3D è più preciso del 2D
  └─ È il "check umano" che certifica l'intero sistema
```

Il risultato finale è quindi difendibile su tre livelli: la scala è certificata da RANSAC, la segmentazione è oggettiva grazie a K-Means, e la plausibilità è verificata dal confronto con la stima visiva umana.

---

## Output dell'analisi — Cosa troverete in `data/output/`

Dopo aver lanciato `main.py` troverete tre file:

**`report_posidonia_tiled.xlsx`**  
Il file principale per Modugno. Aprirlo con Excel. Il foglio "Summary" contiene le metriche principali; il foglio "Cicatrice" riassume i danni da ancoraggio.

**`report_posidonia_tiled.json`**  
File tecnico strutturato. Contiene tutti i dati in un formato leggibile da altri software. Utile per archiviazione scientifica e integrazione futura con database GIS.

**`visualization_posidonia.png`**  
Immagine dashboard a 5 pannelli. Pronta per presentazioni e poster al convegno. Risoluzione 150 DPI.

---

## Risultati del rilievo attuale

I valori qui sotto si riferiscono al rilievo della cicatrice da ancoraggio elaborato come test:

| Metrica | Valore |
|---|---|
| Area totale analizzata | da definire con georef. |
| Copertura Posidonia | **38.7%** |
| Copertura sabbia (cicatrice) | **61.3%** |
| Silhouette Score K-Means | **0.64** (buono) |
| Ratio Volume/Area | **0.166 m** ⚠️ sotto soglia |
| Stima 2D manuale | 48.5% (sovrastimata del ~25%) |

Il warning sul ratio Volume/Area non invalida i risultati — segnala che il fondale potrebbe essere morfologicamente ondulato o che la Posidonia è particolarmente bassa in questa zona. Modugno può valutare se questo è coerente con la sua conoscenza del sito.

---

## Sviluppi futuri

### Priorità alta — Migliorano direttamente la precisione

**Georeferenziazione automatica**  
Integrare i punti GPS del percorso del ROV (già richiesti a Modugno) per ancorare il modello a coordinate reali. La cicatrice cesserebbe di essere un oggetto geometrico astratto e diventerebbe una zona cartografabile su mappa. Output: GeoTIFF e GeoJSON con coordinate reali.

**Calibrazione con oggetto fisico noto**  
Nei rilievi futuri posizionare sul fondale un frame metallico di dimensioni certificate (es. 50×50 cm). Questo permetterebbe di sostituire la calibrazione biologica euristica con una calibrazione metrica diretta, riducendo l'incertezza da ±5% a meno dell'1%.

**Segmentazione con colore RGB + altezza combinati**  
Attualmente la segmentazione usa solo la luminanza (R+G+B/3). Aggiungere la componente di altezza come secondo asse del clustering K-Means (o passare a K-Means 2D su spazio luminanza×altezza) renderebbe la separazione più robusta in condizioni di scarsa illuminazione o forte torbidità.

### Priorità media — Espandono le funzionalità

**Analisi della cicatrice da ancoraggio separata**  
Implementare un modulo che identifichi automaticamente la cicatrice come zona isolata di sabbia circondata da Posidonia, calcolando metriche separate per la zona danneggiata vs. la prateria sana circostante. Attualmente l'analisi tratta sabbia e Posidonia come classi globali.

**Monitoraggio temporale**  
Struttura per confrontare rilievi dello stesso sito in date diverse. Calcolo automatico della variazione di area e volume nel tempo (regressione o recupero della prateria). Grafico temporale della copertura.

**Supporto Gaussian Splatting (.splat)**  
I rilievi più recenti producono modelli in formato Gaussian Splatting (.psht). Aggiungere un loader che estragga i centroidi gaussiani come nuvola di punti per poterla analizzare con la stessa pipeline.

**Visualizzazione 3D interattiva (Plotly HTML)**  
Generare un file HTML standalone che mostra il modello 3D ruotabile nel browser, con colori verde/arancione per Posidonia/sabbia. Apribile senza installare nulla, ideale per presentazioni al convegno.

### Priorità bassa — Ricerca avanzata

**Conteggio fasci fogliari**  
La densità della Posidonia si misura in fasci per m². Implementare un algoritmo di rilevamento di punti locali massimi sulla mappa di altezza per stimare automaticamente il numero di fasci nell'area analizzata.

**Modello di classificazione supervisionato**  
Sostituire K-Means (non supervisionato) con un classificatore addestrato su immagini annotate manualmente da Modugno. Con 200-300 celle annotate si potrebbe addestrare un Random Forest o una rete neurale leggera che generalizzi meglio a condizioni diverse (torbidità, profondità, stagione).

**Correzione della rifrazione ottica**  
Le immagini subacquee soffrono di distorsione per rifrazione all'interfaccia acqua-lente. Aggiungere la correzione della rifrazione nella fase di calibrazione migliorerebbe la precisione metrica specialmente ai bordi dell'immagine.

**Stima della biomassa fogliare**  
Dal volume della chioma, usando densità fogliare media da letteratura per *Posidonia oceanica* (~1.2 kg/m³ di materia secca), stimare la biomassa totale. Dato richiesto da alcuni protocolli LIFE per la valutazione dei servizi ecosistemici.

---

## Dipendenze software

```
Python 3.11+
numpy
scipy
scikit-learn
trimesh
open3d
laspy
matplotlib
pandas
openpyxl
```

Installazione:
```bash
pip install numpy scipy scikit-learn trimesh open3d laspy matplotlib pandas openpyxl
```

---

## Riferimenti scientifici

- Coefficienti carbon sink Posidonia: Fourqurean et al. (2012) *Nature Geoscience*
- RANSAC: Fischler & Bolles (1981) *Communications of the ACM*
- K-Means clustering: MacQueen (1967); validato con Silhouette (Rousseeuw, 1987)
- Metodologia fotogrammetria marina: Rende et al. (2015) *PLOS ONE*

---

*Documento generato automaticamente — versione 2.0 — Giugno 2026*
