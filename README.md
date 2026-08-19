# Evolutionary Priority DSL 0.3.0

Deterministyczna warstwa nadawania wspólnego kierunku agentom Claude Code, Codex/ChatGPT, Gemini CLI i agentom shell/IDE. Model interpretuje ticket, ale nie ustala sam priorytetów, nie wybiera repozytoriów z pamięci i nie zatwierdza własnej zmiany. Kolejność, dowody, budżety, blokady i lifecycle są obliczane poza modelem.

Wersja 0.3.0 rozwija poprzedni evaluator o **mapę faktycznie zaindeksowanego ekosystemu**, **router kontekstu ticketu**, **bramkę wyników `todo2code`**, **projekcję obserwacji na metryki DSL** oraz **oddzielną kontrolę SSOT oferty**.

## Co zostało wdrożone

```text
TOON indexes + source reports
          │
          ▼
registry/ecosystem-tools.yaml
          │  moduły + symbole + HOME + role + capabilities + URI
          ▼
generated/ecosystem-map.json ──► generated/llms.txt
          │
          ▼
examples/ticket-context-request.json
          │
          ▼
adapters/ecosystemctl.py route-ticket
          │
          ├── context-selection.json
          ├── CONTEXT.md
          └── todo2code-request.json
                         │
                         ▼
               wynik planera todo2code
                         │
                         ▼
          validate-plan-set / T2C_PLAN_GAP
                         │
                         ▼
adapters/statectl.py ──► metryki z digestami i rewizją
                         │
                         ▼
adapters/standardctl.py ─► BLOCK / REVIEW_REQUIRED / ACTION_REQUIRED / PASS
                         │
                         ├── receipt
                         └── AGENTS.md / CLAUDE.md / GEMINI.md
```

### 1. Indeks narzędzi oparty na kodzie

`adapters/toon_index.py` czyta mapy TOON jako indeksy dowodowe. Rozpoznaje moduły, eksporty, symbole oraz skompresowane metody klas, np.:

```text
ControlService: generate_governance_plan(...), generate_repair_plan(...)
```

`adapters/ecosystemctl.py index` łączy mapy z wersjonowanym rejestrem. Projekt jest `executionEligible=true` wyłącznie wtedy, gdy wymagane moduły i symbole są potwierdzone przez odpowiednio silne źródło oraz projekt ma lifecycle `active`.

Aktualny snapshot z dołączonych indeksów:

- `subactor`: 6497 modułów w mapie z 2026-08-19;
- `autogrammar`: 6421 modułów w mapie z 2026-08-19;
- 15 projektów w rejestrze;
- 10 projektów zweryfikowanych strukturalnie;
- 9 projektów wykonawczo kwalifikowanych;
- 0 zduplikowanych właścicieli HOME;
- 4 wymagane projekty pozostające na poziomie dokumentacyjnym.

Dlatego bieżący `generated/ecosystem-map.json` ma status `REVIEW_REQUIRED`, a nie sztuczne `PASS`.

### 2. Router kontekstu dla `project/ticket-*`

`route-ticket` wybiera projekty według:

- wymaganych ról;
- concernów i dokładnego właściciela `HOME`;
- capability keywords;
- lifecycle;
- klasy i pokrycia dowodu;
- preferencji i wykluczeń ticketu;
- maksymalnego budżetu repozytoriów.

Dokumentacja może dodać projekt do kontekstu, ale przy ticketach zmieniających kod nie daje mu prawa wykonawczego. Obecny ticket wybiera m.in.:

- `autogrammar/todo2code` jako planner;
- `subactor/diagit` jako obserwator floty i router;
- `subactor/registry` jako HOME katalogu organizacyjnego;
- `subactor/onedev-agent` jako serwerowy Git gateway;
- `subactor/repair-agent` jako wykonawcę;
- `subactor/validator-agent` jako niezależnego walidatora;
- `subactor/offer` jako jedyny HOME wartości oferty;
- `wellmanifest/offer` jako osobny HOME abstrakcyjnego standardu oferty.

Status kontekstu pozostaje `REVIEW_REQUIRED`, ponieważ do pakietu nie dołączono dokładnych map kodu `semcod/pyqual` ani `wellmanifest/*`.

### 3. `todo2code` jako planner, nie dekoracja

Rejestr wskazuje faktycznie zaindeksowane punkty rozszerzeń `autogrammar/todo2code`, w tym:

- `PipelineRun`;
- `proposeCodeChangePlans`;
- `buildPlanFromDiagnostic`;
- `WorkspacePreflightError`.

Pakiet generuje ustrukturyzowany `todo2code-request.json` z wybranymi repozytoriami, otwartymi kryteriami, granicą scope i wymaganiem aktualnych dowodów Git/AST.

`validate-plan-set` stosuje zasadę fail-closed:

