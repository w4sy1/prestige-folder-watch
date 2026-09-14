# Użycie

`python app.py --root ./dane --database ./watch.sqlite --cycles 100 --interval 2`
SQLite musi być poza źródłem. Stan jest zachowywany między uruchomieniami.
Przy pierwszym uruchomieniu tworzony jest stan odniesienia; następnie wykonywane są próbki.

Domyślny backend używa pollingu. Krótkotrwałe create/delete między próbkami mogą być niewidoczne.
Rename rozpoznawany jest na podstawie zgodnego identyfikatora pliku i hash; inne przypadki
mogą być create/delete. Symlinki/junctions są pomijane. Duże katalogi mogą skanować się
dłużej niż interval; nie ma gwarancji obserwacji w czasie rzeczywistym.

## Rozszerzenia 0.2.0

`python app.py --root C:/Dane --database C:/Raporty/watch.sqlite --backend native --cycles 30 --interval 2`
obserwuje Windows przez 60 sekund za pomocą FileSystemWatcher. Obsługuje create/modify/delete/rename,
także krótkotrwałe pliki. Czas pojedynczego wywołania native: maksymalnie 3600 sekund.
Hash jest odczytywany po okresie obserwacji, więc brak pliku daje UNKNOWN; nie odtwarza historycznej treści.
Overflow oznacza możliwe utracone zdarzenia i kod błędu. Linux korzysta z pollingu.
Test lokalny Windows potwierdził create i delete dla chwilowych plików próbnych.
