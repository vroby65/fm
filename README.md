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

Il pannello usa uno **sfondo grigio scuro con testo giallo tenue** (ANSI 256 colori). La riga attiva ha sfondo verde petrolio e testo chiaro. Eseguibili, collegamenti simbolici ed elementi marcati mantengono colori distintivi.

Ogni pannello mostra le colonne **Nome**, **Dimensione** e **Ultima modifica**, con intestazioni giallo acceso come in Midnight Commander. La dimensione è in byte (unità IEC per valori oltre dieci cifre); per le directory è la dimensione della voce, senza sommare il contenuto. La data di modifica usa il formato `gg/mm/aaaa hh:mm` e il fuso orario locale. I nomi lunghi vengono troncati per mantenere allineate le colonne. I separatori verticali proseguono anche sulle righe vuote, fino al fondo del pannello.

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
| **F1** | Apre il menu comandi personale di Midnight Commander |
| **F2** | Apre la finestra Rinomina per il file o la cartella evidenziata |
| **F3** / Spazio | Seleziona o deseleziona il file corrente (`*`) |
| **F4** | Edita il file evidenziato con `$EDITOR`, oppure `nano` se non impostato |
| **F5** | Copia la selezione nel pannello opposto; con un solo pannello chiede la destinazione |
| **F6** | Sposta la selezione nel pannello opposto; con un solo pannello chiede la destinazione |
| **F7** | Crea directory (digitare il nome e premere Invio) |
| **F8** | Elimina file e directory selezionati, dopo conferma (`s`) |
| **F10** | Esce dal file manager e ripristina il terminale (`q` e `Q` non chiudono) |
| **Ctrl+X**, poi **C** | Apre la finestra unificata per permessi, proprietario e gruppo |
| **Ctrl+X**, poi **S** | Crea un link simbolico, come Ctrl+S |
| **Tab** | Passa al pannello opposto quando visibile |
| **Ctrl+H** | Mostra o nasconde file e cartelle nascosti nel pannello attivo |
| **Ctrl+F** | Cerca mentre digiti nel pannello attivo; Invio apre il risultato |
| **Ctrl+S** | Crea nella cartella corrente un link simbolico assoluto chiamato `<nome>.lnk` |
| ↑ / ↓, `j` / `k` | Muovi il cursore |
| PagSu / PagGiù, Home / End | Scorrimento veloce |
| **Freccia destra** / Invio / `l` | Entra nella directory, oppure avvia un file eseguibile |
| **Freccia sinistra** / Backspace / `h` | Risale evidenziando la cartella appena lasciata |
| Mouse sinistro | Seleziona la riga; un doppio click apre una directory oppure esegue il file avviabile |
| Click sull'indicatore di selezione (colonna 3) | Seleziona o deseleziona l'elemento; il bordo esterno non è cliccabile |
| Rotella mouse | Scorre l'elenco |
| Click sulla barra F2–F10 | Attiva la relativa funzione, anche nella barra compatta |
| `r` | Aggiorna |

Le directory appaiono prima dei file e hanno **`/` davanti al nome** (per esempio `/Documenti`), secondo la convenzione visiva di MC. I file e le directory **nascosti (`.nome`) sono visibili per impostazione predefinita**; **Ctrl+H** ne alterna la visibilità nel pannello attivo. Il simbolo `@` indica un collegamento simbolico. La riga `/..` permette di tornare al livello precedente. Durante la sessione, ogni cartella ricorda la riga evidenziata, lo scorrimento e i file marcati con F3/Spazio: uscendo e rientrando vengono ripristinati. La memoria è separata per i due pannelli e funziona anche nella vista singola; i file scomparsi vengono ignorati. Con un solo pannello, F5 e F6 chiedono una cartella di destinazione esistente, con percorso assoluto o relativo alla cartella corrente; Esc annulla. Dopo aver marcato file con F3 in una cartella, si può navigare altrove e usare F5/F6: vengono usati i percorsi assoluti dell’ultima selezione esplicita. In questo caso Invio vuoto sceglie la cartella corrente come destinazione. La selezione viene consumata dopo il tentativo di trasferimento; una sorgente scomparsa viene segnalata senza sostituirla con il file evidenziato nella destinazione. Se non ci sono marcature, operano sull’elemento evidenziato.

