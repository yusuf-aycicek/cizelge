# Gerçekçi set gösterimleri (veri/gercekci.json)

## (2) Haftalık program (60 sn, durum uygun, ceza 529)

Ölçüler: sınıf boşluğu 0, pencere 109, bölünmüş 46, tercih etmez 1, eksik boş gün 25

### 9-A

```
Saat | Pazartesi     | Salı          | Çarşamba      | Perşembe      | Cuma         
------------------------------------------------------------------------------------
   1 | DIN S.Yılmaz  | KIM H.Koç     | TDE M.Özdemir | TDE M.Özdemir | KIM H.Koç    
   2 | COG G.Öztürk  | BIY A.Şahin   | TDE M.Özdemir | REH F.Kara    | BED E.Kara   
   3 | BED E.Kara    | GOR A.Kurt    | COG G.Öztürk  | FIZ M.Erdoğan | FIZ M.Erdoğan
   4 | SEC M.Şimşek  | ALM B.Çetin   | MAT İ.Kurt    | MAT İ.Kurt    | MAT İ.Kurt   
   5 | SEC M.Şimşek  | MAT İ.Kurt    | MAT İ.Kurt    | DIN S.Yılmaz  | TDE M.Özdemir
   6 | TDE M.Özdemir | MAT İ.Kurt    | ING A.Yılmaz  | ALM B.Çetin   | ING A.Yılmaz 
   7 | MUZ A.Kurt    | TAR H.Yılmaz  | TAR H.Yılmaz  | SEC M.Şimşek  | SEC M.Şimşek 
   8 | ING A.Yılmaz  | ING A.Yılmaz  | BIY A.Şahin   | SEC M.Şimşek  | SEC M.Şimşek 
```

### Volkan Kara (Edebiyat, 25 saat, 5 gün)

```
Saat | Pazartesi      | Salı           | Çarşamba       | Perşembe       | Cuma          
-----------------------------------------------------------------------------------------
   1 | ·              | 12-F TDE       | ·              | ·              | 10-F TDE      
   2 | ·              | 10-F TDE       | gelemez        | ·              | ·             
   3 | 11-F TDE       | 10-F TDE       | 9-F TDE        | ·              | ·             
   4 | 12-F TDE       | ·              | 11-F TDE       | 9-F TDE        | 11-F TDE      
   5 | 12-F TDE       | ·              | 12-F TDE       | 9-F TDE        | ·             
   6 | (tercih etmez) | 10-B TDE       | 10-B TDE       | 10-F TDE       | 10-B TDE      
   7 | (tercih etmez) | 9-F TDE        | 10-F TDE       | 11-F TDE       | 10-B TDE      
   8 | gelemez        | 9-F TDE        | 10-B TDE       | 11-F TDE       | 12-F TDE      
```

## (3) En az değişiklik: Burak Çetin artık Çarşamba gelemiyor

Temel programda o gün 8 dersi var (en az 8 ders yer değiştirmek zorunda). Toplam 936 ders saati.

| Yöntem | Süre sınırı | Değişen ders saati | İlk çözüm | Durum | Ölçüler |
|---|---|---|---|---|---|
| Temel programla | 10 sn | 49 | 8.1 sn | uygun | sınıf boşluğu 0, pencere 130, bölünmüş 47, tercih etmez 7, eksik boş gün 27 |
| Temel programla | 60 sn | 16 | 7.1 sn | optimal | sınıf boşluğu 0, pencere 112, bölünmüş 48, tercih etmez 1, eksik boş gün 26 |
| Sıfırdan | 60 sn | 829 | 6.2 sn | uygun | sınıf boşluğu 0, pencere 76, bölünmüş 38, tercih etmez 0, eksik boş gün 27 |

## (4) Çözümsüz örnek: 9-A (40 saat, tam dolu), 14 öğretmeninin hepsi Pazartesi 1. saatte gelemez

Ön kontrol: geçti (bu çelişkiyi yakalayamaz)

Durum: bilinmiyor. Toplam 61.6 sn = çözümsüzlük kanıtı 61.6 sn + çelişki analizi 0.0 sn (analiz bütçesi 30 sn).

