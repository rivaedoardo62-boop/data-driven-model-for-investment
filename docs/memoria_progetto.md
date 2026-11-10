# Memoria del progetto

Riassunto di lavoro del gruppo (4 persone) per il progetto di metà corso di *Data-Driven Models for Investment 2026-27*
(LUISS): cosa abbiamo fatto, cosa abbiamo deciso e perché, a che punto siamo. Aggiornato al **10 novembre 2026** (sera).
I dettagli tecnici e i numeri completi sono nei documenti in inglese della cartella `docs/`, soprattutto
[experiment_log.md](experiment_log.md), che è il registro ufficiale di ogni tentativo.

## Aggiornamento del 10 novembre: cambio di progetto

- **Il progetto finale è la pipeline di Filippo** (repo `filpo-ops/data-driven-models-for-investments`): machine learning
  (logistica + gradient boosting) e momentum sui semiconduttori, Out-of-Sample dal 2018 mai eseguito. Il codice è solo
  sul computer di Filippo: arriva come zip in chat e si riprende seguendo il documento di passaggio, un passo alla volta.
- **Questa repo diventa un archivio**: non si cancella nulla. Il long/short congelato qui non è mai stato eseguito su
  validation e Out-of-Sample. Pezzi riutilizzabili: controlli sui dati, indicatori notte/giorno, pulizia Bloomberg.
- **Idea stagionale scartata** (short da novembre a gennaio, long dalla primavera): sul 2001-2017 novembre-gennaio sono i
  mesi migliori (semiconduttori +3,1% al mese contro +1,15%; SPY +0,8% contro +0,5%), e la regola perde il 5,1% all'anno
  contro il +15% di chi resta long. Da citare nella presentazione come idea verificata e scartata.
- **Urgente, licenza Bloomberg**: il `prices.parquet` caricato e poi cancellato il 9 novembre sulla repo pubblica di
  Filippo è ancora scaricabile dalla storia (commit `4ac81b6`), come `meta.csv`. Filippo rende privata la repo oggi
  (Settings, Danger Zone, Change visibility).

## 1. Il compito

- **Consegna:** 16 novembre, 23:59, un solo file `group_<numero>.zip` con `project/` (questa repo) e `presentation.pdf`.
- **Presentazione:** 17 o 19 novembre, 10 minuti più domande (template in `resources/presentation.pptx`, 11 slide).
- **Voto:** 11 punti in tutto.
  - Rigore 4: niente bias, backtest realistico.
  - Originalità e complessità 3.
  - Analisi delle performance 2: una strategia debole riportata onestamente vale più di una sovra-adattata.
  - Codice e presentazione 1.
  - Bonus 1: market-neutral oppure Sharpe superiore con un test statistico.
- **Regole che seguiamo:**
  - segnale −1/0/+1;
  - almeno 2 asset;
  - prezzi aggiustati per split e dividendi;
  - In-Sample e Out-of-Sample con regimi diversi;
  - scelte fatte solo sul training/validation, Out-of-Sample usato una volta sola;
  - tutte le impostazioni in `config.yaml`;
  - dati nella repo e risultati riproducibili senza riscaricare.

Testo completo: `resources/instructions.pdf`.

## 2. Come lavoriamo

- **Branch di lavoro:** `claude/wonderful-dijkstra-7qpzd9`. Ambiente con `uv sync`, script con `uv run python <script>.py`, mai `pip install`.
- **La repo GitHub è pubblica.** I dati Bloomberg hanno una licenza: `data/bloomberg/` è esclusa da git e va passata a mano tra di noi e messa nello zip finale. Si potrebbe rendere privata la repo: non l'abbiamo ancora deciso.
- **Non rilanciare `01_download_data.py`.** Yahoo ricalcola i prezzi aggiustati e la strategia pilota è congelata sui prezzi salvati.
- **Ogni modifica alla strategia si registra in `docs/experiment_log.md` prima di vederne i risultati.** È la nostra difesa contro l'accusa di data snooping.

## 3. Cronologia