```text
status=succeeded + recordCount=0 + otwarte kryteria
→ BLOCK / T2C_PLAN_GAP
```

Każdy akceptowany plan musi mieć:

- dokładne ścieżki;
- kryteria zachowania;
- co najmniej jeden test negatywny;
- komendę lub URI walidacji;
- spójny `recordCount`.

Pakiet nie uruchamia binarnego `todo2code`, ponieważ załączono indeks kodu, a nie checkout repozytorium ani jego CLI/runtime. Weryfikuje jednak rzeczywiste moduły i symbole planera, przygotowuje jego kontrakt wejściowy i waliduje znormalizowany wynik. Podłączenie wykonania wymaga przypięcia dokładnej wersji CLI.

### 4. Metryki z obserwacji, nie z deklaracji

`adapters/statectl.py` przekłada artefakty na metryki polityki:

- mapa → `duplicate_home_count`, pokrycie manifestów, niezweryfikowane wymagane projekty;
- routing → luki ról, pokrycie kontekstu i niezweryfikowany wybór narzędzi;
- receipt planera → `planning.todo2code_plan_gap_count`;
- receipt oferty → rzeczywisty wynik digest pin-check.

Warstwa rozróżnia dowód strukturalny od behawioralnego. Obecność `offer/bindings/...` w mapie potwierdza strukturę, lecz nie dowodzi zgodności jego SHA-256. Bez receiptu `pin-check` metryka `offer.facade_digest_mismatch_count` pozostaje brakująca i `standardctl` blokuje wykonanie.

### 5. Ewolucyjny DSL priorytetów

Priorytet ma trzy niezależne osie:

1. `priority.class` — porządek leksykograficzny: `constitutional`, `safety`, `correctness`, `standardization`, `delivery`, `optimization`;
2. `importance` — trwała ważność normy w klasie;
3. `dispatchUrgency` — chwilowa pilność wyliczana z metryk i triggerów.

Deadline ani pilny feature nie mogą wyprzeć wyższej klasy. Obniżana jest pilność wykonania, nie znaczenie normatywne.

Wersja 0.3 dodaje intencje:

- `STD-TOOL-GROUNDED-PLANNING`;
- `STD-ECOSYSTEM-CONTEXT-ROUTING`;
- `STD-OFFER-SSOT-INTEGRITY`.

Dodane nieprzekraczalne inwarianty:

- narzędzie wykonawcze musi mieć przypięty dowód;
- pusty plan przy otwartych kryteriach jest blokadą;
- ceny mają jeden HOME w `subactor/offer`;
- fasada oferty musi przejść digest pin-check.

### 6. Komplementarność priorytetów

Evaluator sprawdza:

- `requires`, `reinforces`, `enables`, `excludes`;
- przeciwne `expectedEffects` dla tej samej metryki;
- cykle zależności;
- jeden HOME;
- kompletność budżetu;
- limity plików, linii, tur i równoległych napraw;
- stabilny sort topologiczny;
- ochronę przed oscylacją.

W pełni spełnione pozytywne relacje normalizują wynik do `1.0`. Wcześniejsza wersja rezerwowała w mianowniku wszystkie hipotetyczne kary, przez co poprawny pojedynczy plan dostawy nie mógł przekroczyć progu. Ten błąd został naprawiony i objęty testem.

### 7. Oddzielenie naprawy kodu od naprawy standardu

- `REPAIR_IMPLEMENTATION` naprawia kod, manifest lub binding zgodnie z aktywną normą.
- `PROPOSE_STANDARD_CHANGE` tworzy wyłącznie propozycję, gdy reprezentatywne metryki pokazują false blocks lub konflikt standardów.

Promocja standardu zawsze przebiega:

```text
candidate → shadow → canary → active
```

Implementer nie może walidować ani promować własnego patcha.

## Uruchomienie

Wymagania: Python 3.11+ oraz pakiety z `requirements.txt`.

```bash
python3 -m pip install -r requirements.txt
make verify
```

`make verify` wykonuje walidację schematów, kompilację adapterów oraz 41 testów jednostkowych i negatywnych.

### Cykl accountable autonomy

```bash
make cycle
```

`adapters/autonomyctl.py cycle` zamyka pętlę obserwacja → routing → wywołanie albo abstencja → ewaluacja. Brak przypiętego CLI `todo2code` daje `not-run / T2C_PLANNER_NOT_PINNED`, a nie fałszywe `succeeded` z zerową liczbą planów. Pin-check oferty uruchamia się wyłącznie przy przypiętym `OFFER_BINDING` i `OFFER_FACADE`. Cykl nigdy nie stosuje patcha: `applyAttempted=false`, a `dispatch` zostaje zamknięty przy lifecycle `candidate`.

### Reprodukcja załączonego snapshotu

