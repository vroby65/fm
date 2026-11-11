# Manutenzione di fm

File manager TUI a uno o due pannelli per Linux. Il sorgente e punto di ingresso è `fm`, uno script Bash 4+ che usa stty, comandi GNU e /dev/tty. Non richiede librerie TUI.

Lo script gestisce input tastiera e mouse, stato della selezione, rendering e operazioni sui file. Ripristina il terminale alla chiusura. Conservare la conferma per la cancellazione permanente e il divieto di sovrascrivere destinazioni esistenti. Le variabili pubbliche ABFM_NO_ALT_SCREEN, ABFM_NO_COLOR e ABFM_ASCII sono documentate nel README.

F2 rinomina, F3 seleziona, F4 apre `$EDITOR` (fallback nano), F5 copia e F6 sposta nel pannello opposto (con un solo pannello chiedono la cartella di destinazione), F7 crea cartelle, F8 cancella dopo conferma, F10 esce. Ctrl+X C apre chmod, Ctrl+X O apre chown; Ctrl+S crea un link assoluto `<nome>.lnk`. Durante la TUI `ixon` è disabilitato per ricevere Ctrl+S; editor e programmi figli ricevono il terminale originale.

Da 100 colonne vengono mostrati due pannelli. Tab o mouse cambia lato; `save_pane`/`load_pane` conservano cartella, cursore, scorrimento, filtro, visibilità dei nascosti e marcature. `draw_panel` usa stato locale Bash per disegnare anche il lato inattivo senza alterare quello attivo. Ctrl+F filtra per sottostringa letterale senza distinzione maiuscole/minuscole; vuoto ripristina tutto e `/..` resta disponibile. Ctrl+H mostra/nasconde file e cartelle con nome che inizia per punto nel pannello attivo (visibili all’avvio); azzera la selezione e mantiene il filtro. Ctrl+H usa il byte 0x08; Backspace per navigare usa 0x7f. Il resize conserva lo stato dei due pannelli.

Modificare `fm` per il comportamento, `README.md` per uso e installazione, `tests/smoke.py` per verifiche PTY. `.github/workflows/test.yml` esegue i controlli su GitHub. Installazione utente: `install -Dm755 fm "$HOME/.local/bin/fm"`.

Prima di completare una modifica eseguire dalla radice:

```bash
bash -n fm
python3 tests/smoke.py
```

Per una verifica manuale eseguire `./fm` in un terminale interattivo, quindi F10 per uscire. I test usano Python 3 standard e directory temporanee. Controllare il diff e aggiornare questa guida e il README quando cambiano struttura, opzioni pubbliche, invarianti o comandi di verifica.
