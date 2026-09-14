"""Windows FileSystemWatcher bridge; events carry unknown hashes for vanished files."""
import os
from pathlib import Path
import sqlite3
from runtime import digest,inside,now,powershell


def collect(root,duration):
    if os.name!='nt':raise ValueError('Backend native obecnie wymaga Windows. Użyj polling na Linux.')
    root=Path(root).resolve()
    if not root.is_dir() or not .1<=duration<=3600:raise ValueError('Katalog i czas 0.1–3600 sekund są wymagane.')
    escaped=str(root).replace("'","''")
    script=r'''$watcher=[IO.FileSystemWatcher]::new('ROOT')
$watcher.IncludeSubdirectories=$true
$watcher.InternalBufferSize=65536
$watcher.NotifyFilter=[IO.NotifyFilters]'FileName,DirectoryName,LastWrite,Size'
$prefix='Prestige-'+[guid]::NewGuid().ToString('N')
$rows=[Collections.Generic.List[object]]::new();$overflow=$false
try{
 foreach($kind in @('Created','Changed','Deleted','Renamed','Error')){Register-ObjectEvent -InputObject $watcher -EventName $kind -SourceIdentifier ($prefix+'-'+$kind)|Out-Null}
 $watcher.EnableRaisingEvents=$true
 $until=[DateTime]::UtcNow.AddSeconds(DURATION)
 while([DateTime]::UtcNow -lt $until){
  foreach($event in @(Get-Event | Where-Object {$_.SourceIdentifier.StartsWith($prefix)})){
   $kind=$event.SourceIdentifier.Substring($prefix.Length+1)
   if($kind -eq 'Error'){$overflow=$true}
   elseif($rows.Count -lt 100000){$argument=$event.SourceEventArgs;$rows.Add([pscustomobject]@{kind=$kind;path=$argument.Name;old_path=$(if($kind -eq 'Renamed'){$argument.OldName}else{$null});timestamp=$event.TimeGenerated.ToUniversalTime().ToString('o')})}
   else{$overflow=$true}
   Remove-Event -EventIdentifier $event.EventIdentifier
  }
  Start-Sleep -Milliseconds 20
 }
}finally{
 $watcher.EnableRaisingEvents=$false
 foreach($kind in @('Created','Changed','Deleted','Renamed','Error')){Unregister-Event -SourceIdentifier ($prefix+'-'+$kind) -ErrorAction SilentlyContinue}
 $watcher.Dispose()
}
[pscustomobject]@{events=@($rows);overflow=$overflow}|ConvertTo-Json -Depth 5'''
    return powershell(script.replace('ROOT',escaped).replace('DURATION',str(float(duration))),timeout=int(duration)+30)


def watch(root,database,duration,collector=collect):
    root=Path(root).resolve();database=Path(database).resolve()
    if database.is_relative_to(root):raise ValueError('SQLite musi być poza obserwowanym katalogiem.')
    if not root.is_dir():raise ValueError('Wymagany katalog.')
    db=sqlite3.connect(database)
    try:
        db.executescript('CREATE TABLE IF NOT EXISTS metadata(root TEXT);CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,timestamp TEXT,type TEXT,path TEXT,old_path TEXT,sha256 TEXT);')
        owner=db.execute('SELECT root FROM metadata').fetchone()
        if owner and owner[0]!=str(root):raise ValueError('Ta baza należy do innego katalogu.')
        if owner is None:
            with db:db.execute('INSERT INTO metadata VALUES(?)',(str(root),))
        captured=collector(root,duration);events=[]
        kinds={'Created':'create','Changed':'modify','Deleted':'delete','Renamed':'rename'}
        with db:
            for row in captured['events']:
                if row.get('kind') not in kinds:continue
                relative=Path(row['path']).as_posix();target=inside(root,relative);value=None
                if row.get('old_path'):inside(root,row['old_path'])
                try:
                    if target.is_file() and row['kind']!='Deleted':value=digest(target)
                except OSError:pass
                event={'type':kinds[row['kind']],'path':relative,'old_path':row.get('old_path'),'timestamp':row.get('timestamp',now()),'sha256':value}
                db.execute('INSERT INTO events(timestamp,type,path,old_path,sha256) VALUES(?,?,?,?,?)',(event['timestamp'],event['type'],event['path'],event['old_path'],value))
                events.append(event)
        return {'events':events,'database':str(database),'overflow':captured.get('overflow',False),'ok':not captured.get('overflow',False),
            'note':'Hash odczytany po okresie obserwacji; dla pliku usuniętego lub niedostępnego jest UNKNOWN. System może łączyć zdarzenia; overflow oznacza utratę części zdarzeń.'}
    finally:db.close()