## Due pannelli e filtro

Da **100 colonne** in su compaiono automaticamente due pannelli affiancati, inizialmente nella stessa cartella. **Tab** o un clic nell’elenco cambia il lato attivo, indicato da `*` nel titolo. Ogni lato conserva cartella, cursore, scorrimento, selezione, filtro e visibilità dei nascosti. Riducendo la finestra rimane visibile il pannello attivo; allargando ricompaiono entrambi con il loro stato. Se F5/F6 falliscono, la riga di stato mostra il motivo: stessa cartella, nome già presente, destinazione interna alla sorgente o errore restituito da `cp`/`mv`.

Aprire la cartella di destinazione in un pannello, tornare con Tab al pannello sorgente, selezionare con **F3**, quindi premere **F5** per copiare o **F6** per spostare direttamente nell’altro pannello. Non serve un comando Incolla. Entrambi gli elenchi vengono aggiornati dopo l’operazione; le destinazioni esistenti non vengono sovrascritte.

**Ctrl+F** avvia la ricerca nel pannello attivo: l’elenco si aggiorna **a ogni carattere**, senza distinguere maiuscole e minuscole. Il testo è letterale, compresi gli spazi; Backspace cancella l’ultimo carattere. **Su/Giù** scorrono i risultati e **Invio** entra subito nella cartella evidenziata oppure avvia il file eseguibile. Se non ci sono corrispondenze, Invio mantiene la ricerca aperta. **Esc** rimuove il filtro conservando l’elemento evidenziato; anche il testo vuoto mostra tutto. Durante la ricerca i caratteri stampabili (inclusi `q`, `j`, `k` e Spazio) fanno parte del nome cercato. Clic su una riga, F3, apertura e comandi operativi rimuovono il filtro conservando elemento e marcature; cambiando il testo del filtro si azzerano le marcature del pannello.

Risalendo con **Sinistra**, Backspace o la voce `/..`, il cursore torna sulla cartella da cui si proviene. Lo scorrimento si adatta per mantenerla visibile anche negli elenchi lunghi. Rientrando in una cartella già visitata si ritrovano invece il file evidenziato e le marcature precedenti. **Destra** continua ad aprire la cartella evidenziata.

## Questo PC, SSH e FTP

Alla radice `/`, **Sinistra**, Backspace o l’apertura di `/..` portano al menu **Connessioni**, che inizia con tre voci:

- **Questo PC** torna alla radice del filesystem locale.
- **SSH** apre una connessione **SFTP su SSH**.
- **FTP** apre una connessione FTP.

Invio, Destra o doppio clic aprono la voce. Per SSH/FTP una finestra chiede **`utente@host`** (anche `utente@host:porta`) e **password**, visualizzata mascherata. Lasciare la password vuota per riutilizzare quella salvata nel portachiavi; per SSH sono disponibili anche le chiavi configurate in OpenSSH o nell’agente. La prima verifica dell’identità SSH, se richiesta, mostra impronta e scelte nel terminale: la fiducia nell’host deve essere confermata dall’utente. Esc annulla la finestra; Ctrl+C interrompe una connessione in corso.

Dopo un collegamento riuscito la connessione compare sotto queste tre voci, anche ai successivi avvii. **F2** ne modifica il nome; **F8** la elimina dall’elenco dopo conferma. L’eliminazione riguarda solo la voce salvata e non disconnette il mount né cancella file remoti. Questo PC, SSH e FTP rimangono sempre disponibili. Invio, Destra o doppio clic su una connessione salvata riaprono il dialog con l’indirizzo compilato e la password vuota. Riconnettersi allo stesso indirizzo non crea duplicati e conserva il nome scelto.

