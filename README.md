# Evolutionary Priority DSL — pakiet referencyjny

Ten pakiet pokazuje, jak nadawać Claude Code, Codex/ChatGPT, Gemini CLI i innym agentom jeden, deterministyczny kierunek pracy bez polegania na tym, który model „lepiej zrozumiał” priorytety.

## Najważniejsza decyzja modelowa

Priorytet jest rozdzielony na trzy niezależne osie:

1. **Klasa normatywna** — konstytucyjna, bezpieczeństwo, poprawność, standaryzacja, dostawa, optymalizacja. Klasy są porządkowane leksykograficznie. Punkty z niższej klasy nigdy nie wyprą wyższej klasy.
2. **Ważność (`importance`)** — trwała istotność reguły w obrębie klasy.
3. **Pilność wykonawcza (`dispatchUrgency`)** — zmienna wartość sterowana metrykami i triggerami. Może spaść do zera, gdy nie ma naruszenia, bez obniżania ważności normatywnej.

To eliminuje błąd „pilny feature ma 950 punktów, więc wygrywa z bezpieczeństwem mającym 900”.

## Podział odpowiedzialności

- `wellmanifest/policy-dsl` — HOME abstrakcyjnego schematu, semantyki klas, lifecycle i reguł promocji; bez selektorów repozytoriów, nazw produktów i wyjątków Subactor.
- organizacja lub produkt — HOME konkretnej instancji katalogu priorytetów, metryk i routingu, np. `subactor/platform/config/governance/engineering-priorities.v1.yaml`. Plik `priority-evolution.dsl.yaml` w tym pakiecie jest właśnie taką instancją przykładową, a nie nowym konkurencyjnym standardem.
- projekt — tylko `ADOPT` z wersją i digestem oraz lokalnymi selektorami; bez kopiowania semantyki standardu.
- `semcod/pyqual` — deterministyczna ewaluacja i quality gate.
- `semcod/giton` / `subactor/onedev-agent` — lokalne i serwerowe zdarzenia Git.
- `subactor/diagit` — stan floty, drift, zależności i wybór repozytoriów.
- `autogrammar/todo2code` — plan po utworzeniu ograniczonego ticketu z dokładnym zachowaniem i testami; pusty plan jest `PLAN_GAP`, nie zgodą na brak działania.
- `subactor/repair-agent` — wykonanie naprawy implementacji.
- `validator-agent` — niezależna walidacja dokładnego patcha i rewizji.

## Naprawa implementacji a naprawa standardu

DSL ma dwa osobne tory:

- **`REPAIR_IMPLEMENTATION`** — dowody pokazują, że obowiązujący standard jest poprawny, ale kod/manifest go narusza.
- **`PROPOSE_STANDARD_CHANGE`** — reprezentatywne metryki pokazują fałszywe blokady, konflikt standardów lub regresję całego ekosystemu.

Standard nie naprawia sam siebie bez kontroli. Zmiana standardu zawsze przechodzi:

`candidate → shadow → canary → active`

Wymagane są niezależny walidator, promocja przez właściciela i możliwość rollbacku. Agent może stworzyć propozycję, ale nie może jej sam aktywować.

## Co zawsze pozostaje najwyżej

W przykładzie są to:

- jeden HOME dla concernu;
- zgodność receiptu z dokładną rewizją;
- brak PASS na podstawie nazwy funkcji lub twierdzenia LLM;
- rozdział implementera i walidatora;
- brak wykonania przy `BLOCK` lub nieznanych dowodach.

Te reguły mają `preemptible: false` i listę `nonDemotableBy`. Termin, koszt, wygoda modelu ani pilność produktu nie mogą ich obniżyć.

## Co może obniżyć pilność, ale nie ważność

- naruszenie zostało naprawione i potwierdzone świeżym receiptem;
- reguła nie jest relewantna w bieżącym scope;
- ticket jest duplikatem lub został superseded;
- działanie czeka na obowiązkową zależność — wtedy priorytet przechodzi na odblokowanie zależności;
- brak świeżych danych — agent nie zgaduje, tylko priorytetyzuje odświeżenie dowodów;
- wysoki false-block rate — enforcement przechodzi do review/shadow, a nie do cichego ignorowania standardu;
- wykryta oscylacja — priorytety zostają zamrożone i wymagają review.

## Jak badana jest komplementarność

Evaluator sprawdza sześć warstw:

1. `requires` — czy obowiązkowe zależności istnieją i nie są zablokowane;
2. `reinforces` / `enables` — czy zmiany wzajemnie poprawiają te same cele;
3. `excludes` — czy dwa działania są jawnie wykluczające;
4. `expectedEffects` — czy dwa aktywne działania nie deklarują przeciwnych kierunków dla tej samej metryki;
5. budżet i HOME — czy plan ma pomiar liczby plików, linii i tur agenta, nie przekracza limitów oraz nie tworzy drugiego właściciela normy;
6. graf zależności — stabilny sort topologiczny; cykl zależności jest konfliktem twardym.

