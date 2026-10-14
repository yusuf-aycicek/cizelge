# Pencere formülasyonu deneyi

2026-10-14 17:32, veri/gercekci.json, süre 60 sn, 8 iş parçacığı, OR-Tools 9.15.6755, Python 3.14.7, Intel64 Family 6 Model 154 Stepping 3, GenuineIntel.

Gerçek ceza: bağımsız ölçümlerin ağırlıklı toplamı. Alt sınır: CP-SAT'ın o ana kadar kanıtladığı en iyi alt sınır (gerçek alt sınır en az 0).

## Mini sette doğruluk denetimi

| Varyant | Durum | Model ceza | Gerçek ceza | Doğrulama |
|---|---|---|---|---|
| C | OPTIMAL | 0 | 0 | geçti |

## Ölçüm: veri/gercekci.json

| Varyant | Tohum | Saniye | Gerçek ceza | Model ceza | Alt sınır | Sınıf boşluğu | Pencere | Bölünmüş | Tercih etmez | Eksik boş gün |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 0 | 10 | 1017 | 1100 | 0 | 0 | 231 | 104 | 0 | 29 |
| C | 0 | 30 | 720 | 724 | 0 | 0 | 164 | 62 | 0 | 26 |
| C | 0 | 60 | 501 | 501 | 0 | 0 | 109 | 39 | 0 | 24 |
| C | 1 | 10 | 951 | 1019 | 0 | 0 | 232 | 65 | 1 | 30 |
| C | 1 | 30 | 566 | 571 | 0 | 0 | 127 | 44 | 1 | 23 |
| C | 1 | 60 | 385 | 387 | 0 | 0 | 72 | 34 | 1 | 24 |
| C | 2 | 10 | 1030 | 1152 | 0 | 0 | 236 | 103 | 0 | 29 |
| C | 2 | 30 | 716 | 719 | 0 | 0 | 170 | 55 | 0 | 24 |
| C | 2 | 60 | 521 | 521 | 0 | 0 | 115 | 38 | 0 | 25 |

| Varyant | Tohum | İlk çözüm (sn) | Son alt sınır |
|---|---|---|---|
| C | 0 | 5.6 | 0 |
| C | 1 | 4.8 | 0 |
| C | 2 | 4.7 | 0 |