| Data | Cosa | Decisione e motivo |
|---|---|---|
| 3 nov | Analisi della repo, del testo d'esame e della repo di Advanced Statistics | Il dataset di Taiwan (default delle carte di credito) non serve per il trading; dal metodo prendiamo solo l'idea di logit/Random Forest e delle soglie. Due trappole: lo split casuale e la calibrazione OOB non valgono per le serie storiche |
| 3 nov | Eliminata la "Fase 1" (bilanci da SEC EDGAR, punto per punto nel tempo) | Troppo lavoro per 13 giorni, e con 4 titoli un segnale trimestrale non si può valutare |
| 3 nov | Scritto `docs/strategy.md` per la strategia sulle big tech | Logica esatta del segnale, periodi, insidie |
| 3 nov | Dati macro da FRED (VIX, curva, recessioni, tassi Fed, spread di credito, inflazione, T-bill), più ETF e fondi quant da Yahoo | I test sono stati scritti nel log prima di scaricare i dati (pre-registrazione) |
| 3 nov | Controlli sui dati nuovi | Tre falsi allarmi sui dividendi (dividendi minuscoli) corretti nel controllo; il CPI di ottobre 2025 manca alla fonte (non pubblicato per lo shutdown del governo USA); trovato e corretto un mio bug nell'inflazione su 12 mesi |
| 3 nov | 9 grafici per le slide (`08_make_figures.py`, `docs/figures.md`) | |
| 5 nov | Bloomberg: rivisto lo script di Filippo (`bbg_semis.py`) | Tre problemi: non salvava chi era nell'indice e quando; l'aggiustamento dipendeva dalle impostazioni di chi era loggato; nessun modo di verificare i dati. Sostituito da `09_download_bloomberg.py`; tolto l'intraday a 1 minuto (inutile per una strategia settimanale, 6 mesi di storia, consuma il limite di download) |
| 5 nov | Primo scarico Bloomberg (102 righe di borsa) pulito ed esplorato | `10_clean_bloomberg.py`, `11_eda_bloomberg.py`, `notebooks/01_bloomberg.ipynb`, `docs/bloomberg.md` |
| 8 nov | **Svolta:** la strategia finale è long/short sui semiconduttori dell'indice SOX | La strategia sulle big tech diventa il **pilota**. Cancellati ETF e fondi quant (i loro test sono stati abbandonati prima di eseguirli) |
| 8 nov | Primi run di sviluppo, solo training | La strategia non è neutrale al mercato; neanche dimensionarla a beta zero basta |
| 9 nov | Idea dal paper di Lou, Polk e Skouras (2019), *A tug of war: overnight versus intraday expected returns* | Ogni rendimento giornaliero diviso in notte (chiusura → apertura) e giorno (apertura → chiusura). Verificato sui nostri dati, solo training |
| 10 nov | **Disegno finale congelato** e script di valutazione pronto | 7 indicatori con il momentum notturno, bonus market-neutral abbandonato, parametri confermati |

## 4. Il pilota: strategia sulle 4 big tech

- **Cosa fa:** settimanale, long/flat su AAPL, MSFT, AMZN, GOOG.
  - 4 indicatori: trend, momentum, reversal, volatilità.
  - Finestre, pesi e soglia scelti da un algoritmo genetico (DEAP) sul training 2005-2014.
  - 5 run e voto a maggioranza (long se almeno 3 su 5).
  - Esecuzione all'apertura successiva, 10 bps per operazione.
- **Out-of-Sample (2019-2026), aperto il 1° ottobre:**

  | | Rendimento annuo | Volatilità | Sharpe | Max drawdown | Beta verso SPY |
  |---|---|---|---|---|---|
  | Strategia | 18,6% | 18,4% | 0,91 | −34,5% | 0,62 |
  | Equal weight delle 4 | 28,2% | 25,0% | 1,05 | −36,9% | 1,12 |
  | SPY | 17,9% | 18,2% | 0,88 | −31,8% | 1,00 |

- **Lezioni:**
  - **Survivorship bias:** le 4 aziende sono state scelte nel 2026 sapendo che erano le vincitrici.
  - **L'algoritmo genetico non batte il caso:** in validation 0,93 contro 1,49 della ricerca casuale.
  - **Quasi tutto il guadagno del training viene dal 2008:** +38% sull'equal weight.
  - **Nessuna differenza significativa con SPY:** bootstrap della differenza di Sharpe +0,03, intervallo [−0,71; +0,73].
- **Ruolo nel progetto:** primo tentativo e lezione imparata, da presentare come tale.

## 5. I dati

