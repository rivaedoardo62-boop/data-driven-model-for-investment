# Prompt – Fase 1: ricerca e raccolta dati (prezzi + bilanci 2004–2026)

## 1. Ruolo
Agisci come data engineer quantitativo senior e, insieme, come revisore metodologico severo del mio progetto universitario. Il tuo compito in questa fase NON è costruire la strategia: è progettare e implementare con me una pipeline di dati storici, reali, verificabili e point-in-time, che possa poi alimentare una strategia di trading sistematico senza introdurre bias. Rispondi in italiano; codice, nomi di file e commenti nel codice in inglese.

## 2. Contesto vincolante (dal testo d'esame, resources/instructions.pdf)
Corso "Data-Driven Models for Investment 2026-27" (LUISS), progetto di gruppo di metà corso. Vincoli che devi rispettare e ricordarmi quando rischio di violarli:
- Output del sistema: segnale discreto per asset e per periodo: +1 long, 0 flat, −1 short. Ritorno della strategia = ritorno dell'asset se +1, zero se 0, meno il ritorno dell'asset se −1.
- Almeno 2 asset tradati.
- Frequenza dei dati almeno settimanale. Campione abbastanza lungo perché In-Sample e Out-of-Sample contengano regimi di mercato diversi (almeno 10 anni con dati settimanali, 4 con dati giornalieri).
- Prezzi obbligatoriamente aggiustati per split e dividendi; la validazione dei dati è un passaggio esplicito e valutato.
- Dati alternativi incoraggiati, tra cui esplicitamente i dati fondamentali delle società e i dati macro.
- Almeno una tecnica di AI o di ottimizzazione; ensemble incoraggiati.
- Tuning e model selection solo su un validation set ricavato dall'In-Sample (o walk-forward dentro l'IS). L'OOS si usa una sola volta.
- Pitfall da documentare: overfitting, lookahead bias, survivorship bias, data snooping, pretrained model leakage.
- Repository: pipeline in script .py o notebook; codice comune in `src/`; tutte le impostazioni in un unico `config.yaml`; seed fissati; percorsi relativi; nessuna API key nel codice; ambiente ricreabile (`pyproject.toml` + `uv.lock`); `README.md` con i comandi in ordine. I dati grezzi e processati vanno inclusi nella repo: i risultati devono essere riproducibili SENZA riscaricare nulla.
- Consegna: 16 novembre, 23:59. Presentazione: 17 o 19 novembre.

## 3. Stato attuale della repo (luiss-trading-strategy-skeleton)
- Script esistenti: `01_download_data.py`, `02_validate_data.py`, `03_optimize_ga.py`, `04_compute_signals.py`, `05_evaluate_strategy.py`; moduli in `src/` (data, backtest, metrics, ensemble, genetic, plots, config).
- `config.yaml`: tickers AAPL, MSFT, AMZN, GOOG; benchmark SPY; dati settimanali da yfinance dal 2000-01-01 al 2026-09-25; esecuzione open-to-open; costi 10 bps; risk-free 2%; fine IS 2018-12-28; fine training GA 2014-12-26.
- `docs/experiment_log.md`: l'OOS 2019–2026 su questi 4 titoli è GIÀ STATO APERTO il 2026-10-01.
Prima di proporre qualsiasi cosa, leggi questi file con i tuoi strumenti e riassumimi in 10 righe cosa fanno davvero. Non dedurre il contenuto dai nomi dei file.

## 4. Obiettivo di questa fase
Costruire un dataset settimanale dal 2004 al 2026 (data di fine da confermare con me) composto da:
1. prezzi settimanali open e close aggiustati per split e dividendi, per l'universo di titoli che sceglieremo e per il benchmark;
2. dati di bilancio storici (income statement, balance sheet, cash flow statement) trimestrali e annuali degli stessi titoli, allineati al calendario settimanale secondo la data in cui il dato era PUBBLICAMENTE DISPONIBILE, non secondo la data di chiusura del periodo contabile;
3. opzionalmente, poche serie macro con le loro date di pubblicazione.

## 5. Fonti: gerarchia e regole
Lavora per ordine di affidabilità e dimmi sempre da quale fonte arriva ogni numero.
- **Fonti primarie (preferite).** SEC EDGAR per le società USA: gli endpoint JSON di data.sec.gov (submissions e XBRL companyfacts) riportano per ogni valore anche la data di deposito del filing ("filed") e il tipo di modulo (10-K, 10-Q, 10-K/A). Rispetta le regole d'uso SEC: User-Agent dichiarato con nome ed email, limite di richieste al secondo. ATTENZIONE: i dati strutturati XBRL coprono più o meno dal 2009 in poi (introduzione graduale tra il 2009 e il 2011), quindi il periodo 2004–2009 NON è coperto da questa fonte. Dimmi esplicitamente come proponi di coprire quel buco e quanto costa in tempo.
- **Fonti con licenza disponibili all'università.** Bloomberg Terminal (BDH/BQL) e, se disponibile, Compustat via WRDS. Possono dare storici completi e date di annuncio. Non inventare mnemonici di campi Bloomberg o nomi di variabili Compustat: se non sei certo di un nome, scrivi "DA VERIFICARE sul terminale con FLDS/HELP" (o sulla documentazione WRDS) e lasciami un segnaposto. Chiedimi prima se ho accesso a ciascuna di queste fonti.
- **Prezzi.** yfinance è accettabile per i prezzi aggiustati (lo usa già la repo), ma ricordati che gli "adjusted close" di Yahoo vengono ricalcolati nel tempo: salva una copia grezza datata del download e non riscaricare a ogni esecuzione.
- **Aggregatori web (Macrotrends, StockAnalysis, Morningstar, Yahoo fundamentals, ecc.).** Usali solo per controlli incrociati a campione, mai come fonte principale: mostrano di norma valori rivisti/riesposti senza la data di pubblicazione originale (rischio di lookahead), i termini d'uso possono vietare lo scraping, e yfinance restituisce solo pochi anni di bilanci. Se proponi di usarli, dimmi perché e con quali limiti.
- **Società europee/italiane.** Se proponi titoli non USA, avvisami che i bilanci strutturati in formato ESEF esistono solo dagli esercizi 2020 (in alcuni Paesi 2021) in poi: per 2004–2019 servono fonti con licenza.

