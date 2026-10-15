"""Kuyruk işçisi: kuyruktaki işleri çalıştıran genel süreç (ADR 0011 madde 2).

Hiçbir modülü bilmez. İşler, kuyruğa konurken Python yoluyla adlandırılır
(ör. okulapi.moduller.ders_programi.uretim.uretim_isi); worker yalnızca onları çalıştırır.
Yeni bir modülün arka plan işi bu paketi değiştirmeyi gerektirmez.
"""