| Fonte | Cosa | Dove | Stato |
|---|---|---|---|
| Yahoo Finance | AAPL, MSFT, AMZN, GOOG, SPY, giornalieri 2000-2026, aggiustati | `data/prices/` | Validati (`02_validate_data.py`): tutti i controlli superati |
| FRED | VIXCLS, T10Y3M, USREC, DFF, BAA10Y, CPIAUCSL, DTB3 | `data/extra/macro/` | Validati; manca solo il CPI di ottobre 2025 alla fonte |
| Bloomberg, primo scarico | 102 righe di borsa dei titoli passati dal SOX 2000-2026 | `data/bloomberg/raw/prices.parquet` (non su GitHub) | Pulito: 82 società, 30 uscite dal mercato, 0 FAIL e 111 avvisi spiegati in `docs/bloomberg.md` |
| Bloomberg, scarico definitivo | Composizione del SOX a fine anno, ticker compositi US, nomi, prezzi non aggiustati, dividendi, P/E, indice SOX | Da mettere in `data/bloomberg/raw/` | **In attesa** (`--membership-only`, poi `--lite`) |

Cose trovate pulendo i dati Bloomberg:
- **Una società compariva una volta per borsa.** Le ho unite prendendo ogni giorno la borsa con più volume: la regola ritrova esattamente tutti i cambi di borsa noti.
- **Il total return index di Bloomberg sbaglia su ASML il 29/11/2012**, il giorno del riacquisto sintetico di azioni, e ha una base diversa per ogni borsa.
- **Maxim, Power Integrations e Novanta** sono state sospese dal Nasdaq per mesi.
- **Limiti del primo scarico:**
  - manca la composizione per data, quindi l'universo contiene i vincitori futuri;
  - mancano gli anni prima del cambio di borsa di ADI (2012), CY (2009) e IPHI (2020);
  - 8 società delistate sono senza nome.

  Lo scarico definitivo risolve tutto.

Analisi esplorativa (`data/bloomberg/eda/`):
- **Survivorship bias:** le società ancora quotate rendono il 10,6% annuo mediano, quelle uscite il 5,8%.
- **Nvidia** vale il 34% della capitalizzazione dell'universo (47% al picco). Per questo il benchmark è l'equal weight: con o senza Nvidia cambia poco.
- **Code grasse:** curtosi in eccesso 15,6.
- **L'universo conta molto:** con il solo filtro di liquidità l'equal weight passa da 6.799 a 4.051 (partendo da 100).

## 6. La strategia finale: long/short sui semiconduttori

Disegno congelato il 10 novembre (dettagli in `docs/experiment_log.md`, codice in `src/longshort.py`):