Le connessioni salvate contengono soltanto protocollo, indirizzo e nome, in `${XDG_CONFIG_HOME:-$HOME/.config}/fm/connections/`, con permessi 0600. Gli ultimi indirizzi della versione precedente vengono importati una volta; le voci eliminate non vengono ricreate automaticamente.

Dopo un collegamento riuscito viene ricordato l’ultimo indirizzo per protocollo nei file `${XDG_CONFIG_HOME:-$HOME/.config}/fm/last-ssh` e `last-ftp`, con permessi 0600. **La password non viene scritta nei file di fm, negli argomenti dei processi o nelle variabili d’ambiente**: passa tramite un descrittore anonimo e GVfs la conserva nel **portachiavi di sistema**, usando [PasswordSave.PERMANENTLY](https://docs.gtk.org/gio/enum.PasswordSave.html). Aprendo nuovamente il dialog, l’indirizzo è già compilato e la password è vuota. Il campo vuoto non mostra il segreto: GVfs lo recupera dal portachiavi durante la connessione. Il portachiavi deve essere disponibile e sbloccato; può chiedere lo sblocco con il suo dialog. Se non è disponibile, la connessione con password digitata resta possibile ma fm non crea copie in chiaro. Per gestire o eliminare le credenziali usare Password e chiavi (Seahorse); F8 elimina soltanto la voce dall’elenco di fm.

Le cartelle remote si navigano come quelle locali; dalla radice remota Sinistra torna a Connessioni. I pannelli possono mostrare contemporaneamente cartelle locali e remote, con selezione, F5/F6 e gli altri comandi sui file. Su FTP la copia trasferisce i contenuti senza richiedere la conservazione di attributi Unix; uno spostamento tra mount diversi elimina l’origine soltanto dopo una copia riuscita. Valgono i permessi dell’utente remoto: un rifiuto del server non richiede sudo locale. Le connessioni sono mount della sessione GVfs, condivisibili con le altre applicazioni, e possono rimanere attive dopo l’uscita da fm.

Il supporto remoto opzionale richiede **`/usr/bin/python3`, `python3-gi`, `gvfs-backends`, `gvfs-fuse`**, FUSE e un bus D-Bus utente attivo. Su questo PC sono già disponibili. Il filesystem locale continua a funzionare senza queste dipendenze.

## Menu comandi su F1

**F1** apre il menu personale di MC da `${XDG_CONFIG_HOME:-$HOME/.config}/mc/menu`, oppure quello di sistema `/etc/mc/mc.menu`. Le voci e le loro personalizzazioni sono lette a ogni apertura: sono disponibili anche installazione `.deb`, touch e ZIP se presenti nel proprio menu. I programmi richiesti dalle singole voci devono essere installati.

**Su/Giù**, **PgUp/PgDn**, **Home/End** scelgono una voce; **Invio**, il suo carattere di scelta rapida o il pulsante **Esegui** la avviano. Il mouse permette selezione, doppio clic, rotella e pulsanti. **Esc** annulla. Il menu filtra le voci secondo le condizioni MC su nome, directory, tipo di file, selezione e disponibilità degli eseguibili, rispettando `shell_patterns=0/1` e le condizioni di scelta predefinita.

Gli script del menu vengono eseguiti con Bash nella directory del pannello attivo. Sono supportate le macro `%f`/`%p` (file corrente), `%d` (directory), `%s` (marcati oppure file corrente), `%t` (marcati), `%u` (marcati da smarcare), le corrispondenti maiuscole per l’altro pannello, `%%` e `%{richiesta}`. I nomi sono protetti per la shell; `%0` e `%1` controllano il quoting come in MC. `%view{...}` invia l’output a `$PAGER` (default `less`); gli altri comandi lasciano il risultato nel terminale e attendono Invio. Le voci che contengono `sudo` mantengono la richiesta di autenticazione del loro script.

## Esecuzione e gestione degli attributi

Premendo **Invio** oppure **freccia destra** su un file regolare con permesso di esecuzione, `fm` lo avvia direttamente, senza usare `eval`. Il programma figlio riceve il terminale normale con **stdin, stdout e stderr**; alla sua uscita il file manager attende Invio prima di ripristinare la TUI. Non apre automaticamente file privi del bit eseguibile.

Le scorciatoie **Ctrl+X C/S** sono *sequenze*: premere `Ctrl+X`, rilasciare, quindi `c` per gli attributi o `s` per il link simbolico. La precedente sequenza Ctrl+X O è rimossa. **Ctrl+S** si preme direttamente.

- **Rinomina**: F2 apre una finestra con nome attuale e campo del nuovo nome già selezionato. Digitare sostituisce il nome; frecce, Home/End, Backspace e Canc permettono di modificarlo, Ctrl+U svuota il campo. **Tab** passa fra campo e pulsanti **Rinomina/Annulla**; Invio conferma, Esc annulla. I pulsanti sono utilizzabili anche con il mouse. Un nome esistente non viene sovrascritto.
- **Permessi e proprietario**: Ctrl+X C apre una sola finestra con nove caselle **r/w/x** (Utente, Gruppo, Altri), immissione ottale e liste **Utenti/Gruppi** da `getent`. **Tab** scorre griglia, utenti, gruppi e pulsanti **Imposta/Annulla**. Nella griglia, le frecce spostano il cursore e **Spazio** cambia una casella; si può digitare un modo come `755` o `0644`. Nelle liste, **Su/Giù**, **PgUp/PgDn**, **Home/End** selezionano le voci; si possono anche digitare nomi, ID o `utente:gruppo`. Il mouse seleziona caselle, voci e pulsanti. Nei terminali bassi Tab alterna griglia e liste nello stesso spazio. **Invio applica soltanto i campi modificati; Esc annulla tutto**.
- Se rinomina, copia, spostamento, creazione di cartelle/link, eliminazione, `chmod` o `chown` restituiscono un errore di autorizzazione, `fm` riprova quel comando con **sudo**, passando temporaneamente al terminale normale. La password viene richiesta e gestita da `sudo`, senza essere letta o conservata da `fm`. **Ctrl+C** annulla la richiesta e riporta al file manager. Gli altri errori, come un utente inesistente, non richiedono sudo. Il risultato dipende dalle autorizzazioni sudo dell’utente. Restano la conferma di eliminazione e il blocco delle sovrascritture. Per gli attributi, proprietario e gruppo vengono applicati prima dei permessi; chmod/chown non sono ricorsivi e chmod salta i link simbolici.
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

Le operazioni locali usano Bash; il supporto remoto opzionale usa Python 3/GIO. La suite PTY usa soltanto la libreria standard Python:

```bash
bash -n fm
python3 tests/smoke.py
```

I test usano uno pseudo-terminale e directory temporanee per controllare filtro, pannelli indipendenti, Tab, ridimensionamento, rinomina, editor interattivo, selezione multipla/copia, spostamento, creazione, link `.lnk`, cancellazione, mancata sovrascrittura, eventi mouse, doppio click, rotella, pulsanti F2–F8 e interazione durante i prompt.

Le prove reali dei protocolli sono separate e facoltative: `tests/remote_integration.py` richiede anche `paramiko`, `pyftpdlib`, `dbus-run-session` e OpenSSH client. Avvia server su loopback con chiavi e directory temporanee, un bus D-Bus separato e un portachiavi disabilitato per i test di base:

```bash
/usr/bin/python3 tests/remote_integration.py
```

Con `--keyring` la stessa prova avvia un portachiavi GNOME temporaneo e verifica salvataggio cifrato, riavvio del portachiavi e riconnessione SSH/FTP senza digitare la password. Richiede anche `gnome-keyring-daemon` e le introspezioni Python `Secret` (`gir1.2-secret-1`); nessuna credenziale o configurazione personale viene utilizzata.

## Licenza

MIT, vedere [LICENSE](LICENSE).
