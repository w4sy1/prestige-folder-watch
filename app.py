from pathlib import Path
import json
import sqlite3
import sys
import time
from runtime import digest,entry,files,now,parser

def snapshot(root):
    root=Path(root).resolve();result={}
    for p in files(root):
        before=p.stat();value=digest(p);after=p.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Katalog zmieniał się w trakcie próbkowania.')
        result[p.relative_to(root).as_posix()]={'sha256':value,'size':after.st_size,'mtime_ns':after.st_mtime_ns,'inode':after.st_ino}
    return result

def changes(before,after):
    removed=set(before)-set(after);added=set(after)-set(before);events=[]
    for old in sorted(removed.copy()):
        candidates=[new for new in added if before[old]['inode'] and before[old]['inode']==after[new]['inode'] and before[old]['sha256']==after[new]['sha256']]
        if len(candidates)==1:
            new=candidates[0];events.append({'type':'rename','path':new,'old_path':old,'sha256':after[new]['sha256']});removed.remove(old);added.remove(new)
    for path in sorted(removed):events.append({'type':'delete','path':path,'sha256':None})
    for path in sorted(added):events.append({'type':'create','path':path,'sha256':after[path]['sha256']})
    for path in sorted(before.keys()&after.keys()):
        if before[path]['sha256']!=after[path]['sha256'] or before[path]['mtime_ns']!=after[path]['mtime_ns']:events.append({'type':'modify','path':path,'sha256':after[path]['sha256']})
    return events

def watch(root,database,cycles,interval):
    root=Path(root).resolve();database=Path(database).resolve()
    if database.is_relative_to(root):raise ValueError('SQLite musi być poza obserwowanym katalogiem.')
    db=sqlite3.connect(database)
    try:
        db.executescript('CREATE TABLE IF NOT EXISTS metadata(root TEXT);CREATE TABLE IF NOT EXISTS state(path TEXT PRIMARY KEY,data TEXT);CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,timestamp TEXT,type TEXT,path TEXT,old_path TEXT,sha256 TEXT);')
        owner=db.execute('SELECT root FROM metadata').fetchone()
        if owner and owner[0]!=str(root):raise ValueError('Ta baza należy do innego katalogu.')
        before={path:json.loads(data) for path,data in db.execute('SELECT path,data FROM state')}
        if owner is None:
            before=snapshot(root)
            with db:
                db.execute('INSERT INTO metadata VALUES(?)',(str(root),))
                db.executemany('INSERT INTO state VALUES(?,?)',[(k,json.dumps(v)) for k,v in before.items()])
        all_events=[]
        for _ in range(cycles):
            time.sleep(interval);after=snapshot(root);events=changes(before,after)
            with db:
                for e in events:db.execute('INSERT INTO events(timestamp,type,path,old_path,sha256) VALUES(?,?,?,?,?)',(now(),e['type'],e['path'],e.get('old_path'),e['sha256']))
                db.execute('DELETE FROM state');db.executemany('INSERT INTO state VALUES(?,?)',[(k,json.dumps(v)) for k,v in after.items()])
            all_events.extend(events);before=after
        return {'events':all_events,'database':str(database)}
    finally:db.close()

def build():
    p=parser('Monitor plików; obserwacja nie wykonuje zmian w katalogu źródłowym.')
    p.add_argument('--root');p.add_argument('--database',default='watch.sqlite');p.add_argument('--cycles',type=int,default=1);p.add_argument('--interval',type=float,default=2)
    return p

def handle(a):
    if not a.root or not 1<=a.cycles<=100000 or a.interval<.1:raise ValueError('Nieprawidłowe argumenty.')
    return watch(a.root,a.database,a.cycles,a.interval)

if __name__=='__main__':sys.exit(entry(build,handle))
