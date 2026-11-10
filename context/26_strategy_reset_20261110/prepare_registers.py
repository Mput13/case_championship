from pathlib import Path
import csv,json,hashlib,subprocess
P=Path(__file__).resolve().parent
R=P.parent.parent
src=R/'context/25_completion_audit_20261110/hypotheses/disposition.csv'
rows=list(csv.DictReader(src.open()))
groups={
 'network_hub':(['C01','C02','C03','C04','C05','C06','C21','C23'],'Хаб и база','Проверить место в основном выборе и минимальный ресурс; городское первое место не доказывает преимущество хаба.'),
 'network_existing':(['C07','C08','C09','C11','C13','C16','C17','C22','C26','C31','C33','C34'],'Действующая сеть и ресурс','Проверить эффект при отсутствии новых бортов и при альтернативном назначении ресурса; финалисты требуют donor и календарь.'),
 'commercial_product':(['C10','C12','C14','C15','C18','C19','C20','C24','C25','C32'],'Коммерческий продукт','Углублять при влиянии на финалиста: календарь и договорный/денежный порог. Полезный продукт не равен стратегии компании.'),
 'access_partner':(['C27','C28','C29','C35'],'Подвоз и партнёры','Сравнить с прямым рейсом/новой базой по полному времени и стоимости; соглашение не считать заключённым.'),
 'trigger':(['C30'],'Внешнее условие','Условная ветвь открытия аэропорта; до события оценить границы и действие, не считать маршрут доступным.')
}
lookup={x:(g,title,why) for g,(ids,title,why) in groups.items() for x in ids}
assert len(lookup)==35 and set(lookup)=={r['candidate_id'] for r in rows}
out=[]
for r in rows:
 g,title,why=lookup[r['candidate_id']]
 out.append(dict(id=r['candidate_id'],title=r['title'],family=g,family_label=title,planning_reason=why,
 historical_disposition=r['disposition'],historical_rejection=r['documented_early_rejection'],historical_scope=r['phase2_executed_test'],
 proposed_next_test=r['specific_next_check'],scenario_economics=r['scenario_economics_possible_now'],limits=r['scenario_limits'],
 current_new_evaluation='NOT_STARTED',planned_owner='network',audit_commit='9b65c9ff27f2a03fc9acbacc38de808a88e08358',audit_path=str(src.relative_to(R)),source_commit=r['source_commit']))
