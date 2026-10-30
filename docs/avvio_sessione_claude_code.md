# Prompt di avvio sessione – Claude Code

Incolla il testo qui sotto come primo messaggio di Claude Code, aperto nella cartella `luiss-trading-strategy-skeleton`.
Prima compila le righe tra parentesi quadre: se lasci un campo vuoto, Claude Code deve chiedertelo, non inventarlo.

---

Stiamo lavorando al progetto di gruppo di "Data-Driven Models for Investment 2026-27" (LUISS). Consegna il 16 novembre alle 23:59.

Prima di tutto, in quest'ordine:
1. Leggi `resources/instructions.pdf` (testo d'esame), `README.md`, `config.yaml`, `docs/metrics.md`, `docs/experiment_log.md` e `docs/prompt_fase1_dati.md`.
2. Elenca gli script e i moduli in `src/` e riassumi in 10 righe cosa fanno davvero, leggendo il codice e non solo i nomi dei file.
3. Usa le skill del progetto quando servono:
   - `ddmi-bias-guard` prima di calcolare segnali, fare backtest o mostrare qualsiasi risultato;
   - `ddmi-data-pipeline` per scaricare, salvare e validare prezzi e bilanci;
   - `ddmi-submission-check` quando chiedo di controllare la consegna o la presentazione.

Le mie risposte alle domande aperte:
- Il lavoro in `docs/experiment_log.md` (GA, OOS aperto il 2026-10-01) è: [nostro / esempio del docente]
- Accesso a Bloomberg Terminal: [sì / no]; accesso a WRDS/Compustat: [sì / no]
- Universo di titoli: [restare su AAPL, MSFT, AMZN, GOOG / allargare: come]
- Fine del campione: [2026-09-25 / altra data]
- Bonus a cui puntiamo: [nessuno / market-neutral / Sharpe superiore]
- Gruppo: [numero di persone e chi fa cosa]

Obiettivo di questa sessione: la Fase 1 descritta in `docs/prompt_fase1_dati.md` (dati storici di prezzi e bilanci, point-in-time, 2004–2026).

Regole per tutta la sessione:
- Non scrivere codice nella prima risposta. Dammi il riassunto della repo, la tabella delle fonti candidate, 2–3 opzioni di universo, un piano a passi con stima dei tempi e le domande che restano.
- Lavoriamo un passo alla volta: per ogni passo mi proponi il piano e i file che toccherai, aspetti il mio ok, esegui, verifichi e ti fermi.
- Non toccare il periodo Out-of-Sample e non mostrarmi metriche OOS finché non lo dico esplicitamente.
- Non inventare numeri, date, URL, nomi di campi o tag XBRL. Se non l'hai verificato con uno strumento, scrivi "NON VERIFICATO".
- Se un'informazione manca, fermati e chiedimela.
- Contraddicimi quando propongo qualcosa di metodologicamente debole.
- Rispondi in italiano; codice, nomi di file e commenti in inglese.