| Voce | Scelta |
|---|---|
| Ipotesi | In un settore ciclico la differenza tra vincitori e perdenti è grande: classificare le società con indicatori di prezzo e tenere le migliori contro le peggiori rende indipendentemente dalla direzione del settore |
| Universo | Ogni settimana i membri del SOX (composizione dell'ultima fine anno), con prezzo e indicatori; le società delistate escono al loro ultimo prezzo |
| Indicatori (7) | Rendimento delle ultime 4 settimane, **parte notturna del momentum 52-4 settimane**, trend 26 settimane, distanza dal massimo a 52 settimane, volatilità 26 settimane, rapporto di volatilità 10/52 settimane, beta 52 settimane. Tagliati all'1% e al 99% e standardizzati ogni settimana |
| Segnale | Punteggio = media pesata degli indicatori; +1 al 20% più alto, −1 al 20% più basso, 0 agli altri |
| Pesi del portafoglio | Metà capitale sui long e metà sugli short, uguali dentro ogni lato; esposizione netta 0, lorda 100%, niente leva |
| Esecuzione | Segnale al venerdì sera, esecuzione all'apertura del lunedì, posizione tenuta fino al lunedì successivo |
| Costi | 10 bps per operazione; 0,5% annuo per prendere in prestito le azioni vendute allo short |
| Ottimizzazione | Algoritmo genetico (5 run) solo sul training; strategia = media dei 5 membri; controllo con ricerca casuale |
| Periodi | Training fino al 26/12/2014 (dal 2001), validation 2015-2018, Out-of-Sample dal 31/12/2018 |
| Benchmark | Cassa, equal weight long degli stessi titoli, SPY |
| Bonus | Market-neutral abbandonato (sul training beta circa 0,2 verso SPY); niente forzature |

Perché il momentum notturno, verificato solo sul training:

| Long/short sul 20% più alto contro il 20% più basso | Notte | Giorno | Totale |
|---|---|---|---|
| Momentum classico | −7,4% | +2,3% | −5,1% |
| Momentum fatto solo di notti | +24,0% | −16,8% | **+7,2% (t 2,5)** |
| Momentum fatto solo di giorni | −20,4% | +14,5% | −5,9% |

Il "tiro alla fune" c'è: chi sale di notte continua a salire di notte e scende di giorno.

## 7. Risultati finora (solo training, universo provvisorio)

| Versione | Sharpe training | Note |
|---|---|---|
| 7 indicatori iniziali | 1,13 | Ricerca casuale 0,88; beta 0,24 verso SPY |
| Stessi, dimensionati a beta zero | 0,84 | Beta resta 0,17, 2008 −20%: scartata |
| 9 indicatori (notte e giorno separati) | 0,92 | Pesi poco stabili: scartata |
| **Disegno congelato** | **0,95** | Ricerca casuale 0,81; bootstrap 0,41-1,48; rendimento 12%, max drawdown −20,5% |

Cosa dicono i pesi del disegno congelato:
- **5 indicatori su 7 hanno lo stesso segno in tutti e 5 i run.** Positivi: rendimento a 4 settimane e volatilità. Negativi: distanza dal massimo, rapporto di volatilità e beta.
- **Il momentum notturno**, positivo da solo, insieme agli altri prende un peso negativo in 4 run su 5.

Attenzione: il guadagno viene dal 2001-2003 e dal 2009 (+81%), e dal 2010 al 2014 la strategia è piatta. Un risultato debole in validation o in Out-of-Sample non sarebbe una sorpresa, e lo abbiamo scritto prima di vederlo.

## 8. La pipeline

| Script | Cosa fa |
|---|---|
| `01_download_data.py` | Prezzi Yahoo (pilota). Non rilanciare |
| `02_validate_data.py` | Controlli sui prezzi (split, dividendi, buchi, outlier...) |
| `03_optimize_ga.py` | Algoritmo genetico del pilota |
| `04_compute_signals.py`, `05_evaluate_strategy.py` | Segnali e valutazione del pilota |
| `06_download_extra_data.py`, `07_validate_extra_data.py` | Serie macro FRED e loro controlli |
| `08_make_figures.py` | Grafici del pilota e dei regimi macro (`data/figures/`) |
| `09_download_bloomberg.py` | Solo sul PC del terminale Bloomberg |
| `10_clean_bloomberg.py` | Una serie per società, controlli, tabelle settimanali, indicatori |
| `11_eda_bloomberg.py` | Analisi esplorativa dell'universo |
| `12_optimize_longshort.py` | Pesi della strategia finale (solo training) |
| `13_evaluate_longshort.py` | Training, validation e Out-of-Sample della strategia finale: **da lanciare una volta sola**, sui dati definitivi |

Codice condiviso in `src/`:
- `backtest`, `metrics`, `ensemble` e `genetic`: pilota e algoritmo genetico;
- `data` e `validation`: download e controlli dei dati;
- `bloomberg`, `features` e `longshort`: universo dei semiconduttori e strategia finale;
- `style`: stile dei grafici.

## 9. Cosa manca e chi decide

1. **File Bloomberg definitivi:** `membership.csv`, `meta.csv`, nuovi `prices.parquet` e `benchmark_sox.parquet`. Poi `10`, `12` (circa 8 minuti) e `13`.
2. **PDF di "Which reversals to trust"**, per verificare che il nostro risultato (i rialzi di giorno si invertono, quelli di notte continuano) corrisponda al paper prima di citarlo.
3. **Presentazione:** chi la prepara, numero di gruppo, data (17 o 19), ruoli di ognuno per il contribution statement, strumenti di AI usati (Claude Code, da dichiarare).
4. **Impegno del gruppo:** i risultati di validation e Out-of-Sample si riportano così come sono, senza ritocchi.
5. **Opzionale:** rendere privata la repo GitHub, così i dati Bloomberg possono stare nella repo.

## 10. Insidie del testo d'esame e come le gestiamo

| Insidia | Come la gestiamo |
|---|---|
| Lookahead | Indicatori con i soli dati fino al venerdì (la notte del weekend appartiene alla settimana dopo); esecuzione all'apertura successiva; periodi separati secondo il giorno in cui si realizza il rendimento |
| Overfitting | Parametri scelti solo sul training, media di 5 run, controllo con la ricerca casuale, validation solo per valutare |
| Survivorship | Pilota: presente e dichiarato. Finale: risolto con la composizione storica del SOX, società fallite e acquisite incluse |
| Data snooping | Ogni tentativo e ogni modifica nel log, con la data, prima dei risultati; Out-of-Sample aperto una volta sola |
| Leakage da modelli pre-addestrati | Non applicabile: nessun modello pre-addestrato |