`automaticDispatchAllowed` jest prawdziwe dopiero po przekroczeniu progu, braku konfliktu twardego, pełnym pomiarze budżetu i przejściu ochrony przed oscylacją. Polityka `candidate`, `shadow` lub `canary` nadal nie otwiera bramki produkcyjnej; pełne wykonanie wymaga lifecycle `active`. W produkcyjnym runtime warto dodać symulację na Digital Twin przed dopuszczeniem efektu.

## Metryki operacyjne

Minimalny dashboard powinien pokazywać:

- compliance coverage i freshness coverage;
- liczbę oraz wiek driftów;
- false-block rate z wielkością próby, segmentowany przez `standardId`, wersję i klasę repozytorium;
- conflict density i complementarity score;
- MTTD/MTTR, rollback rate i repair success rate;
- out-of-scope action rate;
- rule citation coverage;
- liczbę priorytetowych zmian na godzinę i oscylacje;
- candidate/shadow/canary promotion lead time;
- odsetek planów, w których wynik przewidywany zgadzał się z wynikiem po wdrożeniu.

Brak pomiaru ma stan `NOT_MEASURED` lub `REVIEW_REQUIRED`, nigdy automatyczne `PASS`. Reference evaluator wymaga także `planEstimates` dla każdej naprawy i blokuje plan przy przekroczeniu `maxFilesPerRepair`, `maxChangedLinesPerRepair`, `maxAgentTurnsPerRepair`, limitu równoległych napraw albo dziennego limitu propozycji zmian standardu.

## Triggery

W DSL zdefiniowano:

- szybki file watch z debounce 2 s;
- pełny kontrolny cykl co 300 s z jitterem;
- `post-commit` i `pre-push` do lokalnej informacji zwrotnej;
- serwerowy `pre-receive` jako nieomijalną bramkę;
- zdarzenia runtime: błąd, nieudany test, drift, wygaśnięcie receiptu i konflikt polityk.

File watch i timer nie wykonują surowych shell stringów z DSL. Emitują typowane URI, które dopiero kontrolowany adapter mapuje na istniejące narzędzia.

## Uruchomienie przykładu

```bash
python3 adapters/standardctl.py validate \
  --policy priority-evolution.dsl.yaml \
  --schema schemas/priority-evolution.schema.json

python3 adapters/standardctl.py evaluate \
  --policy priority-evolution.dsl.yaml \
  --state examples/state.json \
  --now 2026-08-19T10:00:00Z \
  --out receipts/priority-decision.json

python3 adapters/standardctl.py compile-context \
  --policy priority-evolution.dsl.yaml \
  --receipt receipts/priority-decision.json \
  --out-dir generated-context
```

Evaluator celowo zwraca kod różny od zera, gdy wynik to `BLOCK` lub `REVIEW_REQUIRED`, dzięki czemu można go bezpośrednio podpiąć do `pyqual`, hooka lub `pre-receive`.

## Wspólny kierunek dla Claude, ChatGPT/Codex i Gemini

Jedynym HOME instrukcji jest wygenerowany plik `.wellmanifest/generated/agent-policy.md`. Fasady są deterministyczne:

- `AGENTS.md` — pełna projekcja dla Codex/ChatGPT coding agent;
- `CLAUDE.md` — import wspólnej projekcji;
- `GEMINI.md` — import wspólnej projekcji.

Fasad nie edytuje się ręcznie. Każda zawiera digest polityki, digest receiptu, rewizję, aktywne blokady, kolejność priorytetów i dozwolone URI. Dzięki temu różne modele otrzymują ten sam kontrakt, a różnić się mogą tylko jakością implementacji w granicach kontraktu.

## Sugerowane rozmieszczenie w repozytorium

```text
.wellmanifest/
├── adoption.yaml
├── priority-evolution.dsl.yaml
├── schemas/priority-evolution.schema.json
├── state/current.json
├── tools/standardctl.py
├── generated/agent-policy.md
└── receipts/
    ├── priority-decision.json
    └── intent-plan-delta.json
AGENTS.md
CLAUDE.md
GEMINI.md
pyqual.yaml
```

`adoption.yaml` powinien wskazywać wersję i digest abstrakcyjnego standardu oraz HOME organizacyjnego katalogu priorytetów. Projekt może zawęzić scope i podłączyć kolektory, ale nie może zmienić rankingu klas ani reguł promocji standardu. Konkretne selektory `subactor/*`, `semcod/*`, `autogrammar/*` należą do instancji organizacyjnej, nie do `wellmanifest/policy-dsl`.

## Granica tego pakietu

To referencyjny kontrakt i deterministyczny evaluator. Nie udaje gotowej integracji z lokalnymi API `todo2code`, `diagit`, `pyqual`, OneDev lub agentami. Integracja powinna mapować URI do faktycznie istniejących interfejsów po sprawdzeniu ich wersji i kontraktów. Najpierw należy uruchomić tryb shadow i mierzyć konflikty, abstencje oraz false blocks; dopiero potem dopuścić ograniczony canary.
