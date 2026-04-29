# Zakres systemu

## 🎯 Cel systemu

System SaaS do zarządzania zajęciami, obecnościami oraz podstawową obsługą operacyjną organizacji prowadzących zajęcia.

---

## 🧠 Główna koncepcja

System oparty jest na:

- zajęciach jako jednostce operacyjnej
- obecności jako zdarzeniu (event-based)
- QR jako mechanizmie identyfikacji użytkownika

Każda operacja odnosi się do:

lesson_instance

Obecność:

- attendance_events (raw)
- attendance_records (aggregated)

---

## 🔁 Obsługa obecności

Check-in:

- QR scan
- zapis event

Check-out:

- drugi scan

---

## 🧩 Moduły

### Uczniowie
- dane
- grupy
- historia

### Nauczyciele
- dane
- przypisania

### Grupy
- uczniowie
- nauczyciele

### Harmonogram
- lessons
- lesson_instances
- przypisania

### Lista obecności
- lista uczniów
- status obecności

### Integracje
- Google Calendar
- Outlook Calendar

### Dokumenty
- umowy nauczycieli
- umowy uczniów

### KP
- wystawianie
- przypisanie do ucznia

---

## ⚖️ Priorytety

CORE:
- attendance
- lesson_instances
- QR flow

OPERACYJNE:
- uczniowie
- nauczyciele
- grupy
- harmonogram

ADMIN:
- dokumenty
- KP

INTEGRACJE:
- kalendarze

---

## 🗄️ Baza danych

Relacyjny model danych.

Założenia:

- brak vendor lock
- kompatybilność SQL
- decyzja o technologii → ADR

---

## 🧠 Architektura

- API-based
- modularna
- separacja warstw

Technologie → decyzje ADR

---

## 🚫 Zakres wykluczony

- księgowość
- podatki
- płatności online
- CRM

---

## 🧠 Wymagane decyzje (ADR)

- model attendance
- lesson_instances strategy
- integracje kalendarzy
- dokumenty
- wybór technologii

---

## 🎯 Cel końcowy

System do:

- zarządzania zajęciami
- rejestracji obecności
- obsługi uczestników
- generowania dokumentów

Gotowy do realnego użycia.
