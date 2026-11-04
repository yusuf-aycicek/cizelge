/** Seviye şablonu: dersler ve saatler, toplam ve kapasite, şubelere uygulama ve raporu. */
import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { bosRapor, dagilimApisiKur, SINIFLAR } from "../test/dagilimApisi";
import { uygulamayiCiz } from "../test/yardimcilar";

const SABLON_9 = [
  { id: "ss-mat", seviye: 9, sube_grubu_id: null, ders_id: "d-mat", haftalik_saat: 5 },
  { id: "ss-fiz", seviye: 9, sube_grubu_id: null, ders_id: "d-fiz", haftalik_saat: 3 },
];

const RAPOR = bosRapor({
  sube_sayisi: 3,
  subeler: ["9-A", "9-B", "9-C"],
  olusturulan: 4,
  zaten_var: 2,
  farkli_saatli: [
    { atama_id: "a-9b-mat", sinif: "9-B", ders: "Matematik", atamadaki_saat: 6, sablondaki_saat: 5 },
    { atama_id: "a-9c-mat", sinif: "9-C", ders: "Matematik", atamadaki_saat: 6, sablondaki_saat: 5 },
  ],
});

// 9-A ve 9-B "9 Fen" grubunda; grubun şablonunda yalnızca Kimya var.
const GRUP = { id: "g-fen", ad: "9 Fen", seviye: 9 };
const GRUPLU_SINIFLAR = SINIFLAR.map((s) => (s.id === "s-9a" || s.id === "s-9b" ? { ...s, sube_grubu_id: "g-fen" } : s));
const GRUP_SABLONU = [...SABLON_9, { id: "ss-g-kim", seviye: 9, sube_grubu_id: "g-fen", ders_id: "d-kim", haftalik_saat: 4 }];

