# C14: отдельный frozen operating input

Вход — alternative fa39de413ac00a93b0214840aae2e7916332cef5 плюс base core b264780. output_manifest.json задаёт новый input_set_id; прежние a875/b264 и experiment refs не меняются. Foreign collectors не запускались.

Независимый HTMLParser ведущего проверил6 правил по338006 сохранённым primary HTML bytes с SHAe6d324e8...; обе стороны, часы, периоды, дни совпали с frozen CSV. Footer прямо говорит о местном времени аэропортов. Самостоятельное раскрытие календаря подтвердило12 плановых экземпляров, UTC и длительности peer CSV. Два выезда в окне:07Dec20:50→08Dec00:20 и10Dec23:20→11Dec02:15.

Arrival day/UTC/duration остаются DERIVED при допущении перелёта менее24часов. Это не явно опубликованный offset и не performed flight. Новый Mon/Thu не смешан с прежним объявлением Mon/Fri; источник старого объявления в этом модуле повторно не получен, его факт не опровергается задним числом. Stop pattern, inventory, operating legal entity и marketing role UNKNOWN; опубликованная ассоциация Азимут хранится отдельно.

KVX Europe/Kirov и published core Europe/Moscow сохранены как разные имена с одинаковым+03 на7/27Dec2026. Это не конфликт смещения и не проверка границ пояса. Все timezone foreign keys согласованы в timezone_keys_union.csv.

outputs/operating_service_rules_union.csv и operating_dated_instances_union.csv совместимы с базовым профилем:13правил/24датированныхзаписи (12старых departure-only,12новых conditional calendar). Новые записи имеют отдельные component_input_set_id; строки после13Dec отмечены LATER_CONTEXT_14_27, не считаются недельной программой. Никакой источник не получил автоматического полного допуска. Базовый карантин наследуется.

Отсчёт7/10/14 LOCAL HOTEL nights этим модулем не выполняется: actual booking/check-in date и точный transfer неизвестны. Flight arrival после полуночи не равна hotel reservation date;7/13Dec train samples не переносятся на8/11Dec. Hotel/transfer/product gates остаются у отдельного product_probe/experiment. Raw HTML удержан локально под ignore; в Git только безопасные извлечения, hashes, provenance и свой parser. Повтор строит побайтово те же outputs/manifest.
