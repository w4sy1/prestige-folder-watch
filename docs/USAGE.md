# Użycie

`python app.py --root ./dane --database ./watch.sqlite --cycles 100 --interval 2`
SQLite musi być poza źródłem. Stan jest zachowywany między uruchomieniami.
Przy pierwszym uruchomieniu tworzony jest stan odniesienia; następnie wykonywane są próbki.

MVP używa pollingu. Krótkotrwałe create/delete między próbkami mogą być niewidoczne.
Rename rozpoznawany jest na podstawie zgodnego identyfikatora pliku i hash; inne przypadki
mogą być create/delete. Symlinki/junctions są pomijane. Duże katalogi mogą skanować się
dłużej niż interval; nie ma gwarancji obserwacji w czasie rzeczywistym.
