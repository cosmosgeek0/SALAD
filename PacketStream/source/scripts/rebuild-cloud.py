#!/usr/bin/env python3
"""Recreate only the documented Honeygain or PacketStream deployment."""
import argparse
import base64
import getpass
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / '.hg1'
PS_IMAGE = 'docker.io/packetstream/psclient@sha256:6e6a2cefe9f49c33f6c9d4bd41d21daf20c4767f2c66e82f57a5960ec9923987'

def api(key, org, path, method='GET', body=None):
    config = 'header = '+json.dumps('Salad-Api-Key: '+key)+'\nheader = "Content-Type: application/json"\n'
    if body is not None:
        config += 'data-binary = '+json.dumps(json.dumps(body))+'\n'
    result = subprocess.run(['curl','-sS','--max-time','30','--config','-','--request',method,'--write-out','\n%{http_code}',
        'https://api.salad.com/api/public/organizations/'+org+path],input=config,text=True,capture_output=True,timeout=35)
    if result.returncode:
        raise RuntimeError('Salad transport failed')
    raw, code = result.stdout.rsplit('\n',1)
    if not 200 <= int(code) < 300:
        raise RuntimeError(f'Salad {method} {org}{path}: HTTP {code}')
    return json.loads(raw) if raw.strip() else {}

def specifications(protocol, secrets):
    if protocol == 'honeygain':
        spec=importlib.util.spec_from_file_location('hg_control',ROOT/'scripts/hg-fleet-control.py')
        hg=importlib.util.module_from_spec(spec);spec.loader.exec_module(hg)
        return 'deathadder', [dict(name=group,display_name='HG1 Native 0.6.6' if i==0 else 'HG Solo %02d'%(i+1),replicas=1,
            country_codes=['us'],restart_policy='always',autostart_policy=False,
            container=dict(image=hg.IMAGE,command=hg.recovery_command(),image_caching=True,priority='batch' if i==0 else 'low',
                resources=dict(cpu=1,memory=1024,shm_size=64,gpu_classes=[]),
                environment_variables=dict(HONEYGAIN_EMAIL=secrets['email'],HONEYGAIN_PASSWORD=secrets['password'],HONEYGAIN_DEVICE_NAME=hg.DEVICES[i])))
            for i,group in enumerate(hg.GROUPS)]
    code=(ROOT/'packetstream-monitor/start-with-recovery.sh').read_bytes()
    encoded=base64.b64encode(code).decode()
    command=['/bin/bash','-c','umask 077; printf "%s" "$@" | base64 -d > /tmp/ps-self-recovery.sh; exec /bin/bash /tmp/ps-self-recovery.sh',
             'policy-start',*[encoded[i:i+900] for i in range(0,len(encoded),900)]]
    assert len(command)<=100 and max(map(len,command))<=1000
    return 'hyperlane', [dict(name='ps-test-us',display_name='PS Test US',replicas=10,country_codes=['us'],
        restart_policy='always',autostart_policy=False,container=dict(image=PS_IMAGE,command=command,image_caching=True,priority='batch',
            resources=dict(cpu=1,memory=1024,shm_size=64,gpu_classes=[]),environment_variables=dict(CID=secrets['cid'])))]

def verify(actual, desired, compare_account):
    container=actual.get('container',{});expected=desired['container']
    different=[k for k in ('name','display_name','replicas','country_codes','restart_policy','autostart_policy') if actual.get(k)!=desired[k]]
    different += ['container.'+k for k in ('image','command','image_caching') if container.get(k)!=expected[k]]
    different += ['resources.'+k for k,v in expected['resources'].items() if container.get('resources',{}).get(k)!=v]
    if actual.get('priority')!=expected['priority']:different.append('priority')
    different += [k for k in ('networking','readiness_probe','liveness_probe','startup_probe') if actual.get(k) or container.get(k)]
    environment=container.get('environment_variables',{});wanted=expected['environment_variables']
    if set(environment)!=set(wanted) or not all(isinstance(v,str) and v for v in environment.values()):
        different.append('required account environment')
    elif compare_account and environment!=wanted:
        different.append('account environment')
    elif 'HONEYGAIN_DEVICE_NAME' in wanted and environment['HONEYGAIN_DEVICE_NAME']!=wanted['HONEYGAIN_DEVICE_NAME']:
        different.append('Honeygain registration')
    if different:
        raise RuntimeError('Deployment differs in '+', '.join(different)+': '+desired['name']+'; inspect it instead of overwriting it')