with (P/'hypothesis_portfolio.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
reqs=[
('R01','Исходный кейс','10+ городов, критерии/веса, топ-3 и устойчивость','network','Таблица рейтинга с определениями и различиями версий','dash:board/weights','18:00'),
('R02','Исходный кейс','Минимум два региональных конкурента и опыт RW в Екатеринбурге','evidence','Источник/механизм/переносимость; конкуренты на затронутых парах','dash:step2','19:00'),
('R03','Исходный кейс','Хаб и прямые, base/cautious','methods','Общий ресурс/период/спрос; пассажиры, выручка, доля, деньги; доминирование всех найденных допустимых сетей при расширении лимита','dash:vs','20:00'),
('R04','Исходный кейс','Выбранная сеть 8–12','network','Города, аэропорты, рейсы, частоты, сезон, тип; счёт без треугольных дублей','dash:step4/netmap','20:45'),
('R05','Исходный кейс','Источник или метод пассажиров и частоты каждого маршрута','evidence','Датированные строки, единицы, покрытие; неизвестное не ноль','dash:route_table/sources','19:00'),
('R06','Пользователь/AGENTS','Поставка поэтапно/частично/позже/нет','methods','N(t), ввод, ТО, резерв, ротации; сравнимые будущие ветви','dash:fleet_ramp/step5','20:00'),
('R07','Пользователь/AGENTS','Действующий SSJ и будущий SJ100 различены','evidence','Тип/аналог, диапазон и источник; чувствительность переноса','dash:routes + appendix','19:00'),
('R08','Пользователь','Рост без новых самолётов и было/стало','network','KEEP и изменения действующей сети с донором/потерями/креслами','dash:netmap + appendix','20:00'),
('R09','Пользователь/методика','Общий спрос/кресла/один тариф','methods','Пересекающиеся пары и реальные граничные примеры; без двойного счёта','calculation appendix','20:00'),
('R10','Новая версия Насти','Субсидия и реакция конкурентов','evidence','Применимость/период/единица/лимит; порог поддержки; альтернативы','dash:vs/step4','19:00'),
('R11','Пользователь','Полный добавочный результат и cash','methods','База/парк/ТО/запуск/резерв/донор/поддержка; неизвестные диапазоны и пороги','dash:vs + appendix','20:45'),
('R12','Исходный кейс','Годовой эффект и доля рынка','methods','Сезонный календарь, чистая добавка, совместимый знаменатель','dash:vs','20:45'),
('R13','Исходный кейс','Дорожная карта и риски до2028','root','Сигнал/действие/ответственный/условие запуска и остановки','dash:step5','20:45'),
('R14','Пользователь','35 объяснимых исходов','network','Все ID сохранены; доказанный отказ/слияние/условие или честный NOT_DONE','hypotheses appendix','18:00 screen /20:45 final'),
('R15','Уточнение организаторов п2','Поиск/покупка билета','digital','Реальный путь, доказанная проблема либо её отсутствие, изменение и break-even','PNG + passport','20:00'),
('R16','Уточнение организаторов п2','Допуслуги','digital','Уже доступное не новое; чистый эффект, ограничения и тест','PNG + passport','20:00'),
('R17','Уточнение организаторов п2','Основные вопросы/изменение после покупки','digital','Доступность проверки, путь, автоматизация, цена/эффект/зависимости','PNG + passport','20:00'),
('R18','Уточнение организаторов/ответ пользователя','№2 без срока, этап2027–2028, весь бизнес','root','Метрика/граница компании, разрыв масштаба, вклад этапа, условия роста','PNG + passport','20:45'),
('R19','Пользователь','Сохранять модели/решения команды','root','Исходное/исправление/новое допущение отдельны, источник SHA и автор','all artifacts','continuous'),
('R20','Пользователь','Регулярно проверять коллег','root','Refs/diff/влияние каждые30–45мин активной работы и перед сборкой','updates journal','continuous'),
('R21','Пользователь','Работа видна в GitHub','root','Содержательные коммиты/push и короткие handoff; без чужих веток','GitHub','each package'),
('R22','Исходный кейс/пользователь','Паспорт раньше финала и материалы ИИ','root','Ранние безопасные тезисы; позднее только changed claims; методы проверки','passport_now + appendix','now /22:00'),
('R23','Пользователь 17:03','Сохранить форму дашборда; дополнительные вопросы отдельно','root','Совместимые данные + предложения; PNG/PDF без нового обязательного UI','dashboard adapter + PNG','21:15'),
('R24','Пользователь','Срок22:00 и самостоятельная приёмка результата','root','Все требования с доказательствами; незавершённость названа; нет продления','final handoff','22:00')]
with (P/'requirements.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['id','authority','question','owner','acceptance','destination','checkpoint_msk']);w.writerows(reqs)
status={'phase':'DEFINITION_READY','deadline':'2026-11-10T22:00:00+03:00','main_execution_started':False,
'accepted':{'number2_deadline':'unspecified','2027_2028':'first_stage','business':'whole_Red_Wings','priority':'original_network_case','additional_questions':'complete_separate_appendices_not_main_dashboard','colleague_refresh':'30–45 minutes during active work + before runs/handoffs','github':'publish_substantive_own_packages'},
'active_thread':{'role':'nastya_panel_review','thread_id':'mcp:launch:fd8c59f2509a757377a769385c33216925080842ed04be5c8da424e7d266721b','model':'gpt-6.1-sol','reasoning':'xhigh','source_sha':'4a9763565f70b9ab1eddde2f5daca07687560948','author':'kiruha355','status':'LAUNCHED','counts_against_sol_cap':True},
'pool_limit':4,'night_freeze_unchanged':True,'hypotheses_count':35,'new_hypothesis_evaluations_completed':0,
'planning_defaults_not_team_acceptance':['number2 metric: annual traffic individual carrier','scenario stress lags3/6/12months','acceptability criteria and final winner','numeric future fleet assumptions']}
(P/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print('Prepared',len(reqs),'requirements;',len(out),'hypotheses. No new economic evaluation claimed.')
