---
name: review
description: "Comprehensive code review for pull requests and diffs. Covers React 19, Vue 3, Angular, TypeScript, Python, Go, Rust, Java, C#, Kotlin, NestJS, Svelte, Django and more. Actions: review, code review, sprawdź kod, przejrzyj PR, oceń zmiany, review PR, zrób review, pull request."
---

# Code Review

Szczegółowe wytyczne code review z `awesome-skills/code-review-skill`.
Pełna treść skilla: przeczytaj `reference/` dla konkretnego języka/frameworka.

## Kiedy używać

- Review pull requesta przed merge
- Ocena diff przed committem
- Self-review własnych zmian
- Ustalanie standardów review w zespole

## Protokół

### Krok 1 — Zrozum zmianę

Zanim przejdziesz do linii kodu:
- Jaki problem rozwiązuje ta zmiana?
- Czy podejście jest poprawne architektonicznie?
- Czy zakres zgadza się z opisem PR?

Jeśli podejście jest złe — powiedz to od razu, zanim zaczniesz review linii.

### Krok 2 — Analiza PR

1. Przeczytaj opis PR i powiązany issue
2. Dla znaczących zmian: przeczytaj `reference/architecture-review-guide.md`
3. Sprawdź performance-critical kod: `reference/performance-review-guide.md`
4. Sprawdź bezpieczeństwo: `reference/security-review-guide.md`
5. Dla konkretnego języka/frameworka: przeczytaj odpowiedni plik z `reference/`

### Krok 3 — Checklist

**Poprawność**
- [ ] Robi to co deklaruje?
- [ ] Edge case'y obsłużone (null, puste, duże dane, równoległe wywołania)?
- [ ] Błędy obsłużone i komunikowane?
- [ ] Brak cichych błędów (catch bez re-throw lub loga)?

**Bezpieczeństwo** → szczegóły w `reference/security-review-guide.md`
- [ ] Brak sekretów w kodzie
- [ ] Input validowany na granicach systemu
- [ ] Autoryzacja sprawdzana przed dostępem do zasobu

**Wydajność** → szczegóły w `reference/performance-review-guide.md`
- [ ] Brak N+1 queries
- [ ] Brak pełnych skanów tabeli bez paginacji
- [ ] Ciężkie operacje poza głównym wątkiem/requestem

**Konwencje** (sprawdź `docs/CONVENTIONS.md` projektu)
- [ ] Nazewnictwo spójne z codebase
- [ ] Brak magic values — stałe lub config
- [ ] Brak martwego kodu i `TODO` bez odniesienia

**Testy**
- [ ] Nowa funkcjonalność ma testy
- [ ] Testy pokrywają nie tylko happy path
- [ ] Brak mockowania rzeczy które powinny być testowane naprawdę

### Krok 4 — Werdykt

```
## Review: [tytuł PR / opis zmiany]

**Werdykt:** ✅ Zatwierdź / 🔄 Wymaga zmian / ❌ Odrzuć podejście

### Musi być poprawione
- [bloker — konkretny powód]

### Powinno być poprawione
- [ważne, ale nie blokujące]

### Uwagi (opcjonalne)
- [styl, nazewnictwo — do wzięcia lub zostawienia]

### Co jest dobrze
- [zawsze przynajmniej jeden punkt]
```

## Przewodniki językowo-specyficzne

| Język / Framework | Plik |
|-------------------|------|
| React 19 | `reference/react.md` |
| Vue 3 | `reference/vue.md` |
| Angular 17+ | `reference/angular.md` |
| TypeScript | `reference/typescript.md` |
| Python | `reference/python.md` |
| Django / DRF | `reference/django.md` |
| Go | `reference/go.md` |
| Rust | `reference/rust.md` |
| Java | `reference/java.md` |
| C# / .NET | `reference/csharp.md` |
| Kotlin | `reference/kotlin.md` |
| NestJS | `reference/nestjs.md` |
| Svelte | `reference/svelte.md` |
| CSS/Sass | `reference/css-less-sass.md` |
| Architektura | `reference/architecture-review-guide.md` |
| Bezpieczeństwo | `reference/security-review-guide.md` |
| Wydajność | `reference/performance-review-guide.md` |

## Zasady

- Oddziel "złe podejście" od "zła implementacja" — podejście komentuj pierwsze
- Każdy bloker musi mieć uzasadnienie, nie tylko opis
- Zawsze napisz coś pozytywnego — review to rozmowa, nie audit
- Jeśli nie wiesz co zmiana robi z samego opisu — zapytaj przed review
