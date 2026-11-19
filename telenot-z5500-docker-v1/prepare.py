#!/usr/bin/env python3
"""Erstellt nur lokale Laufzeitkonfiguration; keine Alt-Lizenzen, Benutzer oder Passwörter."""
from pathlib import Path
import os, re, secrets, stat

root = Path(__file__).resolve().parent
env = root / '.env'
os.umask(0o077)
if env.is_symlink():
    raise SystemExit('FEHLER: .env darf kein Symlink sein')
if not env.exists():
    d = {
        'TELENOT_V1_DEPLOYMENT_ID': secrets.token_hex(16),
        'DB_PASSWORD': secrets.token_hex(32),
        'MQ_USER': 'telenotv1',
        'MQ_PASSWORD': secrets.token_hex(32),
        'WEB_BIND_IP': '127.0.0.1',
        'WEB_LOCAL_PORT': '18081',
    }
    with env.open('x', encoding='utf8') as f:
        for k, v in d.items():
            f.write(f'{k}={v}\n')
    env.chmod(0o600)
    print('Neue lokale Zugangsdaten erstellt; .env nicht weitergeben.')
else:
    if env.stat().st_mode & 0o077:
        raise SystemExit('FEHLER: chmod 600 .env ausführen')
    d = {}
    for s in env.read_text(encoding='utf8').splitlines():
        if not s.strip() or s.startswith('#'): continue
        if '=' not in s: raise SystemExit('Ungültige .env-Zeile')
        k, v = s.split('=', 1)
        if k in d: raise SystemExit('Doppelter .env-Eintrag')
        d[k] = v
    if not re.fullmatch('[0-9a-f]{32}', d.get('TELENOT_V1_DEPLOYMENT_ID', '')):
        raise SystemExit('FEHLER: Keine V1-Installationsdatei .env')
    for k in ('DB_PASSWORD', 'MQ_PASSWORD'):
        if not re.fullmatch('[0-9a-f]{64}', d.get(k, '')):
            raise SystemExit('FEHLER: Ungültiges ' + k)
    print('Vorhandene V1-Zugangsdaten unverändert.')
conn = '\n'.join((
    'driverClass=org.postgresql.Driver',
    'jdbcUrl=jdbc:postgresql://db:5432/compasz5500',
    'user=compasz',
    'password=' + d['DB_PASSWORD'],
    'hibernate.dialect=org.hibernate.dialect.PostgreSQL95Dialect',
    'hibernate.default_schema=public', '',
))
mq = '\n'.join((
    'eu.inform.mq.MessageQueueClient.host=mq:61616',
    'eu.inform.mq.MessageQueueClient.user=' + d['MQ_USER'],
    'eu.inform.mq.MessageQueueClient.password=' + d['MQ_PASSWORD'],
    'eu.inform.mq.MessageQueueClient.ssl.enabled=false',
    'eu.inform.mq.MessageQueueClient.highAvailability=false',
    'eu.inform.mq.MessageQueueClient.inVM=false', '',
))
for role in ('web', 'comm', 'sched'):
    folder = root / 'runtime' / (role + '-config')
    if folder.is_symlink():
        raise SystemExit('Symlink nicht erlaubt: ' + str(folder))
    folder.mkdir(parents=True, exist_ok=True)
    os.chown(folder, 10001, 10001)
    folder.chmod(0o700)
    for name, value in (('connection.properties', conn), ('mq.properties', mq)):
        path = folder / name
        if path.is_symlink():
            raise SystemExit('Symlink nicht erlaubt: ' + str(path))
        if path.exists():
            if path.read_text(encoding='utf8') != value:
                raise SystemExit('Konflikt: ' + str(path) + ' - kein Überschreiben')
        else:
            with path.open('x', encoding='utf8') as f: f.write(value)
            path.chmod(0o600)
            os.chown(path, 10001, 10001)
    if role != 'web':
        for suffix in ('home', 'app-config'):
            path = root / 'runtime' / (role + '-' + suffix)
            if path.is_symlink(): raise SystemExit('Symlink nicht erlaubt')
            path.mkdir(parents=True, exist_ok=True)
            os.chown(path, 10001, 10001)
            path.chmod(0o700)
print('Konfiguration für die fünf TELENOT-Dienste vorbereitet.')