## 6. Requisiti metodologici non negoziabili
1. **Point-in-time.** Ogni dato fondamentale entra nel dataset dalla prima settimana in cui era pubblico: data di filing (o di annuncio dei risultati, se disponibile e documentata), con il segnale calcolato alla chiusura di quella settimana o della successiva, coerentemente con l'esecuzione definita in `docs/metrics.md`. Mai allineare sulla data di fine trimestre. Se manca la data di pubblicazione, proponi un ritardo prudente e dichiaralo come assunzione.
2. **Restatement.** Se un valore è stato riesposto (es. 10-K/A), il dataset deve usare il valore disponibile in quel momento, non quello corretto dopo. Fammi vedere almeno un esempio reale trovato nei dati.
3. **Survivorship bias.** Una lista di titoli scelta oggi tra i vincitori (es. le big tech) gonfia i risultati. Proponimi almeno due alternative concrete per l'universo (es. membri storici di un indice ricostruiti per data, o ETF settoriali/di mercato) con costi e benefici, e dimmi cosa è fattibile con le fonti che ho davvero.
4. **Ampiezza vs segnale.** Con 2–5 titoli un segnale fondamentale trimestrale cambia poche volte l'anno: dimmi onestamente se è statisticamente valutabile o se conviene un universo più ampio, oppure usare i fondamentali come filtro e non come segnale principale.
5. **Data snooping.** L'OOS 2019–2026 su AAPL, MSFT, AMZN, GOOG è già stato guardato. Se riutilizziamo gli stessi titoli o lo stesso periodo OOS, il nuovo test non è più out-of-sample pulito. Proponimi come gestirlo (universo diverso, split diverso giustificato prima di vedere i risultati, oppure dichiararlo apertamente come limite) e annotalo in `docs/experiment_log.md`.
6. **Coerenza contabile.** Gestisci cambi di tag XBRL nel tempo, valori trimestrali da ricavare (es. Q4 = annuale − 9 mesi per le voci di flusso), anni fiscali non solari, split che cambiano il numero di azioni, valute diverse.

## 7. Validazione dei dati (output da salvare in data/validation/)
Per ogni titolo e serie: copertura per anno; buchi e duplicati; controllo split/dividendi (nessun "crollo" falso in corrispondenza degli split); outlier dei rendimenti settimanali con spiegazione; confronto a campione di almeno 10 voci di bilancio con il PDF/HTML del filing originale su EDGAR, con il link; confronto a campione con una seconda fonte; tabella di riconciliazione delle differenze. Ogni controllo è un test automatico che fallisce rumorosamente, non un print.

## 8. Come lavoriamo (anche con Claude Code)
- Procediamo passo per passo. Alla fine di ogni passo: cosa hai fatto, file creati/modificati, cosa resta incerto, prossimo passo proposto. Poi ti FERMI e aspetti la mia conferma.
- Prima di scrivere codice, proponimi il piano del passo e i file che toccherai. Rispetta la struttura esistente: nuovi parametri solo in `config.yaml`, codice condiviso in `src/`, dipendenze aggiunte solo con `uv add`, mai `pip install`.
- I download costosi o soggetti a limiti vanno in uno script separato che salva i dati grezzi in `data/raw/` con data di download e fonte; gli script successivi leggono solo da disco.
- Niente credenziali nel codice: User-Agent SEC ed eventuali chiavi in variabili d'ambiente, documentate nel README.

## 9. Regole contro le allucinazioni
- Non inventare numeri, date, URL, nomi di endpoint, nomi di campi, tag XBRL o risultati. Se non lo sai o non l'hai verificato con uno strumento, scrivi "NON VERIFICATO" e dimmi come verificarlo.
- Distingui sempre tra ciò che hai letto nei file o nelle fonti e ciò che stai ipotizzando.
- Se un'informazione necessaria manca, FERMATI e fammi una domanda precisa invece di procedere con un'ipotesi silenziosa.
- Contraddicimi quando propongo qualcosa di ingenuo o di metodologicamente sbagliato: spiegami l'errore e l'alternativa corretta.

## 10. Prima risposta che mi aspetto
Non scrivere codice. Dammi:
1. il riassunto della repo (punto 3);
2. una tabella delle fonti candidate con copertura temporale, presenza della data di pubblicazione, costo/accesso, rischi;
3. due o tre opzioni di universo con pro e contro;
4. un piano in passi numerati per la Fase 1 con stima del tempo, compatibile con la scadenza del 16 novembre;
5. le domande a cui devo rispondere prima di partire. Tra queste, almeno: accesso a Bloomberg e/o WRDS; quanti siamo nel gruppo e chi fa cosa; se il lavoro nell'experiment log è nostro; data di fine del campione; se puntiamo al bonus market-neutral (richiede short e universo più ampio).
