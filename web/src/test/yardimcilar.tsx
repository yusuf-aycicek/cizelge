import type { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { sorguIstemcisiOlustur } from "../sorgu";
import { Uygulama } from "../Uygulama";

/** Uygulamanın kendi sorgu istemcisi (oturum süresi dinleyicileriyle), yeniden denemesiz:
 * hata durumu hemen görünsün. */
export function testSorguIstemcisi(): QueryClient {
  return sorguIstemcisiOlustur(false);
}

/** Uygulamanın tamamını verilen adreste çizer. `kullanici`: gerçekçi tıklama ve klavye. */
export function uygulamayiCiz(adres = "/") {
  const kullanici = userEvent.setup();
  const sonuc = render(
    <MemoryRouter initialEntries={[adres]}>
      <Uygulama sorguIstemcisi={testSorguIstemcisi()} />
    </MemoryRouter>,
  );
  return { kullanici, ...sonuc };
}

/** Üst çubuktaki hesap menüsünü (baş harfli düğme) açar; Hesabım ve Çıkış oradadır. */
export async function hesapMenusunuAc(kullanici: ReturnType<typeof userEvent.setup>) {
  await kullanici.click(await screen.findByRole("button", { name: /^Hesap: / }));
}

/** Hesap menüsünden çıkış yapar. */
export async function cikisYap(kullanici: ReturnType<typeof userEvent.setup>) {
  await hesapMenusunuAc(kullanici);
  await kullanici.click(screen.getByRole("button", { name: "Çıkış" }));
}
