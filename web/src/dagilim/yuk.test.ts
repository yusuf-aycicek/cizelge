/** Öğretmen yükü metni: kullanılabilir saat ve boş gün hedefiyle yaklaşık kapasite. */
import { describe, expect, it } from "vitest";
import { yukMetni } from "./veri";

describe("yük metni", () => {
  it("hedef kapasiteyi daraltıyorsa yaklaşık hedefli kapasiteyi de söyler", () => {
    expect(yukMetni({ ders_saati: 8, kullanilabilir_saat: 35, hedefli_kapasite: 21 })).toBe("8 / 35 saat · hedefle ~21");
  });

  it("hedef yoksa ya da daraltmıyorsa yalnızca kullanılabilir saat", () => {
    expect(yukMetni({ ders_saati: 8, kullanilabilir_saat: 35 })).toBe("8 / 35 saat");
    expect(yukMetni({ ders_saati: 8, kullanilabilir_saat: 35, hedefli_kapasite: null })).toBe("8 / 35 saat");
    expect(yukMetni({ ders_saati: 8, kullanilabilir_saat: 20, hedefli_kapasite: 20 })).toBe("8 / 20 saat");
  });
});
