# Manutenzione di fm

File manager TUI a pannello singolo per Linux. Il sorgente e punto di ingresso è `fm`, uno script Bash 4+ che usa stty, comandi GNU e /dev/tty. Non richiede librerie TUI.

Lo script gestisce input tastiera e mouse, stato della selezione e appunti, rendering e operazioni sui file. Ripristina il terminale alla chiusura. Conservare la conferma per la cancellazione permanente e il divieto di sovrascrivere destinazioni esistenti. Le variabili pubbliche ABFM_NO_ALT_SCREEN, ABFM_NO_COLOR e ABFM_ASCII sono documentate nel README.

Modificare `fm` per il comportamento, `README.md` per uso e installazione, `tests/smoke.py` per verifiche PTY. `.github/workflows/test.yml` esegue i controlli su GitHub. Installazione utente: `install -Dm755 fm "$HOME/.local/bin/fm"`.

Prima di completare una modifica eseguire dalla radice:

```bash
bash -n fm
python3 tests/smoke.py
```

Per una verifica manuale eseguire `./fm` in un terminale interattivo, quindi F10 per uscire. I test usano Python 3 standard e directory temporanee. Controllare il diff e aggiornare questa guida e il README quando cambiano struttura, opzioni pubbliche, invarianti o comandi di verifica.
