import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { Uygulama } from "../Uygulama";

/** Testte yeniden deneme yok: hata durumu hemen görünsün. */
export function testSorguIstemcisi(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
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
