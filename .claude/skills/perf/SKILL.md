---
name: perf
description: "Web performance audit and optimization. Invoke when optimizing page speed, fixing Core Web Vitals (LCP, INP, CLS), reducing bundle size, or diagnosing slow loading. Actions: performance, wydajność, wolna strona, optymalizacja, Lighthouse, Core Web Vitals, LCP, CLS, INP, bundle size, lazy loading."
---

# Wydajność — Audyt i Optymalizacja

Audyt wydajności oparty na Lighthouse i Core Web Vitals. Dwa poziomy szczegółowości:

- **Szybki audyt** → sprawdź `performance.md` — ogólne optymalizacje, budżet zasobów
- **Core Web Vitals** → sprawdź `core-web-vitals.md` — konkretne metryki LCP/INP/CLS

## Kiedy używać

Wywołaj gdy:
- Lighthouse score poniżej 90
- Użytkownik skarży się na wolne ładowanie
- Dodajesz nowe zasoby (obrazy, fonty, biblioteki)
- Przed launchem — jako część checklisty deploy

## Budżet zasobów (punkty wyjścia)

| Zasób | Limit | Dlaczego |
|-------|-------|----------|
| Całkowita strona | < 1.5 MB | 3G ładuje w ~4s |
| JavaScript (skompresowany) | < 300 KB | Czas parsowania i wykonania |
| CSS (skompresowany) | < 100 KB | Blokuje renderowanie |
| Obrazy (above-fold) | < 500 KB | Wpływ na LCP |
| Fonty | < 100 KB | FOIT/FOUT |
| Zewnętrzne skrypty | < 200 KB | Niekontrolowane opóźnienia |

## Progi Core Web Vitals

| Metryka | Dobry | Wymaga poprawy | Zły |
|---------|-------|----------------|-----|
| **LCP** (ładowanie) | ≤ 2.5s | 2.5–4s | > 4s |
| **INP** (interaktywność) | ≤ 200ms | 200–500ms | > 500ms |
| **CLS** (stabilność) | ≤ 0.1 | 0.1–0.25 | > 0.25 |

## Protokół audytu

1. Uruchom Lighthouse lub PageSpeed Insights — zanotuj wyniki przed zmianami
2. Zidentyfikuj największy problem (zwykle LCP lub duży JS bundle)
3. Przeczytaj `performance.md` dla ogólnych optymalizacji
4. Przeczytaj `core-web-vitals.md` dla konkretnej metryki którą chcesz poprawić
5. Zmierz wynik po każdej zmianie — jedna zmiana na raz

## Zasady

- Mierz zanim optymalizujesz — bez danych nie wiadomo co poprawić
- Jedna zmiana na raz — łatwiej zmierzyć efekt
- Obrazy w WebP/AVIF z zadeklarowanymi `width` i `height` (zapobiega CLS)
- Fonty z `font-display: swap` + `<link rel="preload">`
- Zewnętrzne skrypty z `async` lub `defer`
- Nie importuj całej biblioteki jeśli potrzebujesz jednej funkcji

## Szczegółowe wytyczne

- Optymalizacja ogólna → przeczytaj `performance.md`
- Core Web Vitals → przeczytaj `core-web-vitals.md`
