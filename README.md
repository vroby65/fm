# fm

File manager **TUI a uno o due pannelli**, ispirato ai tasti funzione di Midnight Commander e pensato per una piccola finestra terminale in **ai-bar**.

Il programma è scritto in **Bash 4+**, usa **mouse xterm/SGR**, il **tema grigio grafite** con convenzioni di navigazione simili a Lynx e cornici Unicode box-drawing (`┌─┐`, `│ │`, `└─┘`), con fallback ASCII. **Niente ncurses, dialog, fzf o dipendenze TUI**: su Linux servono soltanto Bash, `stty` e i comandi GNU di base (`cp`, `mv`, `mkdir`, `rm`).

## Installazione rapida (un solo comando)

Per scaricare e installare `fm` nella directory utente `~/.local/bin`, senza `sudo`, senza compilare e senza clonare il repository, esegui:

```bash
mkdir -p "$HOME/.local/bin" && curl -fsSL "https://raw.githubusercontent.com/vroby65/fm/main/fm" -o "$HOME/.local/bin/fm" && chmod +x "$HOME/.local/bin/fm"
```

Esegui subito il programma con:

```bash
"$HOME/.local/bin/fm"
```

Ripetere il comando di installazione scarica la versione aggiornata da `main`. Per il download e' necessario `curl`; il file manager in esecuzione non richiede `curl` ne' librerie TUI. Se `~/.local/bin` e' gia' nel `PATH`, basta digitare `fm` (anche da Fish).

## Avvio

```bash
git clone https://github.com/vroby65/fm.git
cd fm
./fm
./fm "$HOME/Documenti"
```

Per un'installazione personale, dopo aver ottenuto il sorgente:

```bash
install -Dm755 fm "$HOME/.local/bin/fm"
```

L'interfaccia richiede un terminale interattivo di almeno **35 colonne × 12 righe**; la larghezza consigliata è **70+ colonne**. Per un terminale integrato che gestisce già la propria schermata:

```bash
ABFM_NO_ALT_SCREEN=1 fm
```

Per utilizzare l’interfaccia senza colori o con cornici ASCII:

```bash
ABFM_NO_COLOR=1 fm
ABFM_ASCII=1 fm
```

## Tema grigio e navigazione stile Lynx

Il pannello usa uno **sfondo grigio grafite** (ANSI 256 colori), evitando l'azzurro intenso del tema precedente. La riga attiva e' in grigio chiaro con testo scuro. Restano i colori distintivi per directory, eseguibili, collegamenti simbolici, elementi marcati e la barra F2–F8.

La navigazione prende ispirazione da Lynx:

- **Su / Giu** (o `j` / `k`): sposta la riga evidenziata
- **Destra / Invio** (o `l`): entra nella directory evidenziata
- **Sinistra / Backspace** (o `h`): torna alla directory superiore

Mouse, doppio clic, rotella e funzioni F2–F8 rimangono attivi. Le directory continuano a mostrare il prefisso `/` e i file nascosti sono visibili per impostazione predefinita. Le opzioni `ABFM_NO_COLOR=1` (o `NO_COLOR`) e `ABFM_ASCII=1` permettono di disabilitare i colori e le cornici Unicode.

### Correzione clic ripetuti e locale italiana

Il calcolo dei millisecondi per riconoscere il doppio clic normalizza `EPOCHREALTIME`: accetta **sia la virgola sia il punto decimale**. Questo evita l'errore aritmetico che poteva comparire alla riga 194 con una locale italiana.

## Tasti

