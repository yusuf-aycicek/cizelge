/**
 * Ortak bileşenler. Testing Library sayfayı kullanıcının gördüğü gibi sorgular: rol ve
 * erişilebilir ad ("Kaydet" adlı düğme). Bileşen erişilebilir değilse test onu bulamaz.
 */
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { MetinAlani } from "./Alan";
import { BildirimSaglayici, KAYBOLMA_MS, useBildirim, type BildirimTuru } from "./Bildirim";
import { Dugme } from "./Dugme";
import { OnayPenceresi } from "./OnayPenceresi";
import { Tablo } from "./Tablo";

describe("Dugme", () => {
  it("varsayılan olarak formu göndermez ve klavyeyle çalışır", async () => {
    const kullanici = userEvent.setup();
    const tikla = vi.fn();
    const gonder = vi.fn((olay: { preventDefault: () => void }) => olay.preventDefault());
    render(
      <form onSubmit={gonder}>
        <Dugme onClick={tikla}>Kaydet</Dugme>
      </form>,
    );
    const dugme = screen.getByRole("button", { name: "Kaydet" });
    expect(dugme).toHaveAttribute("type", "button");
    await kullanici.tab();
    expect(dugme).toHaveFocus();
    await kullanici.keyboard("{Enter}");
    await kullanici.keyboard(" ");
    expect(tikla).toHaveBeenCalledTimes(2);
    expect(gonder).not.toHaveBeenCalled();
  });

  it("yüklenirken kilitlenir ve ne yaptığını söyler", async () => {
    const tikla = vi.fn();
    render(
      <Dugme yukleniyor yukleniyorMetni="Kaydediliyor..." onClick={tikla}>
        Kaydet
      </Dugme>,
    );
    const dugme = screen.getByRole("button", { name: "Kaydediliyor..." });
    expect(dugme).toBeDisabled();
    expect(dugme).toHaveAttribute("aria-busy", "true");
    await userEvent.click(dugme);
    expect(tikla).not.toHaveBeenCalled();
  });
});

describe("MetinAlani", () => {
  it("etiket, açıklama ve hata denetime bağlıdır", () => {
    render(<MetinAlani etiket="E-posta" aciklama="Giriş yaparken kullanılır." hata="Geçerli bir e-posta girin" gerekli />);
    // getByLabelText: etiket gerçekten denetime bağlı değilse bulamaz.
    const alan = screen.getByLabelText(/E-posta/);
    expect(alan).toBeRequired();
    expect(alan).toHaveAttribute("aria-invalid", "true");
    expect(alan).toHaveAccessibleDescription("Geçerli bir e-posta girin Giriş yaparken kullanılır.");
  });

  it("hata yoksa alan geçerli işaretlenir", () => {
    render(<MetinAlani etiket="Ad" />);
    const alan = screen.getByRole("textbox", { name: "Ad" });
    expect(alan).not.toHaveAttribute("aria-invalid");
    expect(alan).not.toHaveAccessibleDescription();
  });

  it("etikete tıklamak alana odaklar", async () => {
    render(<MetinAlani etiket="Ad" />);
    await userEvent.click(screen.getByText("Ad"));
    expect(screen.getByRole("textbox", { name: "Ad" })).toHaveFocus();
  });

  it("parola alanında yazılan klavyeyle gösterilip gizlenir", async () => {
    const kullanici = userEvent.setup();
    render(<MetinAlani etiket="Parola" type="password" />);
    const alan = screen.getByLabelText("Parola");
    expect(alan).toHaveAttribute("type", "password");
    await kullanici.tab();
    await kullanici.tab();
    const goz = screen.getByRole("button", { name: "Yazılanı göster" });
    expect(goz).toHaveFocus();
    await kullanici.keyboard("{Enter}");
    expect(alan).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Yazılanı gizle" })).toBeInTheDocument();
    await kullanici.keyboard("{Enter}");
    expect(alan).toHaveAttribute("type", "password");
  });
});