```bash
make rebuild
make reproducibility
```

`make rebuild` odtwarza snapshot z dołączonych map i stałego czasu. `make reproducibility` porównuje SHA-256 18 kluczowych artefaktów przed i po pełnym rebuildzie oraz zapisuje wynik w `generated/reproducibility-report.json`. Kody wyjścia `3` dla oczekiwanych `BLOCK`/`REVIEW_REQUIRED` są akceptowane jako wynik polityki, nie awaria procesu.

### Reconcile na rzeczywistych mapach

```bash
SUBACTOR_MAP=/srv/indexes/subactor.toon.yaml \
AUTOGRAMMAR_MAP=/srv/indexes/autogrammar.toon.yaml \
TICKET_REQUEST=/srv/tickets/ticket-123/request.json \
REVISION=<exact-git-sha> \
PLANNER_RECEIPT=/srv/tickets/ticket-123/todo2code-receipt.json \
OFFER_RECEIPT=/srv/receipts/offer-pin.json \
OUT_ROOT=/srv/policy-runtime \
./scripts/reconcile.sh
```

Brak opcjonalnego receiptu nie jest zastępowany domysłem. Odpowiednia metryka pozostaje niezmierzona.

## Triggery i Git gateway

Pakiet zawiera:

- file watch z debounce 2 s;
- timer co 5 minut z jitterem 30 s;
- szablony systemd;
- kontrakt serwerowego `pre-receive`;
- strukturalny komunikat `CODEVALIDATOR_RESULT=` na `stderr`.

`hooks/pre-receive` wymaga stanu przygotowanego dla dokładnego pushed revision. Nie bada dowolnego worktree serwera i odrzuca push przy niezgodności rewizji.

`integration/pyqual-adapter.yaml` jest świadomie oznaczony jako **adapter contract z wyłączonym enforcementem**. Nie jest natywnym `pyqual.yaml`, dopóki dokładny schemat i rewizja `semcod/pyqual` nie zostaną przypięte.

## Najważniejsze artefakty

```text
priority-evolution.dsl.yaml                polityka 0.3.0
registry/ecosystem-tools.yaml              rejestr projektów, ról i dowodów
adapters/toon_index.py                     czytnik map TOON
adapters/ecosystemctl.py                   indeks, router, ticket i plan gate
adapters/statectl.py                       projekcja obserwacji na metryki
adapters/standardctl.py                    evaluator, complementarity i facades
schemas/                                   schematy wejść i wyników
sources/indexes/                            przypięte mapy źródłowe
sources/reports/                            materiały bazowe
receipts/todo2code-plan-gap.json           oczekiwany BLOCK
receipts/todo2code-plan-valid.json         oczekiwany PASS
generated/ecosystem-map.json               snapshot mapy
generated/ticket-context-selection.json    wybór kontekstu
generated/state-from-index.json             stan z obserwacji
receipts/index-grounded-decision.json       decyzja na bazie indeksu
generated/verification-report.json          raport testów i walidacji
adapters/autonomyctl.py                     cykl discover → evaluate, bez auto-apply
generated/verification-report.md            czytelny raport w Markdown
generated/reproducibility-report.json       digests 18 odtwarzalnych artefaktów
.wellmanifest/generated/agent-policy.md     wspólny kontekst agentów
AGENTS.md / CLAUDE.md / GEMINI.md           deterministyczne fasady
```

## Aktualny wynik fail-closed

Dla stanu zbudowanego z załączonych indeksów i zerowego wyniku planera:

- mapa ekosystemu: `REVIEW_REQUIRED`;
- routing ticketu: `REVIEW_REQUIRED`;
- walidacja pustego planu: `BLOCK / T2C_PLAN_GAP`;
- offer digest pin: `UNKNOWN`, ponieważ brak behawioralnego receiptu;
- końcowa decyzja: `BLOCK`;
- dispatch: `false` również dlatego, że lifecycle polityki to `candidate`.

`examples/healthy-state.json` jest wyłącznie deterministyczną fixture testową. Jej `PASS` nie jest twierdzeniem o stanie produkcji.

## Granice i następna bramka promocji

Pakiet jest działającą implementacją referencyjną, lecz nie ma jeszcze prawa do enforcementu produkcyjnego. Do przejścia w `shadow` potrzebne są:

1. dokładna mapa i kontrakt `semcod/pyqual`;
2. dokładne mapy i wersje `wellmanifest/policy-dsl`, `new-project`, `git-lifecycle` i `offer`;
3. rzeczywisty receipt `subactor/offer pin-check` związany z rewizją;
4. uruchomienie prawdziwego `todo2code` na wygenerowanym requestcie;
5. niezależna walidacja patcha i co najmniej 30 shadow receipts;
6. brak false PASS w testach negatywnych.