describe("seviye şablonu", () => {
  it("seviyeler şube sayısıyla; şablonun dersleri Türkçe sıralı; toplam ve kapasite", async () => {
    dagilimApisiKur({ sablon: SABLON_9 });
    uygulamayiCiz("/seviye-sablonu");
    const seviye = await screen.findByRole("combobox", { name: "Şablon" });
    expect(within(seviye).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "9. sınıflar (3 şube)", "10. sınıflar (1 şube)",
    ]);
    // Okulun bütün dersleri alt alta; şablonda olmayanın kutusu boş.
    const tablo = screen.getByRole("table", { name: "9. sınıf şablonu" });
    expect(within(tablo).getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0]?.textContent))
      .toEqual(["Fizik", "Kimya", "Matematik"]);
    expect(within(tablo).getAllByRole("spinbutton").map((g) => (g as HTMLInputElement).value)).toEqual(["3", "", "5"]);
    expect(screen.getByText(/Haftalık toplam/)).toHaveTextContent("Haftalık toplam 8 saat; okulun haftalık kapasitesi 40 saat.");
  });

  it("toplam kapasiteyi aşınca uyarır", async () => {
    dagilimApisiKur({ sablon: [{ id: "ss-mat", seviye: 9, sube_grubu_id: null, ders_id: "d-mat", haftalik_saat: 41 }] });
    uygulamayiCiz("/seviye-sablonu?seviye=9");
    expect(await screen.findByText(/Haftalık toplam/)).toHaveTextContent(
      "Haftalık toplam 41 saat; okulun haftalık kapasitesi 40 saat. Bu şablonla şubelerin programı üretilemez.",
    );
  });

  it("saatler tabloda yazılır, toplam canlı güncellenir, tek seferde kaydedilir", async () => {
    const api = dagilimApisiKur({ sablon: SABLON_9 });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    const kaydet = await screen.findByRole("button", { name: "Şablonu kaydet" });
    expect(kaydet).toBeDisabled(); // değişiklik yok
    await kullanici.type(screen.getByRole("spinbutton", { name: "Kimya haftalık saat" }), "2");
    const mat = screen.getByRole("spinbutton", { name: "Matematik haftalık saat" });
    await kullanici.clear(mat);
    await kullanici.type(mat, "6");
    expect(screen.getByText(/Haftalık toplam/)).toHaveTextContent("Haftalık toplam 11 saat");
    expect(screen.getByRole("button", { name: "9. sınıf şubelerine uygula" })).toBeDisabled(); // önce kaydet
    expect(api.istekler).toEqual([]); // yazarken istek gitmez

    await kullanici.click(kaydet);
    expect(await screen.findByText("9. sınıf şablonu kaydedildi: 3 ders, haftada 11 saat.")).toBeInTheDocument();
    expect(api.istekler).toEqual([{ yontem: "PUT", yol: "seviye-sablonlari/toplu", govde: { seviye: 9, satirlar: [
      { ders_id: "d-fiz", haftalik_saat: 3 }, { ders_id: "d-kim", haftalik_saat: 2 }, { ders_id: "d-mat", haftalik_saat: 6 },
    ] } }]);
    await waitFor(() => expect(screen.getByRole("button", { name: "Şablonu kaydet" })).toBeDisabled());
  });

  it("geçersiz saat kaydedilmez; değişiklik geri alınır", async () => {
    const api = dagilimApisiKur({ sablon: SABLON_9 });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    const fiz = await screen.findByRole("spinbutton", { name: "Fizik haftalık saat" });
    await kullanici.clear(fiz);
    await kullanici.type(fiz, "1.5");
    await kullanici.click(screen.getByRole("button", { name: "Şablonu kaydet" }));
    expect(screen.getByText(/Haftalık saat 0 ile 99/)).toHaveTextContent("Haftalık saat 0 ile 99 arasında tam sayı olmalı: Fizik.");
    expect(api.istekler).toEqual([]);
    await kullanici.click(screen.getByRole("button", { name: "Değişiklikleri geri al" }));
    expect(fiz).toHaveValue(3);
  });

  it("başka seviyeden kopyalanır; hedef doluysa önce onay istenir", async () => {
    const sablon = [...SABLON_9, { id: "ss-10-kim", seviye: 10, sube_grubu_id: null, ders_id: "d-kim", haftalik_saat: 4 }];
    dagilimApisiKur({ sablon });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    const kaynak = await screen.findByRole("combobox", { name: "Başka şablondan kopyala" });
    expect(within(kaynak).getAllByRole("option").map((o) => o.textContent)).toEqual(["Şablon seçin", "10. sınıflar"]);
    await kullanici.selectOptions(kaynak, "10:");
    await kullanici.click(screen.getByRole("button", { name: "Kopyala" }));
    // 9. sınıf şablonu dolu: onay penceresi.
    const pencere = await screen.findByRole("dialog", { name: "9. sınıf şablonu dolu" });
    await kullanici.click(within(pencere).getByRole("button", { name: "Kopyala" }));
    const tablo = screen.getByRole("table", { name: "9. sınıf şablonu" });
    expect(within(tablo).getAllByRole("spinbutton").map((g) => (g as HTMLInputElement).value)).toEqual(["", "4", ""]);
    expect(screen.getByText(/Haftalık toplam/)).toHaveTextContent("Haftalık toplam 4 saat");
    expect(screen.getByRole("button", { name: "Şablonu kaydet" })).toBeEnabled();
  });

  it("boş şablona onaysız kopyalanır", async () => {
    dagilimApisiKur({ sablon: SABLON_9 });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=10");
    await kullanici.selectOptions(await screen.findByRole("combobox", { name: "Başka şablondan kopyala" }), "9:");
    await kullanici.click(screen.getByRole("button", { name: "Kopyala" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("spinbutton", { name: "Matematik haftalık saat" })).toHaveValue(5);
  });

  it("tüm seviyelere uygulanır; rapor şablon şablon", async () => {
    const api = dagilimApisiKur({
      sablon: SABLON_9,
      topluSonuc: [
        { seviye: 9, sube_grubu_id: null, sablon: "9. sınıflar", sonuc: bosRapor({ sube_sayisi: 3, subeler: ["9-A", "9-B", "9-C"], olusturulan: 4 }) },
        { seviye: 10, sube_grubu_id: null, sablon: "10. sınıflar", sonuc: bosRapor({ sube_sayisi: 1, subeler: ["10-A"], zaten_var: 2 }) },
      ],
    });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    await kullanici.click(await screen.findByRole("button", { name: "Tüm seviyelere uygula" }));
    const baslik = await screen.findByRole("heading", { name: "2 şablon uygulandı" });
    expect(baslik).toHaveFocus();
    const dokuz = screen.getByRole("region", { name: "9. sınıflar" });
    expect(dokuz).toHaveTextContent("3 şubeye toplam 4 ders eklendi (9-A, 9-B, 9-C).");
    expect(screen.getByRole("region", { name: "10. sınıflar" })).toHaveTextContent("Eklenecek yeni ders yoktu");
    expect(api.istekler).toEqual([{ yontem: "POST", yol: "seviye-sablonlari/uygula-hepsi", govde: undefined }]);
  });

  it("uygulama raporu anlaşılır gösterilir; farklı saat tek tıklamayla şablona çekilir", async () => {
    const api = dagilimApisiKur({ sablon: SABLON_9, uygulamaSonucu: RAPOR });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    expect(await screen.findByText(/3 şubeye \(9-A, 9-B, 9-C\) öğretmeni boş olarak eklenir/)).toBeInTheDocument();
    await kullanici.click(screen.getByRole("button", { name: "9. sınıf şubelerine uygula" }));

    const baslik = await screen.findByRole("heading", { name: "Şablon uygulandı" });
    expect(baslik).toHaveFocus(); // klavye ve ekran okuyucu kullanıcısı sonucu hemen duyar
    const rapor = baslik.parentElement!;
    expect(rapor).toHaveTextContent("3 şubeye toplam 4 ders eklendi (9-A, 9-B, 9-C). Öğretmenleri henüz seçilmedi.");
    expect(within(rapor).getByRole("link", { name: "Ders dağılımında öğretmen seçin" }))
      .toHaveAttribute("href", "/ders-dagilimi?gorunum=sube&sinif=s-9a");
    expect(rapor).toHaveTextContent("2 ders şubelerde zaten vardı; değiştirilmedi.");
    expect(rapor).toHaveTextContent("2 dersin saati şablondan farklı.");

    const farkli = within(rapor).getByRole("table", { name: "Saati şablondan farklı dersler" });
    const satir = within(farkli).getByRole("row", { name: /9-B/ });
    expect(within(satir).getAllByRole("cell").slice(0, 4).map((h) => h.textContent)).toEqual(["9-B", "Matematik", "6 saat", "5 saat"]);
    await kullanici.click(within(satir).getByRole("button", { name: "9-B Matematik: şablondaki 5 saati kullan" }));
    expect(await within(satir).findByText("✓ Güncellendi")).toBeInTheDocument();
    expect(api.istekler.slice(1)).toEqual([{ yontem: "PATCH", yol: "atamalar/a-9b-mat", govde: { haftalik_saat: 5 } }]);
    expect(api.istekler[0]).toEqual({ yontem: "POST", yol: "seviye-sablonlari/uygula", govde: { seviye: 9 } });
    // Diğer satır değişmedi.
    expect(within(farkli).getByRole("button", { name: "9-C Matematik: şablondaki 5 saati kullan" })).toBeInTheDocument();
  });

  it("eklenecek ders yoksa bunu söyler", async () => {
    dagilimApisiKur({ sablon: SABLON_9, uygulamaSonucu: bosRapor({ sube_sayisi: 3, zaten_var: 6 }) });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    await kullanici.click(await screen.findByRole("button", { name: "9. sınıf şubelerine uygula" }));
    const rapor = (await screen.findByRole("heading", { name: "Şablon uygulandı" })).parentElement!;
    expect(rapor).toHaveTextContent("Eklenecek yeni ders yoktu: şablondaki derslerin hepsi şubelerde zaten var.");
    expect(rapor).toHaveTextContent("6 ders şubelerde zaten vardı; değiştirilmedi.");
    expect(within(rapor).queryByRole("table")).not.toBeInTheDocument();
  });

  it("şablon seviyeye ya da gruba ait; grubun şubeleri seviyenin şablonundan ayrılır", async () => {
    dagilimApisiKur({ sablon: GRUP_SABLONU, siniflar: GRUPLU_SINIFLAR, gruplar: [GRUP] });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    const secim = await screen.findByRole("combobox", { name: "Şablon" });
    expect(within(secim).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "9. sınıflar (1 şube)", "9 Fen grubu (2 şube)", "10. sınıflar (1 şube)",
    ]);
    expect(screen.getByText(/Bu şablon/)).toHaveTextContent(
      "Bu şablon 9. sınıflara ait. 9-A (9 Fen), 9-B (9 Fen) kendi grubunun şablonunu kullanır.");
    expect(screen.getByText(/1 şubeye \(9-C\) öğretmeni boş olarak eklenir/)).toBeInTheDocument();

    await kullanici.selectOptions(secim, "9:g-fen");
    expect(await screen.findByRole("heading", { name: "9 Fen grubunun dersleri" })).toBeInTheDocument();
    expect(screen.getByRole("spinbutton", { name: "Kimya haftalık saat" })).toHaveValue(4);
    expect(screen.getByRole("spinbutton", { name: "Matematik haftalık saat" })).toHaveValue(null);
    expect(screen.getByText(/Bu şablon/)).toHaveTextContent("Bu şablon 9 Fen grubuna ait (9-A, 9-B).");
    expect(screen.getByRole("button", { name: "9 Fen şubelerine uygula" })).toBeEnabled();
  });

  it("gruba ders eklenir ve grubun şablonu grubun şubelerine uygulanır; rapor istisnaları söyler", async () => {
    const api = dagilimApisiKur({
      sablon: GRUP_SABLONU, siniflar: GRUPLU_SINIFLAR, gruplar: [GRUP],
      uygulamaSonucu: bosRapor({
        sube_sayisi: 2, subeler: ["9-A", "9-B"], olusturulan: 1, zaten_var: 0,
        istisna_atlanan: [{ sinif: "9-B", ders: "Kimya" }],
        istisna_ek: [{ sinif: "9-A", ders: "Fizik", haftalik_saat: 2, eklendi: false }],
        baska_sablonlu: [{ sinif: "9-C", sablon: "9. sınıflar" }],
      }),
    });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9&grup=g-fen");
    await kullanici.type(await screen.findByRole("spinbutton", { name: "Matematik haftalık saat" }), "6");
    await kullanici.click(screen.getByRole("button", { name: "Şablonu kaydet" }));
    expect(await screen.findByText("9 Fen grubunun şablonu kaydedildi: 2 ders, haftada 10 saat.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "9 Fen şubelerine uygula" })).toBeEnabled());
    await kullanici.click(screen.getByRole("button", { name: "9 Fen şubelerine uygula" }));
    const rapor = (await screen.findByRole("heading", { name: "Şablon uygulandı" })).parentElement!;
    expect(rapor).toHaveTextContent("Şubenin almadığı 1 ders eklenmedi (istisna): 9-B Kimya.");
    expect(rapor).toHaveTextContent("Şubelerin ek dersleri: 9-A Fizik (2 saat).");
    expect(rapor).toHaveTextContent("Kendi şablonunu kullandığı için dokunulmayan şubeler: 9-C (9. sınıflar).");
    expect(api.istekler).toEqual([
      { yontem: "PUT", yol: "seviye-sablonlari/toplu", govde: { seviye: 9, sube_grubu_id: "g-fen", satirlar: [
        { ders_id: "d-fiz", haftalik_saat: 0 }, { ders_id: "d-kim", haftalik_saat: 4 }, { ders_id: "d-mat", haftalik_saat: 6 },
      ] } },
      { yontem: "POST", yol: "seviye-sablonlari/uygula", govde: { seviye: 9, sube_grubu_id: "g-fen" } },
    ]);
  });

  it("grubun şablonu boşken grubun şubeleri seviyenin şablonunu kullanır", async () => {
    dagilimApisiKur({ sablon: SABLON_9, siniflar: GRUPLU_SINIFLAR, gruplar: [GRUP] });
    const { kullanici } = uygulamayiCiz("/seviye-sablonu?seviye=9");
    const secim = await screen.findByRole("combobox", { name: "Şablon" });
    expect(within(secim).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "9. sınıflar (3 şube)", "9 Fen grubu (2 şube)", "10. sınıflar (1 şube)",
    ]);
    expect(screen.getByText(/3 şubeye \(9-A, 9-B, 9-C\) öğretmeni boş olarak eklenir/)).toBeInTheDocument();
    await kullanici.selectOptions(secim, "9:g-fen");
    expect(await screen.findByText(/Şablon boşken grubun şubeleri 9. sınıfların şablonunu kullanır/)).toBeInTheDocument();
  });

  it("şablon boşken uygulanamaz", async () => {
    dagilimApisiKur({ sablon: [] });
    uygulamayiCiz("/seviye-sablonu?seviye=9");
    expect(await screen.findByRole("button", { name: "9. sınıf şubelerine uygula" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Tüm seviyelere uygula" })).toBeDisabled();
    expect(screen.queryByRole("combobox", { name: "Başka şablondan kopyala" })).not.toBeInTheDocument();
  });
});
