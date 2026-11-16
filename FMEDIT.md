# fmedit

Piccolo editor da terminale scritto in Bash, ispirato a Zepto. Un solo script,
senza compilazione e senza ncurses, per file di testo e script di shell.

Incluso nel [repository fm](https://github.com/vroby65/fm). Consultare
[README.md](README.md) per installare entrambi i programmi e usare fmedit con F4.
Sorgente importato da `vroby65/fmedit`, branch `italiano`, commit
`acc4550ae482051fc73eec46eb96185faf1a58ba`.
Il sorgente attualmente presente nel branch di origine ha interfaccia e conferme
in inglese, come quello di `main`.

## Avvio e installazione

```bash
./fmedit appunti.txt
./fmedit                 # nuovo buffer senza nome
./fmedit -- -nome-file   # nome che inizia con un trattino
install -Dm755 fmedit "$HOME/.local/bin/fmedit"
```

Ripetere il comando di installazione dopo aver aggiornato il checkout.
Richiede Bash 4+, un terminale ANSI/VT e `stty`, `mktemp`, `cp`, `mv`, `rm`.
Per salvare attraverso un collegamento simbolico serve anche `readlink -f`.
Python non serve durante l'esecuzione. Sviluppato e verificato su Linux.

## Comandi

| Tasto | Azione |
| --- | --- |
| F1 | Aiuto |
| F2 / Ctrl+S | Salva; chiede il nome per un nuovo buffer |
| F10 | Salva ed esce |
| Esc / Ctrl+Q | Esce; se modificato, chiede se salvare, scartare o annullare |
| Frecce, Home, End, PgUp, PgDown | Sposta il cursore |
| Ctrl+Home / Ctrl+End | Inizio / fine documento |
| Shift+frecce, Shift+Home/End | Seleziona testo |
| Ctrl+A | Seleziona tutto |
| Ctrl+C / Ctrl+X / Ctrl+V | Copia / taglia / incolla con appunti interni |
| Ctrl+Z / Ctrl+Y | Annulla / ripeti le ultime 100 modifiche |
| F7 / Ctrl+F | Cerca testo letterale, distinguendo maiuscole e minuscole |
| Ctrl+N | Trova l'occorrenza successiva, ripartendo dall'inizio |

Nei prompt, digitare la risposta e premere Invio; Esc annulla. Con modifiche non
salvate, `s` salva, `d` scarta e Invio annulla l'uscita. La sovrascrittura richiede
`y` oppure `Y`; una risposta vuota annulla. Il terminale deve inoltrare i tasti:
alcune applicazioni intercettano i tasti funzione o Shift+frecce.

## Comportamento

- Palette come fm: sfondo grigio scuro, testo giallo tenue e selezione petrolio.
- Numeri di riga, scorrimento verticale/orizzontale e indicatore di modifica.
  Un indice evita di scandire il documento a ogni movimento; il rendering legge
  direttamente le righe visibili.
- Undo/redo conserva intervalli sostituiti e inseriti per 100 modifiche, senza
  copiare tutto il documento a ogni carattere.
- Colori di base per commenti, stringhe e `$` nei file `.sh` e `.bashrc`, limitati
  alla riga corrente.
- L'incolla bracketed del terminale conta come una modifica; i tasti di controllo
  incollati non eseguono comandi dell'editor.
- UTF-8 secondo la locale Bash; tabulazioni ogni quattro colonne.
- Conserva esattamente il testo, inclusi newline finale e terminatori CRLF.
  Rifiuta file contenenti byte NUL.
- Salva con un temporaneo nella cartella di destinazione e rinomina finale;
  conserva i permessi esistenti, usa `0600` per nuovi file e segue i link simbolici
  senza sostituirli.
- Ripristina terminale, cursore e schermo all'uscita e con HUP, INT e TERM.
  Le modifiche non salvate restano soltanto in memoria.

## Limiti

Il buffer è una stringa Bash e l'indice viene ricostruito dopo le modifiche:
file grandi e righe lunghe possono risultare lenti. Selezioni grandi nella
cronologia consumano memoria; ogni carattere digitato è una voce della cronologia.
Emoji, caratteri larghi e segni combinanti possono disallineare il cursore.
I caratteri di controllo nei file sono visualizzati come `?`, senza inviarli
al terminale.

Non sono implementati mouse, buffer multipli, sostituzione del testo o appunti
di sistema. Il salvataggio sostituisce l'inode: gli hard link continuano a puntare
alla versione precedente. Non gestisce modifiche concorrenti di altri programmi
e non garantisce persistenza in caso di interruzione dell'alimentazione.

## Verifica

I test richiedono Python 3 e usano soltanto la libreria standard:

```bash
bash -n fmedit
python3 -m unittest discover -s tests -p test_editor.py -v
```

Coprono buffer, conservazione dei file e sessioni PTY reali per scorciatoie,
incolla, prompt e ripristino del terminale. Verificano navigazione e modifica
su 40.000 righe senza comandi esterni, salvataggio di 10.000 righe UTF-8/CRLF,
aiuto inglese, sovrascrittura e salvataggio/scarto all'uscita.