| Tasto | Azione |
| --- | --- |
| **F2** | Rinomina il file o la cartella evidenziata (richiede il nuovo nome) |
| **F3** / Spazio | Seleziona o deseleziona il file corrente (`*`) |
| **F4** | Edita il file evidenziato con `$EDITOR`, oppure `nano` se non impostato |
| **F5** | Copia la selezione nel pannello opposto; con un solo pannello chiede la destinazione |
| **F6** | Sposta la selezione nel pannello opposto; con un solo pannello chiede la destinazione |
| **F7** | Crea directory (digitare il nome e premere Invio) |
| **F8** | Elimina file e directory selezionati, dopo conferma (`s`) |
| **F10** | Esce dal file manager e ripristina il terminale |
| **Ctrl+X**, poi **C** | Apre la finestra `chmod` con caselle rwx e immissione ottale |
| **Ctrl+X**, poi **O** | Apre la finestra `chown` con campi proprietario e gruppo |
| **Tab** | Passa al pannello opposto quando visibile |
| **Ctrl+H** | Mostra o nasconde file e cartelle nascosti nel pannello attivo |
| **Ctrl+F** | Filtra i nomi nel pannello attivo; testo vuoto per rimuovere il filtro |
| **Ctrl+S** | Crea nella cartella corrente un link simbolico assoluto chiamato `<nome>.lnk` |
| ↑ / ↓, `j` / `k` | Muovi il cursore |
| PagSu / PagGiù, Home / End | Scorrimento veloce |
| **Freccia destra** / Invio / `l` | Entra nella directory, oppure avvia un file eseguibile |
| **Freccia sinistra** / Backspace / `h` | Torna alla directory superiore (Lynx) |
| Mouse sinistro | Seleziona la riga; un doppio click apre una directory oppure esegue il file avviabile |
| Click sull'indicatore di selezione (colonna 3) | Seleziona o deseleziona l'elemento; il bordo esterno non è cliccabile |
| Rotella mouse | Scorre l'elenco |
| Click sulla barra F2–F10 | Attiva la relativa funzione, anche nella barra compatta |
| `r` | Aggiorna |
| `q` | Esci (alternativa a F10) |

Le directory appaiono prima dei file e hanno **`/` davanti al nome** (per esempio `/Documenti`), secondo la convenzione visiva di MC. I file e le directory **nascosti (`.nome`) sono visibili per impostazione predefinita**; **Ctrl+H** ne alterna la visibilità nel pannello attivo. Il simbolo `@` indica un collegamento simbolico. La riga `/..` permette di tornare al livello precedente. I segni di selezione vengono azzerati quando si cambia directory. Con un solo pannello, F5 e F6 chiedono una cartella di destinazione esistente, con percorso assoluto o relativo alla cartella corrente; Esc annulla. Se non ci sono marcature, operano sull’elemento evidenziato.

## Due pannelli e filtro

Da **100 colonne** in su compaiono automaticamente due pannelli affiancati, inizialmente nella stessa cartella. **Tab** o un clic nell’elenco cambia il lato attivo, indicato da `*` nel titolo. Ogni lato conserva cartella, cursore, scorrimento, selezione, filtro e visibilità dei nascosti. Riducendo la finestra rimane visibile il pannello attivo; allargando ricompaiono entrambi con il loro stato.

Aprire la cartella di destinazione in un pannello, tornare con Tab al pannello sorgente, selezionare con **F3**, quindi premere **F5** per copiare o **F6** per spostare direttamente nell’altro pannello. Non serve un comando Incolla. Entrambi gli elenchi vengono aggiornati dopo l’operazione; le destinazioni esistenti non vengono sovrascritte.

**Ctrl+F** chiede una parte del nome e **Invio** applica il filtro al solo pannello attivo, senza distinguere maiuscole e minuscole. Il testo è letterale, non un’espressione regolare o un glob. Il filtro comprende file e cartelle; `/..` resta sempre disponibile. Per rimuoverlo: Ctrl+F, testo vuoto, Invio. Esc annulla. Cambiare filtro o visibilità dei nascosti azzera la selezione di quel pannello; il filtro si azzera quando si sceglie un elemento con un clic, F3/Spazio, Invio o un comando operativo. L’elemento scelto e le marcature vengono conservati nel nuovo elenco completo. Con le frecce Su/Giù si può continuare a scorrere i risultati senza azzerarlo.

## Esecuzione e gestione degli attributi

Premendo **Invio** oppure **freccia destra** su un file regolare con permesso di esecuzione, `fm` lo avvia direttamente, senza usare `eval`. Il programma figlio riceve il terminale normale con **stdin, stdout e stderr**; alla sua uscita il file manager attende Invio prima di ripristinare la TUI. Non apre automaticamente file privi del bit eseguibile.

Le scorciatoie **Ctrl+X, C/O** sono *sequenze*, non tre tasti tenuti contemporaneamente: premere `Ctrl+X`, rilasciare, quindi `c` oppure `o`. **Ctrl+S** si preme direttamente.