def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('protocol',choices=['honeygain','packetstream'])
    p.add_argument('action',choices=['plan','create','bind'])
    args=p.parse_args();os.umask(0o077)
    values=dict(email='<HONEYGAIN_EMAIL>',password='<HONEYGAIN_PASSWORD>',cid='<PACKETSTREAM_CID>')
    if args.action=='create':
        if args.protocol=='honeygain':
            values.update(email=input('Honeygain account email: ').strip(),password=getpass.getpass('Honeygain password: '))
        else:
            values['cid']=getpass.getpass('PacketStream CID from your account: ').strip()
        if any(not value for value in values.values()):raise ValueError('An account value is empty')
    org, specs=specifications(args.protocol,values)
    if args.action=='plan':
        for item in specs:
            print(json.dumps({k:item[k] for k in ('name','replicas','country_codes','restart_policy','autostart_policy')},sort_keys=True))
        print('Offline plan only; no account access, files, or cloud changes.')
        return
    helper=ROOT/'.runtime/keychain-store'
    key=subprocess.check_output([str(helper),'--read','--service','salad-bandwidth-api','--account',getpass.getuser()],text=True).strip()
    existing={g['name']:g for g in api(key,org,'/projects/default/containers').get('items',[])}
    if args.protocol=='honeygain' and args.action=='create':
        registrations={g['container']['environment_variables']['HONEYGAIN_DEVICE_NAME'] for g in specs}
        intended={g['name'] for g in specs}
        for other_org in ('deathadder','cosmosgeeketh','hyperlane'):
            for group in api(key,other_org,'/projects/default/containers').get('items',[]):
                device=group.get('container',{}).get('environment_variables',{}).get('HONEYGAIN_DEVICE_NAME')
                if device in registrations and not (other_org==org and group['name'] in intended):
                    if api(key,other_org,'/projects/default/containers/'+group['name']+'/instances').get('instances'):
                        raise RuntimeError('A Honeygain registration is already running in '+other_org+'/'+group['name'])
    receipts=[]
    for desired in specs:
        name=desired['name'];path='/projects/default/containers/'+name
        if name in existing:
            actual=api(key,org,path)
        elif args.action=='bind':
            raise RuntimeError('Cannot bind a missing group: '+name)
        else:
            try:
                actual=api(key,org,'/projects/default/containers','POST',desired)
            except RuntimeError:
                # A rejected response can follow an applied creation. Read back once; never duplicate.
                actual=api(key,org,path)
        verify(actual,desired,args.action=='create')
        if args.action=='create':
            for _ in range(60):
                actual=api(key,org,path);state=actual.get('current_state',{}).get('status')
                if state=='stopped':
                    api(key,org,path+'/start','POST');break
                if state in ('running','deploying','starting'):break
                time.sleep(5)
            else:raise RuntimeError('Group did not become startable within five minutes: '+name)
        receipts.append(dict(organization=org,group=name,id=actual['id'],replicas=desired['replicas'],image=actual['container']['image'],version=actual['version']))
    if args.protocol=='packetstream':
        receipt=receipts[0]
        write(DATA/'packetstream/observer-target.json',dict(mode='native-census',organization=org,project='default',group=receipt['group'],group_id=receipt['id']))
    else:
        write(DATA/'hg-fleet/deployment.json',receipts)
    print(json.dumps(receipts,indent=2))
    print('Binding saved. Verify native logs/client acceptance before claiming the fleet is working.')

if __name__=='__main__':main()
