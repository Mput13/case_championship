#!/usr/bin/env python3
"""Small read-only public HTTP receipts. No cookies, auth, booking or browser."""
import concurrent.futures,datetime,hashlib,json,pathlib,sys,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parent
SOURCES={
'kuf_transfer':'https://ar-kuf.ru/rules/transfernym-passazhiram/',
'ren_transfer_probe':'https://ar-ren.ru/rules/transfernym-passazhiram/',
'kuf_mro_yakovlev':'https://yakovlev.ru/press-centre/releases/yakovlev-zapustil-lineynuyu-stantsiyu-tekhnicheskogo-obsluzhivaniya-samoletov-ssj-100-v-aeroportu-sa/',
'ren_atb':'https://ar-ren.ru/about/news/raboty_po_tehnicheskomu_obsluzhivaniju_samolotov_l-410/',
'oms_mro_recheck':'https://www.aeroomsk.ru/ob-aeroporte/press-tsentr/novosti/207/',
'ren_pax_recheck':'https://ar-ren.ru/about/news/aeroport-orenburg-obsluzhil-za-2025-god-bolee-950/',
'ufa_schedule':'https://www.airportufa.ru/passengers/schedule/',
'ufa_home':'https://www.airportufa.ru/',
'kuf_mro_favt':'https://www.favt.gov.ru/novosti-novosti/?id=15460',
'kuf_mro_oak':'https://uacrussia.ru/ru/press-center/news/pamyati-vano-anastasovicha-mikoyana/yakovlev-zapustil-lineynuyu-stantsiyu-tekhnicheskogo-obsluzhivaniya-samoletov-ssj-100-v-aeroportu-sa',
'svx_development_2024':'https://flyredwings.com/en/press/news/red-wings-razvivaet-novye-marshruty-iz-ekaterinburga/',
'nordstar_rw_2024':'https://www.nordstar.ru/about/news/3532/',
'ufa_oms_to':'https://www.airportufa.ru/schedule/omsk/?CITY_CODE=omsk&direction=TO',
'ufa_njc_to':'https://www.airportufa.ru/schedule/nizhnevartovsk/?CITY_CODE=nizhnevartovsk&direction=TO',
'ufa_mrv_to':'https://www.airportufa.ru/schedule/mineralnye_vody/?CITY_CODE=mineralnye_vody&direction=TO',
'ufa_kuf_to':'https://www.airportufa.ru/schedule/samara/?CITY_CODE=samara&direction=TO',
'ufa_goj_fixed':'https://www.airportufa.ru/schedule/nizhny_novgorod/?CITY_CODE=nizhny_novgorod&direction=FROM',
'ufa_goj_to':'https://www.airportufa.ru/schedule/nizhny_novgorod/?CITY_CODE=nizhny_novgorod&direction=TO',
'kuf_ufa_train':'https://samppk.ru/all-news/company-news/zapushcheno-pryamoe-skorostnoe-soobshchenie-samara-ufa-samara/',
'kuf_ufa_train_changes':'https://samppk.ru/all-news/izmeneniya-v-raspisanii/v-svyazi-s-provedeniem-remontnykh-rabot-na-uchastke-abdulino-chishmy-v-avguste-2026-goda-vnosyatsya-/',
'ufa_winter_2026':'https://airportufa.ru/news/2026/perekhod-na-osenne-zimnee-raspisanie-2026-27gg/',
'kuf_schedule_new':'https://ar-kuf.ru/schedule/',
'kuf_schedule_arr_new':'https://ar-kuf.ru/schedule/?type=arr',
'gsv_schedule_new':'https://ar-gsv.ru/schedule/',
'gsv_schedule_arr_new':'https://ar-gsv.ru/schedule/?type=arr',
'svx_results_2025':'https://flyredwings.com/press/news/0B147898-A08F-95E8-F644-53DC1F529E53/',
'nordstar_partners_current':'https://www.nordstar.ru/about/airlines-partners/',
'ufa_index':'https://www.airportufa.ru/schedule/',
'ufa_oms':'https://www.airportufa.ru/schedule/omsk/?CITY_CODE=omsk&direction=FROM',
'ufa_njc':'https://www.airportufa.ru/schedule/nizhnevartovsk/?CITY_CODE=nizhnevartovsk&direction=FROM',
'ufa_mrv':'https://www.airportufa.ru/schedule/mineralnye_vody/?CITY_CODE=mineralnye_vody&direction=FROM',
'ufa_goj':'https://www.airportufa.ru/schedule/nizhniy_novgorod/?CITY_CODE=nizhniy_novgorod&direction=FROM',
'ufa_kuf':'https://www.airportufa.ru/schedule/samara/?CITY_CODE=samara&direction=FROM',
'ufa_gsv_probe':'https://www.airportufa.ru/schedule/saratov/?CITY_CODE=saratov&direction=FROM',
'ufa_vog_probe':'https://www.airportufa.ru/schedule/volgograd/?CITY_CODE=volgograd&direction=FROM',
'ufa_arh_probe':'https://www.airportufa.ru/schedule/arkhangelsk/?CITY_CODE=arkhangelsk&direction=FROM',
'kuf_mro_rostec':'https://rostec.ru/media/news/yakovlev-zapustil-lineynuyu-stantsiyu-tekhnicheskogo-obsluzhivaniya-samoletov-ssj-100-v-aeroportu-samary/',

}
def get(item):
 sid,url=item;
 existing=json.loads((ROOT/'http_receipts.json').read_text()) if (ROOT/'http_receipts.json').exists() else []
 previous=next((r for r in existing if r['source_id']==sid),None)
 if previous:return previous
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();rec=dict(source_id=sid,url=url,captured_at_utc=start,license='UNKNOWN',transport='stdlib urllib.request GET; no auth/cookies',max_bytes=2500000)
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (public evidence research)'})
  with urllib.request.urlopen(req,timeout=30) as r:
   data=r.read(2500001); rec.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type'))
   if len(data)>2500000: raise ValueError('size limit exceeded')
  p=ROOT/'raw'/(sid+'.bin');p.parent.mkdir(exist_ok=True);p.write_bytes(data)
  rec.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),raw_local_path=str(p.relative_to(ROOT)),status='ACQUIRED')
 except Exception as e: rec.update(status='ACCESS_FAILED',error=type(e).__name__+': '+str(e))
 rec['completed_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();return rec
if __name__=='__main__':
 selected={k:v for k,v in SOURCES.items() if len(sys.argv)==1 or k in sys.argv[1:]}
 recs=list(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(get,selected.items()))
 p=ROOT/'http_receipts.json';old=json.loads(p.read_text()) if p.exists() else [];ids=set(selected);p.write_text(json.dumps([r for r in old if r['source_id'] not in ids]+recs,ensure_ascii=False,indent=2)+'\n')
 for r in recs:print(r['source_id'],r['status'],r.get('http_status'),r.get('bytes'),r.get('error',''))