- **chmod** presenta una finestra ispirata a MC con nove caselle **r/w/x** (Utente, Gruppo, Altri) e anteprima dei permessi. Frecce per spostarsi, **Spazio** per cambiare una casella; si possono anche digitare direttamente tre o quattro cifre ottali (per esempio `755` o `0644`). **Invio applica, Esc annulla**. Non è ricorsivo e salta i link simbolici.
- **chown** presenta una finestra con campi **Proprietario** e **Gruppo**, selezionabili con **Tab** o le frecce. Si può anche digitare direttamente `utente:gruppo` nel primo campo. **Invio applica, Esc annulla**. Non è ricorsivo e non usa `sudo`: le modifiche senza privilegi adeguati falliscono in modo controllato.
- **Link simbolico** aggiunge `.lnk` al nome completo dell’elemento evidenziato (per esempio `file.txt.lnk`), nella cartella attuale, con **destinazione assoluta** (per esempio `/home/user/Documenti/file.txt`). Spostare il link in un'altra directory **non ne altera la destinazione**; spostare o cancellare il file originale può comunque romperlo. Non sovrascrive link o file preesistenti.

Le operazioni `chmod` e `chown` si applicano ai file marcati con F3, oppure alla riga corrente se non ci sono marcature. La creazione del link utilizza sempre e soltanto la riga corrente.

F4 passa il terminale all’editor e ripristina la TUI alla sua chiusura. `EDITOR` può contenere il comando e argomenti separati da spazi (per esempio `EDITOR="nano -w"`); non viene interpretato come codice shell. Per usare l’editor serve che sia installato.

## Ridisegno senza sfarfallio

I movimenti del cursore aggiornano soltanto la riga precedente e quella corrente; il terminale non viene cancellato a ogni pressione di tasto. Il ridisegno completo è riservato a cambio di directory, scorrimento, aggiornamento o ridimensionamento. Il bordo in fondo non invia più un ritorno a capo che faceva scorrere lo schermo e poteva sfalsare le coordinate mouse.

## Sicurezza e limiti della versione iniziale

- **Non sovrascrive**: quando il nome di destinazione esiste già, F2, F5 e F6 lasciano invariato l'elemento e lo segnalano come non riuscito.
- F8 esegue una **cancellazione ricorsiva permanente** (`rm -rf`) dopo una conferma esplicita: **non** usa il cestino.
- La copia mantiene i metadati e i link simbolici usando `cp -a` (GNU coreutils). Sposta e rinomina usano `mv`.
- Non si possono copiare directory dentro sé stesse.
- Le directory sono ordinate secondo la locale della shell; il testo è troncato se troppo lungo. Il calcolo della larghezza usa il numero di caratteri Bash, e per caratteri Unicode a doppia larghezza l'allineamento del bordo può risultare imperfetto.
- Invio esegue direttamente i file con permesso di esecuzione; gli altri file normali non vengono aperti.
- Le sequenze dei tasti funzione sono quelle comuni dei terminali xterm e Linux; alcuni terminali grafici possono intercettare F2–F8 e richiedere la riconfigurazione delle scorciatoie.

## Integrazione con ai-bar

Avviare `fm` all'interno di **un PTY** integrato o di un emulatore terminale che supporti le sequenze mouse **xterm SGR (1000/1006)**. Il programma usa `/dev/tty`, la modalità non canonica della tastiera, sequenze ANSI standard e (salvo l'opzione sopra) lo schermo alternativo. Non usa GUI e non necessita dell'ambiente desktop. Per la futura integrazione, si potrà aggiungere una modalità selezione che stampa il percorso scelto su stdout.

## Test

Il funzionamento è verificabile con Python 3 (usato **solo per i test**, non per eseguire il file manager):

```bash
bash -n fm
python3 tests/smoke.py
```

I test usano uno pseudo-terminale e directory temporanee per controllare filtro, pannelli indipendenti, Tab, ridimensionamento, rinomina, editor interattivo, selezione multipla/copia, spostamento, creazione, link `.lnk`, cancellazione, mancata sovrascrittura, eventi mouse, doppio click, rotella, pulsanti F2–F8 e interazione durante i prompt.

## Licenza

MIT, vedere [LICENSE](LICENSE).