describe("Tablo", () => {
  type Satir = { id: string; ad: string; saat: number };
  const sutunlar = [
    { baslik: "Ad", hucre: (s: Satir) => s.ad },
    { baslik: "Saat", hucre: (s: Satir) => s.saat, hizala: "sag" as const },
  ];

  it("başlıkları ve satırları gösterir, adıyla bulunur", () => {
    render(
      <Tablo baslik="Öğretmenler" sutunlar={sutunlar} satirAnahtari={(s) => s.id}
        satirlar={[{ id: "1", ad: "Ayşe", saat: 18 }, { id: "2", ad: "Mehmet", saat: 15 }]} />,
    );
    const tablo = screen.getByRole("table", { name: "Öğretmenler" });
    expect(within(tablo).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Ad", "Saat"]);
    expect(within(tablo).getAllByRole("row")).toHaveLength(3);
    expect(within(tablo).getByRole("cell", { name: "Mehmet" })).toBeInTheDocument();
  });

  it("boşken mesaj gösterir", () => {
    render(<Tablo baslik="Öğretmenler" sutunlar={sutunlar} satirAnahtari={(s) => s.id} satirlar={[]} bosMesaj="Henüz öğretmen yok." />);
    expect(screen.getByRole("cell", { name: "Henüz öğretmen yok." })).toBeInTheDocument();
  });
});

function BildirimDenemesi({ tur, mesaj }: { tur: BildirimTuru; mesaj: string }) {
  const goster = useBildirim();
  return <Dugme onClick={() => goster(tur, mesaj)}>Göster</Dugme>;
}

describe("Bildirim", () => {
  it("başarı nazik bölgede görünür ve kendiliğinden kaybolur", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const kullanici = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <BildirimSaglayici>
        <BildirimDenemesi tur="basari" mesaj="Öğretmen kaydedildi." />
      </BildirimSaglayici>,
    );
    await kullanici.click(screen.getByRole("button", { name: "Göster" }));
    expect(within(screen.getByRole("status")).getByText("Öğretmen kaydedildi.")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(KAYBOLMA_MS + 10));
    expect(screen.queryByText("Öğretmen kaydedildi.")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("hata acil bölgede görünür, kendiliğinden kaybolmaz, kapatılabilir", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const kullanici = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <BildirimSaglayici>
        <BildirimDenemesi tur="hata" mesaj="Kaydedilemedi." />
      </BildirimSaglayici>,
    );
    await kullanici.click(screen.getByRole("button", { name: "Göster" }));
    expect(within(screen.getByRole("alert")).getByText("Kaydedilemedi.")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(KAYBOLMA_MS * 3));
    expect(screen.getByText("Kaydedilemedi.")).toBeInTheDocument();
    await kullanici.click(screen.getByRole("button", { name: "Bildirimi kapat" }));
    expect(screen.queryByText("Kaydedilemedi.")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("sağlayıcı olmadan kullanılırsa anlaşılır hata verir", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<BildirimDenemesi tur="bilgi" mesaj="x" />)).toThrow(/BildirimSaglayici/);
    vi.restoreAllMocks();
  });
});

function PencereDenemesi({ onOnayla }: { onOnayla: () => void }) {
  const [acik, setAcik] = useState(false);
  return (
    <>
      <Dugme onClick={() => setAcik(true)}>Sil...</Dugme>
      <OnayPenceresi acik={acik} baslik="Ayşe Yılmaz silinsin mi?" mesaj="Bu işlem geri alınamaz." onaylaMetni="Sil" tehlikeli
        onVazgec={() => setAcik(false)} onOnayla={() => { onOnayla(); setAcik(false); }} />
    </>
  );
}

describe("OnayPenceresi", () => {
  it("açılınca odak Vazgeç'te; Esc kapatır ve hiçbir şey olmaz", async () => {
    const kullanici = userEvent.setup();
    const onayla = vi.fn();
    render(<PencereDenemesi onOnayla={onayla} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await kullanici.click(screen.getByRole("button", { name: "Sil..." }));
    const pencere = screen.getByRole("dialog", { name: "Ayşe Yılmaz silinsin mi?" });
    expect(pencere).toHaveAccessibleDescription("Bu işlem geri alınamaz.");
    expect(within(pencere).getByRole("button", { name: "Vazgeç" })).toHaveFocus();

    // Esc: tarayıcı "cancel" olayı gönderir (jsdom'da elle).
    act(() => {
      pencere.dispatchEvent(new Event("cancel", { cancelable: true }));
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(onayla).not.toHaveBeenCalled();
  });

  it("Sil onaylar", async () => {
    const kullanici = userEvent.setup();
    const onayla = vi.fn();
    render(<PencereDenemesi onOnayla={onayla} />);
    await kullanici.click(screen.getByRole("button", { name: "Sil..." }));
    await kullanici.click(screen.getByRole("button", { name: "Sil" }));
    expect(onayla).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
