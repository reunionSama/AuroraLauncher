"""Actual official component installations into isolated CI-only instances."""
from pathlib import Path
import json,sys,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aurora.storage import Store
from aurora.engine import Engine
from aurora.installers import InstallerCatalog
from aurora.auth import offline

root=Path(sys.argv[1]);report_path=Path(sys.argv[2]);result={'ok':False,'installations':{},'real_user_credentials':False};started=time.monotonic()
store=Store(root);engine=Engine(store,log=lambda line:print(line,flush=True));catalog=InstallerCatalog(engine)
try:
    for kind,pinned in [('fabric','0.16.10'),('quilt','0.28.1'),('forge','47.2.18'),('optifine','HD_U-I6'),('neoforge','20.4.237')]:
        base='1.20.4' if kind=='neoforge' else '1.20.1';store.create_instance('CI-'+kind,base)
        choices=catalog.choices(kind,base)
        if not choices:raise RuntimeError(kind+' returned no compatible component versions')
        choice=next((v for v in choices if v['id']==pinned),next((v for v in choices if v.get('stable')),choices[0]))
        plan={'minecraft':base,'loader':kind,'loader_version':choice['id']}
        if kind=='fabric':
            apis=catalog.choices('fabric-api',base)
            if not apis:raise RuntimeError('Fabric API has no compatible version')
            plan['fabric-api']=next((v['id'] for v in apis if v.get('stable')),apis[0]['id'])
        start=time.monotonic();target=catalog.install(plan);metadata=engine.metadata(target)
        command=engine.make_command(target,offline('AuroraTester'),store.game_dir())
        if not metadata or engine.loader(target)!=kind or any('${' in part for part in command):raise RuntimeError('Installed component profile is incomplete: '+kind)
        if kind=='fabric' and not list((store.game_dir()/'mods').glob('*.jar')):raise RuntimeError('Selected Fabric API did not install')
        result['installations'][kind]={'ok':True,'minecraft':base,'component_version':choice['id'],'profile':target,'seconds':round(time.monotonic()-start,2),'selected_api_installed':bool(plan.get('fabric-api'))}
        print(json.dumps(result['installations'][kind]),flush=True)
    result['ok']=True
except Exception as exc:result['error']=str(exc);traceback.print_exc()
finally:
    result['seconds']=round(time.monotonic()-started,2);report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
sys.exit(0 if result['ok'] else 1)
